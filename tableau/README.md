# Tableau Report Pack — Retail Sales Pipeline

**Primary BI tool for this repo: Tableau.**  
Workbook briefs, calculated fields, gold mart CSVs, and GitHub screenshots. Rebuild in Tableau Desktop / Tableau Public from the mart CSVs under `tableau/marts/`.

## Two workbooks (different business subjects)

| Workbook | Purpose | Screenshots |
|----------|---------|-------------|
| **Sales Report** | Revenue, orders, stores/regions, categories/products, trends | `sales_01_overview.png`, `sales_02_stores.png`, `sales_03_trends.png` |
| **Customer Satisfaction & Service Report** | CSAT, SLA attainment, pending queue, aging, reason/channel | `service_01_overview.png`, `service_02_sla.png`, `service_03_pending_aging.png` |

## View on GitHub (no Desktop required)

Open the root README **Tableau Reports** section, or browse `tableau/screenshots/`.

Regenerate after refreshing gold marts:

```bash
python scripts/run_local.py --engine pandas
python src/viz/generate_tableau_pages.py --export-marts
```

Committed mart CSVs live in `tableau/marts/` so Desktop recreation works without re-running the full pipeline.

## Rebuild in Tableau Desktop / Public

1. **Connect** → Text file → load CSVs from `tableau/marts/` (or `data/gold/<mart>/data.csv` after a local run).
2. Suggested data sources:

| File | Role |
|------|------|
| `mart_daily_sales_by_store.csv` | Store/day performance |
| `mart_daily_sales_by_category.csv` | Category trends |
| `mart_customer_lifetime_value.csv` | Customer LTV / loyalty |
| `mart_product_performance.csv` | Product rankings |
| `mart_channel_mix.csv` | Channel × payment |
| `mart_service_performance.csv` | Service tickets / SLA / CSAT |

3. Build sheets & dashboards using briefs in [`workbooks/`](workbooks/).
4. Paste calculated fields from [`calculations/`](calculations/) (includes LOD examples).

## Folder map

```
tableau/
├── README.md
├── workbooks/          # sheet / filter / calc briefs per workbook
├── calculations/       # Tableau-style calculated fields
├── screenshots/        # PNGs embedded in root README
└── marts/              # CSVs for Desktop rebuild
```
