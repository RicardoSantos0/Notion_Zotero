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
"""Read-oriented Notion operations (fetch/query/transform).

This module re-exports read-path functions from src.notion_utils with explicit
type-annotated signatures so calling conventions are visible at import time.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from notion_client import Client

from . import notion_utils as _u


# ---------------------------------------------------------------------------
# Client / connection
# ---------------------------------------------------------------------------

def get_notion_client() -> Client:
    """Return an authenticated Notion client using NOTION_TOKEN from the environment."""
    return _u.get_notion_client()


# ---------------------------------------------------------------------------
# Single-object reads
# ---------------------------------------------------------------------------

def get_database(database_id: str | None = None) -> dict:
    """Fetch Notion database metadata.

    Args:
        database_id: Notion database UUID. Defaults to NOTION_DATABASE_ID env var.
    """
    return _u.get_database(database_id)


def get_page(page_id: str | None = None) -> dict:
    """Fetch a single Notion page object.

    Args:
        page_id: Notion page UUID. Defaults to NOTION_PAGE_ID env var.
    """
    return _u.get_page(page_id)


def list_block_children(block_id: str | None = None) -> list[dict]:
    """Return all block children of a page or block.

    Args:
        block_id: Notion block/page UUID. Defaults to NOTION_PAGE_ID env var.
    """
    return _u.list_block_children(block_id)


# ---------------------------------------------------------------------------
# Database queries
# ---------------------------------------------------------------------------

def fetch_database(database_id: str | None = None) -> list[dict]:
    """Fetch all pages from a Notion database, handling pagination.

    Args:
        database_id: Notion database UUID. Defaults to NOTION_DATABASE_ID env var.

    Returns:
        List of raw Notion page objects (dicts).
    """
    return _u.fetch_database(database_id)


def list_child_databases(page_id: str | None = None) -> list[dict[str, str | None]]:
    """Return direct child databases under a page with normalized labels.

    Args:
        page_id: Notion page UUID. Defaults to NOTION_PAGE_ID env var.

    Returns:
        List of dicts with keys: ``database_id``, ``database_name``, ``block_type``.
    """
    return _u.list_child_databases(page_id)


def fetch_selected_child_databases(
    selected_database_names: list[str],
    page_id: str | None = None,
) -> dict[str, Any]:
    """Fetch selected child databases by name.

    Returns:
        Dict with keys ``database_pages``, ``database_records``,
        ``database_dataframes``, ``failed_databases``.
    """
    return _u.fetch_selected_child_databases(selected_database_names, page_id)


# ---------------------------------------------------------------------------
# Transformation
# ---------------------------------------------------------------------------

def pages_to_records(pages: list[dict]) -> list[dict]:
    """Convert a list of raw Notion page objects to flat record dicts.

    Args:
        pages: List of raw Notion page objects as returned by ``fetch_database``.

    Returns:
        List of flat dicts with property values extracted and typed.
    """
    return _u.pages_to_records(pages)


def extract_page_blocks(page_id: str) -> list[dict[str, Any]]:
    """Fetch all block content for a page, recursively expanding nested blocks.

    Args:
        page_id: Notion page UUID (required — no env var fallback).
    """
    return _u.extract_page_blocks(page_id)


def flatten_page_content(block_list: list[dict[str, Any]]) -> dict[str, Any]:
    """Flatten a block list into a structured text/table dict.

    Args:
        block_list: Output of ``extract_page_blocks``.
    """
    return _u.flatten_page_content(block_list)


def enrich_paper_record(
    record: dict[str, Any],
    fetch_blocks: bool = True,
) -> dict[str, Any]:
    """Enrich a paper record with block-level reading notes.

    Args:
        record: Flat paper record dict (from ``pages_to_records``).
        fetch_blocks: If True (default), fetch and embed block content.
    """
    return _u.enrich_paper_record(record, fetch_blocks)


# ---------------------------------------------------------------------------
# Summary / analysis
# ---------------------------------------------------------------------------

def build_summary_tables_by_type(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Build summary tables grouped by summary type from enriched paper records."""
    return _u.build_summary_tables_by_type(records)


def build_summary_tables_from_dataframe(
    reading_list_enriched_df: pd.DataFrame,
) -> dict[str, Any]:
    """Build summary tables from an enriched reading list DataFrame."""
    return _u.build_summary_tables_from_dataframe(reading_list_enriched_df)


def extract_reading_list_to_paper_db(
    reading_list_enriched_df: pd.DataFrame,
) -> list[dict]:
    """Extract Paper DB rows from an enriched reading list DataFrame."""
    return _u.extract_reading_list_to_paper_db(reading_list_enriched_df)


def extract_summaries_to_paper_summaries_db(
    summary_tables_by_type: dict[str, Any],
) -> list[dict]:
    """Extract Paper Summaries DB rows from summary tables."""
    return _u.extract_summaries_to_paper_summaries_db(summary_tables_by_type)


def build_paper_summaries_dataframe(
    summary_tables_by_type: dict[str, Any],
) -> pd.DataFrame:
    """Build a flat Paper Summaries DataFrame from summary tables."""
    return _u.build_paper_summaries_dataframe(summary_tables_by_type)


def export_backup_bundle(
    reading_list_enriched_df: pd.DataFrame,
    summary_tables_by_type: dict[str, Any],
    output_dir: str = "backups",
) -> dict[str, Any]:
    """Export timestamped local backup CSVs for safe Notion migration.

    Args:
        reading_list_enriched_df: Enriched reading list DataFrame.
        summary_tables_by_type: Output of ``build_summary_tables_by_type``.
        output_dir: Directory to write backup files. Defaults to ``backups/``.

    Returns:
        Dict with keys ``exported_files``, ``output_dir``, ``timestamp``.
    """
    return _u.export_backup_bundle(reading_list_enriched_df, summary_tables_by_type, output_dir)


def build_paper_title_id_map(
    database_id: str,
    title_column: str = "Title",
) -> dict[str, str]:
    """Build a mapping from paper title to Notion page ID.

    Args:
        database_id: Notion database UUID.
        title_column: Property name for the title field. Defaults to ``"Title"``.
    """
    return _u.build_paper_title_id_map(database_id, title_column)


def build_v3_page_properties(record: dict[str, Any]) -> dict[str, Any]:
    """Build Notion page properties payload for a v3 Paper DB record."""
    return _u.build_v3_page_properties(record)


# ---------------------------------------------------------------------------
# Zotero integration
# ---------------------------------------------------------------------------

def search_zotero_by_title(
    title: str,
    api_key: str,
    user_id: str,
    limit: int = 5,
) -> list[dict]:
    """Search Zotero library for items matching a title."""
    return _u.search_zotero_by_title(title, api_key, user_id, limit)


def match_papers_to_zotero(
    paper_records: list[dict],
    api_key: str,
    user_id: str,
) -> dict[str, Any]:
    """Match paper records to Zotero items by title."""
    return _u.match_papers_to_zotero(paper_records, api_key, user_id)


__all__ = [
    "get_notion_client",
    "get_database",
    "get_page",
    "list_block_children",
    "fetch_database",
    "list_child_databases",
    "fetch_selected_child_databases",
    "pages_to_records",
    "extract_page_blocks",
    "flatten_page_content",
    "enrich_paper_record",
    "build_summary_tables_by_type",
    "build_summary_tables_from_dataframe",
    "extract_reading_list_to_paper_db",
    "extract_summaries_to_paper_summaries_db",
    "build_paper_summaries_dataframe",
    "export_backup_bundle",
    "build_paper_title_id_map",
    "build_v3_page_properties",
    "match_papers_to_zotero",
    "search_zotero_by_title",
]
