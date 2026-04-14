"""notion_utils.py — backward-compatible re-exports and small shims.

The original Analysis repo exposed many names at top-level; this module
provides a compact compatibility surface for Notion_Zotero's internal callers.
"""

from __future__ import annotations

from .notion_fetch import fetch_database_pages, fetch_page
from .notion_upload import create_page, append_block
from .notion_schemas import build_title_prop, build_rich_text

__all__ = [
    "fetch_database_pages",
    "fetch_page",
    "create_page",
    "append_block",
    "build_title_prop",
    "build_rich_text",
]
    
