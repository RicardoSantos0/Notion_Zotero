"""Task-agnostic canonical bundle summarizer.

Discovers task labels dynamically from the ``tasks[].name`` field in each
bundle — no hardcoded label constants. Pandas is an optional dependency,
imported only inside :func:`build_summary_dataframes`.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

# Canonical acceptance values (lower-cased). A status containing "accepted"
# passes; anything else (including blank) is treated as "include by default".
_ACCEPTED_SUBSTRING = "accepted"


def is_accepted(bundle: dict) -> bool:
    """Return True if a canonical bundle should be included as an accepted paper.

    Checks ``workflow_states[0].state`` first, then falls back to
    ``references[0].sync_metadata.notion_properties.Status``.  Returns True
    when no status information is found (include by default).
    """
    ws = bundle.get("workflow_states") or []
    if ws:
        status = ws[0].get("state") or ""
    else:
        refs = bundle.get("references") or [{}]
        sm = refs[0].get("sync_metadata") or {}
        status = sm.get("notion_properties", {}).get("Status") or ""

    if not status:
        return True
    return _ACCEPTED_SUBSTRING in str(status).lower()


def load_canonical_records(canonical_dir: str | Path) -> list[dict]:
    """Load every ``*.canonical.json`` bundle from *canonical_dir*.

    Silently skips files that cannot be parsed.

    Returns:
        List of bundle dicts sorted by filename.
    """
    canonical_dir = Path(canonical_dir)
    bundles: list[dict] = []
    for path in sorted(canonical_dir.glob("*.canonical.json")):
        try:
            bundles.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            continue
    return bundles


def build_summary_tables(
    bundles: list[dict],
    task_label_fn: Callable[[str], str] | None = None,
) -> dict[str, list[dict]]:
    """Build one list of row-dicts per task label found in *bundles*.

    Task labels are derived from each ``tasks[].name`` entry in the bundle via
    *task_label_fn*.  When *task_label_fn* is ``None`` the task name is used
    as-is (identity function).

    Returns a dict with at least the key ``"Reading List"`` (one row per
    bundle reference) plus one key per discovered task label.

    Args:
        bundles:       List of canonical bundle dicts.
        task_label_fn: ``(task_name: str) -> str`` — defaults to identity.
    """
    label_fn: Callable[[str], str] = task_label_fn or (lambda name: name)

    reading_rows: list[dict] = []
    task_rows: dict[str, list[dict]] = {}

    for bundle in bundles:
        refs = bundle.get("references") or []
        ref: dict[str, Any] = refs[0] if refs else {}

        page_id = (bundle.get("provenance") or {}).get("source_id") or ref.get("id") or ""
        sync_meta = ref.get("sync_metadata") or {}
        notion_props = sync_meta.get("notion_properties") or {}
        domain_props = sync_meta.get("domain_properties") or {}
        reading_rows.append({**ref, **notion_props, **domain_props, "page_id": page_id})

        tasks_by_id = {t.get("id"): t.get("name") for t in (bundle.get("tasks") or [])}
        rt_by_id = {rt.get("id"): rt.get("task_id") for rt in (bundle.get("reference_tasks") or [])}

        for ex in bundle.get("task_extractions") or []:
            extracted = ex.get("extracted") or []
            rt_id = ex.get("reference_task_id")
            if rt_id:
                task_id = rt_by_id.get(rt_id)
                raw_name = tasks_by_id.get(task_id) if task_id else None
            else:
                raw_name = ex.get("schema_name") or ex.get("template_id")

            label = label_fn(raw_name or "") if raw_name else None
            if not label:
                continue

            if label not in task_rows:
                task_rows[label] = []

            for row in (extracted if isinstance(extracted, list) else []):
                if not isinstance(row, dict):
                    continue
                out_row = dict(row)
                out_row.update({
                    "source_page_id": page_id,
                    "source_title": ref.get("title"),
                    "schema_name": ex.get("schema_name"),
                })
                task_rows[label].append(out_row)

    result: dict[str, list[dict]] = {"Reading List": reading_rows}
    result.update(task_rows)
    return result


def build_summary_dataframes(
    bundles: list[dict],
    task_label_fn: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    """Wrap :func:`build_summary_tables` returning ``pd.DataFrame`` values.

    Raises:
        ImportError: When pandas is not installed.
    """
    try:
        import pandas as pd
    except ImportError as exc:
        raise ImportError(
            "pandas is required for build_summary_dataframes. "
            "Install it with: pip install pandas"
        ) from exc

    tables = build_summary_tables(bundles, task_label_fn)
    return {name: pd.DataFrame(rows).fillna("") for name, rows in tables.items()}


__all__ = [
    "load_canonical_records",
    "build_summary_tables",
    "build_summary_dataframes",
    "is_accepted",
]
