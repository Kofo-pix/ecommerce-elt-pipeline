DROP TABLE IF EXISTS stg_products;
CREATE TABLE stg_products AS
WITH ranked AS (
    SELECT *, ROW_NUMBER() OVER (
        PARTITION BY TRIM(product_id) ORDER BY _loaded_at DESC, _source_file DESC) AS rn
    FROM raw_products
    WHERE product_id IS NOT NULL
)
SELECT TRIM(product_id) AS product_id,
       TRIM(name)       AS product_name,
       TRIM(category)   AS category,
       CAST(unit_price AS REAL) AS unit_price
FROM ranked
WHERE rn = 1 AND CAST(unit_price AS REAL) > 0;
