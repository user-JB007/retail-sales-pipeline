# Retail Ops Dashboard — Workbook Brief

**Packaged workbook (main):** [`Retail_Ops_Dashboard.twbx`](Retail_Ops_Dashboard.twbx)

**Department:** Retail Analytics · Ops

## Dashboards (two pages)

1. **Sales** — KPI cards (Net Revenue, Orders, AOV, Gross Margin); Revenue Trend + Revenue by Region; Channel Revenue + Top Stores. Click region/store to filter.
2. **Service** — KPI cards (Ticket Volume, Avg CSAT, Within SLA %, Pending, Avg Resolve); Ticket Volume Trend + Reason/Channel mix; Open Aging Buckets + Within SLA by Region + Open Reasons. Click reason/region to filter.

Individual worksheet windows are **hidden** so Desktop tabs emphasize these two dashboards. Opening the pack lands on **Sales** (maximized).

## Parameters

- **Top N Stores** (5–25, default 10) — Sales top-stores ranking
- **Aging Threshold Hours** (24–336, default 72) — Service aging logic

## Sources (embedded)

Sales marts + `mart_service_performance.csv` (+ Hyper extracts when present).

## Related standalone packs

- [`Retail_Sales_Report.twbx`](Retail_Sales_Report.twbx)
- [`Retail_Service_Satisfaction_Report.twbx`](Retail_Service_Satisfaction_Report.twbx)
