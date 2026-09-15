# Power BI Report Pack — Retail Sales Pipeline

This folder documents an honest portfolio Power BI design: **semantic model + DAX + page briefs + GitHub screenshots**.  
No opaque `.pbix` binaries — hiring managers can view the dashboards on GitHub and recreate them in Power BI Desktop from the gold mart CSVs.

## View on GitHub (no Desktop required)

Open the repo README **Power BI Reports** section, or browse:

`reports/powerbi/screenshots/`

| # | Screenshot | Page |
|---|------------|------|
| 01 | `01_executive_overview.png` | KPI cards, daily revenue, region & category mix |
| 02 | `02_store_performance.png` | Top stores, store type, regional margin |
| 03 | `03_category_trends.png` | Monthly category trends & share |
| 04 | `04_customer_ltv.png` | Loyalty LTV / AOV / state concentration |
| 05 | `05_product_rankings.png` | Top products, brands, margin scatter |
| 06 | `06_channel_mix.png` | Channel × payment heatmap |

Regenerate screenshots after refreshing gold marts:

```bash
python scripts/run_local.py --engine pandas
python src/viz/generate_powerbi_pages.py --export-samples
```

Committed sample CSVs live in `powerbi/sample_marts/` so Desktop recreation works without re-running the full pipeline.

## Recreate in Power BI Desktop

1. **Get data** → Text/CSV (or Parquet if preferred) from either:
   - `powerbi/sample_marts/*.csv` (committed samples), or
   - `data/gold/<mart>/data.csv` after `scripts/run_local.py`
2. Load these tables (rename as shown):

| File | Model table |
|------|-------------|
| `mart_daily_sales_by_store.csv` | `fact_daily_store_sales` |
| `mart_daily_sales_by_category.csv` | `fact_daily_category_sales` |
| `mart_customer_lifetime_value.csv` | `fact_customer_ltv` |
| `mart_product_performance.csv` | `fact_product_performance` |
| `mart_channel_mix.csv` | `fact_channel_mix` |

3. Optional: mark `transaction_date` as a Date hierarchy; create a simple `dim_date` via **New table** if you want calendar intelligence.
4. Paste measures from [`model/measures.dax`](model/measures.dax) into the model.
5. Build pages using the briefs in [`pages/`](pages/) — visuals match the committed screenshots.
6. Star schema notes: [`model/semantic_model.md`](model/semantic_model.md).

## Design intent

Gold marts are the BI source of truth (medallion gold). Screenshots prove the story for profile visitors; DAX + page briefs prove you can ship the same report in Desktop / Fabric / service.
