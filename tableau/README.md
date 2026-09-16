# Tableau Report Pack — Retail Sales Pipeline

**Primary BI deliverable: packaged `.twbx` workbooks** under [`workbooks/`](workbooks/).  
Mart CSVs, calculated-field notes, and screenshots support rebuild and GitHub preview.

## Packaged workbooks

| File | Dashboards | Notes |
|------|------------|-------|
| **[`workbooks/Retail_Ops_Dashboard_v3.twbx`](workbooks/Retail_Ops_Dashboard_v3.twbx)** *(combined)* | **Sales** · **Service** | Open this for both pages in one file |
| [`workbooks/Retail_Sales_Dashboard_v3.twbx`](workbooks/Retail_Sales_Dashboard_v3.twbx) | 1. Overview · 2. Stores · 3. Trends | Reliable single — lands on Overview |
| [`workbooks/Retail_Service_Dashboard_v3.twbx`](workbooks/Retail_Service_Dashboard_v3.twbx) | 1. Overview · 2. SLA · 3. Pending | Reliable single — lands on Overview |
| [`workbooks/Retail_Sales_Report.twbx`](workbooks/Retail_Sales_Report.twbx) | same as Sales Dashboard v3 | Legacy filename |
| [`workbooks/Retail_Service_Satisfaction_Report.twbx`](workbooks/Retail_Service_Satisfaction_Report.twbx) | same as Service Dashboard v3 | Legacy filename |

**Avoid** `Retail_Ops_Dashboard_v2.twbx` — Tableau Desktop opens it as empty **Sheet 31** (dashboards/worksheets discarded).

Each `.twbx` embeds the TWB XML, gold mart CSVs (`Data/Datasources/`), and Hyper extracts (`Data/Extracts/`).

### How to open

1. Install [Tableau Desktop](https://www.tableau.com/products/desktop) or [Tableau Public](https://public.tableau.com/en-us/s/download).
2. File → Open → **`Retail_Ops_Dashboard_v3.twbx`** (or double-click).
3. You should see **Sales** and **Service** dashboard tabs with KPI cards + charts filled — not a blank sheet.
4. Fallback: open `Retail_Sales_Dashboard_v3.twbx` / `Retail_Service_Dashboard_v3.twbx` and click the Overview dashboard tab (grid icon).
5. Worksheet tabs are intentionally visible (v2 hid them; Tableau then nuked the UI).

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
