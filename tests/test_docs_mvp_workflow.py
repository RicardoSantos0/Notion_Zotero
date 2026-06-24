"""M1 / T1.5 — test-first contract: the MVP workflow doc must exist (written in M6)
and cover the daily pull -> health -> review -> apply -> recovery loop.
Fails for missing implementation until docs/mvp_reference_workflow.md is written.
"""
from __future__ import annotations

from pathlib import Path

_DOC = Path(__file__).resolve().parents[1] / "docs" / "mvp_reference_workflow.md"


def test_mvp_workflow_doc_exists():
    assert _DOC.exists(), "docs/mvp_reference_workflow.md not yet written (M6)"


def test_mvp_workflow_doc_covers_core_loop():
    text = _DOC.read_text(encoding="utf-8").lower()
    for cmd in ("plan-sync", "review-plan", "mvp-health",
                "apply-plan", "rollback-plan", "replay-log"):
        assert cmd in text, f"workflow doc does not mention `{cmd}`"
