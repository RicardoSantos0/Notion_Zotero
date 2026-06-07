"""Pre-export audit gate for the review pipeline (façade, T7.3).

Re-exports the stabilized audit gate from
``notion_zotero.analysis.predictive_problem_table``.
"""
from __future__ import annotations

from notion_zotero.analysis.la_review_figure_data import (
    build_audit_dashboard,
    compute_audit_metrics,
)
from notion_zotero.analysis.predictive_problem_table import (
    AuditGateError,
    run_audit_gate,
)

__all__ = [
    "run_audit_gate",
    "AuditGateError",
    "compute_audit_metrics",
    "build_audit_dashboard",
]
