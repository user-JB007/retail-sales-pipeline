"""Generate Power BI–styled executive report page PNGs for GitHub visitors.

Reads gold mart CSVs (or powerbi/sample_marts fallback). Writes 6 polished
screenshots under reports/powerbi/screenshots/.

    # Prefer fresh gold after pipeline run
    python scripts/run_local.py --engine pandas
    python src/viz/generate_powerbi_pages.py

    # Or use committed sample marts
    python src/viz/generate_powerbi_pages.py --marts powerbi/sample_marts
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

PBI_YELLOW = "#F2C811"
PBI_DARK = "#252423"
PBI_NAVY = "#118DFF"
PBI_TEAL = "#01B8AA"
PBI_RED = "#FD625E"
PBI_ORANGE = "#FE9666"
PBI_PURPLE = "#A66999"
PBI_GRAY = "#605E5C"
PBI_LIGHT = "#F3F2F1"
PBI_WHITE = "#FFFFFF"
PBI_BORDER = "#E1DFDD"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "figure.dpi": 140,
        "savefig.dpi": 160,
        "savefig.facecolor": PBI_LIGHT,
        "axes.facecolor": PBI_WHITE,
        "axes.edgecolor": PBI_BORDER,
        "axes.labelcolor": PBI_DARK,
        "xtick.color": PBI_GRAY,
        "ytick.color": PBI_GRAY,
        "text.color": PBI_DARK,
    }
)

PAGES = [
    "Executive Overview",
    "Store Performance",
    "Category Trends",
    "Customer LTV",
    "Product Rankings",
    "Channel Mix",
]

MART_FILES = {
    "store": "mart_daily_sales_by_store.csv",
    "category": "mart_daily_sales_by_category.csv",
    "clv": "mart_customer_lifetime_value.csv",
    "product": "mart_product_performance.csv",
    "channel": "mart_channel_mix.csv",
}


def _resolve_marts(marts: Path) -> Path:
    """Prefer --marts; else data/gold flattened; else powerbi/sample_marts."""
    if marts.exists() and any(marts.glob("*.csv")):
        return marts
    gold = Path("data/gold")
    if gold.exists():
        # Flatten gold/*/data.csv into a temp-like sample folder if CSVs already named
        flat = Path("powerbi/sample_marts")
        flat.mkdir(parents=True, exist_ok=True)
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
    sample = Path("powerbi/sample_marts")
    if sample.exists() and any(sample.glob("*.csv")):
        return sample
    raise FileNotFoundError(
        "No mart CSVs found. Run `python scripts/run_local.py --engine pandas` "
        "or pass --marts powerbi/sample_marts"
    )


def _load(marts: Path, key: str) -> pd.DataFrame:
    path = marts / MART_FILES[key]
    if not path.exists():
        # gold layout fallback
        alt = Path("data/gold") / MART_FILES[key].replace(".csv", "") / "data.csv"
        if alt.exists():
            return pd.read_csv(alt)
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def _chrome(fig: plt.Figure, page_idx: int, title: str, filters: str) -> None:
    fig.patches.append(
        mpatches.FancyBboxPatch(
            (0, 0.965), 1, 0.035, transform=fig.transFigure,
            boxstyle="square,pad=0", facecolor=PBI_YELLOW, edgecolor="none",
            clip_on=False, zorder=0,
        )
    )
    fig.patches.append(
        mpatches.FancyBboxPatch(
            (0, 0.905), 1, 0.06, transform=fig.transFigure,
            boxstyle="square,pad=0", facecolor=PBI_DARK, edgecolor="none",
            clip_on=False, zorder=0,
        )
    )
    fig.text(0.02, 0.935, "Retail Sales Pipeline", fontsize=9, color=PBI_YELLOW,
             fontweight="bold", va="center", transform=fig.transFigure)
    fig.text(0.02, 0.918, title, fontsize=14, color=PBI_WHITE, fontweight="bold",
             va="center", transform=fig.transFigure)
    fig.text(0.98, 0.935, "Power BI · Portfolio Demo", fontsize=8, color="#A19F9D",
             ha="right", va="center", transform=fig.transFigure)
    fig.patches.append(
        mpatches.FancyBboxPatch(
            (0.02, 0.855), 0.96, 0.038, transform=fig.transFigure,
            boxstyle="round,pad=0.002,rounding_size=0.008", facecolor=PBI_WHITE,
            edgecolor=PBI_BORDER, linewidth=1, clip_on=False, zorder=1,
        )
    )
    fig.text(0.035, 0.874, f"Filters  |  {filters}", fontsize=8, color=PBI_GRAY,
             va="center", transform=fig.transFigure)
    n = len(PAGES)
    tab_w = 0.96 / n
    for i, name in enumerate(PAGES):
        x = 0.02 + i * tab_w
        active = i == page_idx
        fig.patches.append(
            mpatches.FancyBboxPatch(
                (x, 0.008), tab_w - 0.004, 0.032, transform=fig.transFigure,
                boxstyle="round,pad=0.001,rounding_size=0.004",
                facecolor=PBI_YELLOW if active else PBI_WHITE,
                edgecolor=PBI_BORDER, linewidth=0.8, clip_on=False, zorder=1,
            )
        )
        fig.text(x + (tab_w - 0.004) / 2, 0.024, name, fontsize=6.5, ha="center",
                 va="center", color=PBI_DARK if active else PBI_GRAY,
                 fontweight="bold" if active else "normal", transform=fig.transFigure)


def _kpi_card(ax, value: str, label: str, accent: str) -> None:
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0.02, 0.08), 0.96, 0.84, transform=ax.transAxes,
                               facecolor=PBI_WHITE, edgecolor=PBI_BORDER, linewidth=1.2))
    ax.add_patch(plt.Rectangle((0.02, 0.08), 0.04, 0.84, transform=ax.transAxes,
                               facecolor=accent, edgecolor="none"))
    ax.text(0.55, 0.58, value, ha="center", va="center", fontsize=17, fontweight="bold",
            color=PBI_DARK, transform=ax.transAxes)
    ax.text(0.55, 0.28, label, ha="center", va="center", fontsize=8, color=PBI_GRAY,
            transform=ax.transAxes)


def page_01(marts: Path, out: Path) -> None:
    store = _load(marts, "store")
    store["transaction_date"] = pd.to_datetime(store["transaction_date"])
    cat = _load(marts, "category")
    daily = store.groupby("transaction_date", as_index=False).agg(
        net_revenue=("net_revenue", "sum"),
        transactions=("transactions", "sum"),
        units_sold=("units_sold", "sum"),
        gross_profit=("gross_profit", "sum"),
    ).sort_values("transaction_date")
    daily["aov"] = daily["net_revenue"] / daily["transactions"].replace(0, np.nan)
    # MoM from monthly rollup
    monthly = daily.set_index("transaction_date").resample("MS").agg(
        net_revenue=("net_revenue", "sum"), transactions=("transactions", "sum")
    )
    monthly["aov"] = monthly["net_revenue"] / monthly["transactions"].replace(0, np.nan)
    mom = monthly["net_revenue"].pct_change().iloc[-1] * 100 if len(monthly) > 1 else 0.0

    total_rev = daily["net_revenue"].sum()
    total_txn = daily["transactions"].sum()
    aov = total_rev / total_txn if total_txn else 0
    margin = daily["gross_profit"].sum() / total_rev * 100 if total_rev else 0

    fig = plt.figure(figsize=(14.5, 9.2), facecolor=PBI_LIGHT)
    _chrome(fig, 0, "01 — Executive Overview", "Date: full year  ·  Region: All  ·  Channel: All  ·  Store type: All")
    gs = fig.add_gridspec(3, 4, left=0.05, right=0.97, top=0.83, bottom=0.07, hspace=0.42, wspace=0.32)
    kpis = [
        (f"${total_rev/1e6:.2f}M", "Net Revenue", PBI_TEAL),
        (f"{int(total_txn):,}", "Transactions", PBI_NAVY),
        (f"${aov:,.0f}", "Avg Order Value", PBI_ORANGE),
        (f"{mom:+.1f}%", "Revenue MoM", PBI_PURPLE if mom >= 0 else PBI_RED),
    ]
    for i, (v, lab, c) in enumerate(kpis):
        _kpi_card(fig.add_subplot(gs[0, i]), v, lab, c)

    ax1 = fig.add_subplot(gs[1, :2])
    ax1.fill_between(daily["transaction_date"], daily["net_revenue"] / 1000, color=PBI_TEAL, alpha=0.25)
    ax1.plot(daily["transaction_date"], daily["net_revenue"] / 1000, color=PBI_TEAL, linewidth=1.4)
    ax1.set_title("Daily Net Revenue ($K)", fontsize=11, fontweight="bold", loc="left")
    ax1.set_ylabel("Revenue ($K)", fontsize=8)
    ax1.grid(axis="y", alpha=0.25)
    ax1.tick_params(axis="x", rotation=30, labelsize=7)

    ax2 = fig.add_subplot(gs[1, 2:])
    by_region = store.groupby("region")["net_revenue"].sum().sort_values(ascending=True)
    ax2.barh(by_region.index, by_region.values / 1000, color=PBI_NAVY)
    ax2.set_title("Net Revenue by Region ($K)", fontsize=11, fontweight="bold", loc="left")
    ax2.set_xlabel("Revenue ($K)")
    ax2.grid(axis="x", alpha=0.25)

    ax3 = fig.add_subplot(gs[2, :2])
    by_cat = cat.groupby("category")["net_revenue"].sum().sort_values(ascending=False)
    ax3.bar(by_cat.index, by_cat.values / 1000, color=[PBI_TEAL, PBI_NAVY, PBI_ORANGE, PBI_PURPLE, PBI_RED, "#8764B8"][: len(by_cat)])
    ax3.set_title("Revenue by Category ($K)", fontsize=11, fontweight="bold", loc="left")
    ax3.set_ylabel("Revenue ($K)")
    ax3.tick_params(axis="x", rotation=20)
    ax3.grid(axis="y", alpha=0.25)

    ax4 = fig.add_subplot(gs[2, 2:])
    ax4.axis("off")
    ax4.text(0.05, 0.9, "Snapshot", fontsize=12, fontweight="bold", color=PBI_DARK, transform=ax4.transAxes)
    snap = (
        f"Gross margin          {margin:.1f}%\n"
        f"Units sold            {int(daily['units_sold'].sum()):,}\n"
        f"Active store-days     {len(store):,}\n"
        f"Categories            {store.merge(cat[['transaction_date','category']].drop_duplicates(), on='transaction_date', how='left')['category'].nunique() if False else by_cat.shape[0]}\n"
        f"Latest month revenue  ${monthly['net_revenue'].iloc[-1]/1e3:,.0f}K"
    )
    # simpler categories count
    snap = (
        f"Gross margin          {margin:.1f}%\n"
        f"Units sold            {int(daily['units_sold'].sum()):,}\n"
        f"Store-day rows        {len(store):,}\n"
        f"Product categories    {by_cat.shape[0]}\n"
        f"Latest month revenue  ${monthly['net_revenue'].iloc[-1]/1e3:,.0f}K"
    )
    ax4.text(0.05, 0.75, snap, fontsize=11, family="monospace", color=PBI_GRAY, va="top",
             transform=ax4.transAxes,
             bbox=dict(boxstyle="round,pad=0.6", facecolor=PBI_WHITE, edgecolor=PBI_TEAL, linewidth=1.5))

    fig.savefig(out / "01_executive_overview.png")
    plt.close(fig)
    print("  wrote 01_executive_overview.png")


def page_02(marts: Path, out: Path) -> None:
    store = _load(marts, "store")
    by_store = store.groupby(["store_name", "region", "store_type"], as_index=False).agg(
        net_revenue=("net_revenue", "sum"),
        transactions=("transactions", "sum"),
        gross_profit=("gross_profit", "sum"),
        avg_order_value=("avg_order_value", "mean"),
    )
    by_store["margin_pct"] = by_store["gross_profit"] / by_store["net_revenue"] * 100
    top = by_store.nlargest(12, "net_revenue")

    fig = plt.figure(figsize=(14.5, 9.2), facecolor=PBI_LIGHT)
    _chrome(fig, 1, "02 — Store Performance", "Ranked by net revenue  ·  Region: All  ·  Store type: All")
    gs = fig.add_gridspec(2, 2, left=0.08, right=0.96, top=0.82, bottom=0.08, hspace=0.38, wspace=0.28)

    ax1 = fig.add_subplot(gs[0, :])
    ax1.barh(top["store_name"][::-1], top["net_revenue"][::-1] / 1000, color=PBI_TEAL)
    ax1.set_title("Top 12 Stores by Net Revenue ($K)", fontsize=11, fontweight="bold", loc="left")
    ax1.set_xlabel("Net Revenue ($K)")
    ax1.grid(axis="x", alpha=0.25)

    ax2 = fig.add_subplot(gs[1, 0])
    type_rev = by_store.groupby("store_type")["net_revenue"].sum().sort_values(ascending=False)
    ax2.bar(type_rev.index, type_rev.values / 1000, color=[PBI_NAVY, PBI_TEAL, PBI_ORANGE][: len(type_rev)])
    ax2.set_title("Revenue by Store Type ($K)", fontsize=11, fontweight="bold", loc="left")
    ax2.set_ylabel("Revenue ($K)")
    ax2.grid(axis="y", alpha=0.25)

    ax3 = fig.add_subplot(gs[1, 1])
    region_margin = by_store.groupby("region").agg(
        revenue=("net_revenue", "sum"), profit=("gross_profit", "sum")
    )
    region_margin["margin"] = region_margin["profit"] / region_margin["revenue"] * 100
    region_margin = region_margin.sort_values("margin")
    ax3.barh(region_margin.index, region_margin["margin"], color=PBI_PURPLE)
    ax3.set_title("Gross Margin % by Region", fontsize=11, fontweight="bold", loc="left")
    ax3.set_xlabel("Margin %")
    ax3.grid(axis="x", alpha=0.25)

    fig.savefig(out / "02_store_performance.png")
    plt.close(fig)
    print("  wrote 02_store_performance.png")


def page_03(marts: Path, out: Path) -> None:
    cat = _load(marts, "category")
    cat["transaction_date"] = pd.to_datetime(cat["transaction_date"])
    monthly = (
        cat.assign(month=cat["transaction_date"].dt.to_period("M").dt.to_timestamp())
        .groupby(["month", "category"], as_index=False)["net_revenue"].sum()
    )
    pivot = monthly.pivot(index="month", columns="category", values="net_revenue").fillna(0)

    fig = plt.figure(figsize=(14.5, 9.2), facecolor=PBI_LIGHT)
    _chrome(fig, 2, "03 — Category Trends", "Monthly net revenue by product category")
    gs = fig.add_gridspec(2, 2, left=0.07, right=0.96, top=0.82, bottom=0.08, hspace=0.4, wspace=0.28)

    ax1 = fig.add_subplot(gs[0, :])
    colors = [PBI_TEAL, PBI_NAVY, PBI_ORANGE, PBI_PURPLE, PBI_RED, "#8764B8", "#3599B8"]
    for i, col in enumerate(pivot.columns):
        ax1.plot(pivot.index, pivot[col] / 1000, label=col, linewidth=2, color=colors[i % len(colors)])
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
    ax3.barh(units.index, units.values, color=PBI_NAVY)
    ax3.set_title("Units Sold by Category", fontsize=11, fontweight="bold", loc="left")
    ax3.set_xlabel("Units")
    ax3.grid(axis="x", alpha=0.25)

    fig.savefig(out / "03_category_trends.png")
    plt.close(fig)
    print("  wrote 03_category_trends.png")


def page_04(marts: Path, out: Path) -> None:
    clv = _load(marts, "clv")
    fig = plt.figure(figsize=(14.5, 9.2), facecolor=PBI_LIGHT)
    _chrome(fig, 3, "04 — Customer Lifetime Value", "Loyalty tiers · AOV · State concentration")
    gs = fig.add_gridspec(2, 2, left=0.07, right=0.96, top=0.82, bottom=0.08, hspace=0.38, wspace=0.28)

    tier_order = ["bronze", "silver", "gold", "platinum"]
    tier_order = [t for t in tier_order if t in clv["loyalty_tier"].str.lower().unique()] or sorted(clv["loyalty_tier"].unique())
    # normalize
    clv["_tier"] = clv["loyalty_tier"].str.lower()
    if set(clv["_tier"]) & {"bronze", "silver", "gold", "platinum"}:
        tier_order = [t for t in ["bronze", "silver", "gold", "platinum"] if t in set(clv["_tier"])]
    else:
        tier_order = list(clv["loyalty_tier"].value_counts().index)
        clv["_tier"] = clv["loyalty_tier"]

    ax1 = fig.add_subplot(gs[0, 0])
    tier_ltv = clv.groupby("_tier")["lifetime_revenue"].mean().reindex(tier_order)
    ax1.bar([t.title() for t in tier_ltv.index], tier_ltv.values, color=[PBI_ORANGE, PBI_GRAY, PBI_YELLOW, PBI_TEAL][: len(tier_ltv)])
    ax1.set_title("Avg Lifetime Revenue by Loyalty Tier", fontsize=11, fontweight="bold", loc="left")
    ax1.set_ylabel("LTV ($)")
    ax1.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax1.grid(axis="y", alpha=0.25)

    ax2 = fig.add_subplot(gs[0, 1])
    tier_aov = clv.groupby("_tier")["avg_order_value"].mean().reindex(tier_order)
    ax2.bar([t.title() for t in tier_aov.index], tier_aov.values, color=PBI_NAVY)
    ax2.set_title("Avg Order Value by Loyalty Tier", fontsize=11, fontweight="bold", loc="left")
    ax2.set_ylabel("AOV ($)")
    ax2.grid(axis="y", alpha=0.25)

    ax3 = fig.add_subplot(gs[1, 0])
    ax3.hist(clv["lifetime_revenue"], bins=30, color=PBI_TEAL, alpha=0.85, edgecolor="white")
    ax3.set_title("Customer LTV Distribution", fontsize=11, fontweight="bold", loc="left")
    ax3.set_xlabel("Lifetime Revenue ($)")
    ax3.set_ylabel("Customers")
    ax3.grid(axis="y", alpha=0.25)

    ax4 = fig.add_subplot(gs[1, 1])
    top_states = clv.groupby("state")["lifetime_revenue"].sum().nlargest(10).sort_values()
    ax4.barh(top_states.index, top_states.values / 1000, color=PBI_PURPLE)
    ax4.set_title("Top 10 States by Lifetime Revenue ($K)", fontsize=11, fontweight="bold", loc="left")
    ax4.set_xlabel("Revenue ($K)")
    ax4.grid(axis="x", alpha=0.25)

    fig.savefig(out / "04_customer_ltv.png")
    plt.close(fig)
    print("  wrote 04_customer_ltv.png")


def page_05(marts: Path, out: Path) -> None:
    prod = _load(marts, "product")
    fig = plt.figure(figsize=(14.5, 9.2), facecolor=PBI_LIGHT)
    _chrome(fig, 4, "05 — Product Rankings", "Top products by net revenue · Brand & category mix")
    gs = fig.add_gridspec(2, 2, left=0.10, right=0.96, top=0.82, bottom=0.08, hspace=0.4, wspace=0.3)

    top = prod.nlargest(15, "net_revenue")
    ax1 = fig.add_subplot(gs[0, :])
    labels = top["product_name"].str.slice(0, 28)
    ax1.barh(labels[::-1], top["net_revenue"][::-1] / 1000, color=PBI_TEAL)
    ax1.set_title("Top 15 Products by Net Revenue ($K)", fontsize=11, fontweight="bold", loc="left")
    ax1.set_xlabel("Net Revenue ($K)")
    ax1.grid(axis="x", alpha=0.25)

    ax2 = fig.add_subplot(gs[1, 0])
    brand = prod.groupby("brand")["net_revenue"].sum().nlargest(8).sort_values()
    ax2.barh(brand.index, brand.values / 1000, color=PBI_NAVY)
    ax2.set_title("Top Brands by Revenue ($K)", fontsize=11, fontweight="bold", loc="left")
    ax2.set_xlabel("Revenue ($K)")
    ax2.grid(axis="x", alpha=0.25)

    ax3 = fig.add_subplot(gs[1, 1])
    prod = prod.copy()
    prod["margin_pct"] = prod["gross_profit"] / prod["net_revenue"] * 100
    scatter = prod.sample(min(len(prod), 80), random_state=7) if len(prod) > 80 else prod
    ax3.scatter(scatter["units_sold"], scatter["margin_pct"], s=scatter["net_revenue"] / 500,
                c=PBI_ORANGE, alpha=0.65, edgecolors=PBI_DARK, linewidths=0.4)
    ax3.set_title("Units vs Margin % (size = revenue)", fontsize=11, fontweight="bold", loc="left")
    ax3.set_xlabel("Units Sold")
    ax3.set_ylabel("Gross Margin %")
    ax3.grid(alpha=0.25)

    fig.savefig(out / "05_product_rankings.png")
    plt.close(fig)
    print("  wrote 05_product_rankings.png")


def page_06(marts: Path, out: Path) -> None:
    ch = _load(marts, "channel")
    fig = plt.figure(figsize=(14.5, 9.2), facecolor=PBI_LIGHT)
    _chrome(fig, 5, "06 — Channel & Payment Mix", "Channel × payment method revenue contribution")
    gs = fig.add_gridspec(2, 2, left=0.08, right=0.96, top=0.82, bottom=0.08, hspace=0.4, wspace=0.3)

    by_channel = ch.groupby("channel")["net_revenue"].sum().sort_values(ascending=False)
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.pie(by_channel, labels=by_channel.index, autopct="%1.0f%%",
            colors=[PBI_TEAL, PBI_NAVY, PBI_ORANGE, PBI_PURPLE][: len(by_channel)],
            textprops={"fontsize": 9}, startangle=90, wedgeprops={"edgecolor": "white", "linewidth": 1.5})
    ax1.set_title("Revenue by Channel", fontsize=11, fontweight="bold")

    by_pay = ch.groupby("payment_method")["net_revenue"].sum().sort_values(ascending=False)
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.bar(by_pay.index, by_pay.values / 1000, color=PBI_NAVY)
    ax2.set_title("Revenue by Payment Method ($K)", fontsize=11, fontweight="bold", loc="left")
    ax2.set_ylabel("Revenue ($K)")
    ax2.tick_params(axis="x", rotation=20)
    ax2.grid(axis="y", alpha=0.25)

    ax3 = fig.add_subplot(gs[1, :])
    pivot = ch.groupby(["channel", "payment_method"])["net_revenue"].sum().unstack(fill_value=0)
    sns.heatmap(pivot / 1000, ax=ax3, cmap="YlGnBu", annot=True, fmt=".0f",
                annot_kws={"size": 8}, linewidths=0.5, linecolor="white",
                cbar_kws={"label": "Revenue ($K)"})
    ax3.set_title("Channel × Payment Method Heatmap ($K)", fontsize=11, fontweight="bold", loc="left", pad=10)
    ax3.set_xlabel("Payment Method")
    ax3.set_ylabel("Channel")

    fig.savefig(out / "06_channel_mix.png")
    plt.close(fig)
    print("  wrote 06_channel_mix.png")


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
    parser = argparse.ArgumentParser(description="Generate Power BI–styled retail report pages")
    parser.add_argument("--marts", type=Path, default=Path("powerbi/sample_marts"))
    parser.add_argument("--out", type=Path, default=Path("reports/powerbi/screenshots"))
    parser.add_argument("--export-samples", action="store_true",
                        help="Copy data/gold/*/data.csv into powerbi/sample_marts/")
    args = parser.parse_args()

    gold = Path("data/gold")
    if args.export_samples or (gold.exists() and not any(Path("powerbi/sample_marts").glob("*.csv"))):
        if gold.exists():
            print("Exporting sample marts from gold…")
            export_sample_marts(gold, Path("powerbi/sample_marts"))

    marts = _resolve_marts(args.marts)
    args.out.mkdir(parents=True, exist_ok=True)
    print(f"Using marts from {marts}")
    print("Generating Power BI–styled report pages…")
    page_01(marts, args.out)
    page_02(marts, args.out)
    page_03(marts, args.out)
    page_04(marts, args.out)
    page_05(marts, args.out)
    page_06(marts, args.out)
    print(f"Done → {args.out.resolve()}")


if __name__ == "__main__":
    main()
