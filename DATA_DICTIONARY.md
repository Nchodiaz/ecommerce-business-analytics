# Data dictionary

## Source fields

| Field | Type | Meaning |
|---|---|---|
| `invoice_id` | string | Invoice identifier; values beginning with `C` are cancellations |
| `product_id` | string | Stock code |
| `description` | string | Product or operational line description |
| `quantity` | numeric | Units; negative values indicate reversed quantities |
| `invoice_date` | timestamp | Transaction timestamp |
| `unit_price` | numeric | Unit price in pounds sterling |
| `customer_id` | nullable integer | Customer identifier |
| `country` | string | Customer country |

## Derived fact measures

| Field | Definition |
|---|---|
| `line_value` | `quantity × unit_price` |
| `is_sale` | Positive quantity and price, and invoice is not cancelled |
| `is_return` | Negative quantity or cancelled invoice |
| `sales_revenue` | Positive line value for sales; otherwise zero |
| `return_value` | Absolute reversed line value for returns; otherwise zero |

## Analytical marts

| Mart | Grain | Purpose |
|---|---|---|
| `kpi_summary` | one row | Executive commercial performance |
| `monthly_performance` | month | Trend, demand and basket economics |
| `country_performance` | country | Geographic scale and order value |
| `product_performance` | merchandise product | Product demand and revenue |
| `rfm_segments` | known customer | Recency, frequency, monetary value and segment |
| `cohort_retention` | acquisition cohort × activity month | Repeat purchase behavior |
| `data_quality` | validation check | Source completeness and referential integrity |

## KPI definitions

| KPI | Definition |
|---|---|
| Revenue | Sum of `sales_revenue` |
| Orders | Distinct sale invoice IDs |
| Customers | Distinct known customers on sale lines |
| Average order value | Revenue / distinct sale orders |
| Return value rate | Return value / positive sales revenue |
| Cohort retention | Active customers in month N / cohort size at month 0 |

