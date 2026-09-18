# Annapurna sales platform

`run.ps1` builds a working analytical warehouse from the supplied 4,457
exports, runs the pipeline three times, and saves reproducible evidence in
`evidence_idempotency.csv`.

```powershell
.\run.ps1
```

## Architecture

PostgreSQL is the relational system of record for `stores`, `products`,
`product_categories`, and `price_revisions`; `docker compose up -d` starts it
from the supplied master-data SQL. MinIO is the object-storage service. DuckDB
is the runnable local analytical query engine in this submission; in a deployed
environment it queries the same Hive-style object prefixes through an S3
catalogue (or can be replaced by Trino without changing the model).

The landing layout is:

```
s3://annapurna-raw/sales/store_id=S01/year=2024/month=10/SALES_S01_20241001.csv
```

Store and year/month partitions are appropriate for the common store-month
filter and are visible to a query engine as partition predicates. `lake/raw` is
a local object-store mirror for the runnable demo and is ready to mirror into
the `annapurna-raw` MinIO bucket. The raw copy
is immutable, while `lake/landing/normalized_lines.csv` is the normalised
staging input.

For a query for S01 during October 2024, this layout can open at most the 31
daily files for that prefix (plus any resend files in that same prefix); a flat
folder can require all 4,457 files / 68,706,877 bytes. The exact prefix scan
counts and bytes are calculated in `evidence_partition_pruning.csv` by the run.

## Correctness rules

* File names define `business_date`; timestamps do not.
* Re-sends are unioned and deduplicated by the vendor business key
  `(bill_no, line_no)`, never by picking a newest file. The fact table is rebuilt
  transactionally, so three runs produce the same row count and checksum.
* Only `SALE`, `RETURN`, `DISCOUNT`, and `VOID` make revenue. TAX and TENDER
  never enter the fact.
* `dim_product` is a slowly changing dimension. The fact resolves product code
  against its valid date interval, so a reissued code points to the product that
  existed on the business date.
* `v_historical_product_price` resolves `price_revisions` as of `date_key`.
  It answers a March price from March's price record, not today’s shelf price.

The star schema keeps store address and product/category text once in their
dimensions; the fact holds compact business keys and measures. `dim_date`
provides day, ISO week and month dashboard slices.

## Historical-price demonstration

Run `powershell -ExecutionPolicy Bypass -File .\scripts\run_price_demo.ps1`.
It executes the identical query in [sql/price_report.sql](sql/price_report.sql)
for `2024-03-01` and `2024-12-01`; only `report_start` changes. The results are
saved in `evidence_price_2024-03-01.csv` and `evidence_price_2024-12-01.csv`.
The join to `dim_price_revision` is bounded by `effective_from` and
`effective_to`, which makes the selected price historical.

## Finance reconciliation

Run `powershell -ExecutionPolicy Bypass -File .\scripts\run_reconciliation.ps1`.
It saves `evidence_reconciliation.csv`. Only three months differ:

| Month | Variance (Finance − warehouse) | Classification | Finance follow-up |
| --- | ---: | --- | --- |
| 2024-03 | ₹486,250.00 | Definition/scope: institutional invoice is outside till exports | Agree an adjustment policy |
| 2024-07 | ₹232,131.70 | Source-data gap: three S07 export days are missing | Add Finance's phone-in adjustment or accept source scope |
| 2024-12 | −₹50.48 | Definition: Finance rounds per bill; warehouse retains paise | Agree rounding policy |

None is a pipeline bug; all other months match exactly.

## Cross-system federation

[sql/federated_query_trino.sql](sql/federated_query_trino.sql) is one Trino
query that reads sales from the Hive/S3 catalogue and dimensions directly from
the PostgreSQL catalogue, without copying either system. Its distributed plan
is the required evidence: retain `TableScan[hive...]` and
`TableScan[postgres...]` nodes plus their constraints and fragment statistics.

The runnable equivalent is
[sql/federated_query_duckdb.sql](sql/federated_query_duckdb.sql). It was
executed successfully against the live PostgreSQL container and the lake's S01
October object prefix; [evidence_federated_query.csv](evidence_federated_query.csv)
is the unedited `EXPLAIN ANALYZE` output. It proves that DuckDB read 31 lake
files / 13,516 source rows and queried PostgreSQL `stores` (with
`store_id='S01'` pushed down), `products`, and `product_categories`; DuckDB
then performed the hash joins and aggregation. No table was copied between the
two systems.
