"""Registry to list and load domain packs and resolve headings to canonical tasks."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, List, Tuple

from .domain_packs import education_learning_analytics as ela

log = logging.getLogger(__name__)


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
    last_word = h.split()[-1] if h.split() else ""
    for tid, meta in domain_pack.get("tasks", {}).items():
        for a in meta.get("aliases", []):
            al = a.lower()
            # substring match on full heading OR exact match on last word
            if al in h or (last_word and al == last_word):
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
    heading = item.get("heading") or ""
    # 1) Domain-pack-driven match — prefer pack injected by importer, fall back to ELA default
    try:
        active_pack = item.get("_domain_pack") or ela.domain_pack
        tid = resolve_task_alias(active_pack, heading)
        if tid:
            meta = active_pack.get("tasks", {}).get(tid, {})
            template_id = meta.get("template_id")

            def _parser(it, schema_name=template_id):
                return {"schema_name": schema_name or "table", "extracted": it.get("rows", [])}

            out.append((tid, _parser))
        elif heading:
            log.warning("heading '%s' (page %s) matched no domain pack task", heading, item.get("page_id", "unknown"))
    except Exception:
        # defensive: ignore domain pack errors
        pass

    # Unmatched tables are returned as an empty list; the importer creates
    # unlinked TaskExtractions for them without any legacy heuristic calls.
    return out


__all__ = [
    "list_domain_packs",
    "load_domain_pack",
    "resolve_task_alias",
    "match_heading_to_task",
]
