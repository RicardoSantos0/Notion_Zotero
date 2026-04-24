"""General-purpose text normalisation utilities.

Pure stdlib — no pandas, numpy, or Polars imports. Safe to import anywhere.

Functions:
    clean_whitespace         — normalise line endings, collapse runs, trim spacing
    apply_regex_fixes        — apply a caller-provided {pattern: replacement} dict
    normalize_cell           — full cell pipeline: whitespace → fixes → value_map lookup
    normalize_search_string  — extend normalize_cell with quote normalisation and AND dedup
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


def normalize_search_string(
    value: Any,
    fixes: dict[str, str] | None = None,
    value_map: dict[str, str] | None = None,
) -> Any:
    """Normalise a search-strategy string.

    Applies :func:`normalize_cell`, then additionally:

    - Replaces typographic quotes (``\\u201c``, ``\\u201d``, ``\\u2019``) with
      ASCII equivalents
    - Splits on ``AND`` (case-insensitive), wraps each term in double-quotes,
      deduplicates (preserving order), and rejoins with `` AND ``

    Non-string values pass through unchanged.
    """
    if not isinstance(value, str):
        return value
    out = normalize_cell(value, fixes, value_map)
    out = (
        out.replace("“", '"')
        .replace("”", '"')
        .replace("’", "'")
        .replace("\n", " ")
        .strip()
    )
    parts = [p.strip() for p in re.split(r"\s+AND\s+", out, flags=re.IGNORECASE) if p.strip()]
    if len(parts) < 2:
        return out
    quoted = [f'"{p.strip(chr(34))}"' for p in parts]
    return " AND ".join(dict.fromkeys(quoted))


__all__ = [
    "clean_whitespace",
    "apply_regex_fixes",
    "normalize_cell",
    "normalize_search_string",
]
