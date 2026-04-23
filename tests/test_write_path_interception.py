"""CI guard: writers must make zero network calls when dry_run=True.

Transport-layer assertion strategy
------------------------------------
The writers are pure in-memory in dry-run mode — they never import or call
any HTTP library.  We assert this at the stdlib transport layer (urllib /
http.client) which is always available.  When the optional 'requests' package
IS installed we also mock requests.Session.send; when it is absent we skip
that extra check (the writers still cannot call it because they never import
requests in dry-run mode).
"""
import sys
import unittest.mock
import pytest

_PROV = {
    "source_id": "test",
    "domain_pack_id": "test-pack",
    "domain_pack_version": "0.0.1",
}

# Determine whether requests is importable in this environment.
_REQUESTS_AVAILABLE = "requests" in sys.modules or (
    __import__("importlib").util.find_spec("requests") is not None
)


def _transport_mocks():
    """Return a list of context managers that intercept all stdlib HTTP paths."""
    mocks = [
        unittest.mock.patch("urllib.request.urlopen"),
        unittest.mock.patch("http.client.HTTPConnection.request"),
    ]
    if _REQUESTS_AVAILABLE:
        mocks.insert(0, unittest.mock.patch("requests.Session.send"))
    return mocks


def test_zotero_writer_no_network_in_dry_run():
    """ZoteroWriter must not make any HTTP calls when dry_run=True."""
    from notion_zotero.writers.zotero_writer import ZoteroWriter
    from notion_zotero.services.diff_engine import DiffReport
    from notion_zotero.core.models import Reference

    writer = ZoteroWriter(dry_run=True)
    ref = Reference(id="test-001", title="Test Paper", provenance=_PROV, sync_metadata={})
    report = DiffReport(entries=[], bundle_id="test-001")

    # Intercept stdlib transport layer; also requests if installed.
    with unittest.mock.patch("urllib.request.urlopen") as mock_urlopen, \
         unittest.mock.patch("http.client.HTTPConnection.request") as mock_http:

        ops = writer.write_reference(ref, report)

        assert mock_urlopen.call_count == 0, "ZoteroWriter used urlopen in dry-run mode"
        assert mock_http.call_count == 0, "ZoteroWriter made raw HTTP connections in dry-run mode"

    assert isinstance(ops, list)


def test_notion_writer_no_network_in_dry_run():
    """NotionWriter must not make any HTTP calls when dry_run=True."""
    from notion_zotero.writers.notion_writer import NotionWriter
    from notion_zotero.services.diff_engine import DiffReport
    from notion_zotero.core.models import Reference

    writer = NotionWriter(dry_run=True)
    ref = Reference(id="test-002", title="Test Paper 2", provenance=_PROV, sync_metadata={})
    report = DiffReport(entries=[], bundle_id="test-002")

    with unittest.mock.patch("urllib.request.urlopen") as mock_urlopen, \
         unittest.mock.patch("http.client.HTTPConnection.request") as mock_http:

        ops = writer.write_reference(ref, report)

        assert mock_urlopen.call_count == 0, "NotionWriter used urlopen in dry-run mode"
        assert mock_http.call_count == 0, "NotionWriter made raw HTTP connections in dry-run mode"

    assert isinstance(ops, list)


@pytest.mark.skipif(not _REQUESTS_AVAILABLE, reason="requests not installed")
def test_zotero_writer_no_requests_send_in_dry_run():
    """ZoteroWriter must not call requests.Session.send when dry_run=True."""
    from notion_zotero.writers.zotero_writer import ZoteroWriter
    from notion_zotero.services.diff_engine import DiffReport
    from notion_zotero.core.models import Reference

    writer = ZoteroWriter(dry_run=True)
    ref = Reference(id="test-001b", title="Test Paper", provenance=_PROV, sync_metadata={})
    report = DiffReport(entries=[], bundle_id="test-001b")

    with unittest.mock.patch("requests.Session.send") as mock_send:
        writer.write_reference(ref, report)
        assert mock_send.call_count == 0, "ZoteroWriter made HTTP calls in dry-run mode"


@pytest.mark.skipif(not _REQUESTS_AVAILABLE, reason="requests not installed")
def test_notion_writer_no_requests_send_in_dry_run():
    """NotionWriter must not call requests.Session.send when dry_run=True."""
    from notion_zotero.writers.notion_writer import NotionWriter
    from notion_zotero.services.diff_engine import DiffReport
    from notion_zotero.core.models import Reference

    writer = NotionWriter(dry_run=True)
    ref = Reference(id="test-002b", title="Test Paper 2", provenance=_PROV, sync_metadata={})
    report = DiffReport(entries=[], bundle_id="test-002b")

    with unittest.mock.patch("requests.Session.send") as mock_send:
        writer.write_reference(ref, report)
        assert mock_send.call_count == 0, "NotionWriter made HTTP calls in dry-run mode"


def test_zotero_writer_apply_raises():
    """ZoteroWriter raises ValueError when dry_run=False and no client provided."""
    from notion_zotero.writers.zotero_writer import ZoteroWriter

    with pytest.raises(ValueError, match="client required for apply mode"):
        ZoteroWriter(dry_run=False, client=None)


def test_notion_writer_apply_raises():
    """NotionWriter raises ValueError when dry_run=False and no client provided."""
    from notion_zotero.writers.notion_writer import NotionWriter

    with pytest.raises(ValueError, match="client required for apply mode"):
        NotionWriter(dry_run=False, client=None)


def test_zotero_writer_dry_run_returns_ops_for_owned_fields():
    """ZoteroWriter in dry-run mode returns op strings for zotero-owned fields."""
    from notion_zotero.writers.zotero_writer import ZoteroWriter
    from notion_zotero.services.diff_engine import DiffReport, DiffEntry
    from notion_zotero.core.models import Reference

    writer = ZoteroWriter(dry_run=True)
    ref = Reference(id="ref-A", title="Old Title", provenance=_PROV, sync_metadata={})
    entry = DiffEntry(
        entity_type="references",
        entity_id="ref-A",
        field="title",
        old_value="Old Title",
        new_value="New Title",
        change_type="changed",
    )
    report = DiffReport(entries=[entry], bundle_id="ref-A")

    ops = writer.write_reference(ref, report)
    assert len(ops) == 1
    assert "title" in ops[0]
    assert "New Title" in ops[0]


def test_notion_writer_dry_run_returns_ops_for_owned_fields():
    """NotionWriter in dry-run mode returns op strings for notion-owned fields."""
    from notion_zotero.writers.notion_writer import NotionWriter
    from notion_zotero.services.diff_engine import DiffReport, DiffEntry
    from notion_zotero.core.models import Reference

    writer = NotionWriter(dry_run=True)
    ref = Reference(id="ref-B", title="Paper B", provenance=_PROV, sync_metadata={})
    entry = DiffEntry(
        entity_type="workflow_states",
        entity_id="ref-B",
        field="state",
        old_value="todo",
        new_value="done",
        change_type="changed",
    )
    report = DiffReport(entries=[entry], bundle_id="ref-B")

    ops = writer.write_reference(ref, report)
    assert len(ops) == 1
    assert "state" in ops[0]
    assert "done" in ops[0]
