"""Deterministic ID helpers copied into the `notion_zotero` package.

This mirrors the legacy `src.schemas.idgen` implementation so the new
canonical code does not depend on the legacy top-level package layout.
"""
from __future__ import annotations

import uuid
from typing import Iterable


def _canonicalize(components: Iterable[str]) -> str:
    return "|".join(str(c).strip() for c in components if c is not None)


def deterministic_short_id(prefix: str, *components: str, length: int = 8) -> str:
    key = _canonicalize(components)
    u = uuid.uuid5(uuid.NAMESPACE_URL, key)
    return f"{prefix}_{u.hex[:length]}"


__all__ = ["deterministic_short_id"]
