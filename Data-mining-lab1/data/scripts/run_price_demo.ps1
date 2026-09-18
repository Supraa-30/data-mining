$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
if (-not (Test-Path warehouse.duckdb)) { throw 'Run run.ps1 first to create warehouse.duckdb.' }

# Identical report SQL; only the report_start variable changes.
@('2024-03-01', '2024-12-01') | ForEach-Object {
  Write-Host "`nHistorical-price report for $_"
  $statement = "SET VARIABLE report_start = DATE '$($_)'; " + (Get-Content sql/price_report.sql -Raw)
  $statement | & duckdb warehouse.duckdb
  # Preserve a machine-readable demonstration for each period.
  $csvStatement = "SET VARIABLE report_start = DATE '$($_)'; " + (Get-Content sql/price_report.sql -Raw)
  $csvStatement | & duckdb -csv warehouse.duckdb | Set-Content "evidence_price_$($_).csv"
}
