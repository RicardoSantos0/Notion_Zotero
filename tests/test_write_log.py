"""Tests for WriteLog (NDJSON-backed write log)."""
from __future__ import annotations

import json
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
    # Filename now has embedded timestamp: write_log_{ts}_sess-1.ndjson
    matches = list(tmp_path.glob("write_log_*_sess-1.ndjson"))
    assert len(matches) == 1


def test_append_writes_valid_json(tmp_path):
    wl = WriteLog(session_id="sess-2", log_dir=tmp_path)
    entry = _minimal_entry(operation_id="op-2", session_id="sess-2")
    wl.append(entry)
    matches = list(tmp_path.glob("write_log_*_sess-2.ndjson"))
    assert len(matches) == 1
    log_file = matches[0]
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
    # Create a file with a 2020 timestamp embedded in the filename (clearly old)
    old_file = tmp_path / "write_log_20200101T000000Z_old-sess.ndjson"
    old_file.write_text(
        json.dumps(_minimal_entry(operation_id="op-old", session_id="old-sess")) + "\n",
        encoding="utf-8",
    )

    wl_new = WriteLog(session_id="new-sess", log_dir=tmp_path)
    wl_new.append(_minimal_entry(operation_id="op-new", session_id="new-sess"))

    deleted = wl_new.prune(days=90)
    assert deleted == 1
    assert not old_file.exists()
    new_matches = list(tmp_path.glob("write_log_*_new-sess.ndjson"))
    assert len(new_matches) == 1


def test_fsync_called(tmp_path):
    wl = WriteLog(session_id="sess-fsync", log_dir=tmp_path)
    entry = _minimal_entry(operation_id="op-fsync", session_id="sess-fsync")

    with unittest.mock.patch("os.fsync") as mock_fsync:
        wl.append(entry)
        assert mock_fsync.call_count == 1


def test_parse_filename_timestamp_non_matching(tmp_path):
    """_parse_filename_timestamp returns None for non-matching filenames."""
    from notion_zotero.writers.write_log import _parse_filename_timestamp
    assert _parse_filename_timestamp(Path("other_log_20200101T000000Z_sess.ndjson")) is None


def test_parse_filename_timestamp_bad_timestamp(tmp_path):
    """_parse_filename_timestamp returns None when timestamp portion is invalid."""
    from notion_zotero.writers.write_log import _parse_filename_timestamp
    assert _parse_filename_timestamp(Path("write_log_NOTADATE_sess.ndjson")) is None


def test_read_ndjson_oserror(tmp_path, monkeypatch):
    """_read_ndjson silently returns [] when the file cannot be opened."""
    from notion_zotero.writers.write_log import _read_ndjson
    bad_path = tmp_path / "nonexistent.ndjson"
    result = _read_ndjson(bad_path)
    assert result == []


def test_prune_real_filesystem(tmp_path):
    """Retention correctly deletes old files and keeps recent ones on a real filesystem."""
    log_dir = tmp_path / "write_logs"
    log_dir.mkdir()

    session_old = "session-old-001"
    session_new = "session-new-001"

    # Create old log file with a 2020 timestamp in the filename
    old_file = log_dir / f"write_log_20200101T000000Z_{session_old}.ndjson"
    old_file.write_text(
        json.dumps({
            "operation_id": "op-old-1",
            "session_id": session_old,
            "timestamp": "2020-01-01T00:00:00Z",
            "entity_type": "references",
            "entity_id": "ref-old",
            "field": "title",
            "old_value": "Old",
            "new_value": "New",
            "actor": "zotero",
            "status": "applied",
        }) + "\n",
        encoding="utf-8",
    )

    # Create a recent log file (current timestamp embedded by WriteLog)
    wl_new = WriteLog(session_id=session_new, log_dir=str(log_dir))
    wl_new.append({
        "operation_id": "op-new-1",
        "session_id": session_new,
        "timestamp": "2026-04-24T00:00:00Z",
        "entity_type": "references",
        "entity_id": "ref-new",
        "field": "title",
        "old_value": "A",
        "new_value": "B",
        "actor": "notion",
        "status": "applied",
    })

    # Prune with 90-day threshold: old file should go, new file should stay
    pruner = WriteLog(session_id="prune-session", log_dir=str(log_dir))
    deleted = pruner.prune(days=90)

    assert deleted == 1, f"Expected 1 file deleted, got {deleted}"
    assert not old_file.exists(), "Old log file should have been deleted"
    new_matches = list(log_dir.glob(f"write_log_*_{session_new}.ndjson"))
    assert len(new_matches) == 1, "Recent log file should have been kept"
