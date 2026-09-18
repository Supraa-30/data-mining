# Annapurna Retail Platform Audit Report

## Executive conclusion

The retail pipeline is implemented and reproducible for the supplied corpus. The complete warehouse workflow was executed successfully with PowerShell execution-policy bypass. The six requirements in `data1.md` are covered by code, SQL, and evidence artifacts.

The only material implementation gap is that the vendor notes mention some Parquet exports, but the supplied corpus contains no Parquet files and `scripts/land_data.py` currently lands CSV files only. The current dataset is therefore complete for validation, but Parquet support is not demonstrated for a future mixed-format drop.

## 1. Platform and data landing

### Design

The raw data is organized using Hive-style object prefixes:

`store_id=S01/year=2024/month=10/SALES_S01_20241001.csv`

The partition order is chosen for the common query shape: one store and one month. The immutable raw files are stored below `lake/raw`; normalized rows are written to `lake/landing/normalized_lines.csv` for the local DuckDB warehouse.

PostgreSQL is the relational master-data system for stores, products, categories, and price revisions. DuckDB is the local analytical engine. MinIO is defined in `docker-compose.yml` as the object-store service for deployment; the runnable demonstration uses the local lake mirror.

### Measured pruning result

For `store=S01` and `month=2024-10`:

| Layout | Possible files opened | Possible bytes opened |
|---|---:|---:|
| Partitioned by store/year/month | 31 | 846,899 |
| One flat folder | 4,457 | 68,706,877 |

The partitioned layout reduces the possible file count by approximately 99.3% and the possible bytes by approximately 98.8% for this query.

Evidence: [evidence_partition_pruning.csv](evidence_partition_pruning.csv).

## 2. Idempotent loading

The loader keeps the raw resend files and removes duplicate lines only in the warehouse. The business key is `(bill_no, line_no)`, as specified by the billing vendor. This is necessary because a resend can be incomplete; choosing the newest whole file could lose lines.

Revenue includes `SALE`, `RETURN`, `DISCOUNT`, and `VOID`. `TAX` and `TENDER` are excluded. The fact table is rebuilt deterministically, and the checksum is calculated from sorted business columns rather than physical load order.

Three consecutive runs produced exactly the same result:

| Run | Fact rows | Fact checksum | Net revenue |
|---:|---:|---|---:|
| 1 | 789,516 | `f2b8ef0e035a22488aa4fba316795212` | 522,865,735.75 |
| 2 | 789,516 | `f2b8ef0e035a22488aa4fba316795212` | 522,865,735.75 |
| 3 | 789,516 | `f2b8ef0e035a22488aa4fba316795212` | 522,865,735.75 |

Evidence: [evidence_idempotency.csv](evidence_idempotency.csv).

## 3. Dashboard schema

The warehouse uses a star-style model:

- `wh.fact_sales_line`: measures, date, store key, product surrogate key, line type, and source lineage.
- `wh.dim_store`: store name and address once per store.
- `wh.dim_product`: product identity and slowly changing validity interval.
- `wh.dim_category`: category and department once per category.
- `wh.dim_date`: day, ISO week, month, year, and calendar attributes.
- `wh.dim_price_revision`: historical selling prices.

The product join uses `product_code` plus `business_date` against `valid_from` and `valid_to`, then carries `product_sk`. This prevents a reissued product code from resolving to the wrong product or duplicating a fact row.

The dashboard view `wh.v_dashboard_sales` supports slicing by store, product, category, day, week, and month without repeating descriptive master data on every fact row.

## 4. Historical prices

The same SQL in `sql/price_report.sql` was executed for `2024-03-01` and `2024-12-01`; only the `report_start` variable changed. The price join uses:

`f.date_key BETWEEN pr.effective_from AND pr.effective_to`

This means March reports use the March price revision and December reports use the December revision. For example, product `2073` appears at `1450.59` in the March result and `1577.69` in the December result.

Evidence:

- [evidence_price_2024-03-01.csv](evidence_price_2024-03-01.csv)
- [evidence_price_2024-12-01.csv](evidence_price_2024-12-01.csv)

## 5. Cross-system query

`sql/federated_query_duckdb.sql` reads October S01 sales directly from the lake and reads stores, products, and categories through DuckDB's PostgreSQL connector. No table is copied from one system into the other.

The execution plan shows:

- CSV/object-side scan of the S01 October prefix.
- PostgreSQL scans of `stores`, `products`, and `product_categories`.
- Store filtering and date-valid product matching.
- DuckDB hash joins and final aggregation.

The query read the S01 October prefix and returned grouped category results. PostgreSQL was available on localhost through the Docker Compose service when the query was executed.

Evidence: [evidence_federated_query.csv](evidence_federated_query.csv).

Note: DuckDB's human-readable `EXPLAIN ANALYZE` output contains box-drawing characters because it is a text plan captured through CSV mode. It is valid engine output but not ideal as a machine-readable plan. The plan still records the actual operators and timings.

## 6. Finance reconciliation

The warehouse was compared with `data/finance_monthly.csv` for all 12 months.

| Month | Variance: Finance - warehouse | Cause | Action |
|---|---:|---|---|
| 2024-03 | 486,250.00 | Finance includes an institutional invoice outside till exports. | Take to Finance as a scope/adjustment policy decision. |
| 2024-07 | 232,131.70 | S07 exports for July 9-11 are permanently missing; Finance received phone-in totals. | Take to Finance as a source-coverage adjustment. |
| 2024-12 | -50.48 | Finance rounds each bill to whole rupees; warehouse retains line-level paise. | Take to Finance as a rounding-policy decision. |
| Other nine months | 0.00 | Definitions and source coverage agree. | No action. |

None of the differences is classified as a pipeline bug.

Evidence: [evidence_reconciliation.csv](evidence_reconciliation.csv).

## 7. CFO validation

The rebuilt warehouse returns October 2024 revenue of:

`56,359,195.92`

This agrees with the October Finance value. The validation query also produces store/category/day slices from the same warehouse rather than manually calculated slide totals.

## 8. Requirement audit

| Requirement | Status | Evidence or implementation |
|---|---|---|
| Relational database and analytical engine | Complete | PostgreSQL in Docker Compose; DuckDB warehouse. |
| Object-store organization and pruning | Complete | `scripts/land_data.py`, partition evidence. |
| Safe repeated loading | Complete | Three matching rows in idempotency evidence. |
| Dashboard dimensions and SCD product identity | Complete | `sql/warehouse.sql`, `wh.v_dashboard_sales`. |
| Historical price by reporting period | Complete | Two outputs from identical SQL. |
| Federation without copying | Complete for supplied environment | PostgreSQL container plus DuckDB connector and plan evidence. |
| Month-by-month reconciliation | Complete | All 12 months classified in reconciliation evidence. |
| Parquet input support | Not demonstrated | No Parquet files are present; lander currently globs CSV only. |
| Fully machine-readable federation plan | Partial | Current evidence is captured human-readable `EXPLAIN ANALYZE` text. |

## 9. Commands used

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\run_price_demo.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\run_reconciliation.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\run_federated_query.ps1
```

The first command rebuilds the local lake and warehouse, executes the load three times, records idempotency evidence, and runs CFO validation. PostgreSQL should be started with `docker compose up -d postgres` before the federation command.
