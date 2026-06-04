"""Build reviewable rollback plans from append-only write logs."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from notion_zotero.core.field_ownership import ZOTERO_OWNED
from notion_zotero.writers.write_log import _read_ndjson


_NOTION_ROLLBACK_ACTORS = frozenset({"notion", "sync_plan_applier"})


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_log_files(log_dir: str | Path) -> list[Path]:
    return sorted(Path(log_dir).glob("write_log_*.ndjson"))


def _load_write_log_entries(log_dir: str | Path, session_id: str | None = None) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in _write_log_files(log_dir):
        for entry in _read_ndjson(path):
            if session_id and entry.get("session_id") != session_id:
                continue
            entries.append(entry)
    return entries


def _skip_entry(entry: Mapping[str, Any]) -> dict[str, Any]:
    operation_id = entry.get("operation_id")
    if entry.get("status") != "applied":
        reason = "status_not_applied"
    elif entry.get("entity_type") != "references":
        reason = "unsupported_entity_type"
    elif entry.get("actor") not in _NOTION_ROLLBACK_ACTORS:
        reason = "unsupported_actor"
    elif not entry.get("entity_id"):
        reason = "missing_entity_id"
    elif not entry.get("field"):
        reason = "missing_field"
    elif entry.get("field") not in ZOTERO_OWNED:
        reason = "unsupported_field"
    else:
        reason = ""
    return {
        "operation_id": operation_id,
        "session_id": entry.get("session_id"),
        "status": entry.get("status"),
        "actor": entry.get("actor"),
        "field": entry.get("field"),
        "reason": reason,
    }


def _rollback_operation(entry: Mapping[str, Any]) -> dict[str, Any]:
    source_operation_id = str(entry.get("operation_id") or "unknown")
    return {
        "operation": "rollback_notion_reference_field",
        "operation_id": f"rollback-{source_operation_id}",
        "rollback_ref": source_operation_id,
        "target": "notion",
        "source": "write_log",
        "session_id": entry.get("session_id"),
        "field": entry.get("field"),
        "old_value": entry.get("new_value"),
        "new_value": entry.get("old_value"),
        "expected_current_value": entry.get("new_value"),
        "notion_reference_id": entry.get("entity_id"),
        "reason": "rollback_applied_write",
    }


def build_rollback_plan(
    log_dir: str | Path = "logs/write_logs",
    *,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Return a non-mutating rollback plan for applied Notion write-log entries."""
    entries = _load_write_log_entries(log_dir, session_id=session_id)
    operations: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for entry in entries:
        skip = _skip_entry(entry)
        if skip["reason"]:
            skipped.append(skip)
            continue
        operations.append(_rollback_operation(entry))

    sessions = {entry.get("session_id") for entry in entries if entry.get("session_id")}
    applied_entries = [entry for entry in entries if entry.get("status") == "applied"]
    return {
        "version": 1,
        "generated_at": _utc_now(),
        "inputs": {
            "write_log_dir": str(log_dir),
            "session_id": session_id,
        },
        "summary": {
            "log_entries": len(entries),
            "applied_entries": len(applied_entries),
            "rollback_operations": len(operations),
            "skipped": len(skipped),
            "sessions": len(sessions),
        },
        "operations": operations,
        "skipped": skipped,
    }


def write_rollback_plan(
    plan: Mapping[str, Any],
    output_path: str | Path,
) -> Path:
    """Write *plan* as indented JSON and return its path."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_rollback_plan_from_logs(
    log_dir: str | Path,
    output_path: str | Path,
    *,
    session_id: str | None = None,
) -> Path:
    plan = build_rollback_plan(log_dir, session_id=session_id)
    return write_rollback_plan(plan, output_path)


__all__ = [
    "build_rollback_plan",
    "write_rollback_plan",
    "write_rollback_plan_from_logs",
]
