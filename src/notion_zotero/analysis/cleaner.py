"""Generalizable pandas DataFrame table cleaner.

Uses :mod:`notion_zotero.core.text_utils` internally.
All fix dicts and column lists are caller-provided — no constants are baked in.
"""
from __future__ import annotations

from typing import Any

from notion_zotero.core.text_utils import normalize_cell, normalize_search_string


def clean_table(
    df: Any,
    typo_fixes: dict[str, str] | None = None,
    value_map: dict[str, str] | None = None,
    search_strategy_columns: list[str] | None = None,
) -> tuple[Any, dict]:
    """Apply text normalisation to every object-typed column in *df*.

    Args:
        df:                       A ``pd.DataFrame`` to clean.
        typo_fixes:               ``{pattern: replacement}`` regex dict applied to
                                  every string cell. Pass ``None`` to skip.
        value_map:                ``{normalised_key: canonical_value}`` lookup dict.
                                  Pass ``None`` to skip.
        search_strategy_columns:  Column names to run the extended search-string
                                  normaliser on (e.g. ``["Search Strategy"]``).
                                  Pass ``None`` or ``[]`` to skip.

    Returns:
        ``(cleaned_df, log_dict)`` where *log_dict* contains:
        ``table``, ``rows_before``, ``rows_after``, ``text_updates``,
        ``search_strategy_updates``.
    """
    out = df.copy()
    search_cols = set(search_strategy_columns or [])
    text_updates = 0
    search_updates = 0

    for col in out.columns:
        # pandas 3+ uses StringDtype ('str') for string columns, not 'object'
        import pandas as pd
        if not (out[col].dtype == object or pd.api.types.is_string_dtype(out[col])):
            continue
        original = out[col].copy()

        if col in search_cols:
            out[col] = out[col].map(
                lambda v: normalize_search_string(v, typo_fixes, value_map)
            )
            search_updates += int((original != out[col]).sum())
        else:
            out[col] = out[col].map(
                lambda v: normalize_cell(v, typo_fixes, value_map)
            )

        text_updates += int((original != out[col]).sum())

    log = {
        "rows_before": len(df),
        "rows_after": len(out),
        "text_updates": text_updates,
        "search_strategy_updates": search_updates,
    }
    return out, log


__all__ = ["clean_table"]
