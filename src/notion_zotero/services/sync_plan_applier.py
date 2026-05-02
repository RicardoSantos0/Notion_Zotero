"""Apply or dry-run reviewed sync plans."""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Mapping

from notion_zotero.core.field_ownership import ZOTERO_OWNED
from notion_zotero.writers.notion_properties import serialize_notion_properties

if TYPE_CHECKING:
    from notion_zotero.core.protocols import NotionClientProtocol
    from notion_zotero.writers.write_log import WriteLog


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _log_entry(
    operation: dict[str, Any],
    status: str,
    *,
    write_log: "WriteLog | None",
    error_message: str | None = None,
) -> dict[str, Any]:
    return {
        "operation_id": operation.get("operation_id") or operation.get("match_id") or str(uuid.uuid4()),
        "session_id": write_log.session_id if write_log else "none",
        "timestamp": _utc_now(),
        "entity_type": "references",
        "entity_id": operation.get("notion_reference_id"),
        "field": operation.get("field"),
        "old_value": operation.get("old_value"),
        "new_value": operation.get("new_value"),
        "actor": "sync_plan_applier",
        "status": status,
        "error_message": error_message,
        "rollback_ref": None,
    }


def apply_sync_plan(
    plan: Mapping[str, Any],
    *,
    dry_run: bool = True,
    notion_client: "NotionClientProtocol | None" = None,
    write_log: "WriteLog | None" = None,
    property_schema: Mapping[str, str | Mapping[str, str]] | None = None,
    rate_limit_sleep: float = 0.35,
) -> list[str]:
    """Apply executable operations from *plan* or return dry-run operation strings."""
    operations = list(plan.get("operations") or [])
    if not dry_run and any(op.get("target") == "notion" for op in operations) and notion_client is None:
        raise ValueError("notion_client required when applying Notion operations")

    applied: list[str] = []
    first_call = True
    for op in operations:
        operation_type = op.get("operation")
        if operation_type != "update_notion_reference_field":
            continue
        if op.get("target") != "notion" or op.get("source") != "zotero":
            continue
        field = op.get("field")
        if field not in ZOTERO_OWNED:
            continue

        page_id = op.get("notion_reference_id")
        op_label = f"notion.update [{page_id}] {field}: {op.get('old_value')!r} -> {op.get('new_value')!r}"
        if dry_run:
            applied.append(f"[DRY-RUN] {op_label}")
            continue

        assert notion_client is not None
        planned = _log_entry(op, "planned", write_log=write_log)
        if write_log:
            write_log.append(planned)

        if not first_call:
            time.sleep(rate_limit_sleep)
        first_call = False

        try:
            properties = serialize_notion_properties({field: op.get("new_value")}, property_schema)
            notion_client.pages.update(str(page_id), properties=properties)
            if write_log:
                write_log.append(_log_entry(op, "applied", write_log=write_log))
        except Exception as exc:
            if write_log:
                write_log.append(_log_entry(op, "failed", write_log=write_log, error_message=str(exc)))
            raise

        applied.append(op_label)

    return applied


__all__ = ["apply_sync_plan"]
