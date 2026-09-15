"""Generate Tableau-styled workbook page PNGs for GitHub visitors.

Two workbooks × 2–3 dashboard pages each, under tableau/screenshots/.

    python scripts/run_local.py --engine pandas
    python src/viz/generate_tableau_pages.py --export-samples
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

# Tableau-inspired palette
TAB_ORANGE = "#E97627"
TAB_BLUE = "#4E79A7"
TAB_TEAL = "#76B7B2"
TAB_RED = "#E15759"
TAB_GREEN = "#59A14F"
TAB_PURPLE = "#B07AA1"
TAB_BROWN = "#9C755F"
TAB_PINK = "#FF9DA7"
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
}

# Per-workbook worksheet tab labels (Tableau worksheet cue)
SALES_TABS = ["Overview", "Stores & Regions", "Trends"]
PRODUCT_TABS = ["Categories", "Customer LTV", "Product Rankings"]


def _resolve_marts(marts: Path) -> Path:
    if marts.exists() and any(marts.glob("*.csv")):
        return marts
    gold = Path("data/gold")
    flat = Path("tableau/sample_marts")
    flat.mkdir(parents=True, exist_ok=True)
    if gold.exists():
        mapping = {
            "mart_daily_sales_by_store": "mart_daily_sales_by_store.csv",
            "mart_daily_sales_by_category": "mart_daily_sales_by_category.csv",
            "mart_customer_lifetime_value": "mart_customer_lifetime_value.csv",
            "mart_product_performance": "mart_product_performance.csv",
            "mart_channel_mix": "mart_channel_mix.csv",
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
        "or pass --marts tableau/sample_marts"
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
) -> None:
    """Tableau Desktop–like header, filter shelf cue, and worksheet tabs."""
    # Orange accent strip (Tableau brand cue)
    fig.patches.append(
        mpatches.FancyBboxPatch(
            (0, 0.968), 1, 0.032, transform=fig.transFigure,
            boxstyle="square,pad=0", facecolor=TAB_ORANGE, edgecolor="none",
            clip_on=False, zorder=0,
        )
    )
    # Dark workbook bar
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
    fig.text(0.98, 0.945, "Tableau · Portfolio Demo", fontsize=8, color="#A8C5D4",
             ha="right", va="center", transform=fig.transFigure)

    # Filter / Marks shelf cue
    fig.patches.append(
        mpatches.FancyBboxPatch(
            (0.02, 0.850), 0.96, 0.040, transform=fig.transFigure,
            boxstyle="round,pad=0.002,rounding_size=0.006", facecolor=TAB_WHITE,
            edgecolor=TAB_BORDER, linewidth=1, clip_on=False, zorder=1,
        )
    )
    fig.text(0.035, 0.870, f"Filters  ·  {filters}", fontsize=8, color="#666666",
             va="center", transform=fig.transFigure)

    # Worksheet tabs (bottom) — Tableau cue
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


# ── Workbook A: Sales Performance ──────────────────────────────────────────

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
    _chrome(fig, "Sales Performance Workbook", SALES_TABS, 0,
            "Executive KPIs & Trends",
            "Date: full year  ·  Region: All  ·  Channel: All  ·  Store type: All")
    gs = fig.add_gridspec(3, 4, left=0.05, right=0.97, top=0.825, bottom=0.07,
                          hspace=0.42, wspace=0.32)
    kpis = [
        (f"${total_rev/1e6:.2f}M", "Net Revenue", TAB_TEAL),
        (f"{int(total_txn):,}", "Transactions", TAB_BLUE),
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
    ax4.text(0.05, 0.9, "Snapshot", fontsize=12, fontweight="bold",
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

    fig.savefig(out / "sales_performance_01_overview.png")
    plt.close(fig)
    print("  wrote sales_performance_01_overview.png")


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
    _chrome(fig, "Sales Performance Workbook", SALES_TABS, 1,
            "Store & Region Performance",
            "Ranked by net revenue  ·  Region: All  ·  Store type: All")
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

    fig.savefig(out / "sales_performance_02_stores.png")
    plt.close(fig)
    print("  wrote sales_performance_02_stores.png")


def sales_03_trends(marts: Path, out: Path) -> None:
    store = _load(marts, "store")
    store["transaction_date"] = pd.to_datetime(store["transaction_date"])
    ch = _load(marts, "channel")

    monthly = (
        store.assign(month=store["transaction_date"].dt.to_period("M").dt.to_timestamp())
        .groupby(["month", "region"], as_index=False)["net_revenue"].sum()
    )
    pivot = monthly.pivot(index="month", columns="region", values="net_revenue").fillna(0)

    fig = plt.figure(figsize=(14.5, 9.2), facecolor=TAB_LIGHT)
    _chrome(fig, "Sales Performance Workbook", SALES_TABS, 2,
            "Regional Trends & Channel Mix",
            "Monthly region trends  ·  Channel × payment contribution")
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
    pivot_ch = ch.groupby(["channel", "payment_method"])["net_revenue"].sum().unstack(fill_value=0)
    sns.heatmap(pivot_ch / 1000, ax=ax3, cmap="Oranges", annot=True, fmt=".0f",
                annot_kws={"size": 8}, linewidths=0.5, linecolor="white",
                cbar_kws={"label": "Revenue ($K)"})
    ax3.set_title("Channel × Payment ($K)", fontsize=11, fontweight="bold", loc="left", pad=10)
    ax3.set_xlabel("Payment Method")
    ax3.set_ylabel("Channel")

    fig.savefig(out / "sales_performance_03_trends.png")
    plt.close(fig)
    print("  wrote sales_performance_03_trends.png")


# ── Workbook B: Product & Customer Analysis ────────────────────────────────

def product_01_categories(marts: Path, out: Path) -> None:
    cat = _load(marts, "category")
    cat["transaction_date"] = pd.to_datetime(cat["transaction_date"])
    monthly = (
        cat.assign(month=cat["transaction_date"].dt.to_period("M").dt.to_timestamp())
        .groupby(["month", "category"], as_index=False)["net_revenue"].sum()
    )
    pivot = monthly.pivot(index="month", columns="category", values="net_revenue").fillna(0)

    fig = plt.figure(figsize=(14.5, 9.2), facecolor=TAB_LIGHT)
    _chrome(fig, "Product & Customer Analysis Workbook", PRODUCT_TABS, 0,
            "Category Mix & Trends",
            "Monthly net revenue by product category")
    gs = fig.add_gridspec(2, 2, left=0.07, right=0.96, top=0.82, bottom=0.08,
                          hspace=0.4, wspace=0.28)

    ax1 = fig.add_subplot(gs[0, :])
    colors = [TAB_TEAL, TAB_BLUE, TAB_ORANGE, TAB_PURPLE, TAB_RED, TAB_GREEN, TAB_BROWN]
    for i, col in enumerate(pivot.columns):
        ax1.plot(pivot.index, pivot[col] / 1000, label=col, linewidth=2,
                 color=colors[i % len(colors)])
    ax1.set_title("Monthly Category Revenue ($K)", fontsize=11, fontweight="bold", loc="left")
    ax1.set_ylabel("Revenue ($K)")
    ax1.legend(fontsize=8, frameon=False, ncol=4, loc="upper left")
    ax1.grid(axis="y", alpha=0.25)

    ax2 = fig.add_subplot(gs[1, 0])
    share = cat.groupby("category")["net_revenue"].sum().sort_values(ascending=False)
    ax2.pie(share, labels=share.index, autopct="%1.0f%%",
            colors=colors[: len(share)], textprops={"fontsize": 8},
            startangle=90, wedgeprops={"edgecolor": "white", "linewidth": 1.5})
    ax2.set_title("Category Revenue Share", fontsize=11, fontweight="bold")

    ax3 = fig.add_subplot(gs[1, 1])
    units = cat.groupby("category")["units_sold"].sum().sort_values(ascending=True)
    ax3.barh(units.index, units.values, color=TAB_BLUE)
    ax3.set_title("Units Sold by Category", fontsize=11, fontweight="bold", loc="left")
    ax3.set_xlabel("Units")
    ax3.grid(axis="x", alpha=0.25)

    fig.savefig(out / "product_customer_01_categories.png")
    plt.close(fig)
    print("  wrote product_customer_01_categories.png")


def product_02_rankings(marts: Path, out: Path) -> None:
    prod = _load(marts, "product")
    fig = plt.figure(figsize=(14.5, 9.2), facecolor=TAB_LIGHT)
    _chrome(fig, "Product & Customer Analysis Workbook", PRODUCT_TABS, 2,
            "Product Rankings",
            "Top products by net revenue · Brand & margin")
    gs = fig.add_gridspec(2, 2, left=0.10, right=0.96, top=0.82, bottom=0.08,
                          hspace=0.4, wspace=0.3)

    top = prod.nlargest(15, "net_revenue")
    ax1 = fig.add_subplot(gs[0, :])
    labels = top["product_name"].str.slice(0, 28)
    ax1.barh(labels[::-1], top["net_revenue"][::-1] / 1000, color=TAB_TEAL)
    ax1.set_title("Top 15 Products by Net Revenue ($K)", fontsize=11, fontweight="bold", loc="left")
    ax1.set_xlabel("Net Revenue ($K)")
    ax1.grid(axis="x", alpha=0.25)

    ax2 = fig.add_subplot(gs[1, 0])
    brand = prod.groupby("brand")["net_revenue"].sum().nlargest(8).sort_values()
    ax2.barh(brand.index, brand.values / 1000, color=TAB_BLUE)
    ax2.set_title("Top Brands by Revenue ($K)", fontsize=11, fontweight="bold", loc="left")
    ax2.set_xlabel("Revenue ($K)")
    ax2.grid(axis="x", alpha=0.25)

    ax3 = fig.add_subplot(gs[1, 1])
    prod = prod.copy()
    prod["margin_pct"] = prod["gross_profit"] / prod["net_revenue"] * 100
    scatter = prod.sample(min(len(prod), 80), random_state=7) if len(prod) > 80 else prod
    ax3.scatter(scatter["units_sold"], scatter["margin_pct"],
                s=scatter["net_revenue"] / 500, c=TAB_ORANGE, alpha=0.65,
                edgecolors=TAB_DARK, linewidths=0.4)
    ax3.set_title("Units vs Margin % (size = revenue)", fontsize=11, fontweight="bold", loc="left")
    ax3.set_xlabel("Units Sold")
    ax3.set_ylabel("Gross Margin %")
    ax3.grid(alpha=0.25)

    fig.savefig(out / "product_customer_03_products.png")
    plt.close(fig)
    print("  wrote product_customer_03_products.png")


def product_03_ltv(marts: Path, out: Path) -> None:
    clv = _load(marts, "clv")
    fig = plt.figure(figsize=(14.5, 9.2), facecolor=TAB_LIGHT)
    _chrome(fig, "Product & Customer Analysis Workbook", PRODUCT_TABS, 1,
            "Customer LTV & Segments",
            "Loyalty tiers · AOV · State concentration")
    gs = fig.add_gridspec(2, 2, left=0.07, right=0.96, top=0.82, bottom=0.08,
                          hspace=0.38, wspace=0.28)

    clv = clv.copy()
    clv["_tier"] = clv["loyalty_tier"].str.lower()
    if set(clv["_tier"]) & {"bronze", "silver", "gold", "platinum"}:
        tier_order = [t for t in ["bronze", "silver", "gold", "platinum"] if t in set(clv["_tier"])]
    else:
        tier_order = list(clv["loyalty_tier"].value_counts().index)
        clv["_tier"] = clv["loyalty_tier"]

    ax1 = fig.add_subplot(gs[0, 0])
    tier_ltv = clv.groupby("_tier")["lifetime_revenue"].mean().reindex(tier_order)
    ax1.bar([t.title() for t in tier_ltv.index], tier_ltv.values,
            color=[TAB_ORANGE, TAB_GRAY, TAB_YELLOW, TAB_TEAL][: len(tier_ltv)])
    ax1.set_title("Avg Lifetime Revenue by Loyalty Tier", fontsize=11, fontweight="bold", loc="left")
    ax1.set_ylabel("LTV ($)")
    ax1.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax1.grid(axis="y", alpha=0.25)

    ax2 = fig.add_subplot(gs[0, 1])
    tier_aov = clv.groupby("_tier")["avg_order_value"].mean().reindex(tier_order)
    ax2.bar([t.title() for t in tier_aov.index], tier_aov.values, color=TAB_BLUE)
    ax2.set_title("Avg Order Value by Loyalty Tier", fontsize=11, fontweight="bold", loc="left")
    ax2.set_ylabel("AOV ($)")
    ax2.grid(axis="y", alpha=0.25)

    ax3 = fig.add_subplot(gs[1, 0])
    ax3.hist(clv["lifetime_revenue"], bins=30, color=TAB_TEAL, alpha=0.85, edgecolor="white")
    ax3.set_title("Customer LTV Distribution", fontsize=11, fontweight="bold", loc="left")
    ax3.set_xlabel("Lifetime Revenue ($)")
    ax3.set_ylabel("Customers")
    ax3.grid(axis="y", alpha=0.25)

    ax4 = fig.add_subplot(gs[1, 1])
    top_states = clv.groupby("state")["lifetime_revenue"].sum().nlargest(10).sort_values()
    ax4.barh(top_states.index, top_states.values / 1000, color=TAB_PURPLE)
    ax4.set_title("Top 10 States by Lifetime Revenue ($K)", fontsize=11, fontweight="bold", loc="left")
    ax4.set_xlabel("Revenue ($K)")
    ax4.grid(axis="x", alpha=0.25)

    fig.savefig(out / "product_customer_02_ltv.png")
    plt.close(fig)
    print("  wrote product_customer_02_ltv.png")


def export_sample_marts(gold: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    mapping = {
        "mart_daily_sales_by_store": "mart_daily_sales_by_store.csv",
        "mart_daily_sales_by_category": "mart_daily_sales_by_category.csv",
        "mart_customer_lifetime_value": "mart_customer_lifetime_value.csv",
        "mart_product_performance": "mart_product_performance.csv",
        "mart_channel_mix": "mart_channel_mix.csv",
    }
    for folder, fname in mapping.items():
        src = gold / folder / "data.csv"
        if src.exists():
            shutil.copy2(src, dest / fname)
            print(f"  sample mart → {dest / fname}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Tableau-styled retail workbook pages")
    parser.add_argument("--marts", type=Path, default=Path("tableau/sample_marts"))
    parser.add_argument("--out", type=Path, default=Path("tableau/screenshots"))
    parser.add_argument("--export-samples", action="store_true",
                        help="Copy data/gold/*/data.csv into tableau/sample_marts/")
    args = parser.parse_args()

    gold = Path("data/gold")
    if args.export_samples or (gold.exists() and not any(Path("tableau/sample_marts").glob("*.csv"))):
        if gold.exists():
            print("Exporting sample marts from gold…")
            export_sample_marts(gold, Path("tableau/sample_marts"))

    marts = _resolve_marts(args.marts)
    args.out.mkdir(parents=True, exist_ok=True)
    print(f"Using marts from {marts}")
    print("Generating Tableau-styled workbook pages…")
    sales_01_overview(marts, args.out)
    sales_02_stores(marts, args.out)
    sales_03_trends(marts, args.out)
    product_01_categories(marts, args.out)
    product_03_ltv(marts, args.out)
    product_02_rankings(marts, args.out)
    print(f"Done → {args.out.resolve()}")


if __name__ == "__main__":
    main()
