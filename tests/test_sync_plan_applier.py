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


def _create_plan(status: str = "approved") -> dict:
    return {
        "version": 1,
        "operations": [],
        "review_actions": [
            {
                "operation": "create_notion_page_from_zotero_record",
                "operation_id": "create-Z1",
                "target": "notion",
                "source": "zotero",
                "status": status,
                "zotero_reference_id": "zotero-1",
                "zotero_key": "Z1",
                "title": "New Zotero Paper",
                "reference": {
                    "title": "New Zotero Paper",
                    "authors": ["Ada Lovelace"],
                    "year": 2026,
                    "zotero_key": "Z1",
                },
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


def test_apply_sync_plan_dry_run_previews_approved_create():
    from notion_zotero.services.sync_plan_applier import apply_sync_plan

    ops = apply_sync_plan(
        _create_plan(),
        dry_run=True,
        include_reviewed_creates=True,
        notion_database_id="db-1",
    )

    assert ops == ["[DRY-RUN] notion.create [db-1] 'New Zotero Paper'"]


def test_apply_sync_plan_ignores_needs_review_create_action():
    from notion_zotero.services.sync_plan_applier import apply_sync_plan

    ops = apply_sync_plan(
        _create_plan(status="needs_review"),
        dry_run=True,
        include_reviewed_creates=True,
        notion_database_id="db-1",
    )

    assert ops == []


def test_apply_sync_plan_creates_approved_notion_page_and_logs(tmp_path):
    from notion_zotero.services.sync_plan_applier import apply_sync_plan
    from notion_zotero.writers.write_log import WriteLog

    mock_client = unittest.mock.MagicMock()
    mock_client.pages.create.return_value = {"id": "notion-page-new"}
    write_log = WriteLog(session_id="sess-create", log_dir=tmp_path)

    ops = apply_sync_plan(
        _create_plan(),
        dry_run=False,
        notion_client=mock_client,
        write_log=write_log,
        include_reviewed_creates=True,
        notion_database_id="db-1",
        property_schema={"title": {"name": "Paper Title", "type": "title"}},
        rate_limit_sleep=0,
    )

    assert ops == ["notion.create [db-1] 'New Zotero Paper'"]
    mock_client.pages.create.assert_called_once()
    assert mock_client.pages.create.call_args.kwargs["parent"] == {"database_id": "db-1"}
    assert mock_client.pages.create.call_args.kwargs["properties"]["Paper Title"] == {
        "title": [{"text": {"content": "New Zotero Paper"}}]
    }
    entries = write_log.entries_for_session("sess-create")
    assert [entry["status"] for entry in entries] == ["planned", "applied"]
    assert entries[-1]["entity_id"] == "notion-page-new"
    assert entries[-1]["field"] == "__page_create__"


def test_apply_sync_plan_requires_database_for_reviewed_create():
    import pytest
    from notion_zotero.services.sync_plan_applier import apply_sync_plan

    with pytest.raises(ValueError, match="notion_database_id required"):
        apply_sync_plan(_create_plan(), dry_run=True, include_reviewed_creates=True)


def test_apply_sync_plan_rejects_duplicate_create_title():
    import pytest
    from notion_zotero.services.sync_plan_applier import apply_sync_plan

    with pytest.raises(ValueError, match="duplicates an existing Notion title"):
        apply_sync_plan(
            _create_plan(),
            dry_run=True,
            include_reviewed_creates=True,
            notion_database_id="db-1",
            existing_notion_titles={"New Zotero Paper"},
        )
