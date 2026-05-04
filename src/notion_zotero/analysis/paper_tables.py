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
    display, shortened = _shorten(raw_text, max_chars=DEFAULT_NARRATIVE_MAX_CHARS)
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


__all__ = [
    "build_paper_summary_tables",
    "build_paper_summary_dataframes",
]
