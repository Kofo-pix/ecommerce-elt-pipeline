-- 1. Monthly revenue by product category
SELECT d.year_month, p.category, ROUND(SUM(f.net_amount),2) AS revenue
FROM fact_sales f
JOIN dim_date d USING (date_key)
JOIN dim_products p USING (product_key)
WHERE f.status IN ('completed','shipped')
GROUP BY 1, 2 ORDER BY 1, 3 DESC;

-- 2. Top 10 customers by lifetime value
SELECT customer_id, country_code, orders, lifetime_value, segment
FROM agg_customer_value ORDER BY lifetime_value DESC LIMIT 10;

-- 3. Weekend vs weekday performance
SELECT d.is_weekend, COUNT(DISTINCT f.order_id) AS orders, ROUND(SUM(f.net_amount),2) AS revenue
FROM fact_sales f JOIN dim_date d USING (date_key)
WHERE f.status IN ('completed','shipped') GROUP BY 1;

-- 4. Return rate by category
SELECT p.category,
       ROUND(100.0 * SUM(CASE WHEN f.status='returned' THEN 1 ELSE 0 END) / COUNT(*), 2) AS return_rate_pct
FROM fact_sales f JOIN dim_products p USING (product_key)
GROUP BY 1 ORDER BY 2 DESC;

-- 5. Data-quality trend: what did we quarantine?
SELECT reject_reason, COUNT(*) AS rows_rejected FROM rejected_order_items GROUP BY 1;
