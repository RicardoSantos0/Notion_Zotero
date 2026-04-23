"""Zotero writer — dry-run (default) and apply mode."""
from __future__ import annotations

import hashlib
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from notion_zotero.core.models import Reference
from notion_zotero.core.field_ownership import ZOTERO_OWNED, assert_ownership
from notion_zotero.services.diff_engine import DiffReport

if TYPE_CHECKING:
    from notion_zotero.writers.write_log import WriteLog

log = logging.getLogger(__name__)

_RATE_LIMIT_SLEEP = 1.0  # seconds between Zotero API calls


class ZoteroWriter:
    """Write Zotero-owned fields back to Zotero from a DiffReport.

    dry_run=True (default): logs planned operations, makes zero network calls.
    dry_run=False (apply mode): calls self._client.update_item() for each diff.
      Requires a client to be injected at construction; raises ValueError otherwise.
    """

    def __init__(
        self,
        dry_run: bool = True,
        client=None,
        write_log: "WriteLog | None" = None,
    ) -> None:
        self.dry_run = dry_run
        self._client = client
        self._write_log = write_log

        if not dry_run and client is None:
            raise ValueError("client required for apply mode")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def write_reference(self, ref: Reference, diff: DiffReport) -> list[str]:
        """Process diff entries for *ref* and apply or log Zotero-owned changes."""
        ops: list[str] = []
        first_call = True

        for entry in diff.entries:
            if entry.entity_id != ref.id:
                continue
            try:
                assert_ownership(entry.field, "zotero")
            except Exception:
                continue
            if entry.field not in ZOTERO_OWNED:
                continue

            op = (
                f"zotero.{entry.change_type} "
                f"[{entry.entity_type}/{entry.entity_id}] "
                f"{entry.field}: {entry.old_value!r} -> {entry.new_value!r}"
            )

            if self.dry_run:
                log.info("[DRY-RUN] would update zotero: %s", op)
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
                "actor": "zotero",
                "status": "planned",
                "error_message": None,
                "rollback_ref": None,
            }
            if self._write_log:
                self._write_log.append(log_entry)

            if not first_call:
                time.sleep(_RATE_LIMIT_SLEEP)
            first_call = False

            try:
                zotero_key = ref.zotero_key or ref.id
                self._client.update_item(zotero_key, {entry.field: entry.new_value})
                log_entry["status"] = "applied"
                log.info("[APPLY] zotero updated: %s", op)
            except Exception as exc:
                log_entry["status"] = "failed"
                log_entry["error_message"] = str(exc)
                log.error("[APPLY] zotero FAILED: %s — %s", op, exc)

            if self._write_log:
                self._write_log.append({**log_entry})

            ops.append(op)

        return ops

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def content_hash(ref: Reference) -> str:
        """SHA-256 hash of concatenated ZOTERO_OWNED field values (sorted by name)."""
        parts = []
        for field_name in sorted(ZOTERO_OWNED):
            val = getattr(ref, field_name, None)
            parts.append(str(val) if val is not None else "")
        raw = "|".join(parts)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = ["ZoteroWriter"]
