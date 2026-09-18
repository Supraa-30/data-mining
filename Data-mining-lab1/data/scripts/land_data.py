#!/usr/bin/env python3
"""Land RetailEdge exports into a Hive-style local object-store layout.

The raw files are immutable evidence.  The canonical CSV is a normalized
landing table; duplicate/re-sent bill lines are deliberately retained here and
are removed only by the warehouse's deterministic business key rule.
"""
from __future__ import annotations

import csv
import hashlib
import re
import shutil
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "sales"
LAKE = ROOT / "lake"
LANDING = LAKE / "landing" / "normalized_lines.csv"
INVENTORY = LAKE / "landing" / "file_inventory.csv"
PRUNING = ROOT / "evidence_partition_pruning.csv"
PATTERN = re.compile(r"^SALES_(S\d{2})_(\d{8})(?:__(R\d+))?\.csv$")
OUT_FIELDS = ["source_file", "source_sha256", "store_id", "business_date", "bill_no", "line_no", "product_code", "qty", "unit_price", "line_type", "source_ts"]

def normalise(path: Path, store: str, business_date: str, writer: csv.DictWriter) -> int:
    delimiter = ";" if store in {"S06", "S07", "S08", "S09"} else ","
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    rows = 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for raw in csv.DictReader(handle, delimiter=delimiter):
            # S01-S05 are already canonical; S06-S09 and S10-S12 use aliases.
            code = raw.get("product_code") or raw.get("item_code")
            qty = raw.get("qty") or raw.get("quantity")
            price = raw.get("unit_price") or raw.get("rate")
            kind = raw.get("line_type") or raw.get("type")
            ts = raw.get("ts") or raw.get("txn_time")
            if store in {"S10", "S11", "S12"}:
                ts = datetime.fromtimestamp(int(ts), UTC).isoformat(sep=" ")
            elif store in {"S06", "S07", "S08", "S09"}:
                ts = datetime.strptime(ts, "%d-%m-%Y %H:%M:%S").isoformat(sep=" ")
            writer.writerow({"source_file": path.name, "source_sha256": digest, "store_id": store,
                             "business_date": f"{business_date[:4]}-{business_date[4:6]}-{business_date[6:]}",
                             "bill_no": raw["bill_no"], "line_no": raw["line_no"], "product_code": code,
                             "qty": qty, "unit_price": price, "line_type": kind, "source_ts": ts})
            rows += 1
    return rows

def main() -> None:
    if LAKE.exists():
        shutil.rmtree(LAKE)
    LANDING.parent.mkdir(parents=True)
    inventory_rows, counts = [], Counter()
    with LANDING.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=OUT_FIELDS)
        writer.writeheader()
        for path in sorted(SOURCE.glob("*.csv")):
            match = PATTERN.match(path.name)
            if not match:
                raise ValueError(f"Unexpected export file name: {path.name}")
            store, date, resend = match.groups()
            # Object-storage prefix is the partition contract used by the query engine.
            target = LAKE / "raw" / f"store_id={store}" / f"year={date[:4]}" / f"month={date[4:6]}" / path.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            rows = normalise(path, store, date, writer)
            inventory_rows.append([path.name, store, date, resend or "original", rows, path.stat().st_size])
            counts[store] += 1
    with INVENTORY.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["file_name", "store_id", "business_date", "revision", "rows", "bytes"])
        writer.writerows(inventory_rows)
    target_files = [r for r in inventory_rows if r[1] == "S01" and r[2].startswith("202410")]
    with PRUNING.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["query", "layout", "possible_files_opened", "possible_bytes_opened"])
        writer.writerow(["store=S01, month=2024-10", "partitioned store/year/month", len(target_files), sum(r[5] for r in target_files)])
        writer.writerow(["store=S01, month=2024-10", "flat folder", len(inventory_rows), sum(r[5] for r in inventory_rows)])
    print(f"landed_files={len(inventory_rows)} landed_rows={sum(r[4] for r in inventory_rows)} bytes={sum(r[5] for r in inventory_rows)}")

if __name__ == "__main__":
    main()
