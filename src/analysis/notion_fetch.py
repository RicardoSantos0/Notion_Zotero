"""notion_fetch.py — high-level fetch helpers for Notion databases.

This module exposes simple functions that the rest of the Notion_Zotero code
can call without depending on the original Analysis repo layout.
"""

from __future__ import annotations

from typing import Any

from ._client import get_notion_client, _collect_paginated_results, get_database_id


def fetch_database_pages(database_id: str | None = None) -> list[dict[str, Any]]:
    client = get_notion_client()
    db_id = get_database_id(database_id)

    def chunk(cursor: str | None):
        return client.databases.query(database_id=db_id, start_cursor=cursor)

    return _collect_paginated_results(chunk)


def fetch_page(page_id: str) -> dict[str, Any]:
    client = get_notion_client()
    return client.pages.retrieve(page_id=page_id)
    
