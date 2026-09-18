-- Executed by DuckDB: CSV in the lake is scanned locally; dimensions are read
-- through DuckDB's PostgreSQL connector. No CREATE TABLE / copy is used.
LOAD postgres;
ATTACH 'postgresql://annapurna:annapurna_dev@localhost:5432/annapurna' AS pg (TYPE POSTGRES);

EXPLAIN ANALYZE
WITH lake_sales AS (
  SELECT 'S01' AS store_id,
         strptime(regexp_extract(filename, 'SALES_S[0-9]+_([0-9]{8})', 1), '%Y%m%d')::DATE AS business_date,
         * EXCLUDE (filename)
  FROM read_csv_auto('lake/raw/store_id=S01/year=2024/month=10/*.csv', header=true, filename=true)
)
SELECT s.store_name, c.category_name, date_trunc('month', l.business_date) AS month,
       round(sum(l.qty * l.unit_price), 2) AS revenue
FROM lake_sales l
JOIN pg.stores s ON s.store_id = l.store_id
JOIN pg.products p ON p.product_code = l.product_code
                  AND l.business_date BETWEEN p.valid_from AND p.valid_to
JOIN pg.product_categories c ON c.category_id = p.category_id
WHERE l.store_id = 'S01'
  AND l.line_type IN ('SALE', 'RETURN', 'VOID')
GROUP BY 1, 2, 3
ORDER BY 2;

-- Run separately after the plan to return dashboard rows.
WITH lake_sales AS (
  SELECT 'S01' AS store_id,
         strptime(regexp_extract(filename, 'SALES_S[0-9]+_([0-9]{8})', 1), '%Y%m%d')::DATE AS business_date,
         * EXCLUDE (filename)
  FROM read_csv_auto('lake/raw/store_id=S01/year=2024/month=10/*.csv', header=true, filename=true)
)
SELECT s.store_name, c.category_name, date_trunc('month', l.business_date) AS month,
       round(sum(l.qty * l.unit_price), 2) AS revenue
FROM lake_sales l
JOIN pg.stores s ON s.store_id = l.store_id
JOIN pg.products p ON p.product_code = l.product_code
                  AND l.business_date BETWEEN p.valid_from AND p.valid_to
JOIN pg.product_categories c ON c.category_id = p.category_id
WHERE l.store_id = 'S01'
  AND l.line_type IN ('SALE', 'RETURN', 'VOID')
GROUP BY 1, 2, 3
ORDER BY 2;
