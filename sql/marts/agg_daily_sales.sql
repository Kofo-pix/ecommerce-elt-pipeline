-- Revenue counts only completed/shipped orders.
DROP TABLE IF EXISTS agg_daily_sales;
CREATE TABLE agg_daily_sales AS
WITH daily AS (
    SELECT order_date,
           COUNT(DISTINCT order_id) AS orders,
           SUM(quantity)            AS units_sold,
           ROUND(SUM(net_amount), 2) AS net_revenue
    FROM fact_sales
    WHERE status IN ('completed', 'shipped')
    GROUP BY order_date
)
SELECT order_date, orders, units_sold, net_revenue,
       ROUND(net_revenue * 1.0 / orders, 2) AS avg_order_value,
       ROUND(AVG(net_revenue) OVER (
           ORDER BY order_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS revenue_7d_avg
FROM daily;
