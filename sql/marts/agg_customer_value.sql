-- Customer lifetime value + RFM-style segmentation.
DROP TABLE IF EXISTS agg_customer_value;
CREATE TABLE agg_customer_value AS
WITH per_customer AS (
    SELECT customer_key,
           COUNT(DISTINCT order_id)  AS orders,
           ROUND(SUM(net_amount), 2) AS lifetime_value,
           MIN(order_date)           AS first_order_date,
           MAX(order_date)           AS last_order_date
    FROM fact_sales
    WHERE status IN ('completed', 'shipped')
    GROUP BY customer_key
),
scored AS (
    SELECT *,
           CAST(JULIANDAY((SELECT MAX(order_date) FROM fact_sales)) - JULIANDAY(last_order_date) AS INTEGER)
               AS days_since_last_order,
           NTILE(4) OVER (ORDER BY lifetime_value DESC) AS value_quartile
    FROM per_customer
)
SELECT s.customer_key, c.customer_id, c.country_code,
       s.orders, s.lifetime_value, s.first_order_date, s.last_order_date,
       s.days_since_last_order,
       CASE WHEN s.value_quartile = 1 AND s.days_since_last_order <= 14 THEN 'VIP active'
            WHEN s.value_quartile = 1 THEN 'VIP at risk'
            WHEN s.days_since_last_order <= 14 THEN 'Active'
            ELSE 'Dormant' END AS segment
FROM scored s
JOIN dim_customers c USING (customer_key);
