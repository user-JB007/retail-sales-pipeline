# Tableau calculated fields — Product & Customer Analysis Workbook

```tableau
// Customer LTV
[Lifetime Revenue]
SUM([lifetime_revenue])

// Orders per customer
[Order Count]
SUM([order_count])

// INCLUDE LOD — avg LTV within loyalty tier (per customer grain)
[Avg LTV in Tier]
{ INCLUDE [loyalty_tier] : AVG([lifetime_revenue]) }

// FIXED LOD — customer segment label by LTV quartile-ish threshold
[LTV Segment]
IF { FIXED [customer_id] : SUM([lifetime_revenue]) } >= 10000 THEN "High"
ELSEIF { FIXED [customer_id] : SUM([lifetime_revenue]) } >= 5000 THEN "Medium"
ELSE "Low"
END

// Product contribution % of category
[Product Share of Category]
SUM([net_revenue]) / { FIXED [category] : SUM([net_revenue]) }

// Rank products within category
[Product Rank in Category]
RANK_UNIQUE(SUM([net_revenue]), 'desc')
```
