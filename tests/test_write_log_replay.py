"""M1 / T1.2 — test-first contract for write-log replay (built in M4).

Replay selects planned/failed write-log entries and re-plans them, dry-run by
default. Fails for missing implementation until
`notion_zotero.services.write_log_replay` exists.
"""
from __future__ import annotations


def _entry(op: str, status: str) -> dict:
    return {
        "operation_id": op, "session_id": "s1", "timestamp": "20260624T000000Z",
        "entity_type": "notion_page", "entity_id": "p1", "field": "Status",
        "old_value": None, "new_value": "Read", "actor": "test", "status": status,
    }


def test_select_replay_candidates_picks_planned_and_failed():
    from notion_zotero.services import write_log_replay

    entries = [_entry("o1", "planned"), _entry("o2", "failed"),
               _entry("o3", "applied"), _entry("o4", "succeeded")]
    cands = write_log_replay.select_replay_candidates(entries)
    assert {c["operation_id"] for c in cands} == {"o1", "o2"}


def test_plan_replay_is_dry_run_by_default():
    from notion_zotero.services import write_log_replay

    result = write_log_replay.plan_replay([_entry("o1", "failed")])
    assert result["dry_run"] is True
    assert result["candidates"] and result.get("applied") == []
