"""Generate Tableau-styled workbook page PNGs for GitHub visitors.

Two workbooks × 3 dashboard pages each, under tableau/screenshots/:
  1) Sales Report — revenue, stores/regions, trends
  2) Customer Satisfaction & Service Report — CSAT, SLA, pending/aging

    python scripts/run_local.py --engine pandas
    python src/viz/generate_tableau_pages.py --export-marts
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
import seaborn as sns

TAB_ORANGE = "#E97627"
TAB_BLUE = "#4E79A7"
TAB_TEAL = "#76B7B2"
TAB_RED = "#E15759"
TAB_GREEN = "#59A14F"
TAB_PURPLE = "#B07AA1"
TAB_BROWN = "#9C755F"
TAB_YELLOW = "#EDC948"
TAB_GRAY = "#BAB0AC"
TAB_DARK = "#333333"
TAB_LIGHT = "#F5F5F5"
TAB_WHITE = "#FFFFFF"
TAB_BORDER = "#D0D0D0"
TAB_NAVY = "#1F4E79"
TAB_SHEET = "#E8E8E8"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "figure.dpi": 140,
        "savefig.dpi": 160,
        "savefig.facecolor": TAB_LIGHT,
        "axes.facecolor": TAB_WHITE,
        "axes.edgecolor": TAB_BORDER,
        "axes.labelcolor": TAB_DARK,
        "xtick.color": "#666666",
        "ytick.color": "#666666",
        "text.color": TAB_DARK,
    }
)

MART_FILES = {
    "store": "mart_daily_sales_by_store.csv",
    "category": "mart_daily_sales_by_category.csv",
    "clv": "mart_customer_lifetime_value.csv",
    "product": "mart_product_performance.csv",
    "channel": "mart_channel_mix.csv",
    "service": "mart_service_performance.csv",
}

SALES_TABS = ["Overview", "Stores & Regions", "Trends"]
SERVICE_TABS = ["Overview", "SLA Performance", "Pending & Aging"]


def _resolve_marts(marts: Path) -> Path:
    if marts.exists() and any(marts.glob("*.csv")):
        return marts
    gold = Path("data/gold")
    flat = Path("tableau/marts")
    flat.mkdir(parents=True, exist_ok=True)
    if gold.exists():
        mapping = {
            "mart_daily_sales_by_store": "mart_daily_sales_by_store.csv",
            "mart_daily_sales_by_category": "mart_daily_sales_by_category.csv",
            "mart_customer_lifetime_value": "mart_customer_lifetime_value.csv",
            "mart_product_performance": "mart_product_performance.csv",
            "mart_channel_mix": "mart_channel_mix.csv",
            "mart_service_performance": "mart_service_performance.csv",
        }
        for folder, fname in mapping.items():
            src = gold / folder / "data.csv"
            if src.exists():
                shutil.copy2(src, flat / fname)
        if any(flat.glob("*.csv")):
            return flat
    if flat.exists() and any(flat.glob("*.csv")):
        return flat
    raise FileNotFoundError(
        "No mart CSVs found. Run `python scripts/run_local.py --engine pandas` "
        "or pass --marts tableau/marts"
    )


def _load(marts: Path, key: str) -> pd.DataFrame:
    path = marts / MART_FILES[key]
    if not path.exists():
        alt = Path("data/gold") / MART_FILES[key].replace(".csv", "") / "data.csv"
        if alt.exists():
            return pd.read_csv(alt)
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def _chrome(
    fig: plt.Figure,
    workbook: str,
    tabs: list[str],
    page_idx: int,
    sheet_title: str,
    filters: str,
    dept: str = "Retail Analytics · Sales",
) -> None:
    """Tableau Desktop–like header, filter shelf cue, and worksheet tabs."""
    fig.patches.append(
        mpatches.FancyBboxPatch(
            (0, 0.968), 1, 0.032, transform=fig.transFigure,
            boxstyle="square,pad=0", facecolor=TAB_ORANGE, edgecolor="none",
            clip_on=False, zorder=0,
        )
    )
    fig.patches.append(
        mpatches.FancyBboxPatch(
            (0, 0.900), 1, 0.068, transform=fig.transFigure,
            boxstyle="square,pad=0", facecolor=TAB_NAVY, edgecolor="none",
            clip_on=False, zorder=0,
        )
    )
    fig.text(0.02, 0.945, workbook, fontsize=9, color=TAB_ORANGE,
             fontweight="bold", va="center", transform=fig.transFigure)
    fig.text(0.02, 0.918, sheet_title, fontsize=14, color=TAB_WHITE, fontweight="bold",
             va="center", transform=fig.transFigure)
    fig.text(0.98, 0.945, dept, fontsize=8, color="#A8C5D4",
             ha="right", va="center", transform=fig.transFigure)

    fig.patches.append(
        mpatches.FancyBboxPatch(
            (0.02, 0.850), 0.96, 0.040, transform=fig.transFigure,
            boxstyle="round,pad=0.002,rounding_size=0.006", facecolor=TAB_WHITE,
            edgecolor=TAB_BORDER, linewidth=1, clip_on=False, zorder=1,
        )
    )
    fig.text(0.035, 0.870, f"Filters  ·  {filters}", fontsize=8, color="#666666",
             va="center", transform=fig.transFigure)

    n = len(tabs)
    tab_w = 0.96 / n
    for i, name in enumerate(tabs):
        x = 0.02 + i * tab_w
        active = i == page_idx
        fig.patches.append(
            mpatches.FancyBboxPatch(
                (x, 0.006), tab_w - 0.005, 0.034, transform=fig.transFigure,
                boxstyle="round,pad=0.001,rounding_size=0.003",
                facecolor=TAB_ORANGE if active else TAB_SHEET,
                edgecolor=TAB_BORDER, linewidth=0.8, clip_on=False, zorder=1,
            )
        )
        fig.text(
            x + (tab_w - 0.005) / 2, 0.023, name, fontsize=8, ha="center",
            va="center", color=TAB_WHITE if active else TAB_DARK,
            fontweight="bold" if active else "normal", transform=fig.transFigure,
        )


def _kpi_card(ax, value: str, label: str, accent: str) -> None:
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.add_patch(plt.Rectangle(
        (0.02, 0.08), 0.96, 0.84, transform=ax.transAxes,
        facecolor=TAB_WHITE, edgecolor=TAB_BORDER, linewidth=1.2,
    ))
    ax.add_patch(plt.Rectangle(
        (0.02, 0.08), 0.04, 0.84, transform=ax.transAxes,
        facecolor=accent, edgecolor="none",
    ))
    ax.text(0.55, 0.58, value, ha="center", va="center", fontsize=17,
            fontweight="bold", color=TAB_DARK, transform=ax.transAxes)
    ax.text(0.55, 0.28, label, ha="center", va="center", fontsize=8,
            color="#666666", transform=ax.transAxes)


# ── Workbook A: Sales Report ────────────────────────────────────────────────

def sales_01_overview(marts: Path, out: Path) -> None:
    store = _load(marts, "store")
    store["transaction_date"] = pd.to_datetime(store["transaction_date"])
    cat = _load(marts, "category")
    daily = store.groupby("transaction_date", as_index=False).agg(
        net_revenue=("net_revenue", "sum"),
        transactions=("transactions", "sum"),
        units_sold=("units_sold", "sum"),
        gross_profit=("gross_profit", "sum"),
    ).sort_values("transaction_date")
    monthly = daily.set_index("transaction_date").resample("MS").agg(
        net_revenue=("net_revenue", "sum"), transactions=("transactions", "sum")
    )
    mom = monthly["net_revenue"].pct_change().iloc[-1] * 100 if len(monthly) > 1 else 0.0
    total_rev = daily["net_revenue"].sum()
    total_txn = daily["transactions"].sum()
    aov = total_rev / total_txn if total_txn else 0
    margin = daily["gross_profit"].sum() / total_rev * 100 if total_rev else 0

    fig = plt.figure(figsize=(14.5, 9.2), facecolor=TAB_LIGHT)
    _chrome(fig, "Sales Report", SALES_TABS, 0,
            "Executive KPIs & Trends",
            "Date: full year  ·  Region: All  ·  Channel: All  ·  Store type: All",
            dept="Retail Analytics · Sales")
    gs = fig.add_gridspec(3, 4, left=0.05, right=0.97, top=0.825, bottom=0.07,
                          hspace=0.42, wspace=0.32)
    kpis = [
        (f"${total_rev/1e6:.2f}M", "Net Revenue", TAB_TEAL),
        (f"{int(total_txn):,}", "Orders", TAB_BLUE),
        (f"${aov:,.0f}", "Avg Order Value", TAB_ORANGE),
        (f"{mom:+.1f}%", "Revenue MoM", TAB_GREEN if mom >= 0 else TAB_RED),
    ]
    for i, (v, lab, c) in enumerate(kpis):
        _kpi_card(fig.add_subplot(gs[0, i]), v, lab, c)

    ax1 = fig.add_subplot(gs[1, :2])
    ax1.fill_between(daily["transaction_date"], daily["net_revenue"] / 1000,
                     color=TAB_TEAL, alpha=0.25)
    ax1.plot(daily["transaction_date"], daily["net_revenue"] / 1000,
             color=TAB_TEAL, linewidth=1.4)
    ax1.set_title("Daily Net Revenue ($K)", fontsize=11, fontweight="bold", loc="left")
    ax1.set_ylabel("Revenue ($K)", fontsize=8)
    ax1.grid(axis="y", alpha=0.25)
    ax1.tick_params(axis="x", rotation=30, labelsize=7)

    ax2 = fig.add_subplot(gs[1, 2:])
    by_region = store.groupby("region")["net_revenue"].sum().sort_values(ascending=True)
    ax2.barh(by_region.index, by_region.values / 1000, color=TAB_BLUE)
    ax2.set_title("Net Revenue by Region ($K)", fontsize=11, fontweight="bold", loc="left")
    ax2.set_xlabel("Revenue ($K)")
    ax2.grid(axis="x", alpha=0.25)

    ax3 = fig.add_subplot(gs[2, :2])
    by_cat = cat.groupby("category")["net_revenue"].sum().sort_values(ascending=False)
    colors = [TAB_TEAL, TAB_BLUE, TAB_ORANGE, TAB_PURPLE, TAB_RED, TAB_GREEN][: len(by_cat)]
    ax3.bar(by_cat.index, by_cat.values / 1000, color=colors)
    ax3.set_title("Revenue by Category ($K)", fontsize=11, fontweight="bold", loc="left")
    ax3.set_ylabel("Revenue ($K)")
    ax3.tick_params(axis="x", rotation=20)
    ax3.grid(axis="y", alpha=0.25)

    ax4 = fig.add_subplot(gs[2, 2:])
    ax4.axis("off")
    ax4.text(0.05, 0.9, "Operating Snapshot", fontsize=12, fontweight="bold",
             color=TAB_DARK, transform=ax4.transAxes)
    snap = (
        f"Gross margin          {margin:.1f}%\n"
        f"Units sold            {int(daily['units_sold'].sum()):,}\n"
        f"Store-day rows        {len(store):,}\n"
        f"Product categories    {by_cat.shape[0]}\n"
        f"Latest month revenue  ${monthly['net_revenue'].iloc[-1]/1e3:,.0f}K"
    )
    ax4.text(0.05, 0.75, snap, fontsize=11, family="monospace", color="#555555",
             va="top", transform=ax4.transAxes,
             bbox=dict(boxstyle="round,pad=0.6", facecolor=TAB_WHITE,
                       edgecolor=TAB_ORANGE, linewidth=1.5))

    fig.savefig(out / "sales_01_overview.png")
    plt.close(fig)
    print("  wrote sales_01_overview.png")


def sales_02_stores(marts: Path, out: Path) -> None:
    store = _load(marts, "store")
    by_store = store.groupby(["store_name", "region", "store_type"], as_index=False).agg(
        net_revenue=("net_revenue", "sum"),
        transactions=("transactions", "sum"),
        gross_profit=("gross_profit", "sum"),
        avg_order_value=("avg_order_value", "mean"),
    )
    by_store["margin_pct"] = by_store["gross_profit"] / by_store["net_revenue"] * 100
    top = by_store.nlargest(12, "net_revenue")

    fig = plt.figure(figsize=(14.5, 9.2), facecolor=TAB_LIGHT)
    _chrome(fig, "Sales Report", SALES_TABS, 1,
            "Store & Region Performance",
            "Ranked by net revenue  ·  Region: All  ·  Store type: All",
            dept="Retail Analytics · Sales")
    gs = fig.add_gridspec(2, 2, left=0.08, right=0.96, top=0.82, bottom=0.08,
                          hspace=0.38, wspace=0.28)

    ax1 = fig.add_subplot(gs[0, :])
    ax1.barh(top["store_name"][::-1], top["net_revenue"][::-1] / 1000, color=TAB_TEAL)
    ax1.set_title("Top 12 Stores by Net Revenue ($K)", fontsize=11, fontweight="bold", loc="left")
    ax1.set_xlabel("Net Revenue ($K)")
    ax1.grid(axis="x", alpha=0.25)

    ax2 = fig.add_subplot(gs[1, 0])
    type_rev = by_store.groupby("store_type")["net_revenue"].sum().sort_values(ascending=False)
    ax2.bar(type_rev.index, type_rev.values / 1000,
            color=[TAB_BLUE, TAB_TEAL, TAB_ORANGE][: len(type_rev)])
    ax2.set_title("Revenue by Store Type ($K)", fontsize=11, fontweight="bold", loc="left")
    ax2.set_ylabel("Revenue ($K)")
    ax2.grid(axis="y", alpha=0.25)

    ax3 = fig.add_subplot(gs[1, 1])
    region_margin = by_store.groupby("region").agg(
        revenue=("net_revenue", "sum"), profit=("gross_profit", "sum")
    )
    region_margin["margin"] = region_margin["profit"] / region_margin["revenue"] * 100
    region_margin = region_margin.sort_values("margin")
    ax3.barh(region_margin.index, region_margin["margin"], color=TAB_PURPLE)
    ax3.set_title("Gross Margin % by Region", fontsize=11, fontweight="bold", loc="left")
    ax3.set_xlabel("Margin %")
    ax3.grid(axis="x", alpha=0.25)

    fig.savefig(out / "sales_02_stores.png")
    plt.close(fig)
    print("  wrote sales_02_stores.png")


def sales_03_trends(marts: Path, out: Path) -> None:
    store = _load(marts, "store")
    store["transaction_date"] = pd.to_datetime(store["transaction_date"])
    ch = _load(marts, "channel")
    prod = _load(marts, "product")

    monthly = (
        store.assign(month=store["transaction_date"].dt.to_period("M").dt.to_timestamp())
        .groupby(["month", "region"], as_index=False)["net_revenue"].sum()
    )
    pivot = monthly.pivot(index="month", columns="region", values="net_revenue").fillna(0)

    fig = plt.figure(figsize=(14.5, 9.2), facecolor=TAB_LIGHT)
    _chrome(fig, "Sales Report", SALES_TABS, 2,
            "Trends, Channel & Product Mix",
            "Monthly region trends  ·  Channel mix  ·  Top products",
            dept="Retail Analytics · Sales")
    gs = fig.add_gridspec(2, 2, left=0.07, right=0.96, top=0.82, bottom=0.08,
                          hspace=0.4, wspace=0.28)

    ax1 = fig.add_subplot(gs[0, :])
    colors = [TAB_BLUE, TAB_TEAL, TAB_ORANGE, TAB_PURPLE, TAB_RED, TAB_GREEN]
    for i, col in enumerate(pivot.columns):
        ax1.plot(pivot.index, pivot[col] / 1000, label=col, linewidth=2,
                 color=colors[i % len(colors)])
    ax1.set_title("Monthly Net Revenue by Region ($K)", fontsize=11, fontweight="bold", loc="left")
    ax1.set_ylabel("Revenue ($K)")
    ax1.legend(fontsize=8, frameon=False, ncol=4, loc="upper left")
    ax1.grid(axis="y", alpha=0.25)

    by_channel = ch.groupby("channel")["net_revenue"].sum().sort_values(ascending=False)
    ax2 = fig.add_subplot(gs[1, 0])
    ax2.pie(by_channel, labels=by_channel.index, autopct="%1.0f%%",
            colors=[TAB_TEAL, TAB_BLUE, TAB_ORANGE, TAB_PURPLE][: len(by_channel)],
            textprops={"fontsize": 9}, startangle=90,
            wedgeprops={"edgecolor": "white", "linewidth": 1.5})
    ax2.set_title("Revenue by Channel", fontsize=11, fontweight="bold")

    ax3 = fig.add_subplot(gs[1, 1])
    top = prod.nlargest(8, "net_revenue")
    ax3.barh(top["product_name"].str.slice(0, 28)[::-1], top["net_revenue"][::-1] / 1000, color=TAB_TEAL)
    ax3.set_title("Top Products by Net Revenue ($K)", fontsize=11, fontweight="bold", loc="left")
    ax3.set_xlabel("Revenue ($K)")
    ax3.grid(axis="x", alpha=0.25)

    fig.savefig(out / "sales_03_trends.png")
    plt.close(fig)
    print("  wrote sales_03_trends.png")


# ── Workbook B: Customer Satisfaction & Service ─────────────────────────────

def service_01_overview(marts: Path, out: Path) -> None:
    svc = _load(marts, "service")
    svc["opened_at"] = pd.to_datetime(svc["opened_at"])
    total = len(svc)
    open_n = int(svc["is_open"].sum()) if "is_open" in svc.columns else int(svc["status"].isin(["pending", "escalated"]).sum())
    avg_csat = float(svc["csat"].dropna().mean()) if svc["csat"].notna().any() else 0.0
    within = int((svc["sla_status"] == "within_sla").sum()) if "sla_status" in svc.columns else 0
    beyond = int(svc["sla_status"].isin(["beyond_sla", "pending_beyond_sla"]).sum()) if "sla_status" in svc.columns else 0
    within_pct = within / max(total - open_n, 1) * 100 if total else 0

    fig = plt.figure(figsize=(14.5, 9.2), facecolor=TAB_LIGHT)
    _chrome(fig, "Customer Satisfaction & Service Report", SERVICE_TABS, 0,
            "Service Volume & CSAT Overview",
            "Date: full year  ·  Region: All  ·  Channel: All  ·  Priority: All",
            dept="Retail Analytics · Customer Service")
    gs = fig.add_gridspec(3, 4, left=0.05, right=0.97, top=0.825, bottom=0.07,
                          hspace=0.42, wspace=0.32)
    kpis = [
        (f"{total:,}", "Tickets Opened", TAB_BLUE),
        (f"{avg_csat:.2f}", "Avg CSAT (1–5)", TAB_TEAL),
        (f"{within_pct:.0f}%", "Resolved Within SLA", TAB_GREEN),
        (f"{open_n:,}", "Still Pending", TAB_ORANGE),
    ]
    for i, (v, lab, c) in enumerate(kpis):
        _kpi_card(fig.add_subplot(gs[0, i]), v, lab, c)

    ax1 = fig.add_subplot(gs[1, :2])
    daily = svc.groupby(svc["opened_at"].dt.date).size()
    ax1.fill_between(pd.to_datetime(daily.index), daily.values, color=TAB_BLUE, alpha=0.25)
    ax1.plot(pd.to_datetime(daily.index), daily.values, color=TAB_BLUE, linewidth=1.2)
    ax1.set_title("Tickets Opened per Day", fontsize=11, fontweight="bold", loc="left")
    ax1.set_ylabel("Tickets")
    ax1.grid(axis="y", alpha=0.25)
    ax1.tick_params(axis="x", rotation=30, labelsize=7)

    ax2 = fig.add_subplot(gs[1, 2:])
    by_reason = svc["reason"].value_counts().sort_values(ascending=True)
    ax2.barh(by_reason.index, by_reason.values, color=TAB_PURPLE)
    ax2.set_title("Tickets by Reason", fontsize=11, fontweight="bold", loc="left")
    ax2.set_xlabel("Count")
    ax2.grid(axis="x", alpha=0.25)

    ax3 = fig.add_subplot(gs[2, :2])
    by_ch = svc["channel"].value_counts()
    ax3.pie(by_ch, labels=by_ch.index, autopct="%1.0f%%",
            colors=[TAB_TEAL, TAB_BLUE, TAB_ORANGE, TAB_PURPLE, TAB_RED][: len(by_ch)],
            textprops={"fontsize": 9}, startangle=90,
            wedgeprops={"edgecolor": "white", "linewidth": 1.5})
    ax3.set_title("Tickets by Channel", fontsize=11, fontweight="bold")

    ax4 = fig.add_subplot(gs[2, 2:])
    csat = svc["csat"].dropna().astype(int)
    counts = csat.value_counts().reindex([1, 2, 3, 4, 5], fill_value=0)
    ax4.bar(counts.index.astype(str), counts.values,
            color=[TAB_RED, TAB_ORANGE, TAB_YELLOW, TAB_TEAL, TAB_GREEN])
    ax4.set_title("CSAT Score Distribution", fontsize=11, fontweight="bold", loc="left")
    ax4.set_xlabel("CSAT")
    ax4.set_ylabel("Responses")
    ax4.grid(axis="y", alpha=0.25)

    fig.savefig(out / "service_01_overview.png")
    plt.close(fig)
    print("  wrote service_01_overview.png")


def service_02_sla(marts: Path, out: Path) -> None:
    svc = _load(marts, "service")
    fig = plt.figure(figsize=(14.5, 9.2), facecolor=TAB_LIGHT)
    _chrome(fig, "Customer Satisfaction & Service Report", SERVICE_TABS, 1,
            "SLA Attainment & Resolution Times",
            "Within SLA · Beyond SLA · By priority & channel",
            dept="Retail Analytics · Customer Service")
    gs = fig.add_gridspec(2, 2, left=0.07, right=0.96, top=0.82, bottom=0.08,
                          hspace=0.38, wspace=0.28)

    ax1 = fig.add_subplot(gs[0, 0])
    status_order = ["within_sla", "beyond_sla", "pending_within_sla", "pending_beyond_sla"]
    labels = {
        "within_sla": "Resolved · Within SLA",
        "beyond_sla": "Resolved · Beyond SLA",
        "pending_within_sla": "Pending · Within SLA",
        "pending_beyond_sla": "Pending · Beyond SLA",
    }
    counts = svc["sla_status"].value_counts().reindex(status_order).fillna(0)
    ax1.pie(counts, labels=[labels.get(i, i) for i in counts.index], autopct="%1.0f%%",
            colors=[TAB_GREEN, TAB_RED, TAB_TEAL, TAB_ORANGE],
            textprops={"fontsize": 8}, startangle=90,
            wedgeprops={"edgecolor": "white", "linewidth": 1.5})
    ax1.set_title("SLA Status Mix", fontsize=11, fontweight="bold")

    ax2 = fig.add_subplot(gs[0, 1])
    resolved = svc[svc["resolve_hours"].notna()].copy()
    by_pri = resolved.groupby("priority")["resolve_hours"].mean().reindex(
        ["critical", "high", "medium", "low"]
    ).dropna()
    ax2.bar([p.title() for p in by_pri.index], by_pri.values,
            color=[TAB_RED, TAB_ORANGE, TAB_BLUE, TAB_TEAL][: len(by_pri)])
    ax2.set_title("Avg Resolve Hours by Priority", fontsize=11, fontweight="bold", loc="left")
    ax2.set_ylabel("Hours")
    ax2.grid(axis="y", alpha=0.25)

    ax3 = fig.add_subplot(gs[1, 0])
    breach = svc.groupby("channel").agg(
        total=("ticket_id", "count"),
        breached=("sla_breach", "sum"),
    )
    breach["breach_pct"] = breach["breached"] / breach["total"] * 100
    breach = breach.sort_values("breach_pct")
    ax3.barh(breach.index, breach["breach_pct"], color=TAB_RED)
    ax3.set_title("SLA Breach Rate by Channel (%)", fontsize=11, fontweight="bold", loc="left")
    ax3.set_xlabel("Breach %")
    ax3.grid(axis="x", alpha=0.25)

    ax4 = fig.add_subplot(gs[1, 1])
    by_region = svc.groupby("region").agg(
        total=("ticket_id", "count"),
        within=("sla_status", lambda s: (s == "within_sla").sum()),
    )
    by_region["within_pct"] = by_region["within"] / by_region["total"] * 100
    by_region = by_region.sort_values("within_pct")
    ax4.barh(by_region.index, by_region["within_pct"], color=TAB_GREEN)
    ax4.set_title("Within-SLA Rate by Region (%)", fontsize=11, fontweight="bold", loc="left")
    ax4.set_xlabel("Within SLA %")
    ax4.grid(axis="x", alpha=0.25)

    fig.savefig(out / "service_02_sla.png")
    plt.close(fig)
    print("  wrote service_02_sla.png")


def service_03_pending_aging(marts: Path, out: Path) -> None:
    svc = _load(marts, "service")
    open_tix = svc[svc["is_open"] == 1].copy() if "is_open" in svc.columns else svc[svc["status"].isin(["pending", "escalated"])].copy()

    fig = plt.figure(figsize=(14.5, 9.2), facecolor=TAB_LIGHT)
    _chrome(fig, "Customer Satisfaction & Service Report", SERVICE_TABS, 2,
            "Pending Queue & Ticket Aging",
            "Open tickets  ·  Age buckets  ·  Priority backlog",
            dept="Retail Analytics · Customer Service")
    gs = fig.add_gridspec(2, 2, left=0.07, right=0.96, top=0.82, bottom=0.08,
                          hspace=0.38, wspace=0.28)

    ax1 = fig.add_subplot(gs[0, 0])
    if len(open_tix):
        bins = [0, 24, 72, 168, 336, 10_000]
        labels = ["<1d", "1–3d", "3–7d", "7–14d", "14d+"]
        open_tix = open_tix.copy()
        open_tix["age_bucket"] = pd.cut(open_tix["age_hours"], bins=bins, labels=labels, right=False)
        age_counts = open_tix["age_bucket"].value_counts().reindex(labels).fillna(0)
        ax1.bar(age_counts.index.astype(str), age_counts.values, color=TAB_ORANGE)
    ax1.set_title("Open Ticket Aging", fontsize=11, fontweight="bold", loc="left")
    ax1.set_ylabel("Tickets")
    ax1.grid(axis="y", alpha=0.25)

    ax2 = fig.add_subplot(gs[0, 1])
    if len(open_tix):
        by_pri = open_tix["priority"].value_counts().reindex(
            ["critical", "high", "medium", "low"]
        ).fillna(0)
        ax2.bar([p.title() for p in by_pri.index], by_pri.values,
                color=[TAB_RED, TAB_ORANGE, TAB_BLUE, TAB_TEAL])
    ax2.set_title("Open Backlog by Priority", fontsize=11, fontweight="bold", loc="left")
    ax2.set_ylabel("Open Tickets")
    ax2.grid(axis="y", alpha=0.25)

    ax3 = fig.add_subplot(gs[1, 0])
    if len(open_tix):
        by_reason = open_tix["reason"].value_counts().sort_values(ascending=True).tail(8)
        ax3.barh(by_reason.index, by_reason.values, color=TAB_PURPLE)
    ax3.set_title("Open Tickets by Reason", fontsize=11, fontweight="bold", loc="left")
    ax3.set_xlabel("Count")
    ax3.grid(axis="x", alpha=0.25)

    ax4 = fig.add_subplot(gs[1, 1])
    ax4.axis("off")
    oldest = open_tix.nlargest(8, "age_hours") if len(open_tix) else open_tix
    ax4.text(0.0, 1.0, "Oldest Open Tickets", fontsize=12, fontweight="bold",
             color=TAB_DARK, transform=ax4.transAxes, va="top")
    header = f"{'Ticket':<10} {'Pri':<8} {'Age(h)':>7} {'Reason'}"
    ax4.text(0.0, 0.88, header, fontsize=9, family="monospace", color="#666666",
             transform=ax4.transAxes, va="top")
    lines = [
        f"{r['ticket_id']:<10} {str(r['priority'])[:7]:<8} {r['age_hours']:>7.0f} {str(r['reason'])[:22]}"
        for _, r in oldest.iterrows()
    ]
    ax4.text(0.0, 0.78, "\n".join(lines) if lines else "No open tickets",
             fontsize=9, family="monospace", color=TAB_DARK,
             transform=ax4.transAxes, va="top",
             bbox=dict(boxstyle="round,pad=0.5", facecolor=TAB_WHITE,
                       edgecolor=TAB_ORANGE, linewidth=1.2))

    fig.savefig(out / "service_03_pending_aging.png")
    plt.close(fig)
    print("  wrote service_03_pending_aging.png")


def export_marts(gold: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    mapping = {
        "mart_daily_sales_by_store": "mart_daily_sales_by_store.csv",
        "mart_daily_sales_by_category": "mart_daily_sales_by_category.csv",
        "mart_customer_lifetime_value": "mart_customer_lifetime_value.csv",
        "mart_product_performance": "mart_product_performance.csv",
        "mart_channel_mix": "mart_channel_mix.csv",
        "mart_service_performance": "mart_service_performance.csv",
    }
    for folder, fname in mapping.items():
        src = gold / folder / "data.csv"
        if src.exists():
            shutil.copy2(src, dest / fname)
            print(f"  mart → {dest / fname}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Tableau-styled retail workbook pages")
    parser.add_argument("--marts", type=Path, default=Path("tableau/marts"))
    parser.add_argument("--out", type=Path, default=Path("tableau/screenshots"))
    parser.add_argument("--export-marts", action="store_true",
                        help="Copy data/gold/*/data.csv into tableau/marts/")
    args = parser.parse_args()

    gold = Path("data/gold")
    if args.export_marts or (gold.exists() and not any(Path("tableau/marts").glob("*.csv"))):
        if gold.exists():
            print("Exporting marts from gold…")
            export_marts(gold, Path("tableau/marts"))

    marts = _resolve_marts(args.marts)
    args.out.mkdir(parents=True, exist_ok=True)

    # Remove obsolete product_customer screenshots
    for obsolete in args.out.glob("product_customer_*.png"):
        obsolete.unlink()
        print(f"  removed {obsolete.name}")
    for obsolete in args.out.glob("sales_performance_*.png"):
        obsolete.unlink()
        print(f"  removed {obsolete.name}")

    print(f"Using marts from {marts}")
    print("Generating Tableau-styled workbook pages…")
    sales_01_overview(marts, args.out)
    sales_02_stores(marts, args.out)
    sales_03_trends(marts, args.out)
    service_01_overview(marts, args.out)
    service_02_sla(marts, args.out)
    service_03_pending_aging(marts, args.out)
    print(f"Done → {args.out.resolve()}")


if __name__ == "__main__":
    main()
