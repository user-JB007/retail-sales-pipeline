# Semantic Model — Retail Sales (Star Schema)

## Grain

| Table | Grain |
|-------|-------|
| `fact_daily_store_sales` | One row per **store × calendar day** |
| `fact_daily_category_sales` | One row per **category × calendar day** |
| `fact_channel_mix` | One row per **channel × payment_method × calendar day** |
| `fact_customer_ltv` | One row per **customer** (lifetime rollup) |
| `fact_product_performance` | One row per **product** (lifetime rollup) |

Optional dimensions (derive in Desktop or from silver):

| Dimension | Key | Attributes |
|-----------|-----|------------|
| `dim_store` | `store_id` | `store_name`, `region`, `store_type` |
| `dim_product` | `product_id` | `product_name`, `category`, `brand`, `unit_price` |
| `dim_customer` | `customer_id` | `loyalty_tier`, `state` |
| `dim_date` | `date` | year, month, week, YoY helpers |
| `dim_channel` | `channel` | channel label |
| `dim_payment` | `payment_method` | payment label |

> Sample gold CSVs already denormalize store/region/type onto the daily store fact and category/brand onto product performance — fine for Desktop demos. Prefer true dims in production Fabric/Snowflake models (see `sql/`).

## Relationships (recommended)

```
dim_date[date]          1—*  fact_daily_store_sales[transaction_date]
dim_date[date]          1—*  fact_daily_category_sales[transaction_date]
dim_date[date]          1—*  fact_channel_mix[transaction_date]
dim_store[store_id]     1—*  fact_daily_store_sales[store_id]     (if split)
dim_product[product_id] 1—*  fact_product_performance[product_id] (if split)
dim_customer[customer_id] 1—* fact_customer_ltv[customer_id]      (if split)
```

Filter direction: single (dims → facts). Cross-filter between facts only via shared dimensions (date / store / product).

## Key columns

**fact_daily_store_sales:** `transaction_date`, `store_id`, `store_name`, `region`, `store_type`, `transactions`, `units_sold`, `gross_revenue`, `net_revenue`, `discount_total`, `cogs`, `gross_profit`, `avg_order_value`, `gross_margin_pct`

**fact_daily_category_sales:** `transaction_date`, `category`, `transactions`, `units_sold`, `net_revenue`, `gross_profit`

**fact_customer_ltv:** `customer_id`, `first_purchase`, `last_purchase`, `order_count`, `lifetime_revenue`, `lifetime_profit`, `avg_order_value`, `loyalty_tier`, `state`

**fact_product_performance:** `product_id`, `category`, `brand`, `units_sold`, `net_revenue`, `gross_profit`, `order_count`, `product_name`, `unit_price`

**fact_channel_mix:** `transaction_date`, `channel`, `payment_method`, `transactions`, `net_revenue`
