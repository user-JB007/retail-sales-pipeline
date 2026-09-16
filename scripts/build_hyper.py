#!/usr/bin/env python3
"""Build Tableau Hyper extracts from retail gold mart CSVs."""

from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path

from tableauhyperapi import (
    Connection,
    CreateMode,
    HyperProcess,
    Inserter,
    NOT_NULLABLE,
    NULLABLE,
    SqlType,
    TableDefinition,
    TableName,
    Telemetry,
)

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "tableau" / "marts"
EXTRACTS = ROOT / "tableau" / "Data" / "Extracts"


def parse_int(v):
    if v is None or v == "":
        return None
    return int(float(v))


def parse_float(v):
    if v is None or v == "":
        return None
    return float(v)


def parse_bool_int(v):
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return int(v)
    s = str(v).strip().lower()
    if s in ("true", "1", "yes"):
        return 1
    if s in ("false", "0", "no"):
        return 0
    return parse_int(v)


def to_date(s):
    if not s:
        return None
    y, m, d = s[:10].split("-")
    return date(int(y), int(m), int(d))


def to_ts(s):
    if not s:
        return None
    s = s.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    if len(s) >= 10:
        return datetime.strptime(s[:10], "%Y-%m-%d")
    return None


def write_hyper(path: Path, table: TableDefinition, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    with HyperProcess(Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
        with Connection(hyper.endpoint, str(path), CreateMode.CREATE_AND_REPLACE) as conn:
            conn.catalog.create_schema("Extract")
            conn.catalog.create_table(table)
            with Inserter(conn, table) as inserter:
                for row in rows:
                    inserter.add_row(row)
                inserter.execute()
    print(f"Wrote {path} ({path.stat().st_size} bytes)")


def build_store_sales():
    csv_path = MARTS / "mart_daily_sales_by_store.csv"
    hyper_path = EXTRACTS / "daily_sales_by_store.hyper"
    table = TableDefinition(
        TableName("Extract", "Extract"),
        [
            TableDefinition.Column("transaction_date", SqlType.date(), NOT_NULLABLE),
            TableDefinition.Column("store_id", SqlType.text(), NOT_NULLABLE),
            TableDefinition.Column("store_name", SqlType.text(), NOT_NULLABLE),
            TableDefinition.Column("region", SqlType.text(), NOT_NULLABLE),
            TableDefinition.Column("store_type", SqlType.text(), NOT_NULLABLE),
            TableDefinition.Column("transactions", SqlType.int(), NOT_NULLABLE),
            TableDefinition.Column("units_sold", SqlType.int(), NOT_NULLABLE),
            TableDefinition.Column("gross_revenue", SqlType.double(), NOT_NULLABLE),
            TableDefinition.Column("net_revenue", SqlType.double(), NOT_NULLABLE),
            TableDefinition.Column("discount_total", SqlType.double(), NOT_NULLABLE),
            TableDefinition.Column("cogs", SqlType.double(), NOT_NULLABLE),
            TableDefinition.Column("gross_profit", SqlType.double(), NOT_NULLABLE),
            TableDefinition.Column("avg_order_value", SqlType.double(), NOT_NULLABLE),
            TableDefinition.Column("gross_margin_pct", SqlType.double(), NOT_NULLABLE),
        ],
    )
    rows = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(
                [
                    to_date(r["transaction_date"]),
                    r["store_id"],
                    r["store_name"],
                    r["region"],
                    r["store_type"],
                    parse_int(r["transactions"]),
                    parse_int(r["units_sold"]),
                    parse_float(r["gross_revenue"]),
                    parse_float(r["net_revenue"]),
                    parse_float(r["discount_total"]),
                    parse_float(r["cogs"]),
                    parse_float(r["gross_profit"]),
                    parse_float(r["avg_order_value"]),
                    parse_float(r["gross_margin_pct"]),
                ]
            )
    write_hyper(hyper_path, table, rows)


def build_service():
    csv_path = MARTS / "mart_service_performance.csv"
    hyper_path = EXTRACTS / "service_performance.hyper"
    table = TableDefinition(
        TableName("Extract", "Extract"),
        [
            TableDefinition.Column("ticket_id", SqlType.text(), NOT_NULLABLE),
            TableDefinition.Column("opened_at", SqlType.timestamp(), NOT_NULLABLE),
            TableDefinition.Column("resolved_at", SqlType.timestamp(), NULLABLE),
            TableDefinition.Column("sla_due_at", SqlType.timestamp(), NOT_NULLABLE),
            TableDefinition.Column("opened_date", SqlType.date(), NOT_NULLABLE),
            TableDefinition.Column("status", SqlType.text(), NOT_NULLABLE),
            TableDefinition.Column("priority", SqlType.text(), NOT_NULLABLE),
            TableDefinition.Column("reason", SqlType.text(), NOT_NULLABLE),
            TableDefinition.Column("channel", SqlType.text(), NOT_NULLABLE),
            TableDefinition.Column("store_id", SqlType.text(), NOT_NULLABLE),
            TableDefinition.Column("store_name", SqlType.text(), NOT_NULLABLE),
            TableDefinition.Column("region", SqlType.text(), NOT_NULLABLE),
            TableDefinition.Column("customer_id", SqlType.text(), NOT_NULLABLE),
            TableDefinition.Column("csat", SqlType.double(), NULLABLE),
            TableDefinition.Column("resolve_hours", SqlType.double(), NULLABLE),
            TableDefinition.Column("age_hours", SqlType.double(), NOT_NULLABLE),
            TableDefinition.Column("is_open", SqlType.int(), NOT_NULLABLE),
            TableDefinition.Column("sla_breach", SqlType.int(), NOT_NULLABLE),
            TableDefinition.Column("sla_status", SqlType.text(), NOT_NULLABLE),
        ],
    )
    rows = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(
                [
                    r["ticket_id"],
                    to_ts(r["opened_at"]),
                    to_ts(r.get("resolved_at") or ""),
                    to_ts(r["sla_due_at"]),
                    to_date(r["opened_date"]),
                    r["status"],
                    r["priority"],
                    r["reason"],
                    r["channel"],
                    r["store_id"],
                    r["store_name"],
                    r["region"],
                    r["customer_id"],
                    parse_float(r.get("csat") or ""),
                    parse_float(r.get("resolve_hours") or ""),
                    parse_float(r["age_hours"]),
                    parse_int(r["is_open"]),
                    parse_bool_int(r["sla_breach"]),
                    r["sla_status"],
                ]
            )
    write_hyper(hyper_path, table, rows)


def main():
    EXTRACTS.mkdir(parents=True, exist_ok=True)
    build_store_sales()
    build_service()


if __name__ == "__main__":
    main()
