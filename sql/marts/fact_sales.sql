-- Grain: one row per order line item.
DROP TABLE IF EXISTS fact_sales;
CREATE TABLE fact_sales AS
SELECT i.order_item_id,
       i.order_id,
       c.customer_key,
       p.product_key,
       CAST(REPLACE(o.order_date, '-', '') AS INTEGER) AS date_key,
       o.order_date,
       o.status,
       i.quantity,
       i.unit_price,
       i.discount,
       ROUND(i.quantity * i.unit_price, 2)                  AS gross_amount,
       ROUND(i.quantity * i.unit_price * (1 - i.discount), 2) AS net_amount
FROM stg_order_items i
JOIN stg_orders    o ON o.order_id    = i.order_id
JOIN dim_customers c ON c.customer_id = o.customer_id
JOIN dim_products  p ON p.product_id  = i.product_id;
CREATE INDEX IF NOT EXISTS ix_fact_sales_date ON fact_sales (date_key);
CREATE INDEX IF NOT EXISTS ix_fact_sales_customer ON fact_sales (customer_key);
