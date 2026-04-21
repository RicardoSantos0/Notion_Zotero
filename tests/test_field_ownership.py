"""Tests for canonical field ownership module."""
from notion_zotero.core.field_ownership import (
    get_owner,
    ZOTERO_OWNED,
    NOTION_OWNED,
    SYSTEM_FIELDS,
)


def test_zotero_owned_fields():
    for field in ("title", "authors", "year", "journal", "doi", "url",
                  "zotero_key", "abstract", "item_type", "tags"):
        assert get_owner(field) == "zotero", f"{field!r} should be zotero-owned"


def test_notion_owned_fields():
    for field in ("state", "inclusion_decision_for_task", "extracted",
                  "relevance_notes", "kind", "text"):
        assert get_owner(field) == "notion", f"{field!r} should be notion-owned"


def test_system_fields():
    for field in ("canonical_id", "provenance", "validation_status", "sync_metadata"):
        assert get_owner(field) == "system", f"{field!r} should be system-owned"


def test_unknown_field_returns_unknown():
    assert get_owner("some_random_field_xyz_99") == "unknown"


def test_ownership_sets_are_disjoint():
    assert ZOTERO_OWNED.isdisjoint(NOTION_OWNED), "zotero and notion sets overlap"
    assert ZOTERO_OWNED.isdisjoint(SYSTEM_FIELDS), "zotero and system sets overlap"
    assert NOTION_OWNED.isdisjoint(SYSTEM_FIELDS), "notion and system sets overlap"
