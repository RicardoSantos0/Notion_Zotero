"""Generate a CSV summarizing migration diffs between canonical v2 and v3.

This is a read-only helper for reviewers to inspect per-file differences.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, Any

from .migration_audit import compare_dirs, load_bundle


def make_rows(left: Path, right: Path) -> list[Dict[str, Any]]:
    left_files = {p.name: p for p in Path(left).glob("*.canonical.json")}
    right_files = {p.name: p for p in Path(right).glob("*.canonical.json")}
    summary = compare_dirs(Path(left), Path(right))

    all_names = sorted(set(left_files) | set(right_files))
    rows: list[Dict[str, Any]] = []
    for name in all_names:
        left_exists = name in left_files
        right_exists = name in right_files
        changed = name in summary["changed"]

        left_keys = right_keys = ""
        left_refs = right_refs = ""

        if left_exists:
            try:
                l = load_bundle(left_files[name])
                left_keys = len(l.keys())
                left_refs = len(l.get("references", []))
            except Exception:
                left_keys = "error"

        if right_exists:
            try:
                r = load_bundle(right_files[name])
                right_keys = len(r.keys())
                right_refs = len(r.get("references", []))
            except Exception:
                right_keys = "error"

        rows.append(
            {
                "filename": name,
                "left_exists": left_exists,
                "right_exists": right_exists,
                "changed": changed,
                "left_keys": left_keys,
                "right_keys": right_keys,
                "left_refs": left_refs,
                "right_refs": right_refs,
            }
        )

    return rows


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Generate migration CSV for canonical bundles")
    p.add_argument("--left", default="fixtures/canonical", help="Left (v2) canonical directory")
    p.add_argument("--right", default="fixtures/canonical_v3", help="Right (v3) canonical directory")
    p.add_argument("--out", default="docs/migration_diffs_v2_v3.csv", help="Output CSV path")
    args = p.parse_args(argv)

    rows = make_rows(Path(args.left), Path(args.right))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "filename",
        "left_exists",
        "right_exists",
        "changed",
        "left_keys",
        "right_keys",
        "left_refs",
        "right_refs",
    ]

    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print("WROTE", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
