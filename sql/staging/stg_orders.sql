DROP TABLE IF EXISTS stg_orders;
CREATE TABLE stg_orders AS
WITH ranked AS (
    SELECT *, ROW_NUMBER() OVER (
        PARTITION BY TRIM(order_id) ORDER BY _loaded_at DESC, _source_file DESC) AS rn
    FROM raw_orders
    WHERE order_id IS NOT NULL AND TRIM(order_id) <> ''
)
SELECT TRIM(order_id)    AS order_id,
       TRIM(customer_id) AS customer_id,
       DATE(order_date)  AS order_date,
       LOWER(TRIM(status)) AS status
FROM ranked
WHERE rn = 1 AND DATE(order_date) IS NOT NULL;
