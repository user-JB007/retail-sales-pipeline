# Page 02 — Store Performance

**Filters:** Region, Store type, Date

## Visuals

1. **Horizontal bar:** Top 12 stores by Net Revenue
2. **Column:** Revenue by Store Type (flagship / mall / online)
3. **Horizontal bar:** Gross Margin % by Region

## Notes

Use `avg_order_value` and `gross_margin_pct` from the store-day fact; prefer recalculating with DAX (`[Avg Order Value]`, `[Gross Margin %]`) for filter context correctness.
