$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
# Connector is installed once by DuckDB; it reads PostgreSQL remotely and the
# CSV lake in place. The output contains the actual EXPLAIN ANALYZE evidence.
Get-Content sql/federated_query_duckdb.sql -Raw | & duckdb -csv :memory: | Tee-Object -FilePath evidence_federated_query.csv
