-- Set `report_start` before running. This query never changes between periods.
-- Example: SET VARIABLE report_start = DATE '2024-03-01';
WITH report_period AS (
  SELECT getvariable('report_start')::DATE AS start_date,
         (getvariable('report_start')::DATE + INTERVAL 1 MONTH)::DATE AS end_date
)
SELECT p.product_sk, p.product_name, c.category_name,
       round(sum(f.qty), 3) AS net_quantity,
       round(sum(f.qty * pr.selling_price), 2) AS revenue_at_price_effective_that_month,
       min(pr.selling_price) AS lowest_effective_price,
       max(pr.selling_price) AS highest_effective_price
FROM wh.fact_sales_line f
JOIN report_period rp ON f.date_key >= rp.start_date AND f.date_key < rp.end_date
JOIN wh.dim_product p USING (product_sk)
JOIN wh.dim_category c USING (category_id)
JOIN wh.dim_price_revision pr ON pr.product_sk = f.product_sk
  AND f.date_key BETWEEN pr.effective_from AND pr.effective_to
WHERE f.line_type IN ('SALE', 'RETURN', 'VOID')
GROUP BY p.product_sk, p.product_name, c.category_name
ORDER BY revenue_at_price_effective_that_month DESC, p.product_name
LIMIT 15;
