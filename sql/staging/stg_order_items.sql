-- Valid rows -> stg_order_items. Invalid rows are quarantined in rejected_order_items
-- with a reason, instead of being silently dropped.
DROP TABLE IF EXISTS rejected_order_items;
CREATE TABLE rejected_order_items AS
SELECT r.*,
       CASE
           WHEN CAST(r.quantity AS INTEGER) <= 0 THEN 'non_positive_quantity'
           WHEN p.product_id IS NULL THEN 'unknown_product'
           WHEN o.order_id IS NULL THEN 'unknown_order'
       END AS reject_reason
FROM raw_order_items r
LEFT JOIN stg_products p ON p.product_id = TRIM(r.product_id)
LEFT JOIN stg_orders   o ON o.order_id   = TRIM(r.order_id)
WHERE CAST(r.quantity AS INTEGER) <= 0 OR p.product_id IS NULL OR o.order_id IS NULL;

DROP TABLE IF EXISTS stg_order_items;
CREATE TABLE stg_order_items AS
WITH ranked AS (
    SELECT *, ROW_NUMBER() OVER (
        PARTITION BY TRIM(order_item_id) ORDER BY _loaded_at DESC, _source_file DESC) AS rn
    FROM raw_order_items
    WHERE order_item_id IS NOT NULL
)
SELECT TRIM(r.order_item_id) AS order_item_id,
       TRIM(r.order_id)      AS order_id,
       TRIM(r.product_id)    AS product_id,
       CAST(r.quantity AS INTEGER) AS quantity,
       CAST(r.unit_price AS REAL)  AS unit_price,
       COALESCE(CAST(r.discount AS REAL), 0) AS discount
FROM ranked r
JOIN stg_products p ON p.product_id = TRIM(r.product_id)
JOIN stg_orders   o ON o.order_id   = TRIM(r.order_id)
WHERE r.rn = 1 AND CAST(r.quantity AS INTEGER) > 0;
