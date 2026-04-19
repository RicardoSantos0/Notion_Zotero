"""Normalization helpers for titles, authors, DOIs, headings, and URLs."""
from __future__ import annotations

import re
from typing import Any, Iterable, List


_WS_RE = re.compile(r"\s+")


def _collapse_whitespace(s: str) -> str:
    return _WS_RE.sub(" ", (s or "")).strip()


def normalize_title(title: str | None) -> str:
    if not title:
        return ""
    t = _collapse_whitespace(title)
    return t


def normalize_authors(authors: Any) -> str:
    if not authors:
        return ""
    if isinstance(authors, str):
        return _collapse_whitespace(authors)
    if isinstance(authors, Iterable):
        return ", ".join(str(a).strip() for a in authors)
    return str(authors)


def normalize_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    d = doi.strip().lower()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    return d


def normalize_heading(h: str | None) -> str:
    return _collapse_whitespace(h or "")


def normalize_status(s: str | None) -> str | None:
    if not s:
        return None
    return s.strip().lower()


def normalize_url(u: str | None) -> str | None:
    if not u:
        return None
    return u.strip()


__all__ = [
    "normalize_title",
    "normalize_authors",
    "normalize_doi",
    "normalize_heading",
    "normalize_status",
    "normalize_url",
]
