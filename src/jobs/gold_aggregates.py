"""Gold layer: business-ready marts for analytics and BI.

Marts:
  - mart_daily_sales_by_store
  - mart_daily_sales_by_category
  - mart_customer_lifetime_value
  - mart_product_performance
  - mart_channel_mix
  - mart_service_performance
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.quality.checks import check_not_empty, check_no_nulls, print_check_report, run_checks
from src.utils.paths import gold_dir, project_root, silver_dir


def _read_silver(name: str) -> pd.DataFrame:
    path = silver_dir() / name / "data.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Missing silver table: {path}. Run silver job first.")
    return pd.read_parquet(path)


def build_marts() -> dict[str, pd.DataFrame]:
    fact = _read_silver("fact_sales")
    stores = _read_silver("dim_store")
    products = _read_silver("dim_product")
    customers = _read_silver("dim_customer")

    fact = fact.merge(stores[["store_id", "store_name", "region", "store_type"]], on="store_id", how="left")
    # category already on fact from silver enrichment; ensure present
    if "category" not in fact.columns:
        fact = fact.merge(products[["product_id", "category", "brand"]], on="product_id", how="left")

    daily_store = (
        fact.groupby(["transaction_date", "store_id", "store_name", "region", "store_type"], as_index=False)
        .agg(
            transactions=("transaction_id", "nunique"),
            units_sold=("quantity", "sum"),
            gross_revenue=("gross_amount", "sum"),
            net_revenue=("net_amount", "sum"),
            discount_total=("discount_amount", "sum"),
            cogs=("cogs", "sum"),
            gross_profit=("gross_profit", "sum"),
        )
    )
    daily_store["avg_order_value"] = (daily_store["net_revenue"] / daily_store["transactions"]).round(2)
    daily_store["gross_margin_pct"] = (
        (daily_store["gross_profit"] / daily_store["net_revenue"].replace(0, pd.NA)) * 100
    ).round(2)

    daily_category = (
        fact.groupby(["transaction_date", "category"], as_index=False)
        .agg(
            transactions=("transaction_id", "nunique"),
            units_sold=("quantity", "sum"),
            net_revenue=("net_amount", "sum"),
            gross_profit=("gross_profit", "sum"),
        )
    )

    # Guest customer rows excluded from CLV
    clv_base = fact[fact["customer_id"] != "CUS00000"]
    clv = (
        clv_base.groupby("customer_id", as_index=False)
        .agg(
            first_purchase=("transaction_date", "min"),
            last_purchase=("transaction_date", "max"),
            order_count=("transaction_id", "nunique"),
            lifetime_revenue=("net_amount", "sum"),
            lifetime_profit=("gross_profit", "sum"),
            avg_order_value=("net_amount", "mean"),
        )
    )
    clv["avg_order_value"] = clv["avg_order_value"].round(2)
    clv = clv.merge(customers[["customer_id", "loyalty_tier", "state"]], on="customer_id", how="left")

    product_perf = (
        fact.groupby(["product_id", "category", "brand"], as_index=False)
        .agg(
            units_sold=("quantity", "sum"),
            net_revenue=("net_amount", "sum"),
            gross_profit=("gross_profit", "sum"),
            order_count=("transaction_id", "nunique"),
        )
        .sort_values("net_revenue", ascending=False)
    )
    product_perf = product_perf.merge(
        products[["product_id", "product_name", "unit_price"]], on="product_id", how="left"
    )

    channel_mix = (
        fact.groupby(["transaction_date", "channel", "payment_method"], as_index=False)
        .agg(
            transactions=("transaction_id", "nunique"),
            net_revenue=("net_amount", "sum"),
        )
    )

    # Service / CSAT performance mart
    service = _read_silver("fact_service_tickets")
    store_lookup = stores[["store_id", "store_name", "store_type"]].drop_duplicates("store_id")
    service = service.merge(store_lookup, on="store_id", how="left")
    keep_cols = [
        c for c in [
            "ticket_id", "opened_at", "resolved_at", "sla_due_at", "opened_date",
            "status", "priority", "reason", "channel", "store_id", "store_name",
            "region", "customer_id", "csat", "resolve_hours", "age_hours",
            "is_open", "sla_breach", "sla_status",
        ] if c in service.columns
    ]
    service_perf = service[keep_cols].copy()

    return {
        "mart_daily_sales_by_store": daily_store,
        "mart_daily_sales_by_category": daily_category,
        "mart_customer_lifetime_value": clv,
        "mart_product_performance": product_perf,
        "mart_channel_mix": channel_mix,
        "mart_service_performance": service_perf,
    }


def run(engine: str = "auto") -> dict:
    _ = engine
    gold = gold_dir()
    gold.mkdir(parents=True, exist_ok=True)
    marts = build_marts()

    checks = []
    for name, df in marts.items():
        checks.append(check_not_empty(df, f"{name}_not_empty"))
    dq = run_checks(checks, raise_on_fail=True)
    print_check_report(dq)

    results = {}
    for name, df in marts.items():
        out = gold / name
        out.mkdir(parents=True, exist_ok=True)
        path = out / "data.parquet"
        df.to_parquet(path, index=False)
        # Also CSV for easy BI / spreadsheet inspection
        csv_path = out / "data.csv"
        df.to_csv(csv_path, index=False)
        results[name] = {"rows": len(df), "path": str(path)}
        print(f"[gold] {name}: {len(df)} rows -> {path}")

    # Preview summary for ops review
    top_stores = (
        marts["mart_daily_sales_by_store"]
        .groupby("store_name", as_index=False)["net_revenue"]
        .sum()
        .sort_values("net_revenue", ascending=False)
        .head(5)
    )
    top_stores["net_revenue"] = top_stores["net_revenue"].round(2)
    top_cats = (
        marts["mart_daily_sales_by_category"]
        .groupby("category", as_index=False)["net_revenue"]
        .sum()
        .sort_values("net_revenue", ascending=False)
    )
    top_cats["net_revenue"] = top_cats["net_revenue"].round(2)
    summary = {
        "top_stores_by_revenue": top_stores.to_dict(orient="records"),
        "top_categories": top_cats.to_dict(orient="records"),
        "service_ticket_count": int(len(marts["mart_service_performance"])),
        "avg_csat": float(marts["mart_service_performance"]["csat"].dropna().mean().round(2))
        if marts["mart_service_performance"]["csat"].notna().any() else None,
    }
    summary_path = gold / "pipeline_outputs.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=str))

    manifest = {
        "layer": "gold",
        "marts": results,
        "dq": dq,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    (gold / "_manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
    print("Gold aggregates complete.")
    return manifest


def main():
    import sys
    root = str(project_root())
    if root not in sys.path:
        sys.path.insert(0, root)
    parser = argparse.ArgumentParser(description="Gold aggregates job")
    parser.add_argument("--engine", choices=["auto", "spark", "pandas"], default="auto")
    args = parser.parse_args()
    run(args.engine)


if __name__ == "__main__":
    main()
