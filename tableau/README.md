# Tableau Report Pack — Retail Sales Pipeline

**Primary BI deliverable: packaged `.twbx` workbooks** under [`workbooks/`](workbooks/).  
Mart CSVs, calculated-field notes, and screenshots support rebuild and GitHub preview.

## Packaged workbooks

| File | Dashboards | Parameter |
|------|------------|-----------|
| **[`workbooks/Retail_Ops_Dashboard.twbx`](workbooks/Retail_Ops_Dashboard.twbx)** *(main)* | **Sales** · **Service** | Top N Stores (5–25) · Aging Threshold Hours (24–336) |
| [`workbooks/Retail_Sales_Report.twbx`](workbooks/Retail_Sales_Report.twbx) | 1. Overview · 2. Stores and Regions · 3. Trends | Top N Stores (5–25) |
| [`workbooks/Retail_Service_Satisfaction_Report.twbx`](workbooks/Retail_Service_Satisfaction_Report.twbx) | 1. Overview · 2. SLA Performance · 3. Pending and Aging | Aging Threshold Hours (24–336) |

Each `.twbx` embeds the TWB XML, gold mart CSVs (`Data/Datasources/`), and Hyper extracts (`Data/Extracts/`).

### How to open

1. Install [Tableau Desktop](https://www.tableau.com/products/desktop) or [Tableau Public](https://public.tableau.com/en-us/s/download).
2. File → Open → **`Retail_Ops_Dashboard.twbx`** (or double-click). Standalone sales/service packs remain available.
3. Land on **Sales**; switch to **Service** for SLA/CSAT. Worksheet KPI tabs are hidden — use the two dashboard tabs. Adjust **Top N Stores** / **Aging Threshold Hours** as needed.

### Rebuild

```bash
# from repo root (venv with tableauhyperapi)
python scripts/build_hyper.py
python scripts/build_workbook.py
```

Authoring scripts mirror the airline-maintenance-ops pattern (`scripts/build_workbook.py`, `scripts/build_hyper.py`).

## Workbooks

| Workbook | Purpose | Screenshots (secondary) |
|----------|---------|-------------------------|
| **Retail Ops Dashboard** | Combined two-page suite (Sales + Service & SLA) | `screenshots/sales_*.png`, `screenshots/service_*.png` |
| **Sales Report** | Revenue, orders, stores/regions, categories/products, trends | `screenshots/sales_*.png` |
| **Customer Satisfaction & Service Report** | CSAT, SLA attainment, pending queue, aging, reason/channel | `screenshots/service_*.png` |

## Data sources (embedded + `marts/`)

| File | Role |
|------|------|
| `mart_daily_sales_by_store.csv` | Store/day performance (Sales primary) |
| `mart_daily_sales_by_category.csv` | Category trends |
| `mart_channel_mix.csv` | Channel × payment |
| `mart_product_performance.csv` | Product rankings |
| `mart_service_performance.csv` | Service tickets / SLA / CSAT |
| `mart_customer_lifetime_value.csv` | Customer LTV (available for extension) |

## Calculated fields

See [`calculations/`](calculations/) — includes AOV, Gross Margin %, Store Share LOD, Within SLA %, Aging Bucket, Pending Flag.

## Folder map

```
tableau/
├── README.md
├── workbooks/          # .twb + .twbx (primary)
├── calculations/
├── screenshots/        # secondary GitHub preview
├── marts/              # gold CSVs
└── Data/Extracts/      # .hyper (also packaged inside twbx)
```
