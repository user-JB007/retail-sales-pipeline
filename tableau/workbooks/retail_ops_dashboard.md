# Retail Ops Dashboard — Workbook Brief

**Packaged workbook (v3):** [`Retail_Ops_Dashboard_v3.twbx`](Retail_Ops_Dashboard_v3.twbx)

**Do not open** `Retail_Ops_Dashboard_v2.twbx` — Tableau Desktop shows empty **Sheet 31** (dashboards discarded).

**Department:** Retail Analytics · Ops

## Dashboards (two pages)

1. **Sales** — KPI cards (Net Revenue, Orders, AOV, Gross Margin); Revenue Trend + Revenue by Region; Category Revenue + Channel Revenue (proven Overview layout).
2. **Service** — KPI cards (Ticket Volume, Avg CSAT, Within SLA %, Pending); Ticket Volume Trend + CSAT/Reason/Channel mix (proven Overview layout).

Landing window is **Sales** (maximized). Worksheet tabs stay **visible** (hiding them in v2 contributed to Tableau discarding UI).

## Reliable singles (if combined ever looks empty)

- [`Retail_Sales_Dashboard_v3.twbx`](Retail_Sales_Dashboard_v3.twbx) — opens on **1. Overview**
- [`Retail_Service_Dashboard_v3.twbx`](Retail_Service_Dashboard_v3.twbx) — opens on **1. Overview**

## Parameters

- **Top N Stores** (5–25, default 10) — retained as a parameter (no INDEX Top-N filter)
- **Aging Threshold Hours** (24–336, default 72) — Service aging logic

## Sources (embedded)

Sales marts + `mart_service_performance.csv` (+ Hyper extracts when present).

## Related packs

- [`Retail_Sales_Report.twbx`](Retail_Sales_Report.twbx)
- [`Retail_Service_Satisfaction_Report.twbx`](Retail_Service_Satisfaction_Report.twbx)
