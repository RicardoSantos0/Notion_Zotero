from __future__ import annotations

import json

from notion_zotero.services.rollback_planner import build_rollback_plan, write_rollback_plan


def _entry(**overrides) -> dict:
    data = {
        "operation_id": "op-1",
        "session_id": "sess-1",
        "timestamp": "2026-06-02T12:00:00Z",
        "entity_type": "references",
        "entity_id": "notion-page-1",
        "field": "title",
        "old_value": "Old title",
        "new_value": "New title",
        "actor": "sync_plan_applier",
        "status": "applied",
        "error_message": None,
        "rollback_ref": None,
    }
    data.update(overrides)
    return data


def _write_log(path, entries):
    path.write_text(
        "\n".join(json.dumps(entry) for entry in entries) + "\n",
        encoding="utf-8",
    )


def test_build_rollback_plan_reverses_applied_notion_write(tmp_path):
    _write_log(tmp_path / "write_log_20260602T120000Z_sess-1.ndjson", [_entry()])

    plan = build_rollback_plan(tmp_path)

    assert plan["summary"]["rollback_operations"] == 1
    operation = plan["operations"][0]
    assert operation["operation"] == "rollback_notion_reference_field"
    assert operation["rollback_ref"] == "op-1"
    assert operation["notion_reference_id"] == "notion-page-1"
    assert operation["old_value"] == "New title"
    assert operation["new_value"] == "Old title"
    assert operation["expected_current_value"] == "New title"


def test_build_rollback_plan_skips_non_applied_and_zotero_entries(tmp_path):
    _write_log(
        tmp_path / "write_log_20260602T120000Z_sess-1.ndjson",
        [
            _entry(operation_id="planned", status="planned"),
            _entry(operation_id="failed", status="failed"),
            _entry(operation_id="zotero", actor="zotero"),
        ],
    )

    plan = build_rollback_plan(tmp_path)

    assert plan["summary"]["rollback_operations"] == 0
    assert plan["summary"]["skipped"] == 3
    reasons = {item["operation_id"]: item["reason"] for item in plan["skipped"]}
    assert reasons == {
        "planned": "status_not_applied",
        "failed": "status_not_applied",
        "zotero": "unsupported_actor",
    }


def test_build_rollback_plan_skips_page_create_entries(tmp_path):
    _write_log(
        tmp_path / "write_log_20260602T120000Z_sess-1.ndjson",
        [_entry(operation_id="create", field="__page_create__")],
    )

    plan = build_rollback_plan(tmp_path)

    assert plan["summary"]["rollback_operations"] == 0
    assert plan["skipped"][0]["reason"] == "unsupported_field"


def test_build_rollback_plan_filters_by_session_id(tmp_path):
    _write_log(
        tmp_path / "write_log_20260602T120000Z_sess-1.ndjson",
        [_entry(operation_id="op-1", session_id="sess-1")],
    )
    _write_log(
        tmp_path / "write_log_20260602T120001Z_sess-2.ndjson",
        [_entry(operation_id="op-2", session_id="sess-2")],
    )

    plan = build_rollback_plan(tmp_path, session_id="sess-2")

    assert plan["summary"]["log_entries"] == 1
    assert plan["summary"]["sessions"] == 1
    assert [op["rollback_ref"] for op in plan["operations"]] == ["op-2"]


def test_write_rollback_plan_creates_parent_directory(tmp_path):
    out = tmp_path / "plans" / "rollback_plan.json"
    path = write_rollback_plan({"version": 1, "operations": []}, out)

    assert path == out
    assert json.loads(out.read_text(encoding="utf-8"))["version"] == 1
