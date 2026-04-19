"""Lightweight citation formatting helpers for canonical references."""
from __future__ import annotations

from typing import List
from .models import Reference


def citation_from_reference(ref: Reference) -> str:
    """Return a short human-readable citation.

    This is intentionally simple and designed for CLI display and quick
    debugging; style can be improved later.
    """
    authors = getattr(ref, "authors", []) or []
    if isinstance(authors, list):
        if len(authors) == 0:
            author_part = ""
        elif len(authors) == 1:
            author_part = authors[0]
        elif len(authors) <= 3:
            author_part = ", ".join(authors)
        else:
            author_part = f"{authors[0]} et al."
    else:
        author_part = str(authors)

    year = getattr(ref, "year", None) or ""
    title = getattr(ref, "title", "") or ""
    journal = getattr(ref, "journal", "") or ""

    parts = []
    if author_part:
        parts.append(author_part)
    if year:
        parts.append(f"({year})")
    if title:
        parts.append(f"{title}.")
    if journal:
        parts.append(journal)

    return " ".join(p for p in parts if p)


__all__ = ["citation_from_reference"]
