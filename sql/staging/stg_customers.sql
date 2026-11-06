-- Dedupe (latest load wins), trim, validate email, standardise country to ISO-2.
DROP TABLE IF EXISTS stg_customers;
CREATE TABLE stg_customers AS
WITH ranked AS (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY TRIM(customer_id)
               ORDER BY _loaded_at DESC, _source_file DESC) AS rn
    FROM raw_customers
    WHERE customer_id IS NOT NULL AND TRIM(customer_id) <> ''
)
SELECT
    TRIM(customer_id) AS customer_id,
    TRIM(name)        AS name,
    CASE WHEN LOWER(TRIM(email)) LIKE '_%@_%.__%' THEN LOWER(TRIM(email)) END AS email,
    CASE UPPER(TRIM(country))
        WHEN 'UNITED STATES' THEN 'US' WHEN 'USA' THEN 'US'
        WHEN 'NIGERIA'       THEN 'NG'
        WHEN 'UNITED KINGDOM' THEN 'GB' WHEN 'UK' THEN 'GB'
        WHEN 'GERMANY'       THEN 'DE'
        WHEN 'INDIA'         THEN 'IN'
        ELSE UPPER(TRIM(country))
    END AS country_code,
    DATE(signup_date) AS signup_date
FROM ranked
WHERE rn = 1;
