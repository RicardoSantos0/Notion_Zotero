"""analysis package initialization.

Expose a compact public surface for the analysis helpers used across the
Notion_Zotero project.
"""

from __future__ import annotations

from ._client import get_notion_client, get_headers, get_database_id, get_page_id
from ._parse import pages_to_records, extract_page_blocks
from .analysis import (
    build_summary_table,
    enrich_paper_record,
    export_compact_json,
    records_from_pages,
)
from .migration import mark_migration_version, needs_migration
from .normalization import normalize_whitespace, normalize_title, normalize_authors
from .notion_fetch import fetch_database_pages, fetch_page
from .notion_schemas import build_title_prop, build_rich_text
from .notion_upload import create_page, append_block
from .pipeline import export_database_snapshot
from .zotero import citation_from_item
from .notion_utils import __all__ as _utils_all

__all__ = [
    "get_notion_client",
    "get_headers",
    "get_database_id",
    "get_page_id",
    "pages_to_records",
    "extract_page_blocks",
    "build_summary_table",
    "enrich_paper_record",
    "export_compact_json",
    "records_from_pages",
    "mark_migration_version",
    "needs_migration",
    "normalize_whitespace",
    "normalize_title",
    "normalize_authors",
    "fetch_database_pages",
    "fetch_page",
    "build_title_prop",
    "build_rich_text",
    "create_page",
    "append_block",
    "export_database_snapshot",
    "citation_from_item",
] + list(_utils_all)

__version__ = "0.1.0"
"""Analysis subpackage: utilities for summary tables, migration, and integrations.

This package is a copy of the Literature Review Analysis modules adjusted to be
importable under `src.analysis` inside the Notion_Zotero project. Imports are
package-relative to avoid depending on a separate top-level `src` layout.
"""

__all__ = [
    # Lightweight re-exports; modules can still be imported directly.
]
