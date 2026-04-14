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
"""pipeline.py — High-level pipeline orchestration for the literature review database export.

Provides the core fetch-and-export logic consumed by both run_pipeline.py
and interactive notebooks. Import this module wherever pipeline logic is needed
instead of duplicating it.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .notion_fetch import fetch_database, list_child_databases, pages_to_records

DATA_DIR = Path("data")


def fetch_all_to_dataframes(page_id: str | None = None) -> list[dict]:
    """List all child databases under *page_id* and load each as a DataFrame.

    Parameters
    ----------
    page_id:
        Notion page ID that contains the target child databases.
        Falls back to the ``NOTION_PAGE_ID`` environment variable when *None*.

    Returns
    -------
    list of dicts with keys:
        ``name`` (str), ``id`` (str), ``df`` (pandas.DataFrame)
    """
    dbs = list_child_databases(page_id)
    results: list[dict] = []
    for db in dbs:
        db_id = str(db["database_id"] or "")
        db_name = str(db["database_name"] or "(unnamed)")
        pages = fetch_database(db_id)
        records = pages_to_records(pages)
        results.append({"name": db_name, "id": db_id, "df": pd.DataFrame(records)})
    return results


def export_to_csv(
    db_results: list[dict],
    out_dir: Path = DATA_DIR,
) -> tuple[list[dict], list[dict]]:
    """Write each database DataFrame to a CSV file under *out_dir*.

    Parameters
    ----------
    db_results:
        Output of :func:`fetch_all_to_dataframes`.
    out_dir:
        Directory to write CSV files into. Created if it does not exist.

    Returns
    -------
    ``(successes, failures)`` — each element is a list of manifest-entry dicts.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    successes: list[dict] = []
    failures: list[dict] = []

    for item in db_results:
        db_name: str = item["name"]
        file_stem = db_name.lower().replace(" ", "_")
        out_path = out_dir / f"{file_stem}.csv"
        try:
            item["df"].to_csv(out_path, index=False)
            successes.append({
                "name": db_name,
                "id": item["id"],
                "rows": len(item["df"]),
                "output": str(out_path),
                "status": "ok",
            })
        except Exception as exc:  # noqa: BLE001
            failures.append({
                "name": db_name,
                "id": item["id"],
                "status": "error",
                "error": str(exc),
            })

    return successes, failures


def write_manifest(
    successes: list[dict],
    failures: list[dict],
    out_dir: Path = DATA_DIR,
) -> Path:
    """Write a ``pipeline_run_manifest.json`` to *out_dir* and return its path.

    The manifest records when the pipeline ran, what was exported, and overall
    status (``ok`` / ``partial`` / ``error``).
    """
    if failures and successes:
        status = "partial"
    elif failures:
        status = "error"
    else:
        status = "ok"

    manifest = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "databases": successes + failures,
        "status": status,
    }
    path = out_dir / "pipeline_run_manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path
