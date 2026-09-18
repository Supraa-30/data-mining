-- CFO's single October number (GST/tender excluded by fact construction).
SELECT year_month, round(sum(net_revenue), 2) AS october_net_revenue
FROM wh.v_dashboard_sales WHERE year_month = '2024-10' GROUP BY 1;

-- Example dashboard grain: store/category/day. Filters can use any dimensions.
SELECT store_name, category_name, date_key, round(sum(net_revenue),2) AS revenue
FROM wh.v_dashboard_sales
WHERE store_id = 'S01' AND year_month = '2024-10'
GROUP BY ALL ORDER BY date_key, store_name, category_name LIMIT 10;

-- A March price lookup is as-of-March, not today's price.
SELECT product_name, date_key, authoritative_selling_price
FROM wh.v_historical_product_price
WHERE date_key >= DATE '2024-03-01' AND date_key < DATE '2024-04-01'
ORDER BY date_key LIMIT 10;
