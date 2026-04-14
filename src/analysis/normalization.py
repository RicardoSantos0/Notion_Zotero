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
        return ", ".join(
            normalize_whitespace(a.get("name") if isinstance(a, dict) else str(a))
            for a in authors
        )
    return normalize_whitespace(str(authors))
