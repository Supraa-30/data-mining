param([switch]$KeepLake)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

# This is the local analytical engine. The compose file starts the relational
# master-data system (PostgreSQL) and object-store service (MinIO) for deploy.
if (-not (Get-Command duckdb -ErrorAction SilentlyContinue)) { throw 'duckdb.exe is required on PATH.' }

function Initialise-Warehouse {
  Remove-Item -LiteralPath warehouse.duckdb -Force -ErrorAction SilentlyContinue
  Get-Content data/masters.sql -Raw | & duckdb warehouse.duckdb
}
function Load-Warehouse {
  Get-Content sql/warehouse.sql -Raw | & duckdb warehouse.duckdb
}

if (-not $KeepLake) { python scripts/land_data.py }
Initialise-Warehouse
$evidence = @()
1..3 | ForEach-Object {
  Load-Warehouse
  $result = Get-Content sql/idempotency_check.sql -Raw | & duckdb -csv -noheader warehouse.duckdb
  $parts = $result.Trim().Split(',')
  $evidence += [PSCustomObject]@{run=$_; fact_rows=$parts[0]; fact_checksum=$parts[1]; net_revenue=$parts[2]}
}
$evidence | Export-Csv evidence_idempotency.csv -NoTypeInformation
$evidence | Format-Table -AutoSize
Write-Host "`nCFO validation:"
Get-Content sql/validation.sql -Raw | & duckdb warehouse.duckdb
