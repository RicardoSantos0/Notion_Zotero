"""Notion writer — dry-run (default) and apply mode."""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from notion_zotero.core.models import Reference
from notion_zotero.core.field_ownership import NOTION_OWNED, assert_ownership
from notion_zotero.services.diff_engine import DiffReport
from notion_zotero.writers.notion_properties import serialize_notion_properties

if TYPE_CHECKING:
    from notion_zotero.core.protocols import NotionClientProtocol
    from notion_zotero.writers.write_log import WriteLog

log = logging.getLogger(__name__)


class NotionWriter:
    """Write Notion-owned fields back to Notion from a DiffReport.

    dry_run=True (default): logs planned operations, makes zero network calls.
    dry_run=False (apply mode): calls self._client.pages.update() for each diff.
      Requires a client to be injected at construction; raises ValueError otherwise.

    The ``staging_db_id`` parameter is retained for compatibility and for apply
    mode to target the correct staging database.
    """

    def __init__(
        self,
        dry_run: bool = True,
        staging_db_id: str | None = None,
        client: "NotionClientProtocol | None" = None,
        write_log: "WriteLog | None" = None,
        property_schema: dict | None = None,
        rate_limit_sleep: float = 0.35,
    ) -> None:
        self.dry_run = dry_run
        self.staging_db_id = staging_db_id
        self._client = client
        self._write_log = write_log
        self._property_schema = property_schema
        self._rate_limit_sleep = rate_limit_sleep

        if not dry_run and client is None:
            raise ValueError("client required for apply mode")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def write_reference(self, ref: Reference, diff: DiffReport) -> list[str]:
        """Process diff entries for *ref* and apply or log Notion-owned changes."""
        ops: list[str] = []
        first_call = True

        for entry in diff.entries:
            if entry.entity_id != ref.id:
                continue
            try:
                assert_ownership(entry.field, "notion")
            except Exception:
                continue
            if entry.field not in NOTION_OWNED:
                continue

            op = (
                f"notion.{entry.change_type} "
                f"[{entry.entity_type}/{entry.entity_id}] "
                f"{entry.field}: {entry.old_value!r} -> {entry.new_value!r}"
            )

            if self.dry_run:
                log.info("[DRY-RUN] would update notion: %s", op)
                ops.append(op)
                continue

            # Apply mode
            operation_id = str(uuid.uuid4())
            timestamp = datetime.now(tz=timezone.utc).isoformat()
            log_entry = {
                "operation_id": operation_id,
                "session_id": self._write_log.session_id if self._write_log else "none",
                "timestamp": timestamp,
                "entity_type": entry.entity_type,
                "entity_id": entry.entity_id,
                "field": entry.field,
                "old_value": entry.old_value,
                "new_value": entry.new_value,
                "actor": "notion",
                "status": "planned",
                "error_message": None,
                "rollback_ref": None,
            }
            if self._write_log:
                self._write_log.append(log_entry)

            if not first_call:
                time.sleep(self._rate_limit_sleep)
            first_call = False

            try:
                page_id = ref.id
                properties = serialize_notion_properties(
                    {entry.field: entry.new_value},
                    self._property_schema,
                )
                self._client.pages.update(page_id, properties=properties)
                log_entry["status"] = "applied"
                log.info("[APPLY] notion updated: %s", op)
            except Exception as exc:
                log_entry["status"] = "failed"
                log_entry["error_message"] = str(exc)
                log.error("[APPLY] notion FAILED: %s — %s", op, exc)

            if self._write_log:
                self._write_log.append({**log_entry})

            ops.append(op)

        return ops


__all__ = ["NotionWriter"]
