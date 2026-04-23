"""Tests for WriteLog (NDJSON-backed write log)."""
from __future__ import annotations

import json
import time
import unittest.mock
from pathlib import Path

import pytest

from notion_zotero.writers.write_log import WriteLog


def _minimal_entry(**overrides) -> dict:
    base = {
        "operation_id": "op-001",
        "session_id": "sess-001",
        "timestamp": "2026-01-01T00:00:00+00:00",
        "entity_type": "references",
        "entity_id": "ref-001",
        "field": "title",
        "old_value": "Old",
        "new_value": "New",
        "actor": "zotero",
        "status": "planned",
    }
    base.update(overrides)
    return base


def test_append_creates_file(tmp_path):
    wl = WriteLog(session_id="sess-1", log_dir=tmp_path)
    wl.append(_minimal_entry(operation_id="op-1", session_id="sess-1"))
    log_file = tmp_path / "write_log_sess-1.ndjson"
    assert log_file.exists()


def test_append_writes_valid_json(tmp_path):
    wl = WriteLog(session_id="sess-2", log_dir=tmp_path)
    entry = _minimal_entry(operation_id="op-2", session_id="sess-2")
    wl.append(entry)
    log_file = tmp_path / "write_log_sess-2.ndjson"
    lines = [l for l in log_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["operation_id"] == "op-2"
    assert parsed["field"] == "title"


def test_append_rejects_missing_required_keys(tmp_path):
    wl = WriteLog(session_id="sess-3", log_dir=tmp_path)
    bad_entry = {
        "operation_id": "op-bad",
        # missing: session_id, timestamp, entity_type, entity_id, field, old_value, new_value, actor, status
    }
    with pytest.raises(ValueError, match="missing required keys"):
        wl.append(bad_entry)


def test_entries_for_session(tmp_path):
    wl = WriteLog(session_id="sess-4", log_dir=tmp_path)
    wl.append(_minimal_entry(operation_id="op-a", session_id="sess-4"))
    wl.append(_minimal_entry(operation_id="op-b", session_id="sess-4"))

    # Write a different session file manually to verify filtering
    other = WriteLog(session_id="sess-other", log_dir=tmp_path)
    other.append(_minimal_entry(operation_id="op-other", session_id="sess-other"))

    entries = wl.entries_for_session("sess-4")
    assert len(entries) == 2
    ids = {e["operation_id"] for e in entries}
    assert ids == {"op-a", "op-b"}


def test_all_entries(tmp_path):
    wl1 = WriteLog(session_id="sessA", log_dir=tmp_path)
    wl1.append(_minimal_entry(operation_id="op-1", session_id="sessA"))

    wl2 = WriteLog(session_id="sessB", log_dir=tmp_path)
    wl2.append(_minimal_entry(operation_id="op-2", session_id="sessB"))
    wl2.append(_minimal_entry(operation_id="op-3", session_id="sessB"))

    # Use either instance to read all
    all_entries = wl1.all_entries()
    assert len(all_entries) == 3


def test_prune_removes_old_files(tmp_path):
    wl_old = WriteLog(session_id="old-sess", log_dir=tmp_path)
    wl_old.append(_minimal_entry(operation_id="op-old", session_id="old-sess"))
    old_file = tmp_path / "write_log_old-sess.ndjson"

    # Set file mtime to 91 days ago
    old_mtime = time.time() - 91 * 86400
    import os
    os.utime(old_file, (old_mtime, old_mtime))

    wl_new = WriteLog(session_id="new-sess", log_dir=tmp_path)
    wl_new.append(_minimal_entry(operation_id="op-new", session_id="new-sess"))

    deleted = wl_new.prune(days=90)
    assert deleted == 1
    assert not old_file.exists()
    assert (tmp_path / "write_log_new-sess.ndjson").exists()


def test_fsync_called(tmp_path):
    wl = WriteLog(session_id="sess-fsync", log_dir=tmp_path)
    entry = _minimal_entry(operation_id="op-fsync", session_id="sess-fsync")

    with unittest.mock.patch("os.fsync") as mock_fsync:
        wl.append(entry)
        assert mock_fsync.call_count == 1
