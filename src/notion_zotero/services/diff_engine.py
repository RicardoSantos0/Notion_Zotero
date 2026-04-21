"""Dry-run diff engine: compare canonical bundles and produce structured diffs."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import json

log = logging.getLogger(__name__)

# All entity collection keys that live inside a canonical bundle dict.
_ENTITY_TYPES = (
    "references",
    "tasks",
    "reference_tasks",
    "task_extractions",
    "workflow_states",
    "annotations",
)


@dataclass
class DiffEntry:
    """A single field-level difference between two canonical bundles."""

    entity_type: str
    entity_id: str
    field: str
    old_value: Any
    new_value: Any
    change_type: str  # "added" | "removed" | "changed"


@dataclass
class DiffReport:
    """Collection of DiffEntry objects for a single bundle comparison."""

    entries: list[DiffEntry] = field(default_factory=list)
    bundle_id: str = ""

    def summary(self) -> str:
        """Return a human-readable one-liner summary of the diff."""
        counts: dict[str, int] = {"added": 0, "removed": 0, "changed": 0}
        for entry in self.entries:
            counts[entry.change_type] = counts.get(entry.change_type, 0) + 1
        total = len(self.entries)
        if total == 0:
            return f"[{self.bundle_id}] No differences."
        parts = [f"{v} {k}" for k, v in counts.items() if v]
        return f"[{self.bundle_id}] {total} diff(s): {', '.join(parts)}"


def _index_by_id(entities: list[dict]) -> dict[str, dict]:
    """Build a {id: entity} mapping from a list of entity dicts."""
    return {e["id"]: e for e in entities if isinstance(e, dict) and "id" in e}


def diff_bundles(baseline: dict, updated: dict) -> DiffReport:
    """Compare two canonical bundle dicts and return a DiffReport.

    For each entity type the entities are matched by their ``id`` field.
    - Entities present in both: every non-id field is compared; differences
      become ``"changed"`` entries.
    - Entities only in ``updated``: every field becomes an ``"added"`` entry.
    - Entities only in ``baseline``: every field becomes a ``"removed"`` entry.
    """
    bundle_id = updated.get("bundle_id") or baseline.get("bundle_id") or ""
    report = DiffReport(bundle_id=bundle_id)

    for entity_type in _ENTITY_TYPES:
        base_list: list[dict] = baseline.get(entity_type) or []
        upd_list: list[dict] = updated.get(entity_type) or []

        base_index = _index_by_id(base_list)
        upd_index = _index_by_id(upd_list)

        all_ids = set(base_index) | set(upd_index)

        for eid in all_ids:
            in_base = eid in base_index
            in_upd = eid in upd_index

            if in_base and in_upd:
                # Both exist — compare field by field
                base_entity = base_index[eid]
                upd_entity = upd_index[eid]
                all_fields = set(base_entity) | set(upd_entity)
                for fname in sorted(all_fields):
                    if fname == "id":
                        continue
                    old_val = base_entity.get(fname)
                    new_val = upd_entity.get(fname)
                    if old_val != new_val:
                        report.entries.append(
                            DiffEntry(
                                entity_type=entity_type,
                                entity_id=eid,
                                field=fname,
                                old_value=old_val,
                                new_value=new_val,
                                change_type="changed",
                            )
                        )
            elif in_upd:
                # New entity
                entity = upd_index[eid]
                for fname, val in sorted(entity.items()):
                    if fname == "id":
                        continue
                    report.entries.append(
                        DiffEntry(
                            entity_type=entity_type,
                            entity_id=eid,
                            field=fname,
                            old_value=None,
                            new_value=val,
                            change_type="added",
                        )
                    )
            else:
                # Removed entity
                entity = base_index[eid]
                for fname, val in sorted(entity.items()):
                    if fname == "id":
                        continue
                    report.entries.append(
                        DiffEntry(
                            entity_type=entity_type,
                            entity_id=eid,
                            field=fname,
                            old_value=val,
                            new_value=None,
                            change_type="removed",
                        )
                    )

    log.debug("diff_bundles(%s): %d entries", bundle_id, len(report.entries))
    return report


def diff_dirs(baseline_dir: Path, updated_dir: Path) -> list[DiffReport]:
    """Diff matching bundle JSON files found in two directories.

    Each ``.json`` file in *updated_dir* is paired with a file of the same
    name in *baseline_dir* (if present).  Files that exist only in
    *updated_dir* are treated as entirely new bundles.
    """
    reports: list[DiffReport] = []
    baseline_files: dict[str, Path] = {
        p.name: p for p in baseline_dir.glob("*.json")
    }
    for upd_path in sorted(updated_dir.glob("*.json")):
        upd_bundle: dict = json.loads(upd_path.read_text(encoding="utf-8"))
        base_path = baseline_files.get(upd_path.name)
        if base_path and base_path.exists():
            base_bundle: dict = json.loads(base_path.read_text(encoding="utf-8"))
        else:
            base_bundle = {}
        upd_bundle.setdefault("bundle_id", upd_path.stem)
        report = diff_bundles(base_bundle, upd_bundle)
        reports.append(report)
        log.debug("diff_dirs: %s", report.summary())
    return reports


__all__ = ["DiffEntry", "DiffReport", "diff_bundles", "diff_dirs"]
