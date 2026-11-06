DROP TABLE IF EXISTS dim_products;
CREATE TABLE dim_products AS
SELECT ROW_NUMBER() OVER (ORDER BY product_id) AS product_key,
       product_id, product_name, category, unit_price AS list_price
FROM stg_products;
CREATE UNIQUE INDEX IF NOT EXISTS ux_dim_products_id ON dim_products (product_id);
