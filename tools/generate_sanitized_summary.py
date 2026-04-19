#!/usr/bin/env python3
"""
Generate a sanitized summary from migration_audit/migration_report.json
This writes migration_audit/sanitized_summary.json next to the report in Notion_Zotero.
"""
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "migration_audit" / "migration_report.json"
OUT = ROOT / "migration_audit" / "sanitized_summary.json"

if not REPORT.exists():
    print("No migration report found at:", REPORT)
    raise SystemExit(1)

with REPORT.open("r", encoding="utf-8") as fh:
    data = json.load(fh)

total = len(data)
title_matches = sum(1 for e in data if bool(e.get("title_match")))
ex_counts = [int(e.get("canonical_extractions_count") or 0) for e in data]
pages_with_extractions = sum(1 for c in ex_counts if c > 0)
avg_extractions = float(statistics.mean(ex_counts)) if ex_counts else 0.0
errors = 0
for e in data:
    lf = e.get("legacy_first_summary")
    cr = e.get("canonical_reference")
    if (isinstance(lf, dict) and lf.get("error")) or (isinstance(cr, dict) and cr.get("error")):
        errors += 1

dist = {"min": min(ex_counts) if ex_counts else 0, "max": max(ex_counts) if ex_counts else 0, "mean": avg_extractions}

sanitized = {
    "total_pages": total,
    "title_matches": title_matches,
    "pages_with_extractions": pages_with_extractions,
    "extractions_distribution": dist,
    "errors": errors,
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(sanitized, indent=2), encoding="utf-8")
print("WROTE", OUT)
print(json.dumps(sanitized, indent=2))
