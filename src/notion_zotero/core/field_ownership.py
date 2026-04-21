"""Field ownership registry for canonical core models.

Every field in the schema belongs to exactly one owner:
- "zotero"  — sourced from / controlled by Zotero metadata
- "notion"  — sourced from / controlled by Notion user input
- "system"  — controlled by the notion_zotero pipeline itself
- "unknown" — field not yet classified (signals a gap to address)
"""
from __future__ import annotations

ZOTERO_OWNED: frozenset[str] = frozenset({
    "title",
    "authors",
    "year",
    "journal",
    "doi",
    "url",
    "zotero_key",
    "abstract",
    "item_type",
    "tags",
})

NOTION_OWNED: frozenset[str] = frozenset({
    "state",
    "workflow_state",
    "inclusion_decision_for_task",
    "extracted",
    "relevance_notes",
    "kind",
    "text",
    "assignment_source",
})

SYSTEM_FIELDS: frozenset[str] = frozenset({
    "canonical_id",
    "id",
    "provenance",
    "validation_status",
    "sync_metadata",
    "template_id",
    "domain_pack_id",
    "domain_pack_version",
    "schema_name",
    "raw_headers",
    "validation",
    "revision_status",
    "reference_id",
    "task_id",
    "reference_task_id",
    "source_field",
    "family",
    "domain_pack",
    "name",
    "aliases",
    "created_from_source",
})


def get_owner(field_name: str) -> str:
    """Return the owner string for a given field name.

    Returns one of: "zotero", "notion", "system", "unknown".
    """
    if field_name in ZOTERO_OWNED:
        return "zotero"
    if field_name in NOTION_OWNED:
        return "notion"
    if field_name in SYSTEM_FIELDS:
        return "system"
    return "unknown"


class FieldOwnershipViolation(Exception):
    """Raised when a system attempts to write a field it does not own."""


def assert_ownership(field_name: str, writing_system: str) -> None:
    """Raise FieldOwnershipViolation if writing_system does not own field_name.

    Unknown fields are not enforced (they pass silently).
    """
    owner = get_owner(field_name)
    if owner == "unknown":
        return  # unknown fields are not enforced
    if owner != writing_system:
        raise FieldOwnershipViolation(
            f"Field {field_name!r} is owned by {owner!r}, "
            f"but {writing_system!r} attempted to write it"
        )


__all__ = [
    "ZOTERO_OWNED",
    "NOTION_OWNED",
    "SYSTEM_FIELDS",
    "get_owner",
    "FieldOwnershipViolation",
    "assert_ownership",
]
