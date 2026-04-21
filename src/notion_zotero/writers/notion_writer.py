"""Dry-run staging-Notion writer. Default mode is --dry-run (no API calls)."""
from __future__ import annotations

import logging

from notion_zotero.core.models import Reference
from notion_zotero.core.field_ownership import NOTION_OWNED, assert_ownership
from notion_zotero.services.diff_engine import DiffReport

log = logging.getLogger(__name__)


class NotionWriter:
    """Produces planned Notion write operations from a DiffReport.

    By default operates in dry-run mode (no network calls are made).
    Passing ``dry_run=False`` is reserved for a future sprint; the apply
    path raises NotImplementedError intentionally.

    The ``staging_db_id`` parameter is required for apply mode to prevent
    accidental writes to a production database.
    """

    def __init__(self, dry_run: bool = True, staging_db_id: str | None = None) -> None:
        self.dry_run = dry_run
        self.staging_db_id = staging_db_id

    def write_reference(self, ref: Reference, diff: DiffReport) -> list[str]:
        """Return a list of planned operation strings for the given reference.

        Only diff entries for NOTION_OWNED fields are processed.  Field
        ownership is enforced via assert_ownership(); entries for fields
        owned by other systems are silently skipped.

        In dry-run mode (default) no network calls are made.  Never touches
        a production database.
        In apply mode a NotImplementedError is raised — apply is intentionally
        deferred to Sprint 4.
        """
        if not self.dry_run:
            raise NotImplementedError("apply mode not yet implemented")

        ops: list[str] = []
        for entry in diff.entries:
            # Skip entries that are not for this reference
            if entry.entity_id != ref.id:
                continue
            # Only process fields owned by notion
            try:
                assert_ownership(entry.field, "notion")
            except Exception:
                # Field is owned by another system — skip
                continue

            if entry.field not in NOTION_OWNED:
                continue

            op = (
                f"notion.{entry.change_type} "
                f"[{entry.entity_type}/{entry.entity_id}] "
                f"{entry.field}: {entry.old_value!r} -> {entry.new_value!r}"
            )
            log.info("[DRY-RUN] would update notion: %s", op)
            ops.append(op)

        return ops


__all__ = ["NotionWriter"]
