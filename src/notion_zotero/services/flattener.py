"""Flatten canonical JSON bundles into Polars DataFrames, CSV, and JSONL."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import polars as pl


def flatten_bundles(input_dir: str | Path) -> dict[str, pl.DataFrame]:
    """Load all *.canonical.json bundles in *input_dir* and merge into DataFrames.

    Returns a dict with keys:
        references, tasks, reference_tasks, task_extractions, workflow_states, annotations
    Each value is a Polars DataFrame of the merged rows across all bundles.
    """
    input_dir = Path(input_dir)
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    buckets: dict[str, list[dict[str, Any]]] = {
        "references": [],
        "tasks": [],
        "reference_tasks": [],
        "task_extractions": [],
        "workflow_states": [],
        "annotations": [],
    }

    for bundle_file in sorted(input_dir.glob("*.canonical.json")):
        try:
            bundle = json.loads(bundle_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(bundle, dict):
            continue
        for key in buckets:
            for row in bundle.get(key) or []:
                if not isinstance(row, dict):
                    continue
                flat = dict(row)
                # Serialize nested structures to JSON strings for tabular storage
                for field in ("extracted", "provenance", "sync_metadata",
                              "validation", "created_from_source", "meta"):
                    if field in flat and not isinstance(
                        flat[field], (str, int, float, bool, type(None))
                    ):
                        flat[field] = json.dumps(flat[field], ensure_ascii=False)
                buckets[key].append(flat)

    return {
        key: pl.DataFrame(rows) if rows else pl.DataFrame()
        for key, rows in buckets.items()
    }


def to_csv(dfs: dict[str, pl.DataFrame], output_dir: str | Path) -> None:
    """Write each DataFrame to <output_dir>/<entity>.csv."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, df in dfs.items():
        df.write_csv(output_dir / f"{name}.csv")


def to_jsonl(dfs: dict[str, pl.DataFrame], output_dir: str | Path) -> None:
    """Write each DataFrame to <output_dir>/<entity>.jsonl (one JSON object per line)."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, df in dfs.items():
        df.write_ndjson(output_dir / f"{name}.jsonl")
