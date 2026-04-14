"""zotero.py — minimal Zotero helpers used in the analysis pipeline.

Only a tiny subset is required for tests and fixtures: resolving items by key
and building simple citation strings.
"""

from __future__ import annotations

from typing import Any


def citation_from_item(item: dict[str, Any]) -> str:
    title = item.get("title") or item.get("Title") or ""
    authors = item.get("creators") or item.get("authors") or []
    if isinstance(authors, list):
        names = ", ".join(a.get("lastName", a.get("name", "")) for a in authors)
    else:
        names = str(authors)
    year = item.get("year") or item.get("Year") or ""
    return f"{names} ({year}) — {title}".strip()
    
