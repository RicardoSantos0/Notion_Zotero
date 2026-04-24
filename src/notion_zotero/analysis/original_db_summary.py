"""Utilities to extract and normalise reading-list summary tables.

This module provides a small programmatic API designed to be imported
by the companion Jupyter notebook. It re-uses the package's
`reading_list_importer` parser to produce canonical bundles and then
concatenates the summary tables (PRED, DESC, KT, REC) as pandas
DataFrames. A lightweight cleaning/normalisation pass is also exposed.

The functions are intentionally conservative (pure data transforms)
and avoid writing files unless explicitly asked.
"""
from __future__ import annotations

import os
import json
import re
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

log = logging.getLogger(__name__)

# The canonical task order expected by the original notebook
TASK_ORDER = ["PRED", "DESC", "KT", "REC"]


def load_credentials() -> Tuple[str, str]:
    """Load NOTION credentials from the environment and return (key, db_id).

    Raises ValueError when either variable is missing.
    """
    key = os.getenv("NOTION_API_KEY", "").strip().strip('"').strip("'")
    dbid = os.getenv("NOTION_DATABASE_ID", "").strip().strip('"').strip("'")
    missing = []
    if not key:
        missing.append("NOTION_API_KEY")
    if not dbid:
        missing.append("NOTION_DATABASE_ID")
    if missing:
        raise ValueError(f"Missing env vars: {', '.join(missing)}")
    return key, dbid


def parse_fixtures_to_canonical(input_dir: Path | str, out_dir: Path | str | None = None, domain_pack_id: str | None = None, force: bool = False) -> List[dict]:
    """Parse JSON fixtures in `input_dir` into canonical dicts.

    If `out_dir` is provided the canonical bundles are written as
    `<page_id>.canonical.json`. Returns the list of canonical dicts.
    """
    from notion_zotero.services.reading_list_importer import parse_fixture

    input_dir = Path(input_dir)
    if out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

    results: List[dict] = []
    for f in sorted(input_dir.glob("*.json")):
        try:
            _, canon = parse_fixture(f, domain_pack_id)
        except Exception as exc:
            log.exception("Failed to parse fixture %s: %s", f, exc)
            continue
        results.append(canon)
        if out_dir is not None:
            out_path = Path(out_dir) / f"{canon.get('provenance', {}).get('source_id', 'unknown')}.canonical.json"
            text = json.dumps(canon, ensure_ascii=False, indent=2)
            if out_path.exists() and not force:
                old = out_path.read_text(encoding="utf-8")
                if old == text:
                    continue
            out_path.write_text(text, encoding="utf-8")

    return results


def load_canonical_records(canonical_dir: Path | str) -> List[dict]:
    """Load all `*.canonical.json` bundles from `canonical_dir` into memory."""
    canonical_dir = Path(canonical_dir)
    out: List[dict] = []
    for p in sorted(canonical_dir.glob("*.canonical.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        out.append(d)
    return out


def _task_label_from_name(name: str | None) -> str | None:
    if not name:
        return None
    n = re.sub(r"[^a-z0-9]", "", name.lower())
    if "pred" in n or "prediction" in n:
        return "PRED"
    if "desc" in n or "description" in n:
        return "DESC"
    if "kt" in n or "knowledge" in n or "tracing" in n:
        return "KT"
    if "rec" in n or "recommend" in n or "recommender" in n:
        return "REC"
    return None


def concatenate_summary_tables(canonical_records: List[dict]) -> Tuple[dict, List[dict]]:
    """From a list of canonical bundles, build the reading-list DataFrame and
    concatenated summary tables for `TASK_ORDER`.

    Returns (analysis_dfs, errors)
    where `analysis_dfs` is a dict with keys:
      - "Reading List + Page Fields"
      - "Concatenated Summary Table Pred"
      - "Concatenated Summary Table Desc"
      - "Concatenated Summary Table KT"
      - "Concatenated Summary Table Rec"
    """
    summary_collectors: Dict[str, List[dict]] = {task: [] for task in TASK_ORDER}
    reading_rows: List[dict] = []
    errors: List[dict] = []

    for canon in canonical_records:
        try:
            refs = canon.get("references", []) or []
            ref = refs[0] if refs else {}
            provenance = canon.get("provenance", {})
            page_id = provenance.get("source_id") or ref.get("id") or ""
            title = ref.get("title") or ""

            # Build a lightweight reading-list row from the reference object
            row = dict(ref)
            row["page_id"] = page_id
            reading_rows.append(row)

            # Build mappings for tasks
            tasks = {t.get("id"): t.get("name") for t in (canon.get("tasks") or [])}
            reference_tasks = {rt.get("id"): rt.get("task_id") for rt in (canon.get("reference_tasks") or [])}

            for ex in (canon.get("task_extractions") or []):
                extracted = ex.get("extracted") or []
                ref_rt_id = ex.get("reference_task_id")
                if ref_rt_id:
                    task_id = reference_tasks.get(ref_rt_id)
                    task_name = tasks.get(task_id) if task_id else None
                else:
                    task_name = ex.get("schema_name") or ex.get("template_id") or ex.get("schema_name")

                label = _task_label_from_name(task_name)
                if label in TASK_ORDER:
                    for r in extracted:
                        out_row = dict(r)
                        out_row.update({
                            "source_page_id": page_id,
                            "source_title": title,
                            "schema_name": ex.get("schema_name"),
                        })
                        summary_collectors[label].append(out_row)

        except Exception as exc:
            errors.append({"source_page": canon.get("provenance", {}).get("source_id"), "error": str(exc)})

    # Convert to pandas DataFrames (keep duplicates by design)
    df_reading_list = pd.DataFrame(reading_rows)
    df_pred = pd.DataFrame(summary_collectors["PRED"]).fillna("")
    df_desc = pd.DataFrame(summary_collectors["DESC"]).fillna("")
    df_kt = pd.DataFrame(summary_collectors["KT"]).fillna("")
    df_rec = pd.DataFrame(summary_collectors["REC"]).fillna("")

    analysis_dfs = {
        "Reading List + Page Fields": df_reading_list,
        "Concatenated Summary Table Pred": df_pred,
        "Concatenated Summary Table Desc": df_desc,
        "Concatenated Summary Table KT": df_kt,
        "Concatenated Summary Table Rec": df_rec,
    }
    return analysis_dfs, errors


# -------------------------------
# Standard cleaning layer (lightweight port from the notebook)
# -------------------------------

TYPO_FIXES = {
    r"\bFiiltering\b": "Filtering",
    r"\bExerrcise\b": "Exercise",
    r"\baprroach\b": "approach",
    r"\bThereotical\b": "Theoretical",
    r"\bMAchine\b": "Machine",
}

GENERIC_VALUE_MAP = {
    "none": "Not Applicable",
    "none applicable": "Not Applicable",
    "not applicable": "Not Applicable",
    "n/a": "Not Applicable",
    "na": "Not Applicable",
    "elearning": "E-Learning",
    "e-learning": "E-Learning",
}

ACRONYM_WORDS = {"LAK", "LMS", "MOOC", "AI", "LLM", "KT", "RS"}


def _norm_key(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").replace("_", " ").replace("-", " ")).strip().lower()


def _clean_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"\s*\|\s*", " | ", text)
    text = re.sub(r"\s*;\s*", "; ", text)
    return text.strip()


def _apply_typos(text: str) -> str:
    out = text
    for pattern, repl in TYPO_FIXES.items():
        out = re.sub(pattern, repl, out, flags=re.IGNORECASE)
    return out


def _normalize_text_cell(v):
    if not isinstance(v, str):
        return v
    out = _clean_whitespace(v)
    out = _apply_typos(out)
    mapped = GENERIC_VALUE_MAP.get(_norm_key(out), out)
    return mapped


def _normalize_search_strategy(value):
    if not isinstance(value, str):
        return value
    s = _normalize_text_cell(value)
    s = s.replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'")
    s = s.replace("\n", " ").strip()
    parts = [p.strip() for p in re.split(r"\s+AND\s+", s, flags=re.IGNORECASE) if p.strip()]
    if not parts:
        return s
    normalized_terms = [f'"{p.strip()}"' for p in parts]
    deduped = list(dict.fromkeys(normalized_terms))
    return " AND ".join(deduped)


def _canonicalize_columns(df: pd.DataFrame, table_name: str):
    # Lightweight aliasing behaviour — keep simple and conservative
    alias = {}
    # allow table-specific aliases in future
    rename_map = {}
    seen_targets = set(df.columns)
    for col in df.columns:
        key = _norm_key(col)
        target = alias.get(key, col)
        if target != col:
            if target in seen_targets and target not in rename_map.values():
                continue
            rename_map[col] = target
    return df.rename(columns=rename_map), rename_map


def standard_clean_table(df: pd.DataFrame, table_name: str):
    out = df.copy()
    # Apply text normalization to object columns
    text_updates = 0
    search_strategy_updates = 0
    for col in out.columns:
        if out[col].dtype != object:
            continue
        original = out[col].copy()
        out[col] = out[col].map(_normalize_text_cell)
        if table_name == "Reading List + Page Fields" and col == "Search Strategy":
            out[col] = out[col].map(_normalize_search_strategy)
            search_strategy_updates += int((original != out[col]).sum())
        text_updates += int((original != out[col]).sum())

    log = {
        "table": table_name,
        "rows_before": len(df),
        "rows_after": len(out),
        "text_updates": text_updates,
        "search_strategy_updates": search_strategy_updates,
    }
    return out, log


def run_analysis(use_notion_api: bool = False, fixtures_dir: str | Path = "fixtures/reading_list", canonical_dir: str | Path = "fixtures/canonical", parse_fixtures: bool = True) -> Tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame], pd.DataFrame]:
    """High-level orchestration used by the notebook.

    - If `use_notion_api` is True the function will attempt to export the
      Notion database (requires `NOTION_API_KEY` in the environment).
    - If `parse_fixtures` is True, fixtures under `fixtures_dir` are
      parsed into canonical bundles (written into `canonical_dir`).
    - Returns (analysis_dfs, analysis_dfs_clean, normalization_log)
    """
    fixtures_dir = Path(fixtures_dir)
    canonical_dir = Path(canonical_dir)

    if use_notion_api:
        # Delegate to the package export helper (requires notion-client)
        try:
            from notion_client import Client
        except Exception as exc:  # pragma: no cover - environment-specific
            raise RuntimeError("notion-client is required for use_notion_api=True") from exc
        token = os.getenv("NOTION_TOKEN") or os.getenv("NOTION_API_KEY") or os.getenv("NOTION_INTEGRATION_TOKEN")
        if not token:
            raise RuntimeError("Set NOTION_TOKEN/NOTION_API_KEY in the environment to export from Notion.")
        from notion_client import Client
        from notion_zotero.scripts.export_reading_list import export_database

        notion = Client(auth=token)
        key, dbid = load_credentials()
        fixtures_dir.mkdir(parents=True, exist_ok=True)
        export_database(notion, dbid, str(fixtures_dir))

    canonical_dir.mkdir(parents=True, exist_ok=True)
    if parse_fixtures:
        parse_fixtures_to_canonical(fixtures_dir, canonical_dir)

    canon_records = load_canonical_records(canonical_dir)

    analysis_dfs, errors = concatenate_summary_tables(canon_records)

    # Standard clean pass
    analysis_dfs_clean: Dict[str, pd.DataFrame] = {}
    logs: List[dict] = []
    for name, df in analysis_dfs.items():
        cleaned, slog = standard_clean_table(df, name)
        analysis_dfs_clean[name] = cleaned
        logs.append(slog)

    normalization_log = pd.DataFrame(logs)
    return analysis_dfs, analysis_dfs_clean, normalization_log
