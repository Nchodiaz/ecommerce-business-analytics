-- 1) Which months contributed most to revenue, and did order value explain the change?
SELECT
    month,
    revenue,
    orders,
    average_order_value,
    ROUND((revenue / lag(revenue) OVER (ORDER BY month)) - 1, 4) AS revenue_mom
FROM monthly_performance
ORDER BY month;

-- 2) Which non-domestic markets combine scale with attractive order value?
SELECT country, revenue, orders, customers, average_order_value, revenue_share
FROM country_performance
WHERE market_type = 'International'
ORDER BY revenue DESC
LIMIT 10;

-- 3) How concentrated is product revenue?
WITH ranked AS (
    SELECT
        *,
        SUM(revenue) OVER (ORDER BY revenue DESC ROWS UNBOUNDED PRECEDING)
            / SUM(revenue) OVER () AS cumulative_revenue_share
    FROM product_performance
)
SELECT * FROM ranked
WHERE cumulative_revenue_share <= 0.80
ORDER BY revenue DESC;

-- 4) Which valuable customers are currently at risk?
SELECT customer_id, recency_days, frequency, monetary_value, rfm_score, segment
FROM rfm_segments
WHERE segment = 'At Risk'
ORDER BY monetary_value DESC
LIMIT 25;

-- 5) What does repeat purchasing look like by acquisition cohort?
SELECT cohort_month, cohort_index, cohort_size, active_customers, retention_rate
FROM cohort_retention
WHERE cohort_index BETWEEN 0 AND 6
ORDER BY cohort_month, cohort_index;

