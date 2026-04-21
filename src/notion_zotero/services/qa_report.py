"""QA report: detect structural problems in canonical bundles."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_VALID_STATES = {"todo", "in_progress", "done"}


@dataclass
class QAReport:
    malformed_extractions: list[dict[str, Any]] = field(default_factory=list)
    missing_columns: list[dict[str, Any]] = field(default_factory=list)
    ambiguous_statuses: list[dict[str, Any]] = field(default_factory=list)
    incomplete_references: list[dict[str, Any]] = field(default_factory=list)
    unlinked_extractions: list[dict[str, Any]] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            "QA Report Summary",
            f"  malformed extractions   : {len(self.malformed_extractions)}",
            f"  missing required columns: {len(self.missing_columns)}",
            f"  ambiguous statuses      : {len(self.ambiguous_statuses)}",
            f"  incomplete references   : {len(self.incomplete_references)}",
            f"  unlinked extractions    : {len(self.unlinked_extractions)}",
        ]
        return "\n".join(lines)


def run_qa(input_dir: str | Path) -> QAReport:
    """Run QA checks across all *.canonical.json bundles in *input_dir*."""
    from notion_zotero.schemas.templates.generic import TEMPLATES

    input_dir = Path(input_dir)
    report = QAReport()

    for bundle_file in sorted(input_dir.glob("*.canonical.json")):
        try:
            bundle = json.loads(bundle_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(bundle, dict):
            continue

        bundle_id = bundle_file.stem

        # References: incomplete metadata
        for ref in bundle.get("references") or []:
            if not ref.get("title") or (not ref.get("doi") and not ref.get("zotero_key")):
                report.incomplete_references.append({
                    "bundle": bundle_id,
                    "reference_id": ref.get("id"),
                    "title": ref.get("title"),
                    "doi": ref.get("doi"),
                    "zotero_key": ref.get("zotero_key"),
                })

        # Workflow states: ambiguous status
        for ws in bundle.get("workflow_states") or []:
            state = ws.get("state", "")
            if state not in _VALID_STATES:
                report.ambiguous_statuses.append({
                    "bundle": bundle_id,
                    "workflow_state_id": ws.get("id"),
                    "state": state,
                })

        # Task extractions: malformed, missing columns, unlinked
        for ex in bundle.get("task_extractions") or []:
            ex_id = ex.get("id")

            if ex.get("reference_task_id") is None:
                report.unlinked_extractions.append({
                    "bundle": bundle_id,
                    "extraction_id": ex_id,
                    "template_id": ex.get("template_id"),
                })

            extracted = ex.get("extracted")
            if not extracted:
                report.malformed_extractions.append({
                    "bundle": bundle_id,
                    "extraction_id": ex_id,
                    "reason": "extracted is None or empty",
                })
                continue

            template_id = ex.get("template_id")
            template = TEMPLATES.get(template_id) if template_id else None
            if template is None:
                continue

            rows = extracted if isinstance(extracted, list) else [extracted]
            for i, row in enumerate(rows):
                if not isinstance(row, dict):
                    continue
                errors = template.validate_extraction_row(row)
                if errors:
                    report.missing_columns.append({
                        "bundle": bundle_id,
                        "extraction_id": ex_id,
                        "template_id": template_id,
                        "row_index": i,
                        "errors": errors,
                    })

    return report
