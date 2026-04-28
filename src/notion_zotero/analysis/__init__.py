"""Analysis helpers for the notion_zotero package.

Public API (pandas-optional):
    load_canonical_records      — load bundle dicts from a directory
    build_summary_tables        — task-agnostic row-dict tables (no pandas)
    build_summary_dataframes    — same, but returns pd.DataFrames
    clean_table                 — configurable DataFrame cleaner
    run_analysis                — full pipeline: load → summarise → clean
    export_database_snapshot    — parse local fixtures → canonical bundles

Legacy notebook helpers (require pandas, import on demand):
    ``from notion_zotero.analysis.original_db_summary import *``
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable, Optional

from notion_zotero.analysis.summarizer import (
    load_canonical_records,
    build_summary_tables,
    build_summary_dataframes,
    is_accepted,
)
from notion_zotero.analysis.cleaner import clean_table
from notion_zotero.schemas.domain_packs.education_learning_analytics import (
    task_label_fn,
)
from notion_zotero.services.reading_list_importer import parse_fixture

from notion_zotero.analysis.table_normalization import (
    normalize_token_key,
    parse_multivalue_cell,
    extract_canonical_terms,
    detect_column,
    normalize_task_tables,
    build_task_value_count_table,
)

log = logging.getLogger(__name__)


def run_analysis(
    canonical_dir: str | Path,
    task_label_fn: Callable[[str], str] | None = None,
    typo_fixes: dict[str, str] | None = None,
    value_map: dict[str, str] | None = None,
    search_strategy_columns: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict]]:
    """Full analysis pipeline: load → summarise → clean.

    Args:
        canonical_dir:            Directory of ``*.canonical.json`` bundles.
        task_label_fn:            Optional ``(task_name) -> label`` mapping.
        typo_fixes:               Regex fix dict forwarded to :func:`clean_table`.
        value_map:                Value-map dict forwarded to :func:`clean_table`.
        search_strategy_columns:  Column names for search-string normalisation.

    Returns:
        ``(raw_dfs, clean_dfs, norm_log)`` — all values are dicts keyed by
        table name.  *raw_dfs* and *clean_dfs* map to ``pd.DataFrame``
        instances; *norm_log* maps to per-table log dicts.
    """
    bundles = load_canonical_records(canonical_dir)
    raw_dfs = build_summary_dataframes(bundles, task_label_fn)
    clean_dfs: dict[str, Any] = {}
    norm_log: dict[str, dict] = {}
    for name, df in raw_dfs.items():
        cleaned, log_entry = clean_table(df, typo_fixes, value_map, search_strategy_columns)
        clean_dfs[name] = cleaned
        norm_log[name] = log_entry
    return raw_dfs, clean_dfs, norm_log


def export_database_snapshot(
    out: str = "data/pulled/notion/canonical_merged.json",
    db: Optional[str] = None,
) -> None:
    """Export a database snapshot to *out* by parsing local raw exports.

    Args:
        out: Output merged canonical JSON file path.
        db:  Unused placeholder for future direct-DB export.
    """
    out_path = Path(out)
    fixtures_dir = Path("data/raw/notion")
    canonical_dir = Path("data/pulled/notion/learning_analytics_review")
    canonical_dir.mkdir(parents=True, exist_ok=True)

    if not fixtures_dir.exists():
        raise FileNotFoundError(f"Raw Notion exports directory not found: {fixtures_dir}")

    bundles: list[dict] = []
    for f in sorted(fixtures_dir.glob("*.json")):
        page_id, canon = parse_fixture(f)
        p = canonical_dir / f"{page_id}.canonical.json"
        p.write_text(json.dumps(canon, ensure_ascii=False, indent=2), encoding="utf-8")
        bundles.append(canon)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(bundles, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("WROTE: %s", out_path)


__all__ = [
    "load_canonical_records",
    "build_summary_tables",
    "build_summary_dataframes",
    "clean_table",
    "run_analysis",
    "export_database_snapshot",
    "is_accepted",
    "task_label_fn",
    "normalize_token_key",
    "parse_multivalue_cell",
    "extract_canonical_terms",
    "detect_column",
    "normalize_task_tables",
    "build_task_value_count_table",
]

