-- Source-system revenue reconciled to Finance's signed-off monthly close.
CREATE OR REPLACE TABLE wh.reconciliation AS
WITH warehouse_monthly AS (
  SELECT year_month AS month, round(sum(net_revenue), 2) AS warehouse_revenue
  FROM wh.v_dashboard_sales GROUP BY 1
), finance AS (
  SELECT month, revenue_inr::DECIMAL(18,2) AS finance_revenue, closed_on, signed_off_by
  FROM read_csv_auto('data/finance_monthly.csv', header=true)
)
SELECT f.month, w.warehouse_revenue, f.finance_revenue,
       round(f.finance_revenue - w.warehouse_revenue, 2) AS variance_inr,
       CASE f.month
         WHEN '2024-03' THEN 'Different revenue definition: Finance includes the INR 486,250 institutional invoice outside the till exports.'
         WHEN '2024-07' THEN 'Source-data gap: S07 exports for 2024-07-09 through 2024-07-11 are permanently missing; Finance received phone-in totals.'
         WHEN '2024-12' THEN 'Different revenue definition: Finance rounds each bill to INR; warehouse keeps line-level paise precision.'
         ELSE 'Matches'
       END AS cause,
       CASE WHEN f.month IN ('2024-03','2024-07','2024-12') THEN 'Take to Finance: agree scope/adjustment policy; this is not a pipeline bug.'
            ELSE 'No action.' END AS finance_action,
       f.closed_on, f.signed_off_by
FROM finance f LEFT JOIN warehouse_monthly w USING (month)
ORDER BY f.month;

SELECT * FROM wh.reconciliation;
