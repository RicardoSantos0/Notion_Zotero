"""Utilities for normalising extracted task tables.

This module is intentionally task-agnostic. It does not know what an LMS log,
a VLE log, or a recommender-system task is. Those meanings should be supplied
by domain packs through alias maps.

Typical use:
    normalized_tables, long_df, audit_df = normalize_task_tables(...)
    counts = build_task_value_count_table(long_df, ...)
"""
from __future__ import annotations

import ast
import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from typing import Any


DEFAULT_SPLIT_PATTERN = r"\s*(?:,|;|\||\n)\s*"

DEFAULT_MISSING_VALUES = {
    "",
    "nan",
    "none",
    "n/a",
    "na",
    "not applicable",
    "not specified",
    "none specified",
    "-",
}


def normalize_token_key(value: Any) -> str:
    """Return a stable comparison key for a free-text token.

    This is useful for matching spelling/case/punctuation variants without
    changing the original display value.
    """
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.replace("&", " and ")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _is_missing_scalar(value: Any) -> bool:
    if value is None:
        return True

    try:
        import pandas as pd

        result = pd.isna(value)
        try:
            return bool(result)
        except (TypeError, ValueError):
            return False
    except Exception:
        return False


def _is_list_like(value: Any) -> bool:
    if isinstance(value, (str, bytes, dict)):
        return False
    if isinstance(value, (list, tuple, set)):
        return True
    if hasattr(value, "tolist"):
        return True
    return isinstance(value, Iterable)


def parse_multivalue_cell(
    value: Any,
    split_pattern: str = DEFAULT_SPLIT_PATTERN,
    missing_values: set[str] | None = None,
) -> list[str]:
    """Parse a cell that may contain one or more values.

    Handles:
    - actual Python lists: ["LMS logs", "Student demographics"]
    - stringified Python lists: "['LMS logs', 'Student demographics']"
    - Notion-like list strings without quotes: "[LMS logs, Student demographics]"
    - delimited strings: "LMS logs; Student demographics"
    """
    missing_keys = {
        normalize_token_key(v)
        for v in (missing_values or DEFAULT_MISSING_VALUES)
    }

    if _is_list_like(value):
        if hasattr(value, "tolist"):
            value = value.tolist()

        values = []
        for item in value:
            values.extend(
                parse_multivalue_cell(
                    item,
                    split_pattern=split_pattern,
                    missing_values=missing_values,
                )
            )
        return values

    if _is_missing_scalar(value):
        return []

    text = str(value).strip()
    if normalize_token_key(text) in missing_keys:
        return []

    # Try real Python literal syntax first.
    # Example: "['LMS logs', 'Student demographics']"
    try:
        parsed = ast.literal_eval(text)
        if _is_list_like(parsed):
            return parse_multivalue_cell(
                parsed,
                split_pattern=split_pattern,
                missing_values=missing_values,
            )
    except Exception:
        pass

    # Handle list-like strings without quotes.
    # Example: "[LMS logs, Student demographics]"
    text = text.strip().strip("[]")

    parts = re.split(split_pattern, text)
    out = []

    for part in parts:
        token = part.strip().strip("'").strip('"').strip()
        if not token:
            continue
        if normalize_token_key(token) in missing_keys:
            continue
        out.append(token)

    return out


def default_unmatched_label(value: str) -> str:
    """Fallback display label for a token that does not match an alias map."""
    value = str(value).strip().strip("[]").strip("'").strip('"')
    value = re.sub(r"\s+", " ", value)
    return value


def extract_canonical_terms(
    value: Any,
    alias_patterns: Mapping[str, Sequence[str]] | None = None,
    keep_unmatched: bool = True,
    split_pattern: str = DEFAULT_SPLIT_PATTERN,
    missing_values: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Extract canonical terms from a possibly multi-value cell.

    Args:
        value:
            Original cell value.
        alias_patterns:
            Mapping of canonical label -> regex patterns.
            Regexes are matched against ``normalize_token_key(token)``.
        keep_unmatched:
            If True, unmapped tokens are preserved using their cleaned raw label.
            If False, unmapped tokens are discarded.
        split_pattern:
            Regex used to split multi-value cells.
        missing_values:
            Values to ignore.

    Returns:
        A list of dictionaries with:
            raw_token, value, matched
    """
    alias_patterns = alias_patterns or {}
    tokens = parse_multivalue_cell(
        value,
        split_pattern=split_pattern,
        missing_values=missing_values,
    )

    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for token in tokens:
        key = normalize_token_key(token)
        matches: list[str] = []

        for canonical, patterns in alias_patterns.items():
            for pattern in patterns:
                if re.search(pattern, key, flags=re.IGNORECASE):
                    matches.append(canonical)
                    break

        if matches:
            for canonical in matches:
                dedupe_key = (key, canonical)
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                records.append(
                    {
                        "raw_token": token,
                        "value": canonical,
                        "matched": True,
                    }
                )
        elif keep_unmatched:
            fallback = default_unmatched_label(token)
            dedupe_key = (key, fallback)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            records.append(
                {
                    "raw_token": token,
                    "value": fallback,
                    "matched": False,
                }
            )

    return records


def detect_column(df: Any, candidates: Sequence[str]) -> str | None:
    """Find a column by normalized-name matching."""
    normalized_columns = {
        normalize_token_key(col): col
        for col in df.columns
    }

    for candidate in candidates:
        key = normalize_token_key(candidate)
        if key in normalized_columns:
            return normalized_columns[key]

    return None


def normalize_task_tables(
    dfs: Mapping[str, Any],
    task_tables: Mapping[str, str] | Sequence[str],
    value_column_candidates: Sequence[str],
    alias_patterns: Mapping[str, Sequence[str]] | None = None,
    value_col: str = "value",
    normalized_column_suffix: str = "__normalized",
    id_column_candidates: Sequence[str] = (
        "source_page_id",
        "page_id",
        "id",
        "source_id",
    ),
    title_column_candidates: Sequence[str] = (
        "source_title",
        "title",
        "paper_title",
    ),
    keep_unmatched: bool = True,
    split_pattern: str = DEFAULT_SPLIT_PATTERN,
    missing_values: set[str] | None = None,
) -> tuple[dict[str, Any], Any, Any]:
    """Normalize one multi-value column across several task tables.

    Args:
        dfs:
            Dictionary of DataFrames, e.g. ``cleaned_dfs``.
        task_tables:
            Either a sequence of table keys, or a mapping of
            ``table_key -> output_task_label``.

            Example:
                {
                    "PRED": "PRED",
                    "DESC": "DESC",
                    "KT": "KT",
                    "REC": "ERS",
                }

        value_column_candidates:
            Candidate column names to normalize, e.g.
            ``["Data sources", "Data source", "Dataset"]``.
        alias_patterns:
            Domain-specific canonicalization map.
        value_col:
            Name of the normalized value column in the long output.

    Returns:
        ``(normalized_tables, long_df, audit_df)``

        normalized_tables:
            Copies of the input task tables with an added normalized list column.

        long_df:
            One row per paper/task/normalized value candidate.

        audit_df:
            Unmatched raw tokens, useful for improving alias maps.
    """
    import pandas as pd

    if isinstance(task_tables, Mapping):
        task_items = list(task_tables.items())
    else:
        task_items = [(task, task) for task in task_tables]

    normalized_tables: dict[str, Any] = {}
    long_rows: list[dict[str, Any]] = []

    for table_key, task_label in task_items:
        if table_key not in dfs:
            continue

        df = dfs[table_key].copy()

        value_column = detect_column(df, value_column_candidates)
        if value_column is None:
            normalized_tables[table_key] = df
            continue

        id_column = detect_column(df, id_column_candidates)
        title_column = detect_column(df, title_column_candidates)

        normalized_column = f"{value_column}{normalized_column_suffix}"
        df[normalized_column] = None

        for row_index, row in df.iterrows():
            raw_value = row.get(value_column)

            term_records = extract_canonical_terms(
                raw_value,
                alias_patterns=alias_patterns,
                keep_unmatched=keep_unmatched,
                split_pattern=split_pattern,
                missing_values=missing_values,
            )

            normalized_values = list(
                dict.fromkeys(record["value"] for record in term_records)
            )
            df.at[row_index, normalized_column] = normalized_values

            if id_column is not None:
                paper_id = row.get(id_column)
            elif title_column is not None:
                paper_id = row.get(title_column)
            else:
                paper_id = f"{table_key}:{row_index}"

            source_title = row.get(title_column) if title_column is not None else ""

            for record in term_records:
                long_rows.append(
                    {
                        "task": task_label,
                        "table": table_key,
                        "paper_id": paper_id,
                        "source_title": source_title,
                        "row_index": row_index,
                        "source_column": value_column,
                        "raw_cell": raw_value,
                        "raw_token": record["raw_token"],
                        value_col: record["value"],
                        "matched": bool(record["matched"]),
                    }
                )

        normalized_tables[table_key] = df

    long_df = pd.DataFrame(long_rows)

    if long_df.empty:
        audit_df = pd.DataFrame(
            columns=["task", "raw_token", value_col, "rows", "papers"]
        )
    else:
        audit_df = (
            long_df[~long_df["matched"]]
            .groupby(["task", "raw_token", value_col], dropna=False)
            .agg(
                rows=("paper_id", "size"),
                papers=("paper_id", "nunique"),
            )
            .reset_index()
            .sort_values(["papers", "rows"], ascending=False)
        )

    return normalized_tables, long_df, audit_df


def build_task_value_count_table(
    long_df: Any,
    task_order: Sequence[str],
    value_col: str = "value",
    paper_id_col: str = "paper_id",
    task_col: str = "task",
    label_col: str = "Value",
    total_col: str = "Total",
    sort_by_total: bool = True,
) -> Any:
    """Build a paper-count table from a normalized long table.

    Counts each paper once per task/value, even if the paper appears in
    multiple extraction rows inside the same task table.

    Output shape:
        Value | PRED | DESC | KT | ERS | Total
    """
    import pandas as pd

    if long_df.empty:
        return pd.DataFrame(columns=[label_col, *task_order, total_col])

    dedup = long_df.dropna(subset=[value_col, paper_id_col, task_col]).copy()

    dedup = dedup.drop_duplicates(
        subset=[task_col, paper_id_col, value_col]
    )

    counts = (
        dedup
        .groupby([value_col, task_col], dropna=False)[paper_id_col]
        .nunique()
        .reset_index(name="n")
    )

    table = (
        counts
        .pivot(index=value_col, columns=task_col, values="n")
        .fillna(0)
        .astype(int)
    )

    for task in task_order:
        if task not in table.columns:
            table[task] = 0

    table = table[list(task_order)]
    table[total_col] = table.sum(axis=1).astype(int)

    if sort_by_total:
        table = table.sort_values(total_col, ascending=False)

    table = table.reset_index().rename(columns={value_col: label_col})

    return table[[label_col, *task_order, total_col]]


__all__ = [
    "DEFAULT_SPLIT_PATTERN",
    "DEFAULT_MISSING_VALUES",
    "normalize_token_key",
    "parse_multivalue_cell",
    "extract_canonical_terms",
    "detect_column",
    "normalize_task_tables",
    "build_task_value_count_table",
]