"""Dry-run or apply reviewed rollback plans."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Mapping

from notion_zotero.core.field_ownership import ZOTERO_OWNED
from notion_zotero.writers.notion_properties import serialize_notion_properties

if TYPE_CHECKING:
    from notion_zotero.core.protocols import NotionClientProtocol
    from notion_zotero.writers.write_log import WriteLog


class RollbackPlanValidationError(ValueError):
    """Raised when a rollback plan is malformed."""


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _validate_operation(operation: Mapping[str, Any]) -> None:
    if operation.get("operation") != "rollback_notion_reference_field":
        raise RollbackPlanValidationError(f"unsupported rollback operation: {operation.get('operation')}")
    if operation.get("target") != "notion":
        raise RollbackPlanValidationError("rollback operation target must be notion")
    if operation.get("source") != "write_log":
        raise RollbackPlanValidationError("rollback operation source must be write_log")
    if operation.get("field") not in ZOTERO_OWNED:
        raise RollbackPlanValidationError(f"unsupported rollback field: {operation.get('field')}")
    if not operation.get("notion_reference_id"):
        raise RollbackPlanValidationError("rollback operation is missing notion_reference_id")
    if not operation.get("rollback_ref"):
        raise RollbackPlanValidationError("rollback operation is missing rollback_ref")


def validate_rollback_plan(plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Validate and return rollback operations from *plan*."""
    if plan.get("version") != 1:
        raise RollbackPlanValidationError(f"unsupported rollback plan version: {plan.get('version')}")
    operations = list(plan.get("operations") or [])
    for operation in operations:
        _validate_operation(operation)
    return [dict(operation) for operation in operations]


def _current_value(
    operation: Mapping[str, Any],
    current_values: Mapping[str, Mapping[str, Any]] | None,
) -> Any:
    page_values = (current_values or {}).get(str(operation.get("notion_reference_id"))) or {}
    return page_values.get(str(operation.get("field")))


def _log_entry(
    operation: Mapping[str, Any],
    status: str,
    *,
    write_log: "WriteLog | None",
    error_message: str | None = None,
) -> dict[str, Any]:
    return {
        "operation_id": operation.get("operation_id"),
        "session_id": write_log.session_id if write_log else "none",
        "timestamp": _utc_now(),
        "entity_type": "references",
        "entity_id": operation.get("notion_reference_id"),
        "field": operation.get("field"),
        "old_value": operation.get("old_value"),
        "new_value": operation.get("new_value"),
        "actor": "rollback_applier",
        "status": status,
        "error_message": error_message,
        "rollback_ref": operation.get("rollback_ref"),
    }


def apply_rollback_plan(
    plan: Mapping[str, Any],
    *,
    dry_run: bool = True,
    notion_client: "NotionClientProtocol | None" = None,
    write_log: "WriteLog | None" = None,
    property_schema: Mapping[str, str | Mapping[str, str]] | None = None,
    current_values: Mapping[str, Mapping[str, Any]] | None = None,
    rate_limit_sleep: float = 0.35,
) -> list[str]:
    """Apply rollback operations or return dry-run labels."""
    operations = validate_rollback_plan(plan)
    if not dry_run and operations and notion_client is None:
        raise ValueError("notion_client required when applying rollback operations")

    applied: list[str] = []
    first_call = True
    for operation in operations:
        expected = operation.get("expected_current_value")
        if current_values is not None and _current_value(operation, current_values) != expected:
            raise ValueError(
                "current Notion value does not match rollback expectation "
                f"for {operation.get('notion_reference_id')}:{operation.get('field')}"
            )

        page_id = str(operation.get("notion_reference_id"))
        field = str(operation.get("field"))
        op_label = (
            f"notion.rollback [{page_id}] {field}: "
            f"{operation.get('old_value')!r} -> {operation.get('new_value')!r}"
        )
        if dry_run:
            applied.append(f"[DRY-RUN] {op_label}")
            continue

        assert notion_client is not None
        if write_log:
            write_log.append(_log_entry(operation, "planned", write_log=write_log))

        if not first_call:
            time.sleep(rate_limit_sleep)
        first_call = False

        try:
            properties = serialize_notion_properties({field: operation.get("new_value")}, property_schema)
            notion_client.pages.update(page_id, properties=properties)
            if write_log:
                write_log.append(_log_entry(operation, "applied", write_log=write_log))
        except Exception as exc:
            if write_log:
                write_log.append(_log_entry(operation, "failed", write_log=write_log, error_message=str(exc)))
            raise

        applied.append(op_label)

    return applied


__all__ = [
    "RollbackPlanValidationError",
    "apply_rollback_plan",
    "validate_rollback_plan",
]
