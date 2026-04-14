"""notion_upload.py — upload helpers for creating pages and blocks in Notion.

These helpers intentionally keep the API minimal and synchronous to make unit
testing straightforward in the Notion_Zotero project.
"""

from __future__ import annotations

from typing import Any

from ._client import get_notion_client, get_page_id


def create_page(parent_page_id: str | None, properties: dict[str, Any], children: list[dict] | None = None) -> dict[str, Any]:
    client = get_notion_client()
    parent = {"type": "page_id", "page_id": get_page_id(parent_page_id)}
    payload = {"parent": parent, "properties": properties}
    if children:
        payload["children"] = children
    return client.pages.create(**payload)


def append_block(parent_block_id: str, block: dict[str, Any]) -> dict[str, Any]:
    client = get_notion_client()
    return client.blocks.children.append(block_id=get_page_id(parent_block_id), children=[block])
"""Write-oriented Notion operations (create/update/import/backfill).

This module re-exports write-path functions from src.notion_utils with explicit
type-annotated signatures so calling conventions are visible at import time.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from notion_client import Client

from . import notion_utils as _u


# ---------------------------------------------------------------------------
# Single-page operations
# ---------------------------------------------------------------------------

def upsert_paper_summary(
    notion_client: Client,
    database_id: str,
    row: dict,
    existing_by_title: dict[str, str],
    max_retries: int = 3,
    retry_seconds: int = 2,
) -> dict:
    """Idempotently create a single Paper Summary page (skips if title exists)."""
    return _u.upsert_paper_summary(
        notion_client, database_id, row, existing_by_title, max_retries, retry_seconds
    )


def create_notion_child_page(parent_page_id: str, title: str) -> dict[str, Any]:
    """Create a child page under a parent Notion page."""
    return _u.create_notion_child_page(parent_page_id, title)


def create_notion_database(
    parent_page_id: str,
    database_name: str,
    properties: dict[str, Any],
) -> dict[str, Any]:
    """Create a new Notion database under a parent page."""
    return _u.create_notion_database(parent_page_id, database_name, properties)


# ---------------------------------------------------------------------------
# Backfill operations
# ---------------------------------------------------------------------------

def backfill_paper_db_to_notion(
    paper_df: pd.DataFrame,
    *,
    database_id: str | None = None,
    max_rows: int | None = None,
) -> dict[str, Any]:
    """Idempotently backfill the Paper database using Title deduplication."""
    return _u.backfill_paper_db_to_notion(paper_df, database_id=database_id, max_rows=max_rows)


def backfill_paper_summaries_db_to_notion(
    summaries_df: pd.DataFrame,
    *,
    paper_title_to_id: dict[str, str],
    database_id: str | None = None,
    max_rows: int | None = None,
) -> dict[str, Any]:
    """Idempotently backfill Paper Summaries and attach Paper relations by title."""
    return _u.backfill_paper_summaries_db_to_notion(
        summaries_df,
        paper_title_to_id=paper_title_to_id,
        database_id=database_id,
        max_rows=max_rows,
    )


def backfill_reading_notes_to_paper_db(
    v3_db_id: str,
    v1_db_id: str,
    title_to_v3_id: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Backfill reading notes from v1 page blocks into v3 Paper DB."""
    return _u.backfill_reading_notes_to_paper_db(v3_db_id, v1_db_id, title_to_v3_id)


def backfill_zotero_metadata(
    v3_db_id: str,
    api_key: str,
    user_id: str,
    title_to_v3_id: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Search Zotero for each paper in v3 Paper DB and backfill DOI, Zotero Key, Abstract, URL."""
    return _u.backfill_zotero_metadata(v3_db_id, api_key, user_id, title_to_v3_id)


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

def import_dataframe_to_notion_database(
    database_id: str,
    dataframe: pd.DataFrame,
    *,
    title_column: str,
    data_source_id: str | None = None,
    select_columns: set[str] | None = None,
    date_columns: set[str] | None = None,
    max_rows: int | None = None,
    skip_existing_by_title: bool = False,
) -> dict[str, Any]:
    """Import a DataFrame into a Notion database."""
    return _u.import_dataframe_to_notion_database(
        database_id,
        dataframe,
        title_column=title_column,
        data_source_id=data_source_id,
        select_columns=select_columns,
        date_columns=date_columns,
        max_rows=max_rows,
        skip_existing_by_title=skip_existing_by_title,
    )


# ---------------------------------------------------------------------------
# Publish / migrate
# ---------------------------------------------------------------------------

def publish_reading_list_v2_to_notion(
    paper_summaries_df: pd.DataFrame,
    *,
    parent_page_id: str | None = None,
    workspace_page_title: str = "Reading List v2 (Relational)",
    existing_v2_page_id: str | None = None,
    existing_paper_summaries_database_id: str | None = None,
    existing_paper_summaries_data_source_id: str | None = None,
    dry_run: bool = False,
    max_rows: int | None = None,
) -> dict[str, Any]:
    """Publish migration data to Notion in a separate V2 page."""
    return _u.publish_reading_list_v2_to_notion(
        paper_summaries_df,
        parent_page_id=parent_page_id,
        workspace_page_title=workspace_page_title,
        existing_v2_page_id=existing_v2_page_id,
        existing_paper_summaries_database_id=existing_paper_summaries_database_id,
        existing_paper_summaries_data_source_id=existing_paper_summaries_data_source_id,
        dry_run=dry_run,
        max_rows=max_rows,
    )


def migrate_papers_from_reading_list(
    v1_db_id: str,
    v3_db_id: str,
) -> dict[str, Any]:
    """Migrate all papers from Reading List v1 into Paper DB v3."""
    return _u.migrate_papers_from_reading_list(v1_db_id, v3_db_id)


def migrate_summaries_from_reading_list(
    v1_db_id: str,
    v3_summaries_db_id: str,
    title_to_v3_paper_id: dict[str, str],
) -> dict[str, Any]:
    """Extract summary tables from v1 page blocks and insert into Paper Summaries DB v3."""
    return _u.migrate_summaries_from_reading_list(v1_db_id, v3_summaries_db_id, title_to_v3_paper_id)


# ---------------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------------

def archive_database(database_id: str) -> dict[str, Any]:
    """Archive (soft-delete) a Notion database."""
    return _u.archive_database(database_id)


def sync_reading_notes_to_zotero(
    v3_db_id: str,
    api_key: str,
    user_id: str,
) -> dict[str, Any]:
    """For each paper with a Zotero Key and Reading Notes, create a Zotero note."""
    return _u.sync_reading_notes_to_zotero(v3_db_id, api_key, user_id)


__all__ = [
    "archive_database",
    "backfill_paper_db_to_notion",
    "backfill_paper_summaries_db_to_notion",
    "backfill_reading_notes_to_paper_db",
    "backfill_zotero_metadata",
    "create_notion_child_page",
    "create_notion_database",
    "import_dataframe_to_notion_database",
    "migrate_papers_from_reading_list",
    "migrate_summaries_from_reading_list",
    "publish_reading_list_v2_to_notion",
    "sync_reading_notes_to_zotero",
    "upsert_paper_summary",
]
