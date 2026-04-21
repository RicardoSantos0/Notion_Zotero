"""Tests for FieldOwnershipViolation and assert_ownership."""
import pytest
from notion_zotero.core.field_ownership import (
    assert_ownership,
    FieldOwnershipViolation,
    get_owner,
    ZOTERO_OWNED,
    NOTION_OWNED,
    SYSTEM_FIELDS,
)


# ---------------------------------------------------------------------------
# assert_ownership — happy paths
# ---------------------------------------------------------------------------

def test_zotero_can_write_zotero_fields():
    assert_ownership("title", "zotero")   # should not raise
    assert_ownership("doi", "zotero")
    assert_ownership("authors", "zotero")
    assert_ownership("year", "zotero")
    assert_ownership("journal", "zotero")


def test_notion_can_write_notion_fields():
    assert_ownership("state", "notion")
    assert_ownership("extracted", "notion")
    assert_ownership("workflow_state", "notion")


# ---------------------------------------------------------------------------
# assert_ownership — violation paths
# ---------------------------------------------------------------------------

def test_notion_cannot_write_zotero_fields():
    with pytest.raises(FieldOwnershipViolation):
        assert_ownership("title", "notion")


def test_notion_cannot_write_doi():
    with pytest.raises(FieldOwnershipViolation):
        assert_ownership("doi", "notion")


def test_zotero_cannot_write_notion_fields():
    with pytest.raises(FieldOwnershipViolation):
        assert_ownership("state", "zotero")


def test_zotero_cannot_write_extracted():
    with pytest.raises(FieldOwnershipViolation):
        assert_ownership("extracted", "zotero")


# ---------------------------------------------------------------------------
# assert_ownership — unknown fields pass silently
# ---------------------------------------------------------------------------

def test_unknown_field_does_not_raise():
    assert_ownership("some_unknown_field_xyz", "zotero")   # unknown = not enforced
    assert_ownership("some_unknown_field_xyz", "notion")
    assert_ownership("some_unknown_field_xyz", "system")


# ---------------------------------------------------------------------------
# get_owner
# ---------------------------------------------------------------------------

def test_get_owner_zotero_fields():
    for f in ZOTERO_OWNED:
        assert get_owner(f) == "zotero", f"Expected 'zotero' for field {f!r}"


def test_get_owner_notion_fields():
    for f in NOTION_OWNED:
        assert get_owner(f) == "notion", f"Expected 'notion' for field {f!r}"


def test_get_owner_system_fields():
    for f in SYSTEM_FIELDS:
        assert get_owner(f) == "system", f"Expected 'system' for field {f!r}"


def test_get_owner_unknown():
    assert get_owner("totally_made_up_field") == "unknown"


# ---------------------------------------------------------------------------
# FieldOwnershipViolation carries a meaningful message
# ---------------------------------------------------------------------------

def test_violation_message_contains_field_name():
    with pytest.raises(FieldOwnershipViolation, match="title"):
        assert_ownership("title", "notion")


def test_violation_message_contains_owner():
    with pytest.raises(FieldOwnershipViolation, match="zotero"):
        assert_ownership("title", "notion")


# ---------------------------------------------------------------------------
# system fields are not writable by zotero or notion
# ---------------------------------------------------------------------------

def test_system_field_not_writable_by_zotero():
    with pytest.raises(FieldOwnershipViolation):
        assert_ownership("id", "zotero")


def test_system_field_not_writable_by_notion():
    with pytest.raises(FieldOwnershipViolation):
        assert_ownership("provenance", "notion")
