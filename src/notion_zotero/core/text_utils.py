"""General-purpose text normalisation utilities.

Pure stdlib — no pandas, numpy, or Polars imports. Safe to import anywhere.

Functions:
    clean_whitespace         — normalise line endings, collapse runs, trim spacing
    apply_regex_fixes        — apply a caller-provided {pattern: replacement} dict
    normalize_cell           — full cell pipeline: whitespace → fixes → value_map lookup
    normalize_search_string  — extend normalize_cell with quote stripping, AND/OR dedup,
                               and canonical term ordering
"""
from __future__ import annotations

import re
from typing import Any


def clean_whitespace(text: str) -> str:
    """Normalise whitespace in *text*.

    - Unify line endings to ``\\n``
    - Collapse runs of spaces/tabs to a single space
    - Trim leading/trailing whitespace from pipe (``|``) and semicolon (``;``) separators
    - Strip leading/trailing whitespace
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"\s*\|\s*", " | ", text)
    text = re.sub(r"\s*;\s*", "; ", text)
    return text.strip()


def apply_regex_fixes(text: str, fixes: dict[str, str]) -> str:
    """Apply each ``{pattern: replacement}`` pair in *fixes* to *text*.

    Patterns are compiled with ``re.IGNORECASE``. The dict is iterated in
    insertion order, so earlier fixes take precedence.
    """
    for pattern, replacement in fixes.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def _norm_key(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").replace("_", " ").replace("-", " ")).strip().lower()


def normalize_cell(
    value: Any,
    fixes: dict[str, str] | None = None,
    value_map: dict[str, str] | None = None,
) -> Any:
    """Normalise a single table cell value.

    Non-string values are returned unchanged. Strings are processed in order:

    1. ``clean_whitespace``
    2. ``apply_regex_fixes`` (skipped when *fixes* is None or empty)
    3. Value-map lookup via a case-insensitive normalised key (skipped when
       *value_map* is None or empty)

    Args:
        value:     Cell value. Non-strings pass through unchanged.
        fixes:     Optional ``{pattern: replacement}`` regex fix dict.
        value_map: Optional ``{normalised_key: canonical_value}`` lookup dict.
                   Keys are matched after lowercasing and collapsing whitespace.

    Returns:
        Normalised string, or the original *value* unchanged.
    """
    if not isinstance(value, str):
        return value
    out = clean_whitespace(value)
    if fixes:
        out = apply_regex_fixes(out, fixes)
    if value_map:
        out = value_map.get(_norm_key(out), out)
    return out


def _strip_quotes(term: str) -> str:
    """Strip surrounding ASCII and typographic double-quotes from *term*."""
    term = term.strip()
    # Collapse runs of multiple double-quotes first
    term = re.sub(r'"{2,}', '"', term)
    # Strip typographic quotes
    term = term.strip('“”‘’')
    # Strip ASCII double-quotes
    while len(term) >= 2 and term[0] == '"' and term[-1] == '"':
        term = term[1:-1].strip()
    return term.strip()


def normalize_search_string(
    value: Any,
    fixes: dict[str, str] | None = None,
    value_map: dict[str, str] | None = None,
) -> Any:
    """Normalise a search-strategy or search-terms string.

    Applies :func:`normalize_cell`, then additionally:

    - Replaces typographic quotes with ASCII equivalents
    - Collapses multiple consecutive double-quotes
    - Splits on ``AND`` / ``OR`` (case-insensitive) boolean connectors
    - Strips surrounding quotes from each individual term
    - Deduplicates terms (case-insensitive, order-independent)
    - Sorts terms canonically so ``"B" AND "A"`` == ``"A" AND "B"``
    - Re-wraps multi-term results in ``"..."`` and rejoins with the dominant
      connector (``AND`` if any AND present, otherwise ``OR``)
    - Single-term results are returned bare (no wrapping quotes)

    Non-string values pass through unchanged.
    """
    if not isinstance(value, str):
        return value
    out = normalize_cell(value, fixes, value_map)
    out = (
        out.replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
        .replace("\n", " ")
        .strip()
    )
    # Collapse double-double-quotes that can arise from copy-paste
    out = re.sub(r'"{2,}', '"', out)

    has_and = bool(re.search(r"\bAND\b", out, re.IGNORECASE))
    has_or = bool(re.search(r"\bOR\b", out, re.IGNORECASE))

    if has_and or has_or:
        connector = "AND" if has_and else "OR"
        raw_parts = re.split(r"\s+(?:AND|OR)\s+", out, flags=re.IGNORECASE)
        # Strip quotes, deduplicate case-insensitively, sort canonically
        seen: dict[str, str] = {}
        for p in raw_parts:
            clean = _strip_quotes(p)
            if clean and clean.lower() not in seen:
                seen[clean.lower()] = clean
        sorted_terms = sorted(seen.values(), key=str.lower)
        return f" {connector} ".join(f'"{t}"' for t in sorted_terms)

    # Single-term: just strip surrounding quotes
    return _strip_quotes(out) or out


__all__ = [
    "clean_whitespace",
    "apply_regex_fixes",
    "normalize_cell",
    "normalize_search_string",
    "_strip_quotes",
]
