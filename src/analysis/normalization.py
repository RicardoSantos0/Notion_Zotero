"""normalization.py — text and metadata normalization helpers.

Keep functions deterministic and idempotent; suitable for canonicalization
pipelines and deduplication.
"""

from __future__ import annotations

import re
from typing import Any


def normalize_whitespace(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def normalize_title(title: str | None) -> str:
    t = normalize_whitespace(title or "")
    t = t.lower()
    t = re.sub(r"[^0-9a-z ]+", "", t)
    return t


def normalize_authors(authors: Any) -> str:
    if not authors:
        return ""
    if isinstance(authors, str):
        return normalize_whitespace(authors)
    if isinstance(authors, list):
        return ", ".join(normalize_whitespace(a.get("name") if isinstance(a, dict) else str(a) for a in authors))
    return normalize_whitespace(str(authors))
"""
Generic text normalization utilities for tabular research data.

All functions are config-driven — no hardcoded column names, domain maps, or
field-specific logic.  Pass the relevant maps/patterns as arguments so the
same functions can be reused across notebooks and projects.
"""

from __future__ import annotations

import re
from typing import Any, Callable

import pandas as pd


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def norm_key(text: str) -> str:
    """Return a normalised lookup key: lowercase, hyphens/underscores → spaces."""
    text = str(text).replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", text).strip().lower()


def clean_whitespace(text: str) -> str:
    """Normalise line endings, collapse spaces/tabs, tidy | and ; separators."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"\s*\|\s*", " | ", text)
    text = re.sub(r"\s*;\s*", "; ", text)
    return text.strip()


def apply_typo_fixes(text: str, fixes: dict[str, str]) -> str:
    """Apply a mapping of {regex_pattern: replacement} to *text* (case-insensitive)."""
    for pattern, replacement in fixes.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def normalize_text_cell(
    v: Any,
    typo_fixes: dict[str, str] | None = None,
    value_map: dict[str, str] | None = None,
) -> Any:
    """
    Clean a single cell value.

    1. clean_whitespace
    2. apply_typo_fixes  (if typo_fixes provided)
    3. exact lookup in value_map by norm_key  (if value_map provided)
    """
    if not isinstance(v, str):
        return v
    out = clean_whitespace(v)
    if typo_fixes:
        out = apply_typo_fixes(out, typo_fixes)
    if value_map:
        out = value_map.get(norm_key(out), out)
    return out


def normalize_term_case(term: str, acronyms: set[str] | None = None) -> str:
    """
    Title-case a term, preserving known acronyms (e.g. "LAK", "LMS").
    Words equal to "and" (case-insensitive) are preserved as "AND".
    """
    words = [w for w in re.split(r"\s+", term.strip()) if w]
    out = []
    for w in words:
        if acronyms and w.upper() in acronyms:
            out.append(w.upper())
        elif w.lower() == "and":
            out.append("AND")
        else:
            out.append(w[:1].upper() + w[1:].lower())
    return " ".join(out)


# ---------------------------------------------------------------------------
# Search-strategy normaliser
# ---------------------------------------------------------------------------

def normalize_search_strategy(
    value: str,
    term_map: dict[str, str],
    *,
    typo_fixes: dict[str, str] | None = None,
    acronyms: set[str] | None = None,
    value_map: dict[str, str] | None = None,
) -> str:
    """
    Canonicalise a search-strategy cell that uses AND-joined quoted terms.
    """
    if not isinstance(value, str):
        return value

    s = normalize_text_cell(value, typo_fixes=typo_fixes, value_map=value_map)
    # Replace smart/curly quotes with straight equivalents
    s = s.replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'")
    s = re.sub(r"\s+", " ", s).strip()

    parts = [p.strip() for p in re.split(r"\s+AND\s+", s, flags=re.IGNORECASE) if p.strip()]
    if not parts:
        return s

    normalized_terms: list[str] = []
    for p in parts:
        p = p.strip(" \"'\u201c\u201d\u2018\u2019()")
        p = normalize_text_cell(p, typo_fixes=typo_fixes, value_map=value_map)
        key = norm_key(p)
        canon = term_map.get(key) or normalize_term_case(p, acronyms=acronyms)
        normalized_terms.append(f'"{canon}"')

    return " AND ".join(dict.fromkeys(normalized_terms))  # deduplicate, preserve order


# ---------------------------------------------------------------------------
# Metric text normaliser
# ---------------------------------------------------------------------------

def _split_metric_segments(text: str) -> list[str]:
    """Split on top-level commas/semicolons (brackets are protected)."""
    segments: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in text:
        if ch in "([{" :
            depth += 1
            current.append(ch)
        elif ch in ")]}":
            depth -= 1
            current.append(ch)
        elif ch in ",;" and depth == 0:
            seg = "".join(current).strip()
            if seg:
                segments.append(seg)
            current = []
        else:
            current.append(ch)
    if current:
        seg = "".join(current).strip()
        if seg:
            segments.append(seg)
    return segments


_SEG_RE = re.compile(
    r"^([A-Za-z][A-Za-z0-9@#%+_\/\- ]{0,40}?)"                          # metric name
    r"\s*[:=]\s*"
    r"(\[?\s*-?\d+(?:\.\d+)?(?:\s*[-\u2013]\s*\d+(?:\.\d+)?)?\s*\]?)"  # value or [lo-hi]
    r"\s*(%?)"                                                            # optional %
    r"(?:\s*[-\u2013]\s*([A-Za-z][A-Za-z0-9 /+\-\.]*?))?"              # optional model name
    r"\s*$",
    re.IGNORECASE,
)


def _metric_to_decimal(
    metric_name: str,
    value: float,
    had_percent: bool,
    proportion_metrics: set[str],
) -> float:
    if had_percent:
        value /= 100.0
    elif metric_name in proportion_metrics and 1.0 < value <= 100.0:
        value /= 100.0
    if metric_name in proportion_metrics:
        value = max(0.0, min(1.0, value))
    return value


def normalize_metric_text(
    text: str,
    metric_name_map: dict[str, str],
    proportion_metrics: set[str],
    typo_fixes: dict[str, str] | None = None,
) -> str:
    """
    Normalise a performance-metric cell to "Name=value [Model]" format.
    """
    if not isinstance(text, str) or not text.strip():
        return text

    text = normalize_text_cell(text, typo_fixes=typo_fixes)
    text = re.sub(r"(?<=\d),(?=\d)", ".", text)  # European decimal comma

    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        stripped = stripped[1:-1].strip()

    segments = _split_metric_segments(stripped)
    pairs: list[str] = []
    unparsed: list[str] = []

    for seg in segments:
        seg = seg.strip(" {}[]")
        m = _SEG_RE.match(seg)
        if not m:
            if seg:
                unparsed.append(seg)
            continue

        raw_name = m.group(1).strip(" -_")
        raw_value_str = m.group(2).strip(" []")
        had_percent = bool(m.group(3))
        model_name = m.group(4).strip() if m.group(4) else None

        # Canonical metric name
        n = norm_key(raw_name)
        metric_name = metric_name_map.get(n, " ".join(w.capitalize() for w in n.split()))

        num_parts = re.findall(r"-?\d+(?:\.\d+)?", raw_value_str)
        if len(num_parts) >= 2:
            lo = _metric_to_decimal(metric_name, float(num_parts[0]), had_percent, proportion_metrics)
            hi = _metric_to_decimal(metric_name, float(num_parts[1]), had_percent, proportion_metrics)
            value_str = f"{lo:.3f}-{hi:.3f}"
        elif len(num_parts) == 1:
            val = _metric_to_decimal(metric_name, float(num_parts[0]), had_percent, proportion_metrics)
            value_str = f"{val:.4f}".rstrip("0").rstrip(".")
        else:
            value_str = raw_value_str

        entry = f"{metric_name}={value_str}"
        if model_name:
            entry += f" [{model_name}]"
        pairs.append(entry)

    if not pairs:
        return text

    out = "; ".join(pairs)
    if unparsed:
        out += "; Notes=" + ", ".join(unparsed)
    return out


# ---------------------------------------------------------------------------
# Generic select-field canonicaliser
# ---------------------------------------------------------------------------

def canonicalize_value(
    value: str,
    canon_map: dict[str, str],
    fallback_fn: Callable[[str], str | None] | None = None,
    typo_fixes: dict[str, str] | None = None,
    value_map: dict[str, str] | None = None,
) -> str:
    """
    Map a select / rich-text cell to a canonical string.
    """
    if not isinstance(value, str):
        return value
    cleaned = normalize_text_cell(value, typo_fixes=typo_fixes, value_map=value_map)
    key = norm_key(cleaned)
    if key in canon_map:
        return canon_map[key]
    if fallback_fn is not None:
        result = fallback_fn(key)
        if result is not None:
            return result
    return cleaned


# ---------------------------------------------------------------------------
# DataFrame-level cleaner
# ---------------------------------------------------------------------------

def clean_dataframe(
    df: pd.DataFrame,
    *,
    column_aliases: dict[str, str] | None = None,
    coalesce_columns: list[tuple[str, str]] | None = None,
    typo_fixes: dict[str, str] | None = None,
    value_map: dict[str, str] | None = None,
    search_strategy_columns: dict[str, dict] | None = None,
    metric_columns: list[str] | None = None,
    metric_name_map: dict[str, str] | None = None,
    proportion_metrics: set[str] | None = None,
    select_columns: dict[str, tuple] | None = None,
    acronyms: set[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Apply a full normalization pass to *df*.  Returns (cleaned_df, log_dict).
    """
    out = df.copy()
    log: dict[str, Any] = {
        "renamed_columns": {},
        "text_updates": 0,
        "search_strategy_updates": 0,
        "metric_updates": 0,
        "select_updates": 0,
    }

    # 1. Rename columns
    if column_aliases:
        rename_map: dict[str, str] = {}
        seen = set(out.columns)
        for col in out.columns:
            target = column_aliases.get(norm_key(col)) or column_aliases.get(col)
            if target and target != col:
                if target in seen and target not in rename_map.values():
                    continue  # would collide with an existing column
                rename_map[col] = target
        out = out.rename(columns=rename_map)
        log["renamed_columns"] = rename_map

    # 2. Coalesce duplicate/alias columns
    if coalesce_columns:
        for primary, secondary in coalesce_columns:
            if primary in out.columns and secondary in out.columns:
                out[primary] = out[primary].where(
                    out[primary].astype(str).str.strip() != "",
                    out[secondary],
                )
                out = out.drop(columns=[secondary])

    # 3. Generic text normalization on all string columns
    for col in out.columns:
        if out[col].dtype != object:
            continue
        original = out[col].copy()
        out[col] = out[col].map(
            lambda v: normalize_text_cell(v, typo_fixes=typo_fixes, value_map=value_map)
        )
        log["text_updates"] += int((original != out[col]).sum())

    # 4. Search-strategy columns
    if search_strategy_columns:
        for col, term_map in search_strategy_columns.items():
            if col not in out.columns:
                continue
            original = out[col].copy()
            out[col] = out[col].map(
                lambda v, _tm=term_map: normalize_search_strategy(
                    v, _tm,
                    typo_fixes=typo_fixes,
                    acronyms=acronyms,
                    value_map=value_map,
                )
            )
            delta = int((original != out[col]).sum())
            log["search_strategy_updates"] += delta
            log["text_updates"] += delta

    # 5. Metric columns
    if metric_columns and metric_name_map and proportion_metrics:
        for col in metric_columns:
            if col not in out.columns:
                continue
            original = out[col].copy()
            out[col] = out[col].map(
                lambda v, _mnm=metric_name_map, _pm=proportion_metrics: normalize_metric_text(
                    v, _mnm, _pm,
                    typo_fixes=typo_fixes,
                )
            )
            log["metric_updates"] += int((original != out[col]).sum())

    # 6. Select / categorical columns
    if select_columns:
        for col, (canon_map, fallback_fn) in select_columns.items():
            if col not in out.columns:
                continue
            original = out[col].copy()
            out[col] = out[col].map(
                lambda v, _cm=canon_map, _fn=fallback_fn: canonicalize_value(
                    v, _cm,
                    fallback_fn=_fn,
                    typo_fixes=typo_fixes,
                    value_map=value_map,
                )
            )
            log["select_updates"] += int((original != out[col]).sum())

    return out, log
