"""Write-log replay (M4).

Selects write-log entries that did not complete — ``planned`` (queued, never run)
and ``failed`` (errored) — and re-plans them. Dry-run by default: the planner never
performs writes itself; the actual re-execution is delegated to the apply path under
the sync lock, keeping the review-first / dry-run-default safety model.
"""
from __future__ import annotations

from typing import Iterable

_REPLAYABLE_STATUSES = frozenset({"planned", "failed"})


def select_replay_candidates(entries: Iterable[dict]) -> list[dict]:
    """Return entries whose status is planned or failed (re-runnable)."""
    return [e for e in (entries or [])
            if isinstance(e, dict) and e.get("status") in _REPLAYABLE_STATUSES]


def plan_replay(entries: Iterable[dict], *, apply: bool = False) -> dict:
    """Build a replay plan. ``dry_run`` is True unless ``apply=True`` is passed.

    The planner does not execute writes (``applied`` is always empty); execution is
    the applier's job, performed under the sync lock.
    """
    candidates = select_replay_candidates(entries)
    return {
        "dry_run": not apply,
        "candidates": candidates,
        "count": len(candidates),
        "applied": [],
    }


__all__ = ["select_replay_candidates", "plan_replay"]
