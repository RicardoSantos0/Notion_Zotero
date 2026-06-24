"""MVP reference-health report (M2).

Aggregates canonical reference bundles — and, when available, local snapshot age,
write-log artifacts, and rollback availability — into one concise health report,
rendered as JSON and Markdown for the daily review-first workflow.

`build_health_report` is input-agnostic: each "bundle" may be a dict or any object
exposing the canonical Reference fields (title, authors, year, journal, doi,
zotero_key), so it serves both unit tests and real `core.models.Reference` objects.
"""
from __future__ import annotations

import json
import re
from typing import Any, Iterable, Optional

_COMPLETENESS_FIELDS = ("doi", "title", "authors", "year", "journal", "zotero_key")


def _get(bundle: Any, name: str):
    if isinstance(bundle, dict):
        return bundle.get(name)
    return getattr(bundle, name, None)


def _nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _norm_title(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value.strip().lower())


def _completeness(bundles: list) -> dict:
    n = len(bundles)
    out: dict[str, dict] = {}
    for f in _COMPLETENESS_FIELDS:
        present = sum(1 for b in bundles if _nonempty(_get(b, f)))
        out[f] = {"present": present, "total": n,
                  "rate": round(present / n, 3) if n else 0.0}
    return out


def _label(bundle: Any) -> Any:
    return _get(bundle, "id") or _get(bundle, "title")


def _duplicate_candidates(bundles: list) -> list[dict]:
    """Group bundles sharing a DOI or a normalized title (potential duplicates)."""
    by_doi: dict[str, list] = {}
    by_title: dict[str, list] = {}
    for b in bundles:
        doi = _get(b, "doi")
        if isinstance(doi, str) and doi.strip():
            by_doi.setdefault(doi.strip().lower(), []).append(_label(b))
        t = _norm_title(_get(b, "title"))
        if t:
            by_title.setdefault(t, []).append(_label(b))
    out: list[dict] = []
    for doi, members in by_doi.items():
        if len(members) > 1:
            out.append({"key": "doi", "value": doi, "members": members})
    for t, members in by_title.items():
        if len(members) > 1:
            out.append({"key": "title", "value": t, "members": members})
    return out


def _source_only(bundles: list) -> list:
    """Records present only in the source (Zotero) with no Notion linkage.

    Heuristic: has a zotero_key but no notion page id in sync_metadata.
    """
    out: list = []
    for b in bundles:
        if not _nonempty(_get(b, "zotero_key")):
            continue
        meta = _get(b, "sync_metadata") or {}
        if isinstance(meta, dict) and not (meta.get("notion_page_id") or meta.get("notion_id")):
            out.append(_label(b))
    return out


def build_health_report(
    bundles: Iterable[Any],
    *,
    snapshot_age_days: Optional[float] = None,
    ambiguous_matches: Optional[list] = None,
    source_only_records: Optional[list] = None,
    write_log_entries: Optional[Iterable[dict]] = None,
    rollback_available: Optional[bool] = None,
) -> dict:
    """Build the MVP health report dict (AC-002 sections)."""
    bundles = list(bundles or [])
    report: dict[str, Any] = {
        "total_records": len(bundles),
        "metadata_completeness": _completeness(bundles),
        "duplicate_candidates": _duplicate_candidates(bundles),
        "ambiguous_matches": list(ambiguous_matches or []),
        "source_only_records": (list(source_only_records)
                                if source_only_records is not None
                                else _source_only(bundles)),
        "stale_snapshot_age_days": snapshot_age_days,
    }
    pending = [e for e in (write_log_entries or [])
               if isinstance(e, dict) and e.get("status") in ("planned", "failed")]
    report["pending_or_failed_writes"] = pending
    report["rollback_available"] = bool(rollback_available)
    return report


def render_json(report: dict) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False, default=str)


def render_markdown(report: dict) -> str:
    lines = ["# MVP Reference Health Report", ""]
    lines.append(f"- Total records: **{report.get('total_records', 0)}**")
    age = report.get("stale_snapshot_age_days")
    lines.append(f"- Snapshot age (days): **{age if age is not None else 'n/a'}**")
    lines.append(f"- Rollback available: **{report.get('rollback_available', False)}**")
    lines.append("")
    lines.append("## Metadata completeness")
    lines.append("")
    lines.append("| Field | Present | Total | Rate |")
    lines.append("|---|---:|---:|---:|")
    for field, c in report.get("metadata_completeness", {}).items():
        lines.append(f"| {field} | {c['present']} | {c['total']} | {c['rate']:.0%} |")
    lines.append("")
    dups = report.get("duplicate_candidates", [])
    lines.append(f"## Duplicate candidates ({len(dups)})")
    for d in dups:
        lines.append(f"- {d['key']}={d['value']}: {d['members']}")
    lines.append("")
    lines.append(f"## Ambiguous matches ({len(report.get('ambiguous_matches', []))})")
    lines.append(f"## Source-only records ({len(report.get('source_only_records', []))})")
    pend = report.get("pending_or_failed_writes", [])
    lines.append(f"## Planned / failed writes ({len(pend)})")
    return "\n".join(lines) + "\n"


__all__ = ["build_health_report", "render_json", "render_markdown"]
