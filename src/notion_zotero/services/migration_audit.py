"""Migration audit: compare legacy Notion fixtures against canonical bundles."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AuditReport:
    missing_references: list[dict[str, Any]] = field(default_factory=list)
    missing_extractions: list[dict[str, Any]] = field(default_factory=list)
    field_loss: list[dict[str, Any]] = field(default_factory=list)
    provenance_loss: list[dict[str, Any]] = field(default_factory=list)
    workflow_state_mismatch: list[dict[str, Any]] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            "Migration Audit Summary",
            f"  missing references        : {len(self.missing_references)}",
            f"  missing extractions       : {len(self.missing_extractions)}",
            f"  field loss                : {len(self.field_loss)}",
            f"  provenance loss           : {len(self.provenance_loss)}",
            f"  workflow state mismatch   : {len(self.workflow_state_mismatch)}",
        ]
        return "\n".join(lines)


_LEGACY_STATUS_MAP = {
    "Not started": "todo",
    "In progress": "in_progress",
    "Done": "done",
    "To do": "todo",
}

_REF_FIELDS = ("title", "authors", "year", "journal", "doi", "url",
               "abstract", "item_type", "tags")
_PROVENANCE_REQUIRED = ("source_id", "domain_pack_id", "domain_pack_version")


def _load_canonical_index(canonical_dir: Path) -> dict[str, dict[str, Any]]:
    """Return mapping page_id -> canonical bundle."""
    index: dict[str, dict[str, Any]] = {}
    for f in sorted(canonical_dir.glob("*.canonical.json")):
        try:
            bundle = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(bundle, dict):
            continue
        refs = bundle.get("references") or []
        page_id = f.stem  # filename is the page_id (without .canonical.json)
        index[page_id] = bundle
        for ref in refs:
            ref_id = ref.get("id", "")
            if ref_id:
                index[ref_id] = bundle
    return index


def _extract_legacy_status(legacy: dict[str, Any]) -> str | None:
    props = legacy.get("properties") or {}
    for key in ("Status", "status"):
        val = props.get(key)
        if val and isinstance(val, dict):
            sel = val.get("select") or {}
            return sel.get("name")
    return None


def run_audit(legacy_dir: str | Path, canonical_dir: str | Path) -> AuditReport:
    """Compare legacy Notion fixture JSON files against canonical bundles."""
    legacy_dir = Path(legacy_dir)
    canonical_dir = Path(canonical_dir)
    report = AuditReport()

    canonical_index = _load_canonical_index(canonical_dir)

    legacy_files = sorted(legacy_dir.glob("*.json"))
    legacy_files = [f for f in legacy_files if ".canonical." not in f.name]

    for legacy_file in legacy_files:
        try:
            legacy = json.loads(legacy_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(legacy, dict):
            continue

        page_id = legacy_file.stem
        bundle = canonical_index.get(page_id)

        # 1. Missing references
        if bundle is None:
            report.missing_references.append({
                "page_id": page_id,
                "legacy_file": legacy_file.name,
            })
            continue

        refs = bundle.get("references") or []
        canonical_ref = refs[0] if refs else {}

        # 2. Missing extractions
        legacy_children = legacy.get("children") or []
        legacy_table_count = sum(
            1 for c in legacy_children
            if isinstance(c, dict) and c.get("type") == "child_database"
        )
        canonical_extraction_count = len(bundle.get("task_extractions") or [])
        if legacy_table_count > 0 and canonical_extraction_count == 0:
            report.missing_extractions.append({
                "page_id": page_id,
                "legacy_tables": legacy_table_count,
                "canonical_extractions": 0,
            })

        # 3. Field loss
        legacy_props = legacy.get("properties") or {}
        for field_name in _REF_FIELDS:
            legacy_val = legacy_props.get(field_name.capitalize()) or legacy_props.get(field_name)
            canonical_val = canonical_ref.get(field_name)
            # Only flag if legacy had a non-empty value but canonical is empty/None
            if legacy_val and not canonical_val:
                report.field_loss.append({
                    "page_id": page_id,
                    "field": field_name,
                    "legacy_value": str(legacy_val)[:120],
                    "canonical_value": canonical_val,
                })

        # 4. Provenance loss
        for entity_key in ("references", "task_extractions", "workflow_states"):
            for obj in bundle.get(entity_key) or []:
                prov = obj.get("provenance") or {}
                missing_keys = [k for k in _PROVENANCE_REQUIRED if not prov.get(k)]
                if missing_keys:
                    report.provenance_loss.append({
                        "page_id": page_id,
                        "entity": entity_key,
                        "object_id": obj.get("id"),
                        "missing_provenance_keys": missing_keys,
                    })

        # 5. Workflow state mismatch
        legacy_status_raw = _extract_legacy_status(legacy)
        if legacy_status_raw:
            expected_state = _LEGACY_STATUS_MAP.get(legacy_status_raw)
            for ws in bundle.get("workflow_states") or []:
                canonical_state = ws.get("state")
                if expected_state and canonical_state != expected_state:
                    report.workflow_state_mismatch.append({
                        "page_id": page_id,
                        "legacy_status": legacy_status_raw,
                        "expected_canonical": expected_state,
                        "actual_canonical": canonical_state,
                    })

    return report
