"""Manuscript export orchestration for the review pipeline (façade, T7.3).

Runs the pre-export audit gate and reports the canonical output locations.
Heavy table/figure generation lives in the sibling façade modules; this module
ties the gate to the export step.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from notion_zotero.analysis.review_pipeline.audit import run_audit_gate

#: Canonical manuscript-output locations (relative to the LA-review root).
EXPORT_ARTIFACTS = (
    "tables/table_3_counts.xlsx",
    "tables/data_source_by_task.xlsx",
    "tables/task_synthesis_matrix.xlsx",
    "tables/evaluation_maturity.xlsx",
    "figures/figure_1.png",
)


def gate_then_export(df: "Any", report_path: "str | Path | None" = None) -> bool:
    """Run the audit gate; return True when export is permitted (gate passed)."""
    run_audit_gate(df, report_path=report_path)
    return True


__all__ = ["EXPORT_ARTIFACTS", "gate_then_export"]
