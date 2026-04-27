"""Original database summary module — kept for backwards compatibility.

All implementations now live in the refactored sub-modules:

    Text utilities  → :mod:`notion_zotero.core.text_utils`
    Summarizer      → :mod:`notion_zotero.analysis.summarizer`
    Cleaner         → :mod:`notion_zotero.analysis.cleaner`

Every public symbol from this module is still importable here.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

from notion_zotero.core.text_utils import (
    clean_whitespace as _cw,
    apply_regex_fixes,
    normalize_cell as _nc,
    normalize_search_string as _nss,
)
from notion_zotero.analysis.summarizer import (
    load_canonical_records,
    build_summary_tables,
    build_summary_dataframes,
)
from notion_zotero.analysis.cleaner import clean_table as _clean_table

# ---------------------------------------------------------------------------
# Domain constants (kept for backwards compatibility)
# ---------------------------------------------------------------------------

TASK_ORDER: list[str] = ["PRED", "DESC", "KT", "REC"]

TYPO_FIXES: dict[str, str] = {
    r"\bFiiltering\b": "Filtering",
    r"\bExerrcise\b": "Exercise",
    r"\baprroach\b": "approach",
    r"\bThereotical\b": "Theoretical",
    r"\bMAchine\b": "Machine",
}

GENERIC_VALUE_MAP: dict[str, str] = {
    "none": "Not Applicable",
    "none applicable": "Not Applicable",
    "not applicable": "Not Applicable",
    "n/a": "Not Applicable",
    "na": "Not Applicable",
    "elearning": "E-Learning",
    "e-learning": "E-Learning",
}

ACRONYM_WORDS: set[str] = {"LAK", "LMS", "MOOC", "AI", "LLM", "KT", "RS"}

# ---------------------------------------------------------------------------
# Backwards-compat private helpers — delegate to core/text_utils
# ---------------------------------------------------------------------------


def _clean_whitespace(text: str) -> str:
    return _cw(text)


def _apply_typos(text: str, fixes: dict[str, str] | None = None) -> str:
    return apply_regex_fixes(text, fixes if fixes is not None else TYPO_FIXES)


def _normalize_text_cell(
    value: Any,
    fixes: dict[str, str] | None = None,
    value_map: dict[str, str] | None = None,
) -> Any:
    return _nc(
        value,
        fixes if fixes is not None else TYPO_FIXES,
        value_map if value_map is not None else GENERIC_VALUE_MAP,
    )


def _normalize_search_strategy(
    value: Any,
    fixes: dict[str, str] | None = None,
    value_map: dict[str, str] | None = None,
) -> Any:
    return _nss(
        value,
        fixes if fixes is not None else TYPO_FIXES,
        value_map if value_map is not None else GENERIC_VALUE_MAP,
    )


# ---------------------------------------------------------------------------
# Domain task-label helper (legacy mapping)
# ---------------------------------------------------------------------------


def _task_label_from_name(task_name: str) -> str:
    """Map a task name to a short domain label (PRED/DESC/KT/REC)."""
    n = re.sub(r"[^a-z0-9]", "", (task_name or "").lower())
    if "pred" in n or "prediction" in n:
        return "PRED"
    if "desc" in n or "description" in n:
        return "DESC"
    if "kt" in n or "knowledge" in n or "tracing" in n:
        return "KT"
    if "rec" in n or "recommend" in n:
        return "REC"
    return task_name.upper()[:4] if task_name else ""


# ---------------------------------------------------------------------------
# Backwards-compat public API
# ---------------------------------------------------------------------------


def concatenate_summary_tables(
    canonical_records: list[dict],
    task_label_fn=None,
) -> tuple[dict[str, pd.DataFrame], list[dict]]:
    """Backwards-compat wrapper around :func:`~.summarizer.build_summary_dataframes`.

    Returns ``(analysis_dfs, errors)`` matching the original contract.
    Keys use the legacy verbose names:
    ``"Reading List + Page Fields"``, ``"Concatenated Summary Table Pred"``, …
    """
    label_fn = task_label_fn or _task_label_from_name
    dfs = build_summary_dataframes(canonical_records, label_fn)

    # Map generic keys back to the original verbose key names
    key_map = {
        "Reading List": "Reading List + Page Fields",
        "PRED": "Concatenated Summary Table Pred",
        "DESC": "Concatenated Summary Table Desc",
        "KT": "Concatenated Summary Table KT",
        "REC": "Concatenated Summary Table Rec",
    }
    renamed = {key_map.get(k, k): v for k, v in dfs.items()}
    return renamed, []


def standard_clean_table(
    df: pd.DataFrame,
    table_name: str = "",
    typo_fixes: dict | None = None,
    value_map: dict | None = None,
    search_strategy_columns: list[str] | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Backwards-compat wrapper around :func:`~.cleaner.clean_table`.

    Defaults to module-level ``TYPO_FIXES`` / ``GENERIC_VALUE_MAP`` when
    the fix dicts are ``None``.  The legacy ``table_name`` parameter is
    accepted but unused — pass ``search_strategy_columns`` explicitly.
    """
    cleaned, log = _clean_table(
        df,
        typo_fixes if typo_fixes is not None else TYPO_FIXES,
        value_map if value_map is not None else GENERIC_VALUE_MAP,
        search_strategy_columns,
    )
    log["table"] = table_name
    log["search_strategy_updates"] = log.get("search_strategy_updates", 0)
    return cleaned, log


def run_analysis(
    use_notion_api: bool = False,
    fixtures_dir: str | Path = "data/raw/notion",
    canonical_dir: str | Path = "data/pulled/notion/learning_analytics_review",
    parse_fixtures: bool = True,
) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame], pd.DataFrame]:
    """High-level orchestration used by the legacy notebook.

    Returns ``(analysis_dfs, analysis_dfs_clean, normalization_log)``.
    """
    import os
    from pathlib import Path as _Path

    canonical_dir = _Path(canonical_dir)
    canonical_dir.mkdir(parents=True, exist_ok=True)

    if parse_fixtures:
        from notion_zotero.analysis.original_db_summary import _parse_fixtures_to_canonical
        _parse_fixtures_to_canonical(_Path(fixtures_dir), canonical_dir)

    canon_records = load_canonical_records(canonical_dir)
    analysis_dfs, _ = concatenate_summary_tables(canon_records)

    analysis_dfs_clean: dict[str, pd.DataFrame] = {}
    logs: list[dict] = []
    for name, df in analysis_dfs.items():
        cleaned, slog = standard_clean_table(df, table_name=name)
        analysis_dfs_clean[name] = cleaned
        logs.append(slog)

    return analysis_dfs, analysis_dfs_clean, pd.DataFrame(logs)


def _parse_fixtures_to_canonical(
    input_dir: Path,
    out_dir: Path,
    domain_pack_id: str | None = None,
    force: bool = False,
) -> list[dict]:
    import json as _json
    from notion_zotero.services.reading_list_importer import parse_fixture

    results: list[dict] = []
    for f in sorted(input_dir.glob("*.json")):
        try:
            _, canon = parse_fixture(f, domain_pack_id)
        except Exception:
            continue
        results.append(canon)
        sid = (canon.get("provenance") or {}).get("source_id", "unknown")
        out_path = out_dir / f"{sid}.canonical.json"
        text = _json.dumps(canon, ensure_ascii=False, indent=2)
        if not force and out_path.exists() and out_path.read_text(encoding="utf-8") == text:
            continue
        out_path.write_text(text, encoding="utf-8")
    return results


def load_credentials():
    import os
    key = os.getenv("NOTION_API_KEY", "").strip().strip('"').strip("'")
    dbid = os.getenv("NOTION_DATABASE_ID", "").strip().strip('"').strip("'")
    missing = [v for v, val in [("NOTION_API_KEY", key), ("NOTION_DATABASE_ID", dbid)] if not val]
    if missing:
        raise ValueError(f"Missing env vars: {', '.join(missing)}")
    return key, dbid


__all__ = [
    "TASK_ORDER",
    "TYPO_FIXES",
    "GENERIC_VALUE_MAP",
    "ACRONYM_WORDS",
    "load_credentials",
    "load_canonical_records",
    "concatenate_summary_tables",
    "standard_clean_table",
    "run_analysis",
    "build_summary_tables",
    "build_summary_dataframes",
]
