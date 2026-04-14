"""pipeline.py — simple pipeline orchestration helpers used by scripts.

This module is intentionally small: it composes the fetch → parse → export
steps used by the project's scripts and tests.
"""

from __future__ import annotations

from typing import Iterable

from .notion_fetch import fetch_database_pages
from .analysis import records_from_pages, export_compact_json


def export_database_snapshot(out_path: str, database_id: str | None = None) -> None:
    pages = fetch_database_pages(database_id)
    records = records_from_pages(pages)
    export_compact_json(records, out_path)
    
