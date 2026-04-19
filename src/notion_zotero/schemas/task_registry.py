"""Registry to list and load domain packs and resolve headings to canonical tasks."""
from __future__ import annotations

from typing import Dict, Optional, List, Tuple

from .domain_packs import education_learning_analytics as ela


DOMAIN_PACKS: Dict[str, Dict] = {
    ela.domain_pack["id"]: ela.domain_pack,
}


def list_domain_packs() -> List[str]:
    return list(DOMAIN_PACKS.keys())


def load_domain_pack(name: str) -> Optional[Dict]:
    return DOMAIN_PACKS.get(name)


def resolve_task_alias(domain_pack: Dict, heading: str | None) -> Optional[str]:
    if not domain_pack or not heading:
        return None
    h = heading.lower()
    for tid, meta in domain_pack.get("tasks", {}).items():
        for a in meta.get("aliases", []):
            if a.lower() in h:
                return tid
    return None


# Convenience: map a heading using the seeded education pack
def match_heading_to_task(heading: str | None) -> Optional[str]:
    return resolve_task_alias(ela.domain_pack, heading)


def get_applicable_tasks(item: dict[str, Any]) -> List[tuple[str, callable]]:
    """Return a list of (task_id, parser) tuples applicable to the item.

    The parser is a callable parser(item) -> {"schema_name": str, "extracted": list}
    """
    out: List[tuple[str, callable]] = []
    # 1) Domain-pack-driven match
    try:
        tid = match_heading_to_task(item.get("heading"))
        if tid:
            meta = ela.domain_pack.get("tasks", {}).get(tid, {})
            template_id = meta.get("template_id")

            def _parser(it, schema_name=template_id):
                return {"schema_name": schema_name or "table", "extracted": it.get("rows", [])}

            out.append((tid, _parser))
    except Exception:
        # defensive: ignore domain pack errors
        pass

    # 2) Fallback to legacy heuristic registry if available
    try:
        from src.schemas.task_registry import get_applicable_tasks as _legacy_get

        legacy = _legacy_get(item)
        # legacy returns list of (name, parser) where name is human-friendly;
        # keep those as-is to preserve behaviour for non-domain tables
        out.extend(legacy)
    except Exception:
        # ignore import/legacy errors
        pass

    return out


__all__ = [
    "list_domain_packs",
    "load_domain_pack",
    "resolve_task_alias",
    "match_heading_to_task",
]
