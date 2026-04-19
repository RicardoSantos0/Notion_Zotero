"""Deterministic ID generation helpers.

Provide stable short IDs suitable for canonical outputs using UUID5 over a
stable namespace and canonicalized component strings.
"""
from __future__ import annotations

import uuid
from typing import Iterable


def _canonicalize(components: Iterable[str]) -> str:
    return "|".join(str(c).strip() for c in components if c is not None)


def deterministic_short_id(prefix: str, *components: str, length: int = 8) -> str:
    """Return a deterministic short id like `<prefix>_<hex>`.

    Uses UUID5 with the URL namespace to produce stable identifiers derived
    from the provided components. The returned hex is truncated to `length`
    characters to remain compact while reasonably collision-resistant.
    """
    key = _canonicalize(components)
    # Use uuid.NAMESPACE_URL to be stable across environments
    u = uuid.uuid5(uuid.NAMESPACE_URL, key)
    return f"{prefix}_{u.hex[:length]}"
