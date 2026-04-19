"""Migration audit: compare legacy Notion export against canonical model.

Usage:
    python legacy/migration_audit.py --legacy <dir_or_file> [--report <out.md>]

Compares fields present in a legacy Notion export against the canonical
Reference model. Outputs a gap report to stdout and optionally to a file.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import fields as dc_fields
from pathlib import Path
from typing import Any

# Canonical Reference fields
try:
    from notion_zotero.core.models import Reference
    CANONICAL_FIELDS = {f.name for f in dc_fields(Reference)}
except Exception:
    # Fallback if package not installed
    CANONICAL_FIELDS = {
        "id", "title", "authors", "year", "journal", "doi",
        "url", "zotero_key", "abstract", "item_type", "tags", "provenance",
    }

# Known legacy property names → canonical field mapping
LEGACY_TO_CANONICAL: dict[str, str] = {
    "Name": "title",
    "Title": "title",
    "Author": "authors",
    "Authors": "authors",
    "Year": "year",
    "Published": "year",
    "Journal": "journal",
    "Venue": "journal",
    "DOI": "doi",
    "URL": "url",
    "Link": "url",
    "Zotero Key": "zotero_key",
    "Key": "zotero_key",
    "Abstract Text": "abstract",
    "Abstract": "abstract",
    "Article Type": "item_type",
    "Type": "item_type",
    "Keywords": "tags",
    "Tags": "tags",
}


def load_pages(source: Path) -> list[dict[str, Any]]:
    if source.is_file():
        data = json.loads(source.read_text(encoding="utf-8"))
        return [data] if isinstance(data, dict) else data
    pages = []
    for f in sorted(source.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(data, list):
                pages.extend(data)
            else:
                pages.append(data)
        except Exception as exc:
            print(f"  WARN  Could not load {f.name}: {exc}", file=sys.stderr)
    return pages


def audit_page(page: dict[str, Any]) -> dict[str, Any]:
    properties = page.get("properties", {})
    legacy_keys = set(properties.keys())
    mapped: dict[str, str] = {}
    unmapped: list[str] = []
    for k in legacy_keys:
        if k in LEGACY_TO_CANONICAL:
            mapped[k] = LEGACY_TO_CANONICAL[k]
        else:
            unmapped.append(k)
    covered_canonical = set(mapped.values())
    missing_canonical = CANONICAL_FIELDS - covered_canonical - {"id", "provenance"}
    return {
        "page_id": page.get("id", "unknown"),
        "legacy_property_count": len(legacy_keys),
        "mapped_count": len(mapped),
        "unmapped_legacy": sorted(unmapped),
        "covered_canonical": sorted(covered_canonical),
        "missing_canonical": sorted(missing_canonical),
    }


def format_report(audits: list[dict[str, Any]]) -> str:
    lines = ["# Migration Audit Report\n"]
    all_unmapped: set[str] = set()
    all_missing: set[str] = set()
    for a in audits:
        all_unmapped.update(a["unmapped_legacy"])
        all_missing.update(a["missing_canonical"])

    lines.append(f"**Pages audited:** {len(audits)}\n")
    lines.append(f"**Canonical fields checked:** {len(CANONICAL_FIELDS)}\n")

    lines.append("\n## Legacy Properties With No Canonical Mapping\n")
    if all_unmapped:
        for k in sorted(all_unmapped):
            lines.append(f"- `{k}` — no mapping in LEGACY_TO_CANONICAL")
    else:
        lines.append("_None — all legacy properties are mapped._")

    lines.append("\n## Canonical Fields Not Covered by Legacy\n")
    if all_missing:
        for k in sorted(all_missing):
            lines.append(f"- `{k}` — not present in any audited legacy page")
    else:
        lines.append("_None — all canonical fields are covered._")

    lines.append("\n## Per-Page Summary\n")
    lines.append("| Page ID | Legacy props | Mapped | Unmapped | Missing canonical |")
    lines.append("|---------|-------------|--------|----------|-------------------|")
    for a in audits:
        lines.append(
            f"| {a['page_id'][:16]} | {a['legacy_property_count']} "
            f"| {a['mapped_count']} | {len(a['unmapped_legacy'])} "
            f"| {len(a['missing_canonical'])} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit legacy Notion export against canonical model")
    parser.add_argument("--legacy", required=True, help="Path to legacy fixture dir or file")
    parser.add_argument("--report", default=None, help="Write report to this file (default: stdout)")
    args = parser.parse_args()

    source = Path(args.legacy)
    if not source.exists():
        print(f"ERROR: source not found: {source}", file=sys.stderr)
        sys.exit(1)

    pages = load_pages(source)
    if not pages:
        print("No pages found to audit.", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(pages)} page(s) from {source}", file=sys.stderr)
    audits = [audit_page(p) for p in pages]
    report = format_report(audits)

    if args.report:
        out = Path(args.report)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"Report written to {out}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
