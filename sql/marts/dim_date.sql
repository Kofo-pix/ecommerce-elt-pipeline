DROP TABLE IF EXISTS dim_date;
CREATE TABLE dim_date AS
WITH RECURSIVE d(dt) AS (
    SELECT MIN(order_date) FROM stg_orders
    UNION ALL
    SELECT DATE(dt, '+1 day') FROM d WHERE dt < (SELECT MAX(order_date) FROM stg_orders)
)
SELECT CAST(REPLACE(dt, '-', '') AS INTEGER) AS date_key,
       dt                                    AS full_date,
       CAST(STRFTIME('%Y', dt) AS INTEGER)   AS year,
       CAST(STRFTIME('%m', dt) AS INTEGER)   AS month,
       STRFTIME('%Y-%m', dt)                 AS year_month,
       CAST(STRFTIME('%w', dt) AS INTEGER)   AS day_of_week,   -- 0 = Sunday
       CASE WHEN STRFTIME('%w', dt) IN ('0','6') THEN 1 ELSE 0 END AS is_weekend
FROM d
WHERE dt IS NOT NULL;
