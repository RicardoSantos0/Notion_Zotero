from __future__ import annotations

import unittest.mock


def _plan() -> dict:
    return {
        "version": 1,
        "operations": [
            {
                "operation": "update_notion_reference_field",
                "operation_id": "op-1",
                "target": "notion",
                "source": "zotero",
                "field": "title",
                "old_value": "Old",
                "new_value": "New",
                "notion_reference_id": "page-1",
                "reason": "zotero_owned_field",
            }
        ],
    }


def test_apply_sync_plan_dry_run_makes_no_client_call():
    from notion_zotero.services.sync_plan_applier import apply_sync_plan

    mock_client = unittest.mock.MagicMock()

    ops = apply_sync_plan(_plan(), dry_run=True, notion_client=mock_client)

    assert ops == ["[DRY-RUN] notion.update [page-1] title: 'Old' -> 'New'"]
    mock_client.pages.update.assert_not_called()


def test_apply_sync_plan_serializes_property_and_logs(tmp_path):
    from notion_zotero.services.sync_plan_applier import apply_sync_plan
    from notion_zotero.writers.write_log import WriteLog

    mock_client = unittest.mock.MagicMock()
    write_log = WriteLog(session_id="sess-plan", log_dir=tmp_path)

    ops = apply_sync_plan(
        _plan(),
        dry_run=False,
        notion_client=mock_client,
        write_log=write_log,
        rate_limit_sleep=0,
    )

    assert ops == ["notion.update [page-1] title: 'Old' -> 'New'"]
    mock_client.pages.update.assert_called_once_with(
        "page-1",
        properties={"title": {"title": [{"text": {"content": "New"}}]}},
    )
    assert [entry["status"] for entry in write_log.entries_for_session("sess-plan")] == [
        "planned",
        "applied",
    ]


def test_apply_sync_plan_requires_client_in_apply_mode():
    import pytest
    from notion_zotero.services.sync_plan_applier import apply_sync_plan

    with pytest.raises(ValueError, match="notion_client required"):
        apply_sync_plan(_plan(), dry_run=False)
