"""analysis.py — high-level analysis utilities used by Notion_Zotero.

This module provides helpers to build summary tables, enrich paper records,
and export compact JSON snapshots. It depends on lower-level parsing and
client modules within this package.
"""

from __future__ import annotations

from typing import Any, Iterable
import json

from ._parse import pages_to_records


def build_summary_table(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for r in records:
        rows.append({
            "id": r.get("id"),
            "title": r.get("Title") or r.get("title") or r.get("Name"),
            "authors": r.get("Authors"),
            "year": r.get("Year"),
        })
    return rows


def enrich_paper_record(raw_page: dict) -> dict[str, Any]:
    rec = {**raw_page}
    # Simple normalization: string-ify some properties
    props = raw_page.get("properties") or {}
    rec.update({k: (v if not isinstance(v, dict) else v.get("plain_text", "")) for k, v in props.items()})
    return rec


def export_compact_json(records: Iterable[dict[str, Any]], out_path: str) -> None:
    rows = build_summary_table(records)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=2)


def records_from_pages(pages: list[dict]) -> list[dict]:
    return pages_to_records(pages)


    return rows


def _collect_summary_rows_from_blocks(blocks: list[dict[str, Any]]) -> dict[str, list[dict[str, str]]]:
    collected: dict[str, list[dict[str, str]]] = {task: [] for task in SUMMARY_TABLE_TYPES}

    index = 0
    while index < len(blocks):
        block = blocks[index]
        block_type = block.get("type")

        if block_type not in {"heading_1", "heading_2", "heading_3"}:
            index += 1
            continue

        heading_text = block.get("text", "")
        task_type = classify_summary_heading(heading_text)
        if not task_type:
            index += 1
            continue

        section_blocks: list[dict[str, Any]] = []
        cursor = index + 1
        while cursor < len(blocks):
            next_block = blocks[cursor]
            if next_block.get("type") in {"heading_1", "heading_2", "heading_3"}:
                break
            section_blocks.append(next_block)
            cursor += 1

        collected[task_type].extend(_extract_rows_from_summary_section(section_blocks))
        index = cursor

    return collected


# ---------------------------------------------------------------------------
# Summary table builders
# ---------------------------------------------------------------------------

def build_summary_tables_by_type(records: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Build one dataframe per summary-table task type.

    Returns a dict with keys: PRED, DESC, KT, REC.
    Each dataframe has at least: Paper Name, Author, plus parsed table columns.
    """
    import pandas as pd

    rows_by_type: dict[str, list[dict[str, Any]]] = {task: [] for task in SUMMARY_TABLE_TYPES}

    for record in records:
        paper_name = record.get("Name")
        author = record.get("Author")

        blocks = record.get("blocks_raw")
        if not isinstance(blocks, list):
            page_id = record.get("notion_page_id")
            blocks = extract_page_blocks(page_id) if page_id else []

        # Backward compatibility: old cached blocks_raw may not include block_id,
        # which is required to fetch table rows from Notion table blocks.
        has_table_without_id = any(
            isinstance(block, dict)
            and block.get("type") == "table"
            and not block.get("block_id")
            for block in blocks
        )
        if has_table_without_id:
            page_id = record.get("notion_page_id")
            blocks = extract_page_blocks(page_id) if page_id else blocks

        extracted = _collect_summary_rows_from_blocks(blocks)

        for task_type, task_rows in extracted.items():
            for row in task_rows:
                rows_by_type[task_type].append(
                    {
                        "Paper Name": paper_name,
                        "Author": author,
                        **row,
                    }
                )

    return {
        task: pd.DataFrame(task_rows)
        for task, task_rows in rows_by_type.items()
    }


def build_summary_tables_from_dataframe(reading_list_enriched_df) -> dict[str, Any]:
    """Convenience wrapper for notebook usage with reading_list_enriched_df."""
    records = reading_list_enriched_df.to_dict("records")
    return build_summary_tables_by_type(records)


# ---------------------------------------------------------------------------
# Data preparation for migration
# ---------------------------------------------------------------------------

def extract_reading_list_to_paper_db(reading_list_enriched_df):
    """
    Prepare a Paper dataframe for relational migration.
    Preserves all current columns and adds migration placeholders.
    """
    paper_df = reading_list_enriched_df.copy()

    rename_map = {
        "Name": "Title",
        "Keywords/Type": "Keywords",
        "Deployed/ Deployable": "Deployed/Deployable",
    }
    paper_df = paper_df.rename(columns={k: v for k, v in rename_map.items() if k in paper_df.columns})

    if "Title" not in paper_df.columns:
        paper_df["Title"] = ""

    if "Status" not in paper_df.columns:
        paper_df["Status"] = "to-read"

    # Preserve legacy secondary status column `Status_1` by moving it into
    # the canonical `Reading Progress` column used by the v3 schema.
    # If `Reading Progress` already exists, prefer its values but fill
    # missing entries from `Status_1`. Always drop the legacy column.
    if "Status_1" in paper_df.columns:
        if "Reading Progress" not in paper_df.columns:
            paper_df["Reading Progress"] = paper_df["Status_1"]
        else:
            paper_df["Reading Progress"] = paper_df["Reading Progress"].fillna(paper_df["Status_1"])
        paper_df = paper_df.drop(columns=["Status_1"])

    if "Zotero ID" not in paper_df.columns:
        paper_df["Zotero ID"] = ""

    if "Notero Sync Settings" not in paper_df.columns:
        paper_df["Notero Sync Settings"] = ""

    if "Date of Retrieval" in paper_df.columns:
        import pandas as pd

        parsed = pd.to_datetime(paper_df["Date of Retrieval"], errors="coerce", utc=True)
        paper_df["Date of Retrieval"] = parsed.dt.strftime("%Y-%m-%d")
        paper_df["Date of Retrieval"] = paper_df["Date of Retrieval"].fillna("")

    ordered = [
        "Title",
        *[col for col in paper_df.columns if col != "Title"],
    ]
    return paper_df[ordered].fillna("")


def build_paper_summaries_dataframe(summary_tables_by_type: dict[str, Any]):
    """
    Build a unified dataframe for Notion v2 `Paper Summaries`.
    Includes one row per extracted summary row across all task types.
    """
    import pandas as pd

    frames: list[Any] = []
    for task_type in SUMMARY_TABLE_TYPES:
        frame = summary_tables_by_type.get(task_type)
        if frame is None or frame.empty:
            continue

        task_frame = frame.copy()
        task_frame["Task Type"] = task_type
        frames.append(task_frame)

    if not frames:
        return pd.DataFrame(columns=["Summary Row ID", "Paper Name", "Author", "Task Type"])

    unified = pd.concat(frames, ignore_index=True, sort=False)
    unified.insert(0, "Summary Row ID", [f"SR-{i + 1:05d}" for i in range(len(unified))])
    unified["Revision Notes"] = "Initial migration from legacy summary tables"
    unified["Last Modified"] = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    unified["Last Edited By"] = "system-backfill"
    return unified


def extract_summaries_to_paper_summaries_db(summary_tables_by_type: dict[str, Any]):
    """
    Prepare Paper Summaries dataframe for relational migration.
    Preserves all task-type fields and guarantees canonical migration fields.
    """
    summaries_df = build_paper_summaries_dataframe(summary_tables_by_type).fillna("")

    required_columns = [
        "Summary Row ID",
        "Paper Name",
        "Author",
        "Task Type",
        "Revision Notes",
        "Last Modified",
        "Last Edited By",
    ]
    for col in required_columns:
        if col not in summaries_df.columns:
            summaries_df[col] = ""

    return summaries_df


# ---------------------------------------------------------------------------
