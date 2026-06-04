from __future__ import annotations

import pytest

from notion_zotero.core.sync_plan_models import SyncPlanValidationError, validate_sync_plan


def _valid_plan(**overrides):
    plan = {
        "version": 1,
        "summary": {"operations": 1},
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
    plan.update(overrides)
    return plan


def test_validate_sync_plan_accepts_current_plan_shape():
    plan = validate_sync_plan(_valid_plan())

    assert plan.version == 1
    assert plan.operations[0].operation_id == "op-1"


def test_validate_sync_plan_rejects_unsupported_version():
    with pytest.raises(SyncPlanValidationError, match="unsupported sync plan version"):
        validate_sync_plan(_valid_plan(version=999))


def test_validate_sync_plan_rejects_unknown_operation_type():
    plan = _valid_plan()
    plan["operations"][0]["operation"] = "delete_notion_page"

    with pytest.raises(SyncPlanValidationError, match="update_notion_reference_field"):
        validate_sync_plan(plan)


def test_validate_sync_plan_rejects_non_zotero_owned_field():
    plan = _valid_plan()
    plan["operations"][0]["field"] = "workflow_state"

    with pytest.raises(SyncPlanValidationError, match="field must be Zotero-owned"):
        validate_sync_plan(plan)


def test_validate_sync_plan_rejects_summary_operation_mismatch():
    plan = _valid_plan(summary={"operations": 2})

    with pytest.raises(SyncPlanValidationError, match="summary.operations"):
        validate_sync_plan(plan)
