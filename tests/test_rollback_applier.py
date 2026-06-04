from __future__ import annotations

import unittest.mock

import pytest


def _plan() -> dict:
    return {
        "version": 1,
        "operations": [
            {
                "operation": "rollback_notion_reference_field",
                "operation_id": "rollback-op-1",
                "rollback_ref": "op-1",
                "target": "notion",
                "source": "write_log",
                "field": "title",
                "old_value": "New",
                "new_value": "Old",
                "expected_current_value": "New",
                "notion_reference_id": "page-1",
                "reason": "rollback_applied_write",
            }
        ],
    }


def test_apply_rollback_plan_dry_run():
    from notion_zotero.services.rollback_applier import apply_rollback_plan

    ops = apply_rollback_plan(_plan(), dry_run=True)

    assert ops == ["[DRY-RUN] notion.rollback [page-1] title: 'New' -> 'Old'"]


def test_apply_rollback_plan_validates_current_value():
    from notion_zotero.services.rollback_applier import apply_rollback_plan

    with pytest.raises(ValueError, match="current Notion value"):
        apply_rollback_plan(
            _plan(),
            dry_run=True,
            current_values={"page-1": {"title": "Someone else edited it"}},
        )


def test_apply_rollback_plan_updates_notion_and_logs(tmp_path):
    from notion_zotero.services.rollback_applier import apply_rollback_plan
    from notion_zotero.writers.write_log import WriteLog

    mock_client = unittest.mock.MagicMock()
    write_log = WriteLog(session_id="sess-rollback", log_dir=tmp_path)

    ops = apply_rollback_plan(
        _plan(),
        dry_run=False,
        notion_client=mock_client,
        write_log=write_log,
        current_values={"page-1": {"title": "New"}},
        property_schema={"title": {"name": "Paper Title", "type": "title"}},
        rate_limit_sleep=0,
    )

    assert ops == ["notion.rollback [page-1] title: 'New' -> 'Old'"]
    mock_client.pages.update.assert_called_once_with(
        "page-1",
        properties={"Paper Title": {"title": [{"text": {"content": "Old"}}]}},
    )
    entries = write_log.entries_for_session("sess-rollback")
    assert [entry["status"] for entry in entries] == ["planned", "applied"]
    assert entries[-1]["rollback_ref"] == "op-1"
    assert entries[-1]["actor"] == "rollback_applier"


def test_apply_rollback_plan_requires_client_in_apply_mode():
    from notion_zotero.services.rollback_applier import apply_rollback_plan

    with pytest.raises(ValueError, match="notion_client required"):
        apply_rollback_plan(_plan(), dry_run=False)


def test_apply_rollback_plan_rejects_bad_operation():
    from notion_zotero.services.rollback_applier import RollbackPlanValidationError, apply_rollback_plan

    plan = _plan()
    plan["operations"][0]["field"] = "__page_create__"

    with pytest.raises(RollbackPlanValidationError, match="unsupported rollback field"):
        apply_rollback_plan(plan, dry_run=True)
