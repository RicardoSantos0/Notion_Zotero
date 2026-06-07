"""Manual-override application for classified contribution rows.

This module is intentionally kept free of pandas and heavy-analysis dependencies
so it can be imported in lightweight contexts (e.g., test stubs, CLI validation)
without triggering the full analysis stack.

Public API:
    apply_overrides(contribution_row, overrides) -> dict

The function is also re-exported from pred_horizon_summary for backward compat.
"""
from __future__ import annotations

from typing import Any, Mapping


def apply_overrides(
    contribution_row: Mapping[str, Any],
    overrides: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Apply manual overrides to a classified contribution row.

    Overrides are applied AFTER the rule-based classifier runs, not before.
    Any field listed in a matching override entry replaces the classifier's
    output for that field.

    Args:
        contribution_row: a dict representing one classified contribution,
            typically with keys like ``contribution_id``, ``paper_id``, and
            taxonomy dimension keys (each a dict with ``label``, ``confidence``,
            ``evidence`` sub-keys, OR a plain scalar).
        overrides: list of override entries.  Each entry must have at minimum
            a ``contribution_id`` key (or ``paper_id`` as fallback) plus the
            field/value pair to apply and a ``rationale`` field.  If None or
            empty, the row is returned unchanged.

    Returns:
        A new dict (copy of the input) with overrides applied.  If any override
        matched, the row carries ``_override_applied=True`` and
        ``_applied_overrides`` contains the list of applied entries for audit.

    Example::

        row = {
            "contribution_id": "c-001",
            "target_construct": {"label": "grade_or_score", "confidence": "high"},
        }
        override = {
            "contribution_id": "c-001",
            "target_construct": "dropout_or_withdrawal",
            "rationale": "Paper actually predicts dropout",
            "taxonomy_version_stamp": "1.1",
        }
        result = apply_overrides(row, overrides=[override])
        # result["target_construct"]["label"] == "dropout_or_withdrawal"
        # result["_override_applied"] == True
    """
    result: dict[str, Any] = dict(contribution_row)

    if not overrides:
        return result

    row_cid = str(result.get("contribution_id") or "")
    row_pid = str(result.get("paper_id") or "")

    applied: list[dict[str, Any]] = []

    for entry in overrides:
        entry_cid = str(entry.get("contribution_id") or "")
        entry_pid = str(entry.get("paper_id") or "")

        # Match by contribution_id (preferred) or paper_id (fallback)
        matches = (entry_cid and entry_cid == row_cid) or (
            not entry_cid and entry_pid and entry_pid == row_pid
        )
        if not matches:
            continue

        field = entry.get("field") or entry.get("dimension")
        value = entry.get("value")

        if field is None:
            # Support simplified entry format where the field is a direct key
            # (not nested under "field"/"value").
            # E.g. {"contribution_id": "x", "target_construct": "dropout_or_withdrawal", ...}
            reserved = {
                "contribution_id",
                "paper_id",
                "rationale",
                "reviewer",
                "date",
                "taxonomy_version_stamp",
                "supersedes",
            }
            for k, v in entry.items():
                if k not in reserved:
                    field = k
                    value = v
                    break

        if field is not None and value is not None:
            existing = result.get(field)
            if isinstance(existing, dict):
                # Preserve label+confidence+evidence structure; replace label only
                updated = dict(existing)
                updated["label"] = value
                updated["_overridden"] = True
                updated["_override_rationale"] = entry.get("rationale", "")
                result[field] = updated
            else:
                result[field] = value

            applied.append(entry)

    if applied:
        result["_override_applied"] = True
        result["_applied_overrides"] = applied

    return result


__all__ = ["apply_overrides"]
