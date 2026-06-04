"""Apply or dry-run reviewed sync plans."""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Mapping

from notion_zotero.core.field_ownership import ZOTERO_OWNED
from notion_zotero.core.normalize import normalize_title
from notion_zotero.core.sync_plan_models import validate_sync_plan
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


def _create_log_entry(
    action: dict[str, Any],
    status: str,
    *,
    write_log: "WriteLog | None",
    page_id: str | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    return {
        "operation_id": action.get("operation_id") or f"create-notion-page-{action.get('zotero_key') or uuid.uuid4()}",
        "session_id": write_log.session_id if write_log else "none",
        "timestamp": _utc_now(),
        "entity_type": "references",
        "entity_id": page_id or action.get("zotero_reference_id") or action.get("zotero_key"),
        "field": "__page_create__",
        "old_value": None,
        "new_value": action.get("reference") or {"title": action.get("title")},
        "actor": "sync_plan_applier",
        "status": status,
        "error_message": error_message,
        "rollback_ref": None,
    }


def _reference_payload_from_action(action: Mapping[str, Any]) -> dict[str, Any]:
    reference = action.get("reference")
    if isinstance(reference, Mapping):
        payload = {
            field: reference.get(field)
            for field in sorted(ZOTERO_OWNED)
            if reference.get(field) not in (None, "", [])
        }
    else:
        payload = {}
    for field in sorted(ZOTERO_OWNED):
        value = action.get(field)
        if value not in (None, "", []) and field not in payload:
            payload[field] = value
    if action.get("title") and "title" not in payload:
        payload["title"] = action.get("title")
    if action.get("zotero_key") and "zotero_key" not in payload:
        payload["zotero_key"] = action.get("zotero_key")
    return payload


def _plan_duplicate_titles(plan: Mapping[str, Any]) -> set[str]:
    titles: set[str] = set()

    def add_title(value: Any) -> None:
        normalized = normalize_title(value).casefold()
        if normalized:
            titles.add(normalized)

    for match in plan.get("matches") or []:
        add_title((match.get("notion") or {}).get("title"))
        add_title((match.get("zotero") or {}).get("title"))
    for record in plan.get("only_notion") or []:
        add_title(record.get("title"))
    for item in plan.get("ambiguous") or []:
        add_title((item.get("zotero") or {}).get("title"))
        for candidate in item.get("candidates") or []:
            add_title((candidate.get("notion") or {}).get("title"))
    return titles


def _approved_create_actions(plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for action in plan.get("review_actions") or []:
        if action.get("operation") != "create_notion_page_from_zotero_record":
            continue
        if action.get("status") != "approved":
            continue
        actions.append(dict(action))
    return actions


def apply_sync_plan(
    plan: Mapping[str, Any],
    *,
    dry_run: bool = True,
    notion_client: "NotionClientProtocol | None" = None,
    write_log: "WriteLog | None" = None,
    property_schema: Mapping[str, str | Mapping[str, str]] | None = None,
    include_reviewed_creates: bool = False,
    notion_database_id: str | None = None,
    existing_notion_titles: set[str] | None = None,
    rate_limit_sleep: float = 0.35,
) -> list[str]:
    """Apply executable operations from *plan* or return dry-run operation strings."""
    typed_plan = validate_sync_plan(plan)
    operations = [operation.model_dump(mode="python") for operation in typed_plan.operations]
    create_actions = _approved_create_actions(plan) if include_reviewed_creates else []
    if create_actions and not notion_database_id:
        raise ValueError("notion_database_id required when applying reviewed create actions")
    if not dry_run and (any(op.get("target") == "notion" for op in operations) or create_actions) and notion_client is None:
        raise ValueError("notion_client required when applying Notion operations")

    applied: list[str] = []
    first_call = True
    duplicate_titles = _plan_duplicate_titles(plan)
    duplicate_titles.update(normalize_title(title).casefold() for title in (existing_notion_titles or set()) if title)
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

    for action in create_actions:
        payload = _reference_payload_from_action(action)
        title = payload.get("title") or action.get("title")
        normalized_title = normalize_title(title).casefold()
        if not normalized_title:
            raise ValueError("approved create action is missing a title")
        if normalized_title in duplicate_titles:
            raise ValueError(f"approved create action duplicates an existing Notion title: {title}")

        assert notion_database_id is not None
        op_label = f"notion.create [{notion_database_id}] {title!r}"
        if dry_run:
            applied.append(f"[DRY-RUN] {op_label}")
            continue

        assert notion_client is not None
        if write_log:
            write_log.append(_create_log_entry(action, "planned", write_log=write_log))

        if not first_call:
            time.sleep(rate_limit_sleep)
        first_call = False

        try:
            properties = serialize_notion_properties(payload, property_schema)
            response = notion_client.pages.create(
                parent={"database_id": notion_database_id},
                properties=properties,
            )
            page_id = response.get("id") if isinstance(response, Mapping) else None
            if write_log:
                write_log.append(_create_log_entry(action, "applied", write_log=write_log, page_id=page_id))
        except Exception as exc:
            if write_log:
                write_log.append(_create_log_entry(action, "failed", write_log=write_log, error_message=str(exc)))
            raise

        applied.append(op_label)

    return applied


__all__ = ["apply_sync_plan"]
