# Tableau Report Pack — Retail Sales Pipeline

**Primary BI tool for this repo: Tableau.**  
Honest portfolio design: **workbook briefs + calculated fields + sample mart CSVs + GitHub screenshots**.  
No opaque `.twbx` binaries — hiring managers view dashboards on GitHub and rebuild in Tableau Desktop / Tableau Public from gold mart CSVs.

## Two workbooks (same retail domain, different questions)

| Workbook | Purpose | Screenshots |
|----------|---------|-------------|
| **Sales Performance Workbook** | Executive KPIs, store/region performance, trends & channel mix | `sales_performance_01_overview.png`, `sales_performance_02_stores.png`, `sales_performance_03_trends.png` |
| **Product & Customer Analysis Workbook** | Category mix, customer LTV/segments, product rankings | `product_customer_01_categories.png`, `product_customer_02_ltv.png`, `product_customer_03_products.png` |

## View on GitHub (no Desktop required)

Open the root README **Tableau Reports** section, or browse `tableau/screenshots/`.

Regenerate after refreshing gold marts:

```bash
python scripts/run_local.py --engine pandas
python src/viz/generate_tableau_pages.py --export-samples
```

Committed sample CSVs live in `tableau/sample_marts/` so Desktop recreation works without re-running the full pipeline.

## Rebuild in Tableau Desktop / Public

1. **Connect** → Text file → load CSVs from `tableau/sample_marts/` (or `data/gold/<mart>/data.csv` after a local run).
2. Suggested data sources:

| File | Role |
|------|------|
| `mart_daily_sales_by_store.csv` | Store/day performance |
| `mart_daily_sales_by_category.csv` | Category trends |
| `mart_customer_lifetime_value.csv` | Customer LTV / loyalty |
| `mart_product_performance.csv` | Product rankings |
| `mart_channel_mix.csv` | Channel × payment |

3. Build sheets & dashboards using briefs in [`workbooks/`](workbooks/).
4. Paste calculated fields from [`calculations/`](calculations/) (includes LOD examples).
5. Optional: publish to Tableau Public and link from your profile.

## Folder map

```
tableau/
├── README.md
├── workbooks/          # sheet / filter / calc briefs per workbook
├── calculations/       # Tableau-style calculated fields
├── screenshots/        # PNGs embedded in root README
└── sample_marts/       # CSVs for Desktop rebuild
```
