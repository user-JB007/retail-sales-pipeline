"""Generate source extracts for the retail sales & service analytics pipeline.

Produces operational CSVs under data/raw/:
  - stores.csv
  - products.csv
  - customers.csv
  - sales_transactions.csv
  - service_tickets.csv
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)

REGIONS = ["Northeast", "Southeast", "Midwest", "Southwest", "West"]
STORE_TYPES = ["flagship", "outlet", "express", "online"]
CATEGORIES = {
    "Electronics": ["Laptops", "Phones", "Headphones", "Tablets"],
    "Apparel": ["Men", "Women", "Kids", "Accessories"],
    "Home": ["Furniture", "Kitchen", "Decor", "Bedding"],
    "Grocery": ["Produce", "Dairy", "Snacks", "Beverages"],
    "Sports": ["Fitness", "Outdoor", "Team Sports", "Footwear"],
}
PAYMENT_METHODS = ["credit_card", "debit_card", "cash", "mobile_pay", "gift_card"]
CHANNELS = ["in_store", "online", "mobile_app"]

SERVICE_REASONS = [
    "Product defect",
    "Late delivery",
    "Wrong item",
    "Refund request",
    "Pricing dispute",
    "Staff conduct",
    "Store experience",
    "Online order issue",
]
SERVICE_CHANNELS = ["phone", "email", "chat", "in_store", "social"]
SERVICE_STATUSES = ["resolved", "pending", "escalated", "closed_unresolved"]
# SLA hours by priority
SLA_HOURS = {"critical": 4, "high": 24, "medium": 72, "low": 168}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def generate_stores(n: int = 25) -> pd.DataFrame:
    cities = [
        ("New York", "NY"), ("Boston", "MA"), ("Atlanta", "GA"), ("Miami", "FL"),
        ("Chicago", "IL"), ("Detroit", "MI"), ("Dallas", "TX"), ("Houston", "TX"),
        ("Phoenix", "AZ"), ("Denver", "CO"), ("Los Angeles", "CA"), ("Seattle", "WA"),
        ("Portland", "OR"), ("San Francisco", "CA"), ("Austin", "TX"),
        ("Nashville", "TN"), ("Charlotte", "NC"), ("Minneapolis", "MN"),
        ("Philadelphia", "PA"), ("San Diego", "CA"), ("Las Vegas", "NV"),
        ("Orlando", "FL"), ("Kansas City", "MO"), ("Salt Lake City", "UT"),
        ("Raleigh", "NC"),
    ]
    rows = []
    for i in range(n):
        city, state = cities[i % len(cities)]
        rows.append(
            {
                "store_id": f"STR{i+1:03d}",
                "store_name": f"{city} {'Downtown' if i % 3 == 0 else 'Mall'} #{i+1}",
                "store_type": STORE_TYPES[i % len(STORE_TYPES)],
                "region": REGIONS[i % len(REGIONS)],
                "city": city,
                "state": state,
                "opened_date": (datetime(2015, 1, 1) + timedelta(days=int(RNG.integers(0, 3000)))).strftime("%Y-%m-%d"),
                "square_footage": int(RNG.integers(2000, 45000)),
                "is_active": True if i < n - 2 else False,
            }
        )
    return pd.DataFrame(rows)


def generate_products(n: int = 120) -> pd.DataFrame:
    rows = []
    brands = ["Nova", "Apex", "Lumina", "Forge", "Cascade", "Orbit", "Pinnacle", "Harbor"]
    idx = 1
    for _ in range(n):
        category = list(CATEGORIES.keys())[idx % len(CATEGORIES)]
        subcategory = CATEGORIES[category][idx % len(CATEGORIES[category])]
        unit_cost = float(round(RNG.uniform(2, 400), 2))
        margin = float(RNG.uniform(1.15, 2.4))
        rows.append(
            {
                "product_id": f"PRD{idx:04d}",
                "product_name": f"{brands[idx % len(brands)]} {subcategory} {idx}",
                "category": category,
                "subcategory": subcategory,
                "brand": brands[idx % len(brands)],
                "unit_cost": unit_cost,
                "unit_price": float(round(unit_cost * margin, 2)),
                "sku": f"SKU-{category[:3].upper()}-{idx:05d}",
                "is_active": True if idx % 17 != 0 else False,
            }
        )
        idx += 1
    return pd.DataFrame(rows)


def generate_customers(n: int = 500) -> pd.DataFrame:
    first_names = [
        "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery", "Quinn",
        "Sam", "Jamie", "Cameron", "Drew", "Blake", "Reese", "Harper", "Rowan",
    ]
    last_names = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
        "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson",
    ]
    tiers = ["bronze", "silver", "gold", "platinum"]
    rows = []
    for i in range(1, n + 1):
        rows.append(
            {
                "customer_id": f"CUS{i:05d}",
                "first_name": first_names[i % len(first_names)],
                "last_name": last_names[i % len(last_names)],
                "email": f"customer{i}@example.com",
                "loyalty_tier": tiers[min(i % 10, 3)],
                "signup_date": (datetime(2018, 1, 1) + timedelta(days=int(RNG.integers(0, 2200)))).strftime("%Y-%m-%d"),
                "state": ["NY", "CA", "TX", "FL", "IL", "WA", "GA", "CO"][i % 8],
                "is_active": True if i % 23 != 0 else False,
            }
        )
    return pd.DataFrame(rows)


def generate_transactions(
    stores: pd.DataFrame,
    products: pd.DataFrame,
    customers: pd.DataFrame,
    n: int = 5000,
    start: str = "2024-01-01",
    end: str = "2024-12-31",
) -> pd.DataFrame:
    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d")
    days = (end_dt - start_dt).days

    active_stores = stores[stores["is_active"]]["store_id"].tolist()
    active_products = products[products["is_active"]].reset_index(drop=True)
    active_customers = customers[customers["is_active"]]["customer_id"].tolist()

    rows = []
    for i in range(1, n + 1):
        prod = active_products.iloc[int(RNG.integers(0, len(active_products)))]
        qty = int(RNG.integers(1, 6))
        discount_pct = float(RNG.choice([0.0, 0.0, 0.0, 0.05, 0.10, 0.15, 0.20], p=[0.45, 0.2, 0.1, 0.1, 0.08, 0.05, 0.02]))
        unit_price = float(prod["unit_price"])
        gross = round(unit_price * qty, 2)
        discount_amt = round(gross * discount_pct, 2)
        net = round(gross - discount_amt, 2)
        # Inject a few intentional DQ issues for silver layer to catch
        bad_row = i % 487 == 0
        rows.append(
            {
                "transaction_id": f"TXN{i:07d}",
                "transaction_ts": (start_dt + timedelta(days=int(RNG.integers(0, days)), hours=int(RNG.integers(8, 22)), minutes=int(RNG.integers(0, 60)))).strftime("%Y-%m-%d %H:%M:%S"),
                "store_id": active_stores[int(RNG.integers(0, len(active_stores)))] if not bad_row else "STR999",
                "product_id": prod["product_id"],
                "customer_id": active_customers[int(RNG.integers(0, len(active_customers)))] if i % 11 != 0 else None,
                "quantity": qty if not (i % 911 == 0) else -1,
                "unit_price": unit_price,
                "discount_pct": discount_pct,
                "discount_amount": discount_amt,
                "net_amount": net if not (i % 733 == 0) else None,
                "payment_method": PAYMENT_METHODS[int(RNG.integers(0, len(PAYMENT_METHODS)))],
                "channel": CHANNELS[int(RNG.integers(0, len(CHANNELS)))],
                "currency": "USD",
            }
        )
    return pd.DataFrame(rows)


def generate_service_tickets(
    stores: pd.DataFrame,
    customers: pd.DataFrame,
    n: int = 1800,
    start: str = "2024-01-01",
    end: str = "2024-12-31",
) -> pd.DataFrame:
    """Seed customer service / complaint tickets with SLA clocks and CSAT."""
    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d")
    days = (end_dt - start_dt).days
    active_stores = stores[stores["is_active"]]["store_id"].tolist()
    active_customers = customers[customers["is_active"]]["customer_id"].tolist()
    priorities = ["low", "medium", "high", "critical"]
    priority_p = [0.35, 0.40, 0.18, 0.07]

    rows = []
    for i in range(1, n + 1):
        opened = start_dt + timedelta(
            days=int(RNG.integers(0, days)),
            hours=int(RNG.integers(7, 21)),
            minutes=int(RNG.integers(0, 60)),
        )
        priority = str(RNG.choice(priorities, p=priority_p))
        sla_hours = SLA_HOURS[priority]
        sla_due = opened + timedelta(hours=sla_hours)

        # Resolution behavior: most resolve; some pending / late
        roll = float(RNG.random())
        if roll < 0.12:
            status = "pending"
            resolved = None
            resolve_hours = None
            csat = None
        elif roll < 0.18:
            status = "escalated"
            # Still open but aged
            resolved = None
            resolve_hours = None
            csat = None
        else:
            # Resolve within or beyond SLA
            if RNG.random() < 0.78:
                # Within SLA
                resolve_hours = float(RNG.uniform(0.5, sla_hours * 0.95))
                status = "resolved"
            else:
                resolve_hours = float(RNG.uniform(sla_hours * 1.05, sla_hours * 2.8))
                status = RNG.choice(["resolved", "closed_unresolved"], p=[0.85, 0.15])
            resolved = opened + timedelta(hours=resolve_hours)
            # CSAT 1–5; late tickets score lower
            if status == "closed_unresolved":
                csat = int(RNG.choice([1, 2, 3], p=[0.45, 0.35, 0.20]))
            elif resolve_hours <= sla_hours:
                csat = int(RNG.choice([3, 4, 5], p=[0.15, 0.40, 0.45]))
            else:
                csat = int(RNG.choice([1, 2, 3, 4], p=[0.20, 0.30, 0.35, 0.15]))

        within_sla = None
        if resolved is not None:
            within_sla = resolved <= sla_due
        elif status in ("pending", "escalated"):
            within_sla = None  # open — evaluated vs now in marts

        store_id = active_stores[int(RNG.integers(0, len(active_stores)))]
        rows.append(
            {
                "ticket_id": f"TKT{i:06d}",
                "opened_at": opened.strftime("%Y-%m-%d %H:%M:%S"),
                "resolved_at": resolved.strftime("%Y-%m-%d %H:%M:%S") if resolved else None,
                "sla_due_at": sla_due.strftime("%Y-%m-%d %H:%M:%S"),
                "status": status,
                "priority": priority,
                "reason": str(RNG.choice(SERVICE_REASONS)),
                "channel": str(RNG.choice(SERVICE_CHANNELS)),
                "store_id": store_id,
                "customer_id": active_customers[int(RNG.integers(0, len(active_customers)))],
                "csat": csat,
                "resolve_hours": round(resolve_hours, 2) if resolve_hours is not None else None,
                "within_sla": within_sla,
            }
        )
    df = pd.DataFrame(rows)
    store_region = stores.set_index("store_id")["region"].to_dict()
    df["region"] = df["store_id"].map(store_region)
    return df


def main(output_dir: Path | None = None, n_txns: int = 5000, n_tickets: int = 1800) -> dict[str, Path]:
    out = output_dir or (_project_root() / "data" / "raw")
    out.mkdir(parents=True, exist_ok=True)

    stores = generate_stores()
    products = generate_products()
    customers = generate_customers()
    txns = generate_transactions(stores, products, customers, n=n_txns)
    tickets = generate_service_tickets(stores, customers, n=n_tickets)

    paths = {
        "stores": out / "stores.csv",
        "products": out / "products.csv",
        "customers": out / "customers.csv",
        "sales_transactions": out / "sales_transactions.csv",
        "service_tickets": out / "service_tickets.csv",
    }
    stores.to_csv(paths["stores"], index=False)
    products.to_csv(paths["products"], index=False)
    customers.to_csv(paths["customers"], index=False)
    txns.to_csv(paths["sales_transactions"], index=False)
    tickets.to_csv(paths["service_tickets"], index=False)

    # Compact parquet for Spark-friendly ingest
    txns.to_parquet(out / "sales_transactions.parquet", index=False)
    tickets.to_parquet(out / "service_tickets.parquet", index=False)

    print(
        f"Wrote {len(stores)} stores, {len(products)} products, {len(customers)} customers, "
        f"{len(txns)} transactions, {len(tickets)} service tickets -> {out}"
    )
    return paths


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate retail source extracts (sales + service)")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--n-transactions", type=int, default=5000)
    parser.add_argument("--n-tickets", type=int, default=1800)
    args = parser.parse_args()
    main(args.output_dir, args.n_transactions, args.n_tickets)
