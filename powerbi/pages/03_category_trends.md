# Page 03 — Category Trends

**Filters:** Date, Category

## Visuals

1. **Multi-line:** Monthly Net Revenue by Category
2. **Donut:** Category Revenue Share (full period)
3. **Horizontal bar:** Units Sold by Category

## Measures

`[Category Net Revenue]`, `[Category Units]`, optional `% of total` via `DIVIDE ( [Category Net Revenue], CALCULATE ( [Category Net Revenue], ALL ( fact_daily_category_sales[category] ) ) )`.
