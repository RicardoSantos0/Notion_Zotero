"""Status mapping utilities for notion_zotero.

Maps common Reading List status labels into canonical workflow state tokens.
"""
from __future__ import annotations

from typing import Optional

_MAP = {
    "to read": "todo",
    "to-read": "todo",
    "todo": "todo",
    "in progress": "in_progress",
    "reading": "in_progress",
    "in_progress": "in_progress",
    "done": "done",
    "read": "done",
    "completed": "done",
}


def map_status(value: str | None) -> Optional[str]:
    if not value:
        return None
    v = str(value).strip().lower()
    return _MAP.get(v, v)


__all__ = ["map_status"]
