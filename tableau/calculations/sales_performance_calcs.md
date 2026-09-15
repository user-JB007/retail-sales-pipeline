# Tableau calculated fields — Sales Performance Workbook

```tableau
// Net Revenue (if not already a measure)
[Net Revenue]
SUM([net_revenue])

// Gross Margin %
[Gross Margin %]
SUM([gross_profit]) / SUM([net_revenue])

// Average Order Value
[AOV]
SUM([net_revenue]) / SUM([transactions])

// MoM Revenue % (table calc alternate: use LOOKUP on monthly extract)
[Revenue MoM %]
(SUM([net_revenue]) - LOOKUP(SUM([net_revenue]), -1))
/ ABS(LOOKUP(SUM([net_revenue]), -1))

// FIXED LOD — store share of total revenue
[Store Share of Total]
SUM([net_revenue]) / { FIXED : SUM([net_revenue]) }

// FIXED LOD — region average daily revenue
[Region Avg Daily Revenue]
{ FIXED [region] : AVG([net_revenue]) }
```
