"""Simple export helpers for `notion_zotero`.

The implemented `export_database_snapshot` is intentionally conservative: it
parses local `fixtures/reading_list/*.json` pages via the canonical importer
and writes per-page canonical bundles to `fixtures/canonical/` and a merged
array to the provided `out` path.

This provides a safe, local export path suitable for CLI use and tests.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from notion_zotero.services.reading_list_importer import parse_fixture

log = logging.getLogger(__name__)


def export_database_snapshot(out: str = "fixtures/canonical_merged.json", db: Optional[str] = None) -> None:
    """Export a database snapshot to `out` by parsing local fixtures.

    - `out`: output merged canonical JSON file path
    - `db`: optional (not used) placeholder for future direct-DB export
    """
    out_path = Path(out)
    fixtures_dir = Path("fixtures") / "reading_list"
    canonical_dir = Path("fixtures") / "canonical"
    canonical_dir.mkdir(parents=True, exist_ok=True)

    bundles: list[dict] = []
    if not fixtures_dir.exists():
        raise FileNotFoundError(f"Reading list fixtures directory not found: {fixtures_dir}")

    for f in sorted(fixtures_dir.glob("*.json")):
        page_id, canon = parse_fixture(f)
        p = canonical_dir / f"{page_id}.canonical.json"
        p.write_text(json.dumps(canon, ensure_ascii=False, indent=2), encoding="utf-8")
        bundles.append(canon)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(bundles, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("WROTE: %s", out_path)


__all__ = ["export_database_snapshot"]
