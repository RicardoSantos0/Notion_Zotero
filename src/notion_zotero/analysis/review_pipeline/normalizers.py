"""Controlled-vocabulary normalizers for the review pipeline (façade, T7.3).

Re-exports the canonical-term extraction helpers from
``notion_zotero.analysis.table_normalization``.
"""
from __future__ import annotations

from notion_zotero.analysis.table_normalization import (
    extract_canonical_terms,
    normalize_token_key,
)

__all__ = ["extract_canonical_terms", "normalize_token_key"]
