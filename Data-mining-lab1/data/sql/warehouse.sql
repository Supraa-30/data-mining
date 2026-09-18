-- DuckDB analytical warehouse. PostgreSQL remains the system of record for
-- masters (see docker-compose.yml); this demo copies its versioned dimensions.
CREATE SCHEMA IF NOT EXISTS wh;

CREATE OR REPLACE TABLE wh.raw_sales_line AS
SELECT * FROM read_csv_auto('lake/landing/normalized_lines.csv', header=true,
  types={'source_file':'VARCHAR','source_sha256':'VARCHAR','store_id':'VARCHAR',
         'business_date':'DATE','bill_no':'VARCHAR','line_no':'INTEGER',
         'product_code':'VARCHAR','qty':'DECIMAL(18,3)','unit_price':'DECIMAL(18,2)',
         'line_type':'VARCHAR','source_ts':'TIMESTAMP'});

-- `masters.sql` is PostgreSQL DDL/data. In production this is replicated from
-- PostgreSQL; for this portable demo, `run.ps1` imports its INSERT values into
-- these type-compatible dimensions before this script runs.
CREATE OR REPLACE TABLE wh.dim_date AS
SELECT d::DATE AS date_key, year(d) AS calendar_year, month(d) AS month_number,
       strftime(d, '%Y-%m') AS year_month, week(d) AS iso_week,
       strftime(d, '%G-W%V') AS year_week, dayofweek(d) AS day_of_week
FROM generate_series(DATE '2024-01-01', DATE '2024-12-31', INTERVAL 1 DAY) t(d);

CREATE OR REPLACE TABLE wh.dim_store AS SELECT * FROM stores;
CREATE OR REPLACE TABLE wh.dim_category AS SELECT * FROM product_categories;
CREATE OR REPLACE TABLE wh.dim_product AS SELECT * FROM products;
CREATE OR REPLACE TABLE wh.dim_price_revision AS SELECT * FROM price_revisions;

-- Safe across re-sends and safe on repeated runs. The business key is defined
-- by the vendor as (bill_no, line_no); ordering only selects an identical
-- duplicate deterministically when a resend repeats it.
CREATE OR REPLACE TABLE wh.fact_sales_line AS
WITH chosen AS (
  SELECT *, row_number() OVER (
    PARTITION BY bill_no, line_no ORDER BY source_sha256, source_file
  ) AS rn
  FROM wh.raw_sales_line
), revenue AS (
  SELECT * FROM chosen WHERE rn = 1 AND line_type IN ('SALE','RETURN','DISCOUNT','VOID')
)
SELECT r.bill_no, r.line_no, r.store_id, r.business_date AS date_key,
       p.product_sk, r.product_code, r.line_type, r.qty, r.unit_price AS printed_unit_price,
       CAST(r.qty * r.unit_price AS DECIMAL(18,2)) AS net_revenue,
       r.source_file, r.source_sha256
FROM revenue r
LEFT JOIN wh.dim_product p ON p.product_code = r.product_code
  AND r.business_date BETWEEN p.valid_from AND p.valid_to;

CREATE OR REPLACE VIEW wh.v_dashboard_sales AS
SELECT f.*, d.calendar_year, d.month_number, d.year_month, d.iso_week, d.year_week,
       s.store_name, s.city, s.region, p.product_name, p.brand,
       c.category_name, c.department
FROM wh.fact_sales_line f
JOIN wh.dim_date d USING (date_key)
JOIN wh.dim_store s USING (store_id)
LEFT JOIN wh.dim_product p USING (product_sk)
LEFT JOIN wh.dim_category c USING (category_id);

-- Historical price answer: never join to today's product/price record.
CREATE OR REPLACE VIEW wh.v_historical_product_price AS
SELECT f.date_key, f.store_id, f.bill_no, f.line_no, p.product_name,
       pr.selling_price AS authoritative_selling_price, f.printed_unit_price
FROM wh.fact_sales_line f
JOIN wh.dim_product p USING (product_sk)
JOIN wh.dim_price_revision pr ON pr.product_sk = f.product_sk
  AND f.date_key BETWEEN pr.effective_from AND pr.effective_to
WHERE f.line_type IN ('SALE','RETURN','VOID');
