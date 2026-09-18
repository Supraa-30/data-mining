-- Execute in Trino with `postgres` pointing to PostgreSQL and `hive` pointing
-- to the annapurna-raw object-store catalogue. Neither side is copied.
-- The Hive table must expose the normalised fields and store/year/month
-- partitions created by scripts/land_data.py.
EXPLAIN (TYPE DISTRIBUTED)
SELECT s.store_name, c.category_name, date_trunc('month', l.business_date) AS month,
       round(sum(l.qty * l.unit_price), 2) AS revenue
FROM hive.sales.normalized_lines l
JOIN postgres.public.stores s ON s.store_id = l.store_id
JOIN postgres.public.products p
  ON p.product_code = l.product_code
 AND l.business_date BETWEEN p.valid_from AND p.valid_to
JOIN postgres.public.product_categories c ON c.category_id = p.category_id
WHERE l.store_id = 'S01'
  AND l.business_date >= DATE '2024-10-01'
  AND l.business_date < DATE '2024-11-01'
  AND l.line_type IN ('SALE','RETURN','DISCOUNT','VOID')
GROUP BY 1,2,3;

-- Run the same SELECT with EXPLAIN ANALYZE after the two catalogues are live.
-- Evidence to retain: output's TableScan[hive...] and TableScan[postgres...]
-- nodes, their constraint predicates, and CPU/input rows per fragment.
