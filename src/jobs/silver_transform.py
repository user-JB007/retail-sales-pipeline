"""Silver layer: clean, conform, and enforce data quality.

- Type casting and column standardization
- Drop / quarantine invalid rows (negative qty, null amounts, orphan store refs)
- Enrich transactions with product cost and derived metrics
- Write cleaned parquet + quarantine parquet + DQ report
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.quality.checks import (
    check_no_nulls,
    check_not_empty,
    check_positive,
    check_referential,
    check_unique,
    check_value_in_set,
    print_check_report,
    run_checks,
)
from src.utils.paths import bronze_dir, project_root, silver_dir
from src.utils.spark_session import get_spark


ALLOWED_CHANNELS = {"in_store", "online", "mobile_app"}
ALLOWED_PAYMENTS = {"credit_card", "debit_card", "cash", "mobile_pay", "gift_card"}


def _read_bronze_table(bronze: Path, table: str) -> pd.DataFrame:
    path = bronze / table
    parquet_file = path / "data.parquet"
    if parquet_file.exists():
        return pd.read_parquet(parquet_file)
    # Spark writes directory of part files
    if path.exists() and any(path.glob("*.parquet")):
        return pd.read_parquet(path)
    raise FileNotFoundError(f"Bronze table not found: {path}")


def transform_dims(bronze: Path) -> dict[str, pd.DataFrame]:
    stores = _read_bronze_table(bronze, "stores")
    products = _read_bronze_table(bronze, "products")
    customers = _read_bronze_table(bronze, "customers")

    meta_cols = [c for c in stores.columns if c.startswith("_")]
    stores = stores.drop(columns=meta_cols, errors="ignore")
    products = products.drop(columns=[c for c in products.columns if c.startswith("_")], errors="ignore")
    customers = customers.drop(columns=[c for c in customers.columns if c.startswith("_")], errors="ignore")

    stores["opened_date"] = pd.to_datetime(stores["opened_date"])
    products["unit_cost"] = products["unit_cost"].astype(float)
    products["unit_price"] = products["unit_price"].astype(float)
    customers["signup_date"] = pd.to_datetime(customers["signup_date"])
    customers["email"] = customers["email"].str.lower().str.strip()

    # Active-only dims for analytics (inactive kept in bronze)
    stores_s = stores[stores["is_active"] == True].copy()  # noqa: E712
    products_s = products[products["is_active"] == True].copy()  # noqa: E712
    customers_s = customers[customers["is_active"] == True].copy()  # noqa: E712

    return {
        "dim_store": stores_s,
        "dim_product": products_s,
        "dim_customer": customers_s,
        "dim_store_all": stores,
        "dim_product_all": products,
        "dim_customer_all": customers,
    }


def transform_fact(bronze: Path, dims: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    txns = _read_bronze_table(bronze, "sales_transactions")
    txns = txns.drop(columns=[c for c in txns.columns if c.startswith("_")], errors="ignore")

    txns["transaction_ts"] = pd.to_datetime(txns["transaction_ts"])
    txns["transaction_date"] = txns["transaction_ts"].dt.date.astype(str)
    txns["quantity"] = pd.to_numeric(txns["quantity"], errors="coerce")
    txns["unit_price"] = pd.to_numeric(txns["unit_price"], errors="coerce")
    txns["discount_pct"] = pd.to_numeric(txns["discount_pct"], errors="coerce").fillna(0.0)
    txns["discount_amount"] = pd.to_numeric(txns["discount_amount"], errors="coerce")
    txns["net_amount"] = pd.to_numeric(txns["net_amount"], errors="coerce")

    # Recalculate net when missing but components present
    missing_net = txns["net_amount"].isna()
    txns.loc[missing_net, "net_amount"] = (
        txns.loc[missing_net, "unit_price"] * txns.loc[missing_net, "quantity"]
        - txns.loc[missing_net, "discount_amount"].fillna(0)
    ).round(2)

    quarantine_mask = (
        txns["quantity"].isna()
        | (txns["quantity"] <= 0)
        | txns["net_amount"].isna()
        | (txns["net_amount"] < 0)
        | (~txns["store_id"].isin(dims["dim_store_all"]["store_id"]))
        | (~txns["product_id"].isin(dims["dim_product_all"]["product_id"]))
        | (~txns["channel"].isin(ALLOWED_CHANNELS))
        | (~txns["payment_method"].isin(ALLOWED_PAYMENTS))
    )
    quarantine = txns[quarantine_mask].copy()
    quarantine["quarantine_reason"] = "invalid_qty_amount_or_fk"
    clean = txns[~quarantine_mask].copy()

    # Guest customers: fill unknown
    clean["customer_id"] = clean["customer_id"].fillna("CUS00000")

    # Enrich with product cost for margin
    prod = dims["dim_product_all"][["product_id", "unit_cost", "category", "subcategory", "brand"]]
    clean = clean.merge(prod, on="product_id", how="left")
    clean["gross_amount"] = (clean["unit_price"] * clean["quantity"]).round(2)
    clean["cogs"] = (clean["unit_cost"] * clean["quantity"]).round(2)
    clean["gross_profit"] = (clean["net_amount"] - clean["cogs"]).round(2)
    clean["gross_margin_pct"] = (
        (clean["gross_profit"] / clean["net_amount"].replace(0, pd.NA)) * 100
    ).round(2)

    return clean, quarantine



def transform_service_tickets(bronze: Path, dims: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Clean service tickets and derive SLA / aging metrics."""
    tix = _read_bronze_table(bronze, "service_tickets")
    tix = tix.drop(columns=[c for c in tix.columns if c.startswith("_")], errors="ignore")
    tix["opened_at"] = pd.to_datetime(tix["opened_at"])
    tix["sla_due_at"] = pd.to_datetime(tix["sla_due_at"])
    tix["resolved_at"] = pd.to_datetime(tix["resolved_at"], errors="coerce")
    tix["csat"] = pd.to_numeric(tix["csat"], errors="coerce")
    tix["resolve_hours"] = pd.to_numeric(tix["resolve_hours"], errors="coerce")

    as_of = tix["opened_at"].max() + pd.Timedelta(days=1)
    open_mask = tix["status"].isin(["pending", "escalated"]) | tix["resolved_at"].isna()
    tix["is_open"] = open_mask.astype(int)
    tix["age_hours"] = (
        (tix["resolved_at"].fillna(as_of) - tix["opened_at"]).dt.total_seconds() / 3600
    ).round(2)
    tix["sla_breach"] = (
        (~open_mask & (tix["resolved_at"] > tix["sla_due_at"]))
        | (open_mask & (as_of > tix["sla_due_at"]))
    )
    tix["sla_status"] = "within_sla"
    tix.loc[tix["sla_breach"], "sla_status"] = "beyond_sla"
    tix.loc[open_mask & ~tix["sla_breach"], "sla_status"] = "pending_within_sla"
    tix.loc[open_mask & tix["sla_breach"], "sla_status"] = "pending_beyond_sla"
    tix["opened_date"] = tix["opened_at"].dt.date.astype(str)

    # Keep only tickets with known stores when possible
    valid_stores = set(dims["dim_store_all"]["store_id"])
    tix = tix[tix["store_id"].isin(valid_stores)].copy()
    return tix


def run_dq(dims: dict[str, pd.DataFrame], fact: pd.DataFrame) -> dict:
    checks = [
        check_not_empty(fact, "fact_not_empty"),
        check_unique(fact, ["transaction_id"], "fact_pk_unique"),
        check_no_nulls(fact, ["transaction_id", "store_id", "product_id", "quantity", "net_amount"], "fact_required_nulls"),
        check_positive(fact, "quantity"),
        check_positive(fact, "net_amount"),
        check_referential(fact, dims["dim_store_all"], "store_id", "store_id", "fk_store"),
        check_referential(fact, dims["dim_product_all"], "product_id", "product_id", "fk_product"),
        check_value_in_set(fact, "channel", ALLOWED_CHANNELS),
        check_value_in_set(fact, "payment_method", ALLOWED_PAYMENTS),
        check_unique(dims["dim_store"], ["store_id"], "store_pk"),
        check_unique(dims["dim_product"], ["product_id"], "product_pk"),
        check_unique(dims["dim_customer"], ["customer_id"], "customer_pk"),
    ]
    summary = run_checks(checks, raise_on_fail=True)
    print_check_report(summary)
    return summary


def run(engine: str = "auto") -> dict:
    # Engine flag reserved for Spark parity; transforms use pandas for portability.
    # Structure mirrors Spark job boundaries (read bronze -> transform -> write silver).
    _ = engine
    bronze = bronze_dir()
    silver = silver_dir()
    silver.mkdir(parents=True, exist_ok=True)

    dims = transform_dims(bronze)
    fact, quarantine = transform_fact(bronze, dims)
    service = transform_service_tickets(bronze, dims)
    dq = run_dq(dims, fact)

    for name, df in [
        ("dim_store", dims["dim_store"]),
        ("dim_product", dims["dim_product"]),
        ("dim_customer", dims["dim_customer"]),
        ("fact_sales", fact),
        ("quarantine_sales", quarantine),
        ("fact_service_tickets", service),
    ]:
        out = silver / name
        out.mkdir(parents=True, exist_ok=True)
        path = out / "data.parquet"
        df.to_parquet(path, index=False)
        print(f"[silver] {name}: {len(df)} rows -> {path}")

    manifest = {
        "layer": "silver",
        "fact_rows": len(fact),
        "service_ticket_rows": len(service),
        "quarantine_rows": len(quarantine),
        "dq": dq,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    (silver / "_manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
    print(f"Silver transform complete. Quarantined {len(quarantine)} rows. Service tickets: {len(service)}.")
    return manifest


def main():
    import sys
    root = str(project_root())
    if root not in sys.path:
        sys.path.insert(0, root)
    parser = argparse.ArgumentParser(description="Silver transform job")
    parser.add_argument("--engine", choices=["auto", "spark", "pandas"], default="auto")
    args = parser.parse_args()
    run(args.engine)


if __name__ == "__main__":
    main()
