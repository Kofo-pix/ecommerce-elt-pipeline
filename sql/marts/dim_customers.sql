DROP TABLE IF EXISTS dim_customers;
CREATE TABLE dim_customers AS
SELECT ROW_NUMBER() OVER (ORDER BY customer_id) AS customer_key,
       customer_id, name, email, country_code, signup_date
FROM stg_customers;
CREATE UNIQUE INDEX IF NOT EXISTS ux_dim_customers_id ON dim_customers (customer_id);
