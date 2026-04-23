"""Tests for ZoteroWriter and NotionWriter apply mode."""
from __future__ import annotations

import unittest.mock

import pytest

_PROV = {
    "source_id": "test",
    "domain_pack_id": "test-pack",
    "domain_pack_version": "0.0.1",
}


def _make_zotero_diff(entity_id="ref-Z", field="title", old="Old", new="New"):
    from notion_zotero.services.diff_engine import DiffEntry, DiffReport
    entry = DiffEntry(
        entity_type="references",
        entity_id=entity_id,
        field=field,
        old_value=old,
        new_value=new,
        change_type="changed",
    )
    return DiffReport(entries=[entry], bundle_id=entity_id)


def _make_notion_diff(entity_id="ref-N", field="state", old="todo", new="done"):
    from notion_zotero.services.diff_engine import DiffEntry, DiffReport
    entry = DiffEntry(
        entity_type="workflow_states",
        entity_id=entity_id,
        field=field,
        old_value=old,
        new_value=new,
        change_type="changed",
    )
    return DiffReport(entries=[entry], bundle_id=entity_id)


def test_zotero_writer_apply_calls_client(tmp_path):
    from notion_zotero.writers.zotero_writer import ZoteroWriter
    from notion_zotero.core.models import Reference

    mock_client = unittest.mock.MagicMock()
    writer = ZoteroWriter(dry_run=False, client=mock_client)
    ref = Reference(id="ref-Z", title="Old", provenance=_PROV, sync_metadata={})
    diff = _make_zotero_diff(entity_id="ref-Z", field="title", old="Old", new="New")

    writer.write_reference(ref, diff)

    mock_client.update_item.assert_called_once()
    call_args = mock_client.update_item.call_args
    assert call_args[0][1] == {"title": "New"}


def test_zotero_writer_apply_logs_to_write_log(tmp_path):
    from notion_zotero.writers.zotero_writer import ZoteroWriter
    from notion_zotero.writers.write_log import WriteLog
    from notion_zotero.core.models import Reference

    mock_client = unittest.mock.MagicMock()
    wl = WriteLog(session_id="sess-z", log_dir=tmp_path)
    writer = ZoteroWriter(dry_run=False, client=mock_client, write_log=wl)
    ref = Reference(id="ref-Z2", title="Old", provenance=_PROV, sync_metadata={})
    diff = _make_zotero_diff(entity_id="ref-Z2", field="title", old="Old", new="New2")

    writer.write_reference(ref, diff)

    entries = wl.entries_for_session("sess-z")
    # Expect planned + applied entries
    assert len(entries) == 2
    statuses = {e["status"] for e in entries}
    assert "planned" in statuses
    assert "applied" in statuses


def test_zotero_writer_apply_skips_no_diff(tmp_path):
    from notion_zotero.writers.zotero_writer import ZoteroWriter
    from notion_zotero.services.diff_engine import DiffReport
    from notion_zotero.core.models import Reference

    mock_client = unittest.mock.MagicMock()
    writer = ZoteroWriter(dry_run=False, client=mock_client)
    ref = Reference(id="ref-empty", title="Title", provenance=_PROV, sync_metadata={})
    empty_diff = DiffReport(entries=[], bundle_id="ref-empty")

    ops = writer.write_reference(ref, empty_diff)

    assert ops == []
    mock_client.update_item.assert_not_called()


def test_notion_writer_apply_calls_client(tmp_path):
    from notion_zotero.writers.notion_writer import NotionWriter
    from notion_zotero.core.models import Reference

    mock_client = unittest.mock.MagicMock()
    writer = NotionWriter(dry_run=False, client=mock_client)
    ref = Reference(id="ref-N", title="Paper", provenance=_PROV, sync_metadata={})
    diff = _make_notion_diff(entity_id="ref-N", field="state", old="todo", new="done")

    writer.write_reference(ref, diff)

    mock_client.pages.update.assert_called_once()
    call_args = mock_client.pages.update.call_args
    assert call_args[0][0] == "ref-N"
    assert call_args[1]["properties"] == {"state": "done"}


def test_notion_writer_apply_logs_to_write_log(tmp_path):
    from notion_zotero.writers.notion_writer import NotionWriter
    from notion_zotero.writers.write_log import WriteLog
    from notion_zotero.core.models import Reference

    mock_client = unittest.mock.MagicMock()
    wl = WriteLog(session_id="sess-n", log_dir=tmp_path)
    writer = NotionWriter(dry_run=False, client=mock_client, write_log=wl)
    ref = Reference(id="ref-N2", title="Paper", provenance=_PROV, sync_metadata={})
    diff = _make_notion_diff(entity_id="ref-N2", field="state", old="todo", new="done")

    writer.write_reference(ref, diff)

    entries = wl.entries_for_session("sess-n")
    assert len(entries) == 2
    statuses = {e["status"] for e in entries}
    assert "planned" in statuses
    assert "applied" in statuses


def test_conflict_resolution_zotero_owned_field(tmp_path):
    """ZoteroWriter apply must skip entries for NOTION_OWNED fields."""
    from notion_zotero.writers.zotero_writer import ZoteroWriter
    from notion_zotero.core.models import Reference

    mock_client = unittest.mock.MagicMock()
    writer = ZoteroWriter(dry_run=False, client=mock_client)
    ref = Reference(id="ref-cr1", title="T", provenance=_PROV, sync_metadata={})
    # "state" is NOTION_OWNED — ZoteroWriter must skip it
    diff = _make_notion_diff(entity_id="ref-cr1", field="state")

    ops = writer.write_reference(ref, diff)

    assert ops == []
    mock_client.update_item.assert_not_called()


def test_conflict_resolution_notion_owned_field(tmp_path):
    """NotionWriter apply must skip entries for ZOTERO_OWNED fields."""
    from notion_zotero.writers.notion_writer import NotionWriter
    from notion_zotero.core.models import Reference

    mock_client = unittest.mock.MagicMock()
    writer = NotionWriter(dry_run=False, client=mock_client)
    ref = Reference(id="ref-cr2", title="T", provenance=_PROV, sync_metadata={})
    # "title" is ZOTERO_OWNED — NotionWriter must skip it
    diff = _make_zotero_diff(entity_id="ref-cr2", field="title")

    ops = writer.write_reference(ref, diff)

    assert ops == []
    mock_client.pages.update.assert_not_called()


def test_zotero_writer_raises_without_client_in_apply_mode():
    from notion_zotero.writers.zotero_writer import ZoteroWriter

    with pytest.raises(ValueError, match="client required for apply mode"):
        ZoteroWriter(dry_run=False, client=None)


def test_notion_writer_raises_without_client_in_apply_mode():
    from notion_zotero.writers.notion_writer import NotionWriter

    with pytest.raises(ValueError, match="client required for apply mode"):
        NotionWriter(dry_run=False, client=None)
