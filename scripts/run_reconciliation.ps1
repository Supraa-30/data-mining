$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
if (-not (Test-Path warehouse.duckdb)) { throw 'Run run.ps1 first to create warehouse.duckdb.' }
Get-Content sql/reconciliation.sql -Raw | & duckdb warehouse.duckdb
& duckdb -csv warehouse.duckdb "SELECT * FROM wh.reconciliation ORDER BY month" | Set-Content evidence_reconciliation.csv
