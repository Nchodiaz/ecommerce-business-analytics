CREATE TABLE kpi_summary AS
WITH sales AS (
    SELECT * FROM fact_transactions WHERE is_sale
),
returns AS (
    SELECT SUM(return_value) AS return_value FROM fact_transactions WHERE is_return
)
SELECT
    ROUND(SUM(sales_revenue), 2) AS revenue,
    COUNT(DISTINCT invoice_id) AS orders,
    COUNT(DISTINCT customer_id) AS customers,
    ROUND(SUM(sales_revenue) / COUNT(DISTINCT invoice_id), 2) AS average_order_value,
    SUM(quantity)::BIGINT AS units_sold,
    ROUND((SELECT return_value FROM returns), 2) AS return_value,
    ROUND((SELECT return_value FROM returns) / SUM(sales_revenue), 4) AS return_value_rate,
    MIN(CAST(invoice_date AS DATE)) AS start_date,
    MAX(CAST(invoice_date AS DATE)) AS end_date
FROM sales;

CREATE TABLE monthly_performance AS
SELECT
    date_trunc('month', invoice_date)::DATE AS month,
    ROUND(SUM(sales_revenue), 2) AS revenue,
    COUNT(DISTINCT invoice_id) AS orders,
    COUNT(DISTINCT customer_id) AS active_customers,
    SUM(quantity)::BIGINT AS units_sold,
    ROUND(SUM(sales_revenue) / COUNT(DISTINCT invoice_id), 2) AS average_order_value
FROM fact_transactions
WHERE is_sale
GROUP BY 1
ORDER BY 1;

CREATE TABLE country_performance AS
SELECT
    c.country,
    c.market_type,
    ROUND(SUM(f.sales_revenue), 2) AS revenue,
    COUNT(DISTINCT f.invoice_id) AS orders,
    COUNT(DISTINCT f.customer_id) AS customers,
    ROUND(SUM(f.sales_revenue) / COUNT(DISTINCT f.invoice_id), 2) AS average_order_value,
    ROUND(SUM(f.sales_revenue) / SUM(SUM(f.sales_revenue)) OVER (), 4) AS revenue_share
FROM fact_transactions f
JOIN dim_country c USING (country_key)
WHERE f.is_sale
GROUP BY 1, 2
ORDER BY revenue DESC;

CREATE TABLE product_performance AS
SELECT
    f.product_id,
    p.product_description,
    SUM(f.quantity)::BIGINT AS units_sold,
    ROUND(SUM(f.sales_revenue), 2) AS revenue,
    COUNT(DISTINCT f.invoice_id) AS orders,
    COUNT(DISTINCT f.customer_id) AS customers
FROM fact_transactions f
LEFT JOIN dim_product p USING (product_id)
WHERE f.is_sale
  AND p.product_type = 'Merchandise'
GROUP BY 1, 2
HAVING SUM(f.sales_revenue) > 0
ORDER BY revenue DESC;

CREATE TABLE rfm_segments AS
WITH snapshot AS (
    SELECT MAX(CAST(invoice_date AS DATE)) + INTERVAL 1 DAY AS snapshot_date
    FROM fact_transactions
),
customer_metrics AS (
    SELECT
        customer_id,
        date_diff('day', MAX(CAST(invoice_date AS DATE)), MAX(snapshot_date)) AS recency_days,
        COUNT(DISTINCT invoice_id) AS frequency,
        ROUND(SUM(sales_revenue), 2) AS monetary_value
    FROM fact_transactions
    CROSS JOIN snapshot
    WHERE is_sale AND customer_id IS NOT NULL
    GROUP BY customer_id
),
scored AS (
    SELECT
        *,
        6 - ntile(5) OVER (ORDER BY recency_days, customer_id) AS r_score,
        ntile(5) OVER (ORDER BY frequency, customer_id) AS f_score,
        ntile(5) OVER (ORDER BY monetary_value, customer_id) AS m_score
    FROM customer_metrics
)
SELECT
    *,
    concat(r_score, f_score, m_score) AS rfm_score,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal'
        WHEN r_score >= 4 AND f_score <= 2 THEN 'Promising'
        WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
        WHEN r_score = 1 AND f_score <= 2 THEN 'Hibernating'
        ELSE 'Needs Attention'
    END AS segment
FROM scored
ORDER BY monetary_value DESC;

CREATE TABLE cohort_retention AS
WITH customer_months AS (
    SELECT DISTINCT
        customer_id,
        date_trunc('month', invoice_date)::DATE AS order_month
    FROM fact_transactions
    WHERE is_sale AND customer_id IS NOT NULL
),
cohorts AS (
    SELECT customer_id, MIN(order_month) AS cohort_month
    FROM customer_months
    GROUP BY customer_id
),
activity AS (
    SELECT
        c.cohort_month,
        m.order_month,
        date_diff('month', c.cohort_month, m.order_month) AS cohort_index,
        COUNT(DISTINCT m.customer_id) AS active_customers
    FROM customer_months m
    JOIN cohorts c USING (customer_id)
    GROUP BY 1, 2, 3
),
sizes AS (
    SELECT cohort_month, COUNT(*) AS cohort_size
    FROM cohorts
    GROUP BY cohort_month
)
SELECT
    a.cohort_month,
    a.order_month,
    a.cohort_index,
    s.cohort_size,
    a.active_customers,
    ROUND(a.active_customers::DOUBLE / s.cohort_size, 4) AS retention_rate
FROM activity a
JOIN sizes s USING (cohort_month)
ORDER BY cohort_month, cohort_index;

CREATE TABLE data_quality AS
SELECT 'source_rows' AS check_name, COUNT(*)::DOUBLE AS check_value FROM raw_transactions
UNION ALL SELECT 'missing_customer_rows', COUNT(*)::DOUBLE FROM raw_transactions WHERE customer_id IS NULL
UNION ALL SELECT 'missing_description_rows', COUNT(*)::DOUBLE FROM raw_transactions WHERE description IS NULL
UNION ALL SELECT 'zero_or_negative_price_rows', COUNT(*)::DOUBLE FROM raw_transactions WHERE unit_price <= 0
UNION ALL SELECT 'cancelled_invoice_rows', COUNT(*)::DOUBLE FROM raw_transactions WHERE is_cancelled
UNION ALL SELECT 'modeled_fact_rows', COUNT(*)::DOUBLE FROM fact_transactions
UNION ALL SELECT 'orphan_customer_keys', COUNT(*)::DOUBLE FROM fact_transactions f LEFT JOIN dim_customer c USING (customer_id) WHERE f.customer_id IS NOT NULL AND c.customer_id IS NULL
UNION ALL SELECT 'orphan_product_keys', COUNT(*)::DOUBLE FROM fact_transactions f LEFT JOIN dim_product p USING (product_id) WHERE p.product_id IS NULL;
