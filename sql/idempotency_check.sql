-- One stable fingerprint for the dashboard fact.  This is deliberately based
-- on sorted business columns, not physical load order or source filename.
SELECT count(*) AS fact_rows,
       md5(string_agg(
         bill_no || '|' || line_no::VARCHAR || '|' || coalesce(product_sk::VARCHAR, '') || '|' ||
         net_revenue::VARCHAR, '' ORDER BY bill_no, line_no
       )) AS fact_checksum,
       round(sum(net_revenue),2) AS net_revenue
FROM wh.fact_sales_line;
