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
"""notion_utils.py â€” Backward-compatibility re-export shim.

The original monolith has been decomposed. This module re-exports symbols
from the package-local modules so older calling code can `import src.notion_utils`.
"""

# ruff: noqa: F401
from ._client import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_SECONDS,
    MAX_BACKOFF_SECONDS,
    PAGE_SIZE,
    RETRYABLE_STATUS_CODES,
    _backoff_seconds,
    _call_with_retry,
    _clean_env_value,
    _collect_paginated_results,
    _extract_plain_text,
    _get_notion_token,
    _get_platform_ds_id,
    _is_retryable_exception,
    _normalize_notion_id,
    _resolve_query_target_id,
    _resolve_required_id,
    _sdk_request,
    get_block_id,
    get_database_id,
    get_headers,
    get_notion_client,
    get_page_id,
    notion_get,
    notion_post,
)
from ._parse import (
    extract_block_content,
    extract_page_blocks,
    extract_property,
    fetch_database,
    fetch_selected_child_databases,
    flatten_page_content,
    get_block_label,
    get_database,
    get_database_title,
    get_page,
    get_page_title,
    list_block_children,
    list_child_databases,
    pages_to_records,
)
from .analysis import (
    SUMMARY_TABLE_TYPES,
    _collect_summary_rows_from_blocks,
    _extract_rows_from_summary_section,
    _extract_table_row_cells,
    _normalize_heading_text,
    build_paper_summaries_dataframe,
    build_summary_tables_by_type,
    build_summary_tables_from_dataframe,
    classify_summary_heading,
    enrich_paper_record,
    export_backup_bundle,
    extract_reading_list_to_paper_db,
    extract_summaries_to_paper_summaries_db,
    parse_markdown_pipe_tables,
    parse_notion_table_block,
)
from .migration import (
    NOTION_PAPER_DB_ID,
    NOTION_PAPER_SUMMARIES_DB_ID,
    _build_database_properties_from_dataframe,
    _build_page_properties_from_row,
    _build_property_key_map,
    _collect_existing_title_values,
    _is_missing_value,
    _paper_summary_properties,
    _remap_properties_to_schema_keys,
    _to_chk,
    _to_dt,
    _to_ms,
    _to_num,
    _to_rt,
    _to_sel,
    _to_status,
    _to_url,
    _truncate_text,
    archive_database,
    backfill_paper_db_to_notion,
    backfill_paper_summaries_db_to_notion,
    backfill_reading_notes_to_paper_db,
    build_paper_title_id_map,
    build_v3_page_properties,
    create_notion_child_page,
    create_notion_database,
    extract_reading_notes_from_page,
    import_dataframe_to_notion_database,
    migrate_papers_from_reading_list,
    migrate_summaries_from_reading_list,
    publish_reading_list_v2_to_notion,
    upsert_paper_summary,
)
from .zotero import (
    DEBUG_MODE,
    _normalize_title,
    _zotero_headers,
    backfill_zotero_metadata,
    match_papers_to_zotero,
    search_zotero_by_title,
    sync_reading_notes_to_zotero,
)
