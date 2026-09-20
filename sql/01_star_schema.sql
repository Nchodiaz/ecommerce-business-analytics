-- Dimensional model: one sales/return line per row, surrounded by reusable dimensions.
CREATE TABLE dim_date AS
SELECT DISTINCT
    CAST(strftime(invoice_date, '%Y%m%d') AS INTEGER) AS date_key,
    CAST(invoice_date AS DATE) AS calendar_date,
    EXTRACT(year FROM invoice_date)::INTEGER AS year,
    EXTRACT(quarter FROM invoice_date)::INTEGER AS quarter,
    EXTRACT(month FROM invoice_date)::INTEGER AS month,
    strftime(invoice_date, '%B') AS month_name,
    strftime(invoice_date, '%Y-%m') AS year_month,
    EXTRACT(isodow FROM invoice_date)::INTEGER AS weekday_number,
    strftime(invoice_date, '%A') AS weekday_name,
    CASE WHEN EXTRACT(isodow FROM invoice_date) IN (6, 7) THEN TRUE ELSE FALSE END AS is_weekend
FROM raw_transactions
WHERE invoice_date IS NOT NULL;

CREATE TABLE dim_customer AS
SELECT
    customer_id,
    MIN(CAST(invoice_date AS DATE)) AS first_seen_date,
    MAX(CAST(invoice_date AS DATE)) AS last_seen_date,
    mode(country) AS primary_country
FROM raw_transactions
WHERE customer_id IS NOT NULL
GROUP BY customer_id;

CREATE TABLE dim_product AS
SELECT
    product_id,
    arg_max(description, invoice_date) AS product_description,
    median(unit_price) FILTER (WHERE unit_price > 0) AS median_unit_price,
    CASE
        WHEN regexp_matches(product_id, '^[0-9]') THEN 'Merchandise'
        ELSE 'Service or adjustment'
    END AS product_type
FROM raw_transactions
WHERE product_id IS NOT NULL
GROUP BY product_id;

CREATE TABLE dim_country AS
SELECT
    dense_rank() OVER (ORDER BY country) AS country_key,
    country,
    CASE WHEN country = 'United Kingdom' THEN 'Domestic' ELSE 'International' END AS market_type
FROM (SELECT DISTINCT country FROM raw_transactions WHERE country IS NOT NULL);

CREATE TABLE fact_transactions AS
SELECT
    row_number() OVER () AS transaction_line_id,
    r.invoice_id,
    CAST(strftime(r.invoice_date, '%Y%m%d') AS INTEGER) AS date_key,
    r.invoice_date,
    r.customer_id,
    r.product_id,
    c.country_key,
    r.quantity,
    r.unit_price,
    r.line_value,
    r.sales_revenue,
    r.return_value,
    r.is_sale,
    r.is_return,
    r.is_cancelled
FROM raw_transactions r
LEFT JOIN dim_country c USING (country)
WHERE r.invoice_id IS NOT NULL AND r.invoice_date IS NOT NULL;
