"""Paper-facing task summary tables.

The notebook summary tables are extraction/audit artifacts: they can contain
multiple rows per paper and long note-like cells. This module converts them
into compact task tables for manuscript/supplement use:

    one output row = one distinct paper contribution within one task

Raw extraction tables are not mutated. The output is additive and auditable.
"""
from __future__ import annotations

import ast
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from notion_zotero.analysis.table_normalization import (
    extract_canonical_terms,
    normalize_token_key,
)
from notion_zotero.core.text_utils import clean_whitespace, remove_ellipsis_fragments
from notion_zotero.schemas.domain_packs import education_learning_analytics as ela


DEFAULT_MAX_CELL_CHARS = 180
DEFAULT_NARRATIVE_MAX_CHARS = 5120
DEFAULT_MAX_LIST_ITEMS = 8
DEFAULT_MAX_RESULT_ITEMS = 4

_CONTRIBUTION_SIGNATURE_FIELDS: dict[str, tuple[str, ...]] = {
    "ERS": (
        "Target of Recommendation",
        "Recommender System Type",
        "Recommendation types",
        "Evaluation",
    ),
    "REC": (
        "Target of Recommendation",
        "Recommender System Type",
        "Recommendation types",
        "Evaluation",
    ),
    "DESC": (
        "Task",
        "Models",
        "Groups Created",
        "Cluster Description",
        "Theoretical Grounding",
        "Thereotical Model",
    ),
    "PRED": (
        "Task",
        "Student Performance Definition",
        "Target",
        "Moment of Prediction",
        "Models",
        "Assessment Strategy",
    ),
    "KT": (
        "Student Performance Definition",
        "Target",
        "Models",
        "Novelty of Model",
        "Flaw of Previous Models",
        "Assessment Strategy",
    ),
}


def _table_to_records(table: Any) -> list[dict[str, Any]]:
    if table is None:
        return []
    if isinstance(table, list):
        return [dict(row) for row in table if isinstance(row, Mapping)]
    if hasattr(table, "to_dict"):
        try:
            return [dict(row) for row in table.to_dict("records")]
        except TypeError:
            pass
    return []


def _detect_row_column(rows: Sequence[Mapping[str, Any]], candidates: Sequence[str]) -> str | None:
    normalized_candidates = {normalize_token_key(candidate) for candidate in candidates}
    for row in rows:
        for column in row:
            if normalize_token_key(column) in normalized_candidates:
                return str(column)
    return None


def _is_missing(value: Any, missing_values: set[str] | None = None) -> bool:
    if value is None:
        return True
    text = clean_whitespace(str(value))
    if not text:
        return True
    missing_keys = {
        normalize_token_key(item)
        for item in (missing_values or ela.PAPER_SUMMARY_MISSING_VALUES)
    }
    return normalize_token_key(text) in missing_keys


def _display_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return "; ".join(_display_value(item) for item in value if not _is_missing(item))
    if isinstance(value, dict):
        return clean_whitespace(str(value))
    text = clean_whitespace(str(value))
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, (list, tuple, set)):
            return "; ".join(_display_value(item) for item in parsed if not _is_missing(item))
    except Exception:
        pass
    text = text.strip().strip("[]").strip("'").strip('"')
    return remove_ellipsis_fragments(clean_whitespace(text))


def _dedupe(values: Sequence[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        value = clean_whitespace(str(value)).strip()
        if not value:
            continue
        key = normalize_token_key(value)
        if key in seen:
            continue
        seen.add(key)
        out.append(value)
    return out


def _shorten(text: str, max_chars: int = DEFAULT_MAX_CELL_CHARS) -> tuple[str, bool]:
    text = clean_whitespace(text)
    if len(text) <= max_chars:
        return text, False

    cut = text[: max_chars + 1]
    boundary = max(cut.rfind("; "), cut.rfind(". "), cut.rfind(", "), cut.rfind(" "))
    if boundary < max(60, int(max_chars * 0.55)):
        boundary = max_chars
    shortened = text[:boundary].rstrip(" ;,.") + "..."
    return shortened, True


def _join_and_shorten(
    values: Sequence[str],
    max_chars: int,
) -> tuple[str, bool, int]:
    unique = _dedupe(values)
    joined = "; ".join(unique)
    display, shortened = _shorten(joined, max_chars=max_chars)
    return display, shortened, len(unique)


def _limit_display_values(
    values: Sequence[str],
    max_items: int = DEFAULT_MAX_LIST_ITEMS,
) -> tuple[list[str], int]:
    unique = _dedupe(values)
    if len(unique) <= max_items:
        return unique, 0
    return unique[:max_items], len(unique) - max_items


def _collect_alias_values(
    rows: Sequence[Mapping[str, Any]],
    candidates: Sequence[str],
    alias_patterns: Mapping[str, Sequence[str]],
    audit_rows: list[dict[str, Any]],
    task: str,
    paper_id: str,
    output_column: str,
    keep_unmatched: bool = True,
) -> list[str]:
    column = _detect_row_column(rows, candidates)
    if column is None:
        return []

    values: list[str] = []
    for row in rows:
        raw_value = row.get(column)
        if _is_missing(raw_value):
            continue
        terms = extract_canonical_terms(
            raw_value,
            alias_patterns=alias_patterns,
            keep_unmatched=keep_unmatched,
            missing_values=ela.PAPER_SUMMARY_MISSING_VALUES,
        )
        for term in terms:
            values.append(str(term["value"]))
            if not term["matched"] and keep_unmatched:
                audit_rows.append(
                    {
                        "task": task,
                        "paper_id": paper_id,
                        "column": output_column,
                        "action": "unmatched_token",
                        "detail": str(term["raw_token"]),
                    }
                )
    return values


def _collect_alias_values_from_all_candidates(
    rows: Sequence[Mapping[str, Any]],
    candidates: Sequence[str],
    alias_patterns: Mapping[str, Sequence[str]],
    audit_rows: list[dict[str, Any]],
    task: str,
    paper_id: str,
    output_column: str,
    keep_unmatched: bool = True,
) -> list[str]:
    values: list[str] = []
    seen_columns: set[str] = set()
    for candidate in candidates:
        column = _detect_row_column(rows, [candidate])
        if column is None or column in seen_columns:
            continue
        seen_columns.add(column)
        for row in rows:
            raw_value = row.get(column)
            if _is_missing(raw_value):
                continue
            terms = extract_canonical_terms(
                raw_value,
                alias_patterns=alias_patterns,
                keep_unmatched=keep_unmatched,
                missing_values=ela.PAPER_SUMMARY_MISSING_VALUES,
            )
            for term in terms:
                values.append(str(term["value"]))
                if not term["matched"] and keep_unmatched:
                    audit_rows.append(
                        {
                            "task": task,
                            "paper_id": paper_id,
                            "column": output_column,
                            "action": "unmatched_token",
                            "detail": str(term["raw_token"]),
                        }
                    )
    return values


def _format_limited_values(
    values: Sequence[str],
    audit_rows: list[dict[str, Any]],
    task: str,
    paper_id: str,
    output_column: str,
    max_items: int = DEFAULT_MAX_LIST_ITEMS,
    max_chars: int = DEFAULT_MAX_CELL_CHARS,
) -> str:
    display_values, remaining = _limit_display_values(values, max_items=max_items)
    if remaining:
        display_values = [*display_values, f"+{remaining} more"]
        audit_rows.append(
            {
                "task": task,
                "paper_id": paper_id,
                "column": output_column,
                "action": "limited_display_items",
                "detail": str(remaining),
            }
        )
    display, shortened, _count = _join_and_shorten(display_values, max_chars=max_chars)
    if shortened:
        audit_rows.append(
            {
                "task": task,
                "paper_id": paper_id,
                "column": output_column,
                "action": "shortened_cell",
                "detail": str(len("; ".join(_dedupe(display_values)))),
            }
        )
    return display


def _format_algorithms(
    rows: Sequence[Mapping[str, Any]],
    audit_rows: list[dict[str, Any]],
    task: str,
    paper_id: str,
    candidates: Sequence[str] = ("Models",),
) -> str:
    values = _collect_alias_values(
        rows,
        candidates,
        ela.ALGORITHM_ALIAS_PATTERNS,
        audit_rows,
        task,
        paper_id,
        "Algorithms / models",
        keep_unmatched=True,
    )
    return _format_limited_values(
        values,
        audit_rows,
        task,
        paper_id,
        "Algorithms / models",
        max_items=8,
        max_chars=150,
    )


def _format_recommender_algorithms(
    rows: Sequence[Mapping[str, Any]],
    audit_rows: list[dict[str, Any]],
    task: str,
    paper_id: str,
) -> str:
    candidates = (
        "Models",
        "Model",
        "Algorithm",
        "Algorithms",
        "Algorithm Used",
        "Recommender System Type",
        "Initialization Method",
        "Updates to Recommendations",
        "Preprocessing Details",
        "Comments",
    )
    values = _collect_alias_values_from_all_candidates(
        rows,
        candidates,
        ela.RECOMMENDER_ALGORITHM_ALIAS_PATTERNS,
        audit_rows,
        task,
        paper_id,
        "Algorithms / models",
        keep_unmatched=False,
    )
    if not values:
        return _format_algorithms(
            rows,
            audit_rows,
            task,
            paper_id,
            candidates=("Recommender System Type", "Models", "Algorithm", "Algorithms"),
        )
    return _format_limited_values(
        values,
        audit_rows,
        task,
        paper_id,
        "Algorithms / models",
        max_items=8,
        max_chars=170,
    )


def _format_features(
    rows: Sequence[Mapping[str, Any]],
    audit_rows: list[dict[str, Any]],
    task: str,
    paper_id: str,
) -> str:
    categories = _collect_alias_values(
        rows,
        ["Features"],
        ela.FEATURE_CATEGORY_ALIAS_PATTERNS,
        audit_rows,
        task,
        paper_id,
        "Features",
        keep_unmatched=False,
    )
    if categories:
        return _format_limited_values(
            categories,
            audit_rows,
            task,
            paper_id,
            "Features",
            max_items=7,
            max_chars=170,
        )
    return _merge_raw_fields(rows, ["Features"], audit_rows, task, paper_id, "Features", 170)


def _canonical_metric_label(label: str) -> str:
    key = normalize_token_key(label)
    return ela.RESULT_METRIC_LABELS.get(key, clean_whitespace(label).strip())


def _extract_metric_snippets(text: str) -> list[str]:
    snippets: list[str] = []
    metric_pattern = re.compile(
        r"([A-Za-z][A-Za-z0-9@/_+\- ]{0,35})\s*[:=]\s*"
        r"([+-]?\d+(?:\.\d+)?%?)"
        r"(?:\s*-\s*([^,;}\n]+))?"
    )
    for metric, value, model in metric_pattern.findall(text):
        metric_label = _canonical_metric_label(metric)
        snippet = f"{metric_label}={value}"
        model = clean_whitespace(model).strip()
        if model:
            snippet += f" ({model})"
        snippets.append(snippet)
    return snippets


def _format_results(
    rows: Sequence[Mapping[str, Any]],
    audit_rows: list[dict[str, Any]],
    task: str,
    paper_id: str,
    candidates: Sequence[str] = ("Performance Metric: Best Model", "Evaluation"),
) -> str:
    raw_text = _merge_raw_fields(
        rows,
        candidates,
        audit_rows,
        task,
        paper_id,
        "Results",
        max_chars=DEFAULT_NARRATIVE_MAX_CHARS,
    )
    snippets = _extract_metric_snippets(raw_text)
    if snippets:
        return _format_limited_values(
            snippets,
            audit_rows,
            task,
            paper_id,
            "Results",
            max_items=DEFAULT_MAX_RESULT_ITEMS,
            max_chars=DEFAULT_NARRATIVE_MAX_CHARS,
        )
    display, shortened = _shorten(raw_text, max_chars=DEFAULT_MAX_CELL_CHARS)
    if shortened:
        audit_rows.append(
            {
                "task": task,
                "paper_id": paper_id,
                "column": "Results",
                "action": "shortened_cell",
                "detail": str(len(raw_text)),
            }
        )
    return display


def _normalize_values(
    rows: Sequence[Mapping[str, Any]],
    candidates: Sequence[str],
    alias_patterns: Mapping[str, Sequence[str]] | None,
    audit_rows: list[dict[str, Any]],
    task: str,
    paper_id: str,
    output_column: str,
    max_chars: int = DEFAULT_MAX_CELL_CHARS,
    missing_values: set[str] | None = None,
) -> str:
    column = _detect_row_column(rows, candidates)
    if column is None:
        return ""

    values: list[str] = []
    for row in rows:
        raw_value = row.get(column)
        if _is_missing(raw_value, missing_values):
            continue
        if alias_patterns:
            terms = extract_canonical_terms(
                raw_value,
                alias_patterns=alias_patterns,
                keep_unmatched=True,
                missing_values=missing_values or ela.PAPER_SUMMARY_MISSING_VALUES,
            )
            for term in terms:
                values.append(str(term["value"]))
                if not term["matched"]:
                    audit_rows.append(
                        {
                            "task": task,
                            "paper_id": paper_id,
                            "column": output_column,
                            "action": "unmatched_token",
                            "detail": str(term["raw_token"]),
                        }
                    )
        else:
            values.append(_display_value(raw_value))

    display, shortened, value_count = _join_and_shorten(values, max_chars=max_chars)
    if value_count > 1:
        audit_rows.append(
            {
                "task": task,
                "paper_id": paper_id,
                "column": output_column,
                "action": "merged_values",
                "detail": str(value_count),
            }
        )
    if shortened:
        audit_rows.append(
            {
                "task": task,
                "paper_id": paper_id,
                "column": output_column,
                "action": "shortened_cell",
                "detail": str(len("; ".join(_dedupe(values)))),
            }
        )
    return display


def _merge_raw_fields(
    rows: Sequence[Mapping[str, Any]],
    candidates: Sequence[str],
    audit_rows: list[dict[str, Any]],
    task: str,
    paper_id: str,
    output_column: str,
    max_chars: int = DEFAULT_NARRATIVE_MAX_CHARS,
) -> str:
    values: list[str] = []
    for candidate in candidates:
        column = _detect_row_column(rows, [candidate])
        if column is None:
            continue
        for row in rows:
            value = row.get(column)
            if not _is_missing(value):
                values.append(_display_value(value))

    display, shortened, value_count = _join_and_shorten(values, max_chars=max_chars)
    if value_count > 1:
        audit_rows.append(
            {
                "task": task,
                "paper_id": paper_id,
                "column": output_column,
                "action": "merged_values",
                "detail": str(value_count),
            }
        )
    if shortened:
        audit_rows.append(
            {
                "task": task,
                "paper_id": paper_id,
                "column": output_column,
                "action": "shortened_cell",
                "detail": str(len("; ".join(_dedupe(values)))),
            }
        )
    return display


def _combine_parts(
    parts: Sequence[str],
    max_chars: int,
) -> str:
    values = [part for part in (_display_value(part) for part in parts) if part]
    display, _ = _shorten(" - ".join(_dedupe(values)), max_chars=max_chars)
    return display


def _canonicalize_free_text(
    text: str,
    alias_patterns: Mapping[str, Sequence[str]],
) -> str:
    text = _display_value(text)
    if not text:
        return ""
    normalized_text = normalize_token_key(text)
    for canonical, patterns in alias_patterns.items():
        for pattern in patterns:
            try:
                if re.search(pattern, text, flags=re.IGNORECASE):
                    return canonical
            except re.error:
                pass
            normalized_pattern = normalize_token_key(pattern)
            if normalized_pattern and normalized_pattern in normalized_text:
                return canonical
    return text


def _first_record_value(records: Sequence[Mapping[str, Any]], candidates: Sequence[str]) -> Any:
    column = _detect_row_column(records, candidates)
    if column is None:
        return ""
    for record in records:
        value = record.get(column)
        if not _is_missing(value):
            return value
    return ""


def _contribution_signature(row: Mapping[str, Any], task: str) -> str:
    parts: list[str] = []
    for field in _CONTRIBUTION_SIGNATURE_FIELDS.get(task, ()):
        value = row.get(field)
        if not _is_missing(value):
            parts.append(normalize_token_key(_display_value(value)))
    return " | ".join(part for part in parts if part)


def _group_rows_by_contribution(
    task_rows: Sequence[Mapping[str, Any]],
    table_key: str,
    output_task: str,
) -> dict[tuple[str, str], list[Mapping[str, Any]]]:
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for index, row in enumerate(task_rows):
        paper_id = _display_value(
            row.get("source_page_id")
            or row.get("page_id")
            or row.get("id")
            or row.get("source_title")
            or f"{table_key}:{index}"
        )
        signature = _contribution_signature(row, output_task or table_key)
        grouped[(paper_id, signature or "__paper__")].append(row)
    return grouped


def _citation_from_reference(reference: Mapping[str, Any] | None, fallback_title: str = "") -> str:
    reference = reference or {}
    authors = _display_value(reference.get("authors"))
    year = _display_value(reference.get("year"))
    title = _display_value(reference.get("title") or fallback_title)

    author_label = ""
    if authors:
        first_author = authors.split(";")[0].split(",")[0].strip()
        author_label = first_author or authors
    if author_label and year:
        return f"{author_label} ({year})"
    if author_label:
        return author_label
    if title and year:
        return f"{title} ({year})"
    return title or "Unknown study"


def _reference_year(reference: Mapping[str, Any] | None, study_label: str = "") -> int | None:
    reference = reference or {}
    for value in (reference.get("year"), study_label):
        text = _display_value(value)
        match = re.search(r"\b(19|20)\d{2}\b", text)
        if match:
            return int(match.group(0))
    return None


def _paper_sort_key(row: Mapping[str, str]) -> tuple[int, str, str]:
    year = _reference_year(None, row.get("Study", ""))
    sort_year = year if year is not None else 9999
    study = clean_whitespace(row.get("Study", "")).lower()
    title = clean_whitespace(row.get("Paper title", "")).lower()
    return sort_year, study, title


def _reference_index(reading_list: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    index: dict[str, Mapping[str, Any]] = {}
    for row in reading_list:
        for key in ("page_id", "id", "source_page_id"):
            value = row.get(key)
            if not _is_missing(value):
                index[str(value)] = row
    return index


def _sample_setting(
    rows: Sequence[Mapping[str, Any]],
    audit_rows: list[dict[str, Any]],
    task: str,
    paper_id: str,
) -> str:
    students = _merge_raw_fields(
        rows,
        ["Students"],
        audit_rows,
        task,
        paper_id,
        "Sample / setting",
        max_chars=90,
    )
    courses = _merge_raw_fields(
        rows,
        ["Courses"],
        audit_rows,
        task,
        paper_id,
        "Sample / setting",
        max_chars=90,
    )
    return _combine_parts([students, courses], max_chars=150)


def _base_output_row(
    task: str,
    paper_id: str,
    rows: Sequence[Mapping[str, Any]],
    references: Mapping[str, Mapping[str, Any]],
    audit_rows: list[dict[str, Any]],
    include_title: bool,
) -> dict[str, str]:
    reference = references.get(paper_id, {})
    fallback_title = _display_value(_first_record_value(rows, ["source_title", "title"]))
    out = {
        "Study": _citation_from_reference(reference, fallback_title),
    }
    if include_title:
        out["Paper title"] = _display_value(reference.get("title") or fallback_title)
    out.update(
        {
            "Learner representation": _display_value(reference.get("Learner Representation")),
            "Work nature": _display_value(reference.get("Work Nature")),
            "Deployed / Deployable": _display_value(reference.get("Deployed/ Deployable")),
            "Context": _normalize_values(
                rows,
                ela.CONTEXT_COLUMN_CANDIDATES,
                ela.CONTEXT_ALIAS_PATTERNS,
                audit_rows,
                task,
                paper_id,
                "Context",
                max_chars=80,
            ),
            "Teaching modality": _normalize_values(
                rows,
                ela.TEACHING_METHOD_COLUMN_CANDIDATES,
                ela.TEACHING_METHOD_ALIAS_PATTERNS,
                audit_rows,
                task,
                paper_id,
                "Teaching modality",
                max_chars=90,
            ),
            "Data sources": _normalize_values(
                rows,
                ela.DATA_SOURCE_COLUMN_CANDIDATES,
                ela.DATA_SOURCE_ALIAS_PATTERNS,
                audit_rows,
                task,
                paper_id,
                "Data sources",
                max_chars=150,
                missing_values=ela.DATA_SOURCE_MISSING_VALUES,
            ),
            "Sample / setting": _sample_setting(rows, audit_rows, task, paper_id),
        }
    )
    return out


def _build_ers_row(
    paper_id: str,
    rows: Sequence[Mapping[str, Any]],
    references: Mapping[str, Mapping[str, Any]],
    audit_rows: list[dict[str, Any]],
    include_title: bool,
) -> dict[str, str]:
    task = "ERS"
    out = _base_output_row(task, paper_id, rows, references, audit_rows, include_title)
    out.update(
        {
            "Recommendation target": _merge_raw_fields(
                rows, ["Target of Recommendation"], audit_rows, task, paper_id, "Recommendation target", 120
            ),
            "Recommender type": _normalize_values(
                rows,
                ela.RECOMMENDER_TYPE_COLUMN_CANDIDATES,
                ela.RECOMMENDER_TYPE_ALIAS_PATTERNS,
                audit_rows,
                task,
                paper_id,
                "Recommender type",
                max_chars=110,
            ),
            "Recommendation output": _merge_raw_fields(
                rows, ["Recommendation types"], audit_rows, task, paper_id, "Recommendation output", 140
            ),
            "Algorithms / models": _format_recommender_algorithms(rows, audit_rows, task, paper_id),
            "Results": _format_results(rows, audit_rows, task, paper_id, ("Evaluation",)),
            "Limitations": _merge_raw_fields(
                rows, ["Limitations"], audit_rows, task, paper_id, "Limitations", DEFAULT_NARRATIVE_MAX_CHARS
            ),
            "Key implementation note": _merge_raw_fields(
                rows,
                ["Initialization Method", "Updates to Recommendations", "Comments"],
                audit_rows,
                task,
                paper_id,
                "Key implementation note",
                500,
            ),
        }
    )
    out["Recommendation target"] = _canonicalize_free_text(
        out["Recommendation target"],
        ela.RECOMMENDATION_TARGET_ALIAS_PATTERNS,
    )
    return out


def _build_desc_row(
    paper_id: str,
    rows: Sequence[Mapping[str, Any]],
    references: Mapping[str, Mapping[str, Any]],
    audit_rows: list[dict[str, Any]],
    include_title: bool,
) -> dict[str, str]:
    task = "DESC"
    out = _base_output_row(task, paper_id, rows, references, audit_rows, include_title)
    out.update(
        {
            "Analytic task": _normalize_values(
                rows,
                ela.ANALYTIC_TASK_COLUMN_CANDIDATES,
                ela.ANALYTIC_TASK_ALIAS_PATTERNS,
                audit_rows,
                task,
                paper_id,
                "Analytic task",
                max_chars=100,
            ),
            "Algorithms / models": _format_algorithms(rows, audit_rows, task, paper_id),
            "Results / patterns": _merge_raw_fields(
                rows,
                ["Groups Created", "Cluster Description", "Performance Metric: Best Model"],
                audit_rows,
                task,
                paper_id,
                "Results / patterns",
                400,
            ),
            "Theoretical grounding": _normalize_values(
                rows,
                ela.THEORETICAL_GROUNDING_COLUMN_CANDIDATES,
                ela.THEORETICAL_GROUNDING_ALIAS_PATTERNS,
                audit_rows,
                task,
                paper_id,
                "Theoretical grounding",
                max_chars=120,
            ),
            "Main result / implication": _merge_raw_fields(
                rows, ["Implications", "Comments"], audit_rows, task, paper_id, "Main result / implication", DEFAULT_NARRATIVE_MAX_CHARS
            ),
            "Limitations": _merge_raw_fields(
                rows, ["Limitations"], audit_rows, task, paper_id, "Limitations", DEFAULT_NARRATIVE_MAX_CHARS
            ),
        }
    )
    return out


def _prediction_task_type(
    rows: Sequence[Mapping[str, Any]],
    audit_rows: list[dict[str, Any]],
    task: str,
    paper_id: str,
) -> str:
    return _normalize_values(
        rows,
        ela.ANALYTIC_TASK_COLUMN_CANDIDATES,
        ela.ANALYTIC_TASK_ALIAS_PATTERNS,
        audit_rows,
        task,
        paper_id,
        "Prediction task type",
        max_chars=80,
    )


def _prediction_target_timing(
    rows: Sequence[Mapping[str, Any]],
    audit_rows: list[dict[str, Any]],
    task: str,
    paper_id: str,
) -> str:
    performance_definition = _merge_raw_fields(
        rows,
        ["Student Performance Definition"],
        audit_rows,
        task,
        paper_id,
        "Prediction target / timing",
        110,
    )
    target = _merge_raw_fields(rows, ["Target"], audit_rows, task, paper_id, "Prediction target / timing", 100)
    timing = _merge_raw_fields(
        rows,
        ["Moment of Prediction"],
        audit_rows,
        task,
        paper_id,
        "Prediction target / timing",
        120,
    )
    target_label = _canonicalize_free_text(
        _combine_parts([performance_definition, target], max_chars=150),
        ela.PREDICTION_TARGET_ALIAS_PATTERNS,
    )
    return _combine_parts([target_label, timing], max_chars=190)


def _build_pred_row(
    paper_id: str,
    rows: Sequence[Mapping[str, Any]],
    references: Mapping[str, Mapping[str, Any]],
    audit_rows: list[dict[str, Any]],
    include_title: bool,
) -> dict[str, str]:
    task = "PRED"
    out = _base_output_row(task, paper_id, rows, references, audit_rows, include_title)
    out.update(
        {
            "Prediction task type": _prediction_task_type(rows, audit_rows, task, paper_id),
            "Prediction target / timing": _prediction_target_timing(rows, audit_rows, task, paper_id),
            "Features": _format_features(rows, audit_rows, task, paper_id),
            "Algorithms / models": _format_algorithms(rows, audit_rows, task, paper_id),
            "Assessment strategy": _normalize_values(
                rows,
                ela.ASSESSMENT_STRATEGY_COLUMN_CANDIDATES,
                ela.ASSESSMENT_STRATEGY_ALIAS_PATTERNS,
                audit_rows,
                task,
                paper_id,
                "Assessment strategy",
                max_chars=100,
            ),
            "Results": _format_results(rows, audit_rows, task, paper_id),
            "Limitations": _merge_raw_fields(
                rows, ["Limitations"], audit_rows, task, paper_id, "Limitations", DEFAULT_NARRATIVE_MAX_CHARS
            ),
        }
    )
    return out


def _build_kt_row(
    paper_id: str,
    rows: Sequence[Mapping[str, Any]],
    references: Mapping[str, Mapping[str, Any]],
    audit_rows: list[dict[str, Any]],
    include_title: bool,
) -> dict[str, str]:
    task = "KT"
    out = _base_output_row(task, paper_id, rows, references, audit_rows, include_title)
    out.update(
        {
            "KT target": _canonicalize_free_text(
                _combine_parts(
                    [
                        _merge_raw_fields(
                            rows,
                            ["Student Performance Definition"],
                            audit_rows,
                            task,
                            paper_id,
                            "KT target",
                            110,
                        ),
                        _merge_raw_fields(rows, ["Target"], audit_rows, task, paper_id, "KT target", 100),
                    ],
                    max_chars=170,
                ),
                ela.KT_TARGET_ALIAS_PATTERNS,
            ),
            "Algorithms / models": _format_algorithms(rows, audit_rows, task, paper_id),
            "Assessment strategy": _normalize_values(
                rows,
                ela.ASSESSMENT_STRATEGY_COLUMN_CANDIDATES,
                ela.ASSESSMENT_STRATEGY_ALIAS_PATTERNS,
                audit_rows,
                task,
                paper_id,
                "Assessment strategy",
                max_chars=100,
            ),
            "Results": _format_results(rows, audit_rows, task, paper_id),
            "Prior-model limitations": _merge_raw_fields(
                rows,
                ["Flaw of Previous Models"],
                audit_rows,
                task,
                paper_id,
                "Prior-model limitations",
                500,
            ),
            "New contribution": _merge_raw_fields(
                rows,
                ["Novelty of Model", "Comments"],
                audit_rows,
                task,
                paper_id,
                "New contribution",
                500,
            ),
            "Study limitations": _merge_raw_fields(
                rows, ["Limitations"], audit_rows, task, paper_id, "Study limitations", DEFAULT_NARRATIVE_MAX_CHARS
            ),
        }
    )
    return out


_ROW_BUILDERS = {
    "ERS": _build_ers_row,
    "REC": _build_ers_row,
    "DESC": _build_desc_row,
    "PRED": _build_pred_row,
    "KT": _build_kt_row,
}


def build_paper_summary_tables(
    dfs: Mapping[str, Any],
    task_tables: Mapping[str, str] | None = None,
    reading_list_key: str = "Reading List",
    include_title: bool = True,
) -> tuple[dict[str, list[dict[str, str]]], list[dict[str, str]]]:
    """Build camera-ready task tables from cleaned notebook summary tables.

    Args:
        dfs: Mapping of notebook summary table name to DataFrame-like object or
            list of row dictionaries.
        task_tables: Mapping of input task table key to output task label.
            Defaults to the education-learning-analytics paper table mapping.
        reading_list_key: Key used for Reading List metadata in *dfs*.
        include_title: Include ``Paper title`` in task table outputs.

    Returns:
        ``(paper_tables, audit_rows)``. ``paper_tables`` maps task labels to
        row dictionaries. Repeated papers are only merged when their
        task-specific contribution signature matches. ``audit_rows`` records
        duplicate-row merges, distinct same-paper contributions, unmatched
        controlled-vocabulary values, and shortened cells.
    """
    task_tables = task_tables or ela.PAPER_TASK_TABLES
    reading_records = _table_to_records(dfs.get(reading_list_key))
    references = _reference_index(reading_records)
    output: dict[str, list[dict[str, str]]] = {}
    audit_rows: list[dict[str, str]] = []

    for table_key, output_task in task_tables.items():
        task_rows = _table_to_records(dfs.get(table_key))
        if not task_rows:
            continue

        builder = _ROW_BUILDERS.get(output_task) or _ROW_BUILDERS.get(table_key)
        if builder is None:
            continue

        grouped = _group_rows_by_contribution(task_rows, table_key, output_task)
        paper_group_counts: dict[str, int] = defaultdict(int)
        for paper_id, _signature in grouped:
            paper_group_counts[paper_id] += 1

        paper_rows: list[dict[str, str]] = []
        for (paper_id, signature), rows in grouped.items():
            if paper_group_counts[paper_id] > 1:
                audit_rows.append(
                    {
                        "task": output_task,
                        "paper_id": paper_id,
                        "column": "__row__",
                        "action": "preserved_distinct_paper_contribution",
                        "detail": signature,
                    }
                )
            if len(rows) > 1:
                audit_rows.append(
                    {
                        "task": output_task,
                        "paper_id": paper_id,
                        "column": "__row__",
                        "action": "merged_duplicate_extraction_rows",
                        "detail": str(len(rows)),
                    }
                )
            paper_rows.append(builder(paper_id, rows, references, audit_rows, include_title))

        output[output_task] = sorted(paper_rows, key=_paper_sort_key)

    return output, audit_rows


def build_paper_summary_dataframes(
    dfs: Mapping[str, Any],
    task_tables: Mapping[str, str] | None = None,
    reading_list_key: str = "Reading List",
    include_title: bool = True,
) -> tuple[dict[str, Any], Any]:
    """Pandas wrapper for :func:`build_paper_summary_tables`."""
    try:
        import pandas as pd
    except ImportError as exc:
        raise ImportError(
            "pandas is required for build_paper_summary_dataframes. "
            "Use build_paper_summary_tables for row dictionaries."
        ) from exc

    tables, audit_rows = build_paper_summary_tables(
        dfs,
        task_tables=task_tables,
        reading_list_key=reading_list_key,
        include_title=include_title,
    )
    return {name: pd.DataFrame(rows) for name, rows in tables.items()}, pd.DataFrame(audit_rows)


def write_paper_summary_workbook(
    dfs: Mapping[str, Any],
    output_path: str | Path = "data/analysis_outputs/paper_task_summary_tables.xlsx",
    task_tables: Mapping[str, str] | None = None,
    reading_list_key: str = "Reading List",
    include_title: bool = True,
) -> Path:
    """Write paper-facing task tables and audit rows to an Excel workbook."""
    try:
        import pandas as pd  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "pandas is required to write the paper summary workbook. "
            "Install the analysis extras with: pip install -e .[analysis]"
        ) from exc

    tables, audit = build_paper_summary_dataframes(
        dfs,
        task_tables=task_tables,
        reading_list_key=reading_list_key,
        include_title=include_title,
    )
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with pd.ExcelWriter(path) as writer:
            for sheet_name, df in tables.items():
                df.to_excel(writer, sheet_name=str(sheet_name)[:31], index=False)
            audit.to_excel(writer, sheet_name="audit", index=False)
    except ImportError as exc:
        raise ImportError(
            "An Excel writer engine is required. Install openpyxl or the "
            "analysis extras with: pip install -e .[analysis]"
        ) from exc
    return path


# ---------------------------------------------------------------------------
# generate_table2 — data sources by LA task (R-006)
# ---------------------------------------------------------------------------

#: Mapping from canonical task_id in bundle to display column label
_TASK_ID_TO_LABEL: dict[str, str] = {
    "performance_prediction": "PRED",
    "descriptive_modelling": "DESC",
    "knowledge_tracing": "KT",
    "recommender_systems": "ERS",
}

#: Ordered display columns for Table 2
_TABLE2_TASK_ORDER: list[str] = ["PRED", "DESC", "KT", "ERS"]

#: Missing-value sentinels for the Data sources field
_DS_MISSING = {
    "",
    "none",
    "n/a",
    "na",
    "not applicable",
    "none specified",
    "not specified",
    "-",
}

#: Caption text for the Markdown output
_TABLE2_MD_CAPTION = (
    "**Table II** – Data sources identified in the reviewed studies by analytical task. "
    "Counts represent the number of papers using each data source."
)


def _load_canonical_bundles(canonical_dir: "Path") -> "list[dict]":
    """Load all *.canonical.json bundles from *canonical_dir*."""
    import json

    bundles = []
    for path in sorted(canonical_dir.glob("*.canonical.json")):
        try:
            bundles.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            continue
    return bundles


def _bundle_task_label(bundle: dict) -> "str | None":
    """Return the display-label (PRED/DESC/KT/ERS) for the bundle's primary task."""
    tasks = bundle.get("tasks") or []
    for task in tasks:
        task_id = (task.get("id") or "").strip()
        label = _TASK_ID_TO_LABEL.get(task_id)
        if label is not None:
            return label
    return None


def _collect_data_source_terms(
    bundle: dict,
) -> "list[dict]":
    """Extract canonical data-source terms from all task_extractions in *bundle*.

    Returns a list of dicts with keys: raw_token, value, matched.
    Duplicates within the same bundle are kept so the caller can inspect
    per-extraction occurrences; deduplication to paper level is done upstream.
    """
    terms: list[dict] = []
    for te in bundle.get("task_extractions") or []:
        for row in te.get("extracted") or []:
            raw_ds = row.get("Data sources")
            if raw_ds is None:
                continue
            raw_str = str(raw_ds).strip()
            if normalize_token_key(raw_str) in _DS_MISSING:
                continue
            row_terms = extract_canonical_terms(
                raw_ds,
                alias_patterns=ela.DATA_SOURCE_ALIAS_PATTERNS,
                keep_unmatched=True,
                missing_values=ela.DATA_SOURCE_MISSING_VALUES,
            )
            terms.extend(row_terms)
    return terms


def generate_table2(
    canonical_dir: "str | Path",
    output_dir: "str | Path | None" = None,
    audit_dir: "str | Path | None" = None,
) -> "Any":
    """Generate Table 2 — data sources by LA task (R-006).

    Reads all ``*.canonical.json`` bundles from *canonical_dir*, counts unique
    papers per (task, data-source category), and returns a cross-tab DataFrame.

    Count semantics
    ---------------
    A paper using a data source across multiple extraction rows counts **once**
    per task per data-source category (dedup on paper_id within task).

    Output files (written to *output_dir* and *audit_dir*)
    -------------------------------------------------------
    - ``data_source_by_task.xlsx``
    - ``data_source_by_task.csv``
    - ``data_source_by_task.md`` — includes Table II caption
    - ``../audits/table2_unmatched_audit.md`` — unmatched tokens with examples

    Args:
        canonical_dir:
            Directory containing ``*.canonical.json`` bundle files.
        output_dir:
            Directory for table outputs.  Defaults to
            ``<repo_root>/data/analysis_outputs/la_review/tables/``.
        audit_dir:
            Directory for audit outputs.  Defaults to
            ``<repo_root>/data/analysis_outputs/la_review/audits/``.

    Returns:
        ``pandas.DataFrame`` with columns:
        ``Data source | PRED | DESC | KT | ERS | Total``
    """
    try:
        import pandas as pd
    except ImportError as exc:
        raise ImportError(
            "pandas is required for generate_table2. "
            "Install the analysis extras: pip install -e .[analysis]"
        ) from exc

    canonical_dir = Path(canonical_dir)

    # Resolve output directories
    _repo_root = Path(__file__).resolve().parents[3]
    _la_review_root = _repo_root / "data" / "analysis_outputs" / "la_review"

    if output_dir is None:
        output_dir = _la_review_root / "tables"
    if audit_dir is None:
        audit_dir = _la_review_root / "audits"

    output_dir = Path(output_dir)
    audit_dir = Path(audit_dir)

    bundles = _load_canonical_bundles(canonical_dir)

    # -----------------------------------------------------------------------
    # Build long table: one record per (paper_id, task_label, category)
    # We also collect unmatched tokens for audit output.
    # -----------------------------------------------------------------------

    # For counting: set of paper_ids per (task_label, category)
    paper_sets: dict[tuple[str, str], set[str]] = {}

    # For audit: unmatched raw tokens with paper_id examples
    # Structure: {raw_token: {"count": int, "papers": set}}
    unmatched_index: dict[str, dict] = {}

    for bundle in bundles:
        task_label = _bundle_task_label(bundle)
        if task_label is None:
            # Not one of the four primary tasks — skip
            continue

        paper_id = (bundle.get("provenance") or {}).get("source_id", "")
        if not paper_id:
            refs = bundle.get("references") or []
            paper_id = (refs[0].get("id") or "") if refs else ""
        if not paper_id:
            continue

        # Collect per-paper categories (dedup within paper x task x category)
        seen_categories_this_paper: set[str] = set()

        terms = _collect_data_source_terms(bundle)
        for term in terms:
            if term["matched"]:
                category = term["value"]
                key = (task_label, category)
                if key not in paper_sets:
                    paper_sets[key] = set()
                if category not in seen_categories_this_paper:
                    paper_sets[key].add(paper_id)
                    seen_categories_this_paper.add(category)
            else:
                # Unmatched token — collect for audit
                raw_token = str(term["raw_token"]).strip()
                if raw_token not in unmatched_index:
                    unmatched_index[raw_token] = {"count": 0, "papers": set()}
                unmatched_index[raw_token]["count"] += 1
                unmatched_index[raw_token]["papers"].add(paper_id)

    # -----------------------------------------------------------------------
    # Pivot into a DataFrame
    # -----------------------------------------------------------------------

    # Collect all categories (rows) from matched terms
    all_categories: set[str] = {cat for (_task, cat) in paper_sets}

    # Sort categories by descending Total count, then alphabetically
    def _category_total(cat: str) -> int:
        return sum(
            len(paper_sets.get((t, cat), set()))
            for t in _TABLE2_TASK_ORDER
        )

    sorted_categories = sorted(
        all_categories,
        key=lambda c: (-_category_total(c), c),
    )

    output_rows: list[dict] = []
    for cat in sorted_categories:
        row: dict = {"Data source": cat}
        total = 0
        for task in _TABLE2_TASK_ORDER:
            n = len(paper_sets.get((task, cat), set()))
            row[task] = n
            total += n
        row["Total"] = total
        output_rows.append(row)

    col_order = ["Data source", *_TABLE2_TASK_ORDER, "Total"]
    df = pd.DataFrame(output_rows, columns=col_order)

    # -----------------------------------------------------------------------
    # Write output files
    # -----------------------------------------------------------------------

    output_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)

    # CSV
    csv_path = output_dir / "data_source_by_task.csv"
    df.to_csv(csv_path, index=False)

    # Markdown (with caption)
    md_path = output_dir / "data_source_by_task.md"
    md_lines: list[str] = [
        _TABLE2_MD_CAPTION,
        "",
        "| " + " | ".join(col_order) + " |",
        "| " + " | ".join("---" for _ in col_order) + " |",
    ]
    for _, row in df.iterrows():
        md_lines.append("| " + " | ".join(str(row[c]) for c in col_order) + " |")
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    # Excel
    xlsx_path = output_dir / "data_source_by_task.xlsx"
    try:
        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Table2_DataSource", index=False)
    except ImportError:
        pass  # Excel write is best-effort; CSV is the authoritative output

    # Audit report: unmatched tokens
    audit_path = audit_dir / "table2_unmatched_audit.md"
    audit_lines: list[str] = [
        "# Table 2 Unmatched Data-Source Token Audit",
        "",
        f"Generated from `{canonical_dir}`.",
        "",
        f"**Total distinct unmatched tokens:** {len(unmatched_index)}",
        "",
        "| Token | Occurrence count | Example paper IDs |",
        "| --- | --- | --- |",
    ]
    # Sort by occurrence count descending
    for token, info in sorted(
        unmatched_index.items(), key=lambda x: -x[1]["count"]
    ):
        example_papers = "; ".join(sorted(info["papers"])[:3])
        audit_lines.append(
            f"| {token} | {info['count']} | {example_papers} |"
        )
    audit_path.write_text("\n".join(audit_lines) + "\n", encoding="utf-8")

    return df


# ---------------------------------------------------------------------------
# generate_table4 — task synthesis matrix (R-007)
# generate_table5 — evaluation maturity by task (R-008)
#
# Both read the same canonical bundles as generate_table2/3 and aggregate to
# the task level.  Table 4 is a qualitative synthesis (one row per task); Table
# 5 is a quantitative maturity cross-tab (one row per task per maturity level).
# ---------------------------------------------------------------------------

#: One-line purpose statement per LA task (domain definition — not derived data).
_TASK_PURPOSE: dict[str, str] = {
    "PRED": "Predict future student outcomes (grades, pass/fail, dropout, retention) "
    "to enable early, targeted intervention.",
    "DESC": "Describe and segment learner behaviour and profiles through clustering "
    "and exploratory modelling.",
    "KT": "Model the evolving knowledge state of a student over time to estimate "
    "mastery and guide practice.",
    "ERS": "Recommend learning resources, activities, peers, or paths tailored to "
    "the individual learner.",
}

#: Actionability-gap synthesis per task (review interpretation, not a count).
_TASK_ACTIONABILITY_GAP: dict[str, str] = {
    "PRED": "Few studies move beyond retrospective backtesting to deployed "
    "early-warning systems with evaluated interventions.",
    "DESC": "Descriptive clusters are rarely linked to actionable interventions or "
    "validated prospectively.",
    "KT": "Knowledge-tracing gains are mostly benchmarked offline; classroom "
    "deployment and learning-impact evidence is sparse.",
    "ERS": "Recommenders are seldom evaluated with real learners over time; "
    "long-term learning-outcome effects are largely untested.",
}

#: Ordered evaluation-maturity scale (R-008), lowest to highest.
_MATURITY_LEVELS: list[str] = [
    "public benchmark only",
    "backtested",
    "tested with new students",
    "deployed",
    "deployed with intervention evaluation",
]

#: Crosswalk: PRED actionability_status (WP2 classifier) -> maturity level.
_ACTIONABILITY_TO_MATURITY: dict[str, str] = {
    "deployed_with_intervention_evaluation": "deployed with intervention evaluation",
    "deployed_or_deployable": "deployed",
    "early_backtest_only": "backtested",
    "retrospective_only": "backtested",
    "unclear": "backtested",
}

#: Crosswalk: DEPLOYED_STATUS canonical value (non-PRED tasks) -> maturity level.
_DEPLOYED_STATUS_TO_MATURITY: dict[str, str] = {
    "Deployed by Instructor": "deployed",
    "Prototype": "tested with new students",
    "Not Ready": "backtested",
    "Out of Scope": "backtested",
}

_TABLE4_COLUMNS: list[str] = [
    "Task",
    "Purpose",
    "Data sources",
    "Representations",
    "Models",
    "Metrics",
    "Actionability gaps",
]


def _bundle_paper_id(bundle: dict) -> str:
    """Return the stable paper id for a canonical *bundle* (provenance first)."""
    paper_id = (bundle.get("provenance") or {}).get("source_id", "") or ""
    if not paper_id:
        refs = bundle.get("references") or []
        paper_id = (refs[0].get("id") or "") if refs else ""
    return str(paper_id)


def _bundle_extracted_rows(bundle: dict) -> list[dict]:
    """Flatten all task_extractions[*].extracted rows of a *bundle*."""
    rows: list[dict] = []
    for te in bundle.get("task_extractions") or []:
        rows.extend(te.get("extracted") or [])
    return rows


def _group_bundles_by_task(
    bundles: list[dict],
) -> dict[str, list[tuple[str, list[dict]]]]:
    """Group bundles into ``{task_label: [(paper_id, extracted_rows), ...]}``."""
    grouped: dict[str, list[tuple[str, list[dict]]]] = {
        t: [] for t in _TABLE2_TASK_ORDER
    }
    for bundle in bundles:
        label = _bundle_task_label(bundle)
        if label is None:
            continue
        paper_id = _bundle_paper_id(bundle)
        if not paper_id:
            continue
        grouped[label].append((paper_id, _bundle_extracted_rows(bundle)))
    return grouped


def _unique_paper_counts(
    items: Sequence[tuple[str, list[dict]]],
    collector,
) -> dict[str, int]:
    """Count distinct papers contributing each canonical term.

    *collector* maps a paper's extracted rows to a list of canonical terms.
    A term is counted once per paper even if it appears in several rows.
    """
    paper_sets: dict[str, set[str]] = {}
    for paper_id, rows in items:
        for term in set(collector(rows)):
            paper_sets.setdefault(term, set()).add(paper_id)
    return {term: len(papers) for term, papers in paper_sets.items()}


def _top_terms(counts: dict[str, int], limit: int = 5) -> str:
    """Render the *limit* most frequent terms as ``term (n); …`` (desc, then name)."""
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    return "; ".join(f"{term} ({n})" for term, n in ordered)


def _collect_data_sources(rows: Sequence[Mapping[str, Any]], task: str) -> list[str]:
    return _collect_alias_values(
        rows,
        ela.DATA_SOURCE_COLUMN_CANDIDATES,
        ela.DATA_SOURCE_ALIAS_PATTERNS,
        [],
        task,
        "",
        "Data sources",
        keep_unmatched=False,
    )


def _collect_models(rows: Sequence[Mapping[str, Any]], task: str) -> list[str]:
    if task == "ERS":
        return _collect_alias_values_from_all_candidates(
            rows,
            ("Recommender System Type", "Models", "Model", "Algorithm", "Algorithms"),
            ela.RECOMMENDER_ALGORITHM_ALIAS_PATTERNS,
            [],
            task,
            "",
            "Models",
            keep_unmatched=False,
        )
    return _collect_alias_values(
        rows,
        ("Models", "Model", "Algorithm", "Algorithms"),
        ela.ALGORITHM_ALIAS_PATTERNS,
        [],
        task,
        "",
        "Models",
        keep_unmatched=False,
    )


def _collect_representations(rows: Sequence[Mapping[str, Any]], task: str) -> list[str]:
    return _collect_alias_values(
        rows,
        ["Features"],
        ela.FEATURE_CATEGORY_ALIAS_PATTERNS,
        [],
        task,
        "",
        "Features",
        keep_unmatched=False,
    )


def _collect_metrics(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    """Detect canonical evaluation-metric names mentioned anywhere in a paper's rows."""
    text = " ; ".join(
        str(v) for row in rows for v in row.values() if v is not None
    ).lower()
    labels: list[str] = []
    for key, label in ela.RESULT_METRIC_LABELS.items():
        if re.search(r"(?<![a-z0-9])" + re.escape(key) + r"(?![a-z0-9])", text):
            labels.append(label)
    return labels


def generate_table4(
    canonical_dir: "str | Path",
    output_dir: "str | Path | None" = None,
) -> "Any":
    """Generate Table 4 — task synthesis matrix (R-007).

    One row per LA task (PRED, DESC, KT, ERS) summarising, across that task's
    papers: purpose, the most common data sources, learner representations,
    models, and evaluation metrics (each as ``term (unique_papers)``), plus a
    one-line actionability-gap synthesis.

    Writes ``task_synthesis_matrix.{xlsx,csv,md}`` to *output_dir* (defaults to
    ``<repo_root>/data/analysis_outputs/la_review/tables/``).
    """
    try:
        import pandas as pd
    except ImportError as exc:
        raise ImportError(
            "pandas is required for generate_table4. "
            "Install the analysis extras: pip install -e .[analysis]"
        ) from exc

    canonical_dir = Path(canonical_dir)
    _repo_root = Path(__file__).resolve().parents[3]
    if output_dir is None:
        output_dir = _repo_root / "data" / "analysis_outputs" / "la_review" / "tables"
    output_dir = Path(output_dir)

    grouped = _group_bundles_by_task(_load_canonical_bundles(canonical_dir))

    out_rows: list[dict] = []
    for task in _TABLE2_TASK_ORDER:
        items = grouped.get(task, [])
        data = _top_terms(
            _unique_paper_counts(items, lambda r, t=task: _collect_data_sources(r, t))
        )
        reps = _top_terms(
            _unique_paper_counts(items, lambda r, t=task: _collect_representations(r, t))
        )
        models = _top_terms(
            _unique_paper_counts(items, lambda r, t=task: _collect_models(r, t))
        )
        metrics = _top_terms(
            _unique_paper_counts(items, lambda r: _collect_metrics(r))
        )
        out_rows.append(
            {
                "Task": task,
                "Purpose": _TASK_PURPOSE[task],
                "Data sources": data or "not reported",
                "Representations": reps
                or "engineered/tabular features (not separately coded)",
                "Models": models or "not reported",
                "Metrics": metrics or "not consistently reported",
                "Actionability gaps": _TASK_ACTIONABILITY_GAP[task],
            }
        )

    df = pd.DataFrame(out_rows, columns=_TABLE4_COLUMNS)

    output_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_dir / "task_synthesis_matrix.csv", index=False)

    md_lines = [
        "**Table IV** – Task-level synthesis matrix across the four learning-analytics "
        "tasks. Cell entries show the most frequent canonical terms with the number of "
        "distinct papers in parentheses.",
        "",
        "| " + " | ".join(_TABLE4_COLUMNS) + " |",
        "| " + " | ".join("---" for _ in _TABLE4_COLUMNS) + " |",
    ]
    for _, row in df.iterrows():
        md_lines.append("| " + " | ".join(str(row[c]) for c in _TABLE4_COLUMNS) + " |")
    (output_dir / "task_synthesis_matrix.md").write_text(
        "\n".join(md_lines) + "\n", encoding="utf-8"
    )

    try:
        with pd.ExcelWriter(
            output_dir / "task_synthesis_matrix.xlsx", engine="openpyxl"
        ) as writer:
            df.to_excel(writer, sheet_name="Table4_TaskSynthesis", index=False)
    except ImportError:
        pass

    return df


def _pred_paper_maturity(canonical_dir: "Path") -> dict[str, str]:
    """Map each PRED paper to its highest maturity via the WP2 classifier."""
    from notion_zotero.analysis.contribution_rows import (
        build_contribution_rows,
        deduplicate_contribution_rows,
    )
    from notion_zotero.analysis.predictive_problem_table import _classify_rows

    classified = _classify_rows(
        deduplicate_contribution_rows(build_contribution_rows(canonical_dir))
    )
    level_idx = {lvl: i for i, lvl in enumerate(_MATURITY_LEVELS)}
    out: dict[str, str] = {}
    for row in classified:
        paper_id = str(row.get("paper_id", ""))
        if not paper_id:
            continue
        status = str(row.get("actionability_status", "unclear"))
        maturity = _ACTIONABILITY_TO_MATURITY.get(status, "backtested")
        if paper_id not in out or level_idx[maturity] > level_idx[out[paper_id]]:
            out[paper_id] = maturity
    return out


def _maturity_from_deployed_status(rows: Sequence[Mapping[str, Any]]) -> str:
    """Derive a maturity level for non-PRED papers from deployment-status signals.

    Defaults to ``"backtested"`` (retrospective evaluation) when no explicit
    deployment signal is present — the baseline maturity for LA studies.
    """
    values = _collect_alias_values_from_all_candidates(
        rows,
        ("Deployed/ Deployable", "Deployed / Deployable", "Work Nature", "Deployment"),
        ela.DEPLOYED_STATUS_ALIAS_PATTERNS,
        [],
        "",
        "",
        "Deployed status",
        keep_unmatched=False,
    )
    level_idx = {lvl: i for i, lvl in enumerate(_MATURITY_LEVELS)}
    best = "backtested"
    for value in values:
        mapped = _DEPLOYED_STATUS_TO_MATURITY.get(value)
        if mapped and level_idx[mapped] > level_idx[best]:
            best = mapped
    return best


def generate_table5(
    canonical_dir: "str | Path",
    output_dir: "str | Path | None" = None,
) -> "Any":
    """Generate Table 5 — evaluation maturity by task (R-008).

    One row per (task, maturity level) with the count of distinct papers.  PRED
    maturity is taken from the WP2 actionability classifier; the other tasks use
    deployment-status signals (defaulting to ``backtested``).  A paper is placed
    in its single highest maturity level.

    Writes ``evaluation_maturity.{xlsx,csv,md}`` to *output_dir* (defaults to
    ``<repo_root>/data/analysis_outputs/la_review/tables/``).
    """
    try:
        import pandas as pd
    except ImportError as exc:
        raise ImportError(
            "pandas is required for generate_table5. "
            "Install the analysis extras: pip install -e .[analysis]"
        ) from exc

    canonical_dir = Path(canonical_dir)
    _repo_root = Path(__file__).resolve().parents[3]
    if output_dir is None:
        output_dir = _repo_root / "data" / "analysis_outputs" / "la_review" / "tables"
    output_dir = Path(output_dir)

    grouped = _group_bundles_by_task(_load_canonical_bundles(canonical_dir))
    pred_maturity = _pred_paper_maturity(canonical_dir)

    counts: dict[tuple[str, str], set[str]] = {}
    for task in _TABLE2_TASK_ORDER:
        for paper_id, rows in grouped.get(task, []):
            if task == "PRED" and paper_id in pred_maturity:
                maturity = pred_maturity[paper_id]
            else:
                maturity = _maturity_from_deployed_status(rows)
            counts.setdefault((task, maturity), set()).add(paper_id)

    out_rows = [
        {
            "Task": task,
            "Maturity level": level,
            "Unique papers": len(counts.get((task, level), set())),
        }
        for task in _TABLE2_TASK_ORDER
        for level in _MATURITY_LEVELS
    ]
    df = pd.DataFrame(out_rows, columns=["Task", "Maturity level", "Unique papers"])

    output_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_dir / "evaluation_maturity.csv", index=False)

    md_lines = [
        "**Table V** – Evaluation maturity by learning-analytics task. Counts are "
        "distinct papers at each maturity level (a paper is shown at its highest level).",
        "",
        "| Task | Maturity level | Unique papers |",
        "| --- | --- | --- |",
    ]
    for _, row in df.iterrows():
        md_lines.append(
            f"| {row['Task']} | {row['Maturity level']} | {row['Unique papers']} |"
        )
    (output_dir / "evaluation_maturity.md").write_text(
        "\n".join(md_lines) + "\n", encoding="utf-8"
    )

    try:
        with pd.ExcelWriter(
            output_dir / "evaluation_maturity.xlsx", engine="openpyxl"
        ) as writer:
            df.to_excel(writer, sheet_name="Table5_Maturity", index=False)
    except ImportError:
        pass

    return df


__all__ = [
    "build_paper_summary_tables",
    "build_paper_summary_dataframes",
    "write_paper_summary_workbook",
    "generate_table2",
    "generate_table4",
    "generate_table5",
]
