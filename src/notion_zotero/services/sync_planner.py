"""Read-only sync planning between local Notion and Zotero snapshots.

The planner does not call live APIs and does not mutate local files. It turns
two canonical-bundle directories into an auditable plan that can be reviewed
before any writer is allowed to apply changes.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from notion_zotero.core.field_ownership import ZOTERO_OWNED
from notion_zotero.core.normalize import normalize_authors, normalize_doi, normalize_title

PLAN_VERSION = 1


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _load_bundles(input_dir: str | Path, source: str) -> list[dict[str, Any]]:
    path = Path(input_dir)
    if not path.exists():
        raise FileNotFoundError(f"{source} directory not found: {path}")

    records: list[dict[str, Any]] = []
    for bundle_file in sorted(path.glob("*.canonical.json")):
        try:
            bundle = json.loads(bundle_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(bundle, dict):
            continue
        refs = bundle.get("references") or []
        if not refs or not isinstance(refs[0], dict):
            continue
        records.append(
            {
                "source": source,
                "bundle_path": str(bundle_file),
                "bundle_id": bundle.get("bundle_id") or bundle_file.stem.replace(".canonical", ""),
                "bundle": bundle,
                "reference": refs[0],
            }
        )
    return records


def _clean_key(value: Any) -> str:
    return str(value or "").strip().casefold()


def _title_authors_key(ref: dict[str, Any]) -> str:
    title = normalize_title(ref.get("title")).casefold()
    authors = normalize_authors(ref.get("authors")).casefold()
    if not title:
        return ""
    return f"{title}|{authors}"


def _match_keys(ref: dict[str, Any]) -> list[tuple[str, str]]:
    keys: list[tuple[str, str]] = []
    zotero_key = _clean_key(ref.get("zotero_key"))
    if zotero_key:
        keys.append(("zotero_key", zotero_key))

    doi = normalize_doi(ref.get("doi"))
    if doi:
        keys.append(("doi", doi))

    title_authors = _title_authors_key(ref)
    if title_authors:
        keys.append(("title_authors", title_authors))

    return keys


def _index_records(records: list[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    index: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for record in records:
        for key in _match_keys(record["reference"]):
            index.setdefault(key, []).append(record)
    return index


def _record_summary(record: dict[str, Any]) -> dict[str, Any]:
    ref = record["reference"]
    sync_metadata = ref.get("sync_metadata") or {}
    zotero_metadata = sync_metadata.get("zotero") if isinstance(sync_metadata, dict) else {}
    return {
        "source": record["source"],
        "bundle_id": record["bundle_id"],
        "bundle_path": record["bundle_path"],
        "reference_id": ref.get("id"),
        "title": ref.get("title"),
        "authors": ref.get("authors") or [],
        "year": ref.get("year"),
        "doi": ref.get("doi"),
        "zotero_key": ref.get("zotero_key"),
        "zotero_version": (zotero_metadata or {}).get("version"),
    }


def _bibliographic_diffs(
    notion_ref: dict[str, Any],
    zotero_ref: dict[str, Any],
) -> list[dict[str, Any]]:
    diffs: list[dict[str, Any]] = []
    for field in sorted(ZOTERO_OWNED):
        notion_value = notion_ref.get(field)
        zotero_value = zotero_ref.get(field)
        if notion_value != zotero_value:
            diffs.append(
                {
                    "field": field,
                    "notion_value": notion_value,
                    "zotero_value": zotero_value,
                }
            )
    return diffs


def _operation_for_diff(
    match_id: str,
    notion_record: dict[str, Any],
    zotero_record: dict[str, Any],
    diff: dict[str, Any],
) -> dict[str, Any]:
    notion_ref = notion_record["reference"]
    zotero_ref = zotero_record["reference"]
    return {
        "operation": "update_notion_reference_field",
        "operation_id": f"{match_id}-{diff['field']}",
        "match_id": match_id,
        "target": "notion",
        "source": "zotero",
        "field": diff["field"],
        "old_value": diff["notion_value"],
        "new_value": diff["zotero_value"],
        "notion_reference_id": notion_ref.get("id"),
        "zotero_reference_id": zotero_ref.get("id"),
        "zotero_key": zotero_ref.get("zotero_key") or notion_ref.get("zotero_key"),
        "reason": "zotero_owned_field",
    }


def _review_action_for_zotero_only(record: dict[str, Any]) -> dict[str, Any]:
    summary = _record_summary(record)
    return {
        "operation": "create_notion_page_from_zotero_record",
        "target": "notion",
        "source": "zotero",
        "status": "needs_review",
        "zotero_reference_id": summary["reference_id"],
        "zotero_key": summary["zotero_key"],
        "zotero_version": summary["zotero_version"],
        "title": summary["title"],
        "reason": "zotero_record_missing_from_notion",
    }


def build_sync_plan(
    notion_dir: str | Path,
    zotero_dir: str | Path,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build a read-only sync plan from local Notion and Zotero snapshots."""
    notion_records = _load_bundles(notion_dir, "notion")
    zotero_records = _load_bundles(zotero_dir, "zotero")
    notion_index = _index_records(notion_records)

    matched: list[dict[str, Any]] = []
    operations: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    only_zotero: list[dict[str, Any]] = []
    review_actions: list[dict[str, Any]] = []
    used_notion_ids: set[int] = set()
    ambiguous_notion_ids: set[int] = set()

    for zotero_record in zotero_records:
        candidates_by_key: list[tuple[tuple[str, str], dict[str, Any]]] = []
        seen_candidate_ids: set[int] = set()
        for key in _match_keys(zotero_record["reference"]):
            for candidate in notion_index.get(key, []):
                candidate_id = id(candidate)
                if candidate_id in seen_candidate_ids:
                    continue
                seen_candidate_ids.add(candidate_id)
                candidates_by_key.append((key, candidate))

        if not candidates_by_key:
            only_zotero.append(_record_summary(zotero_record))
            review_actions.append(_review_action_for_zotero_only(zotero_record))
            continue

        available = [
            (key, candidate)
            for key, candidate in candidates_by_key
            if id(candidate) not in used_notion_ids
        ]
        if len(available) != 1:
            ambiguous_notion_ids.update(id(candidate) for _, candidate in candidates_by_key)
            ambiguous.append(
                {
                    "zotero": _record_summary(zotero_record),
                    "candidates": [
                        {
                            "match_key": {"type": key[0], "value": key[1]},
                            "notion": _record_summary(candidate),
                        }
                        for key, candidate in candidates_by_key
                    ],
                    "reason": "no_available_candidate" if not available else "multiple_candidates",
                }
            )
            continue

        match_key, notion_record = available[0]
        used_notion_ids.add(id(notion_record))
        match_id = f"match-{len(matched) + 1:04d}"
        diffs = _bibliographic_diffs(notion_record["reference"], zotero_record["reference"])
        match_entry = {
            "match_id": match_id,
            "match_key": {"type": match_key[0], "value": match_key[1]},
            "notion": _record_summary(notion_record),
            "zotero": _record_summary(zotero_record),
            "bibliographic_diffs": diffs,
        }
        matched.append(match_entry)
        operations.extend(
            _operation_for_diff(match_id, notion_record, zotero_record, diff)
            for diff in diffs
        )

    only_notion = [
        _record_summary(record)
        for record in notion_records
        if id(record) not in used_notion_ids and id(record) not in ambiguous_notion_ids
    ]

    return {
        "version": PLAN_VERSION,
        "generated_at": generated_at or _utc_now(),
        "inputs": {
            "notion_dir": str(notion_dir),
            "zotero_dir": str(zotero_dir),
        },
        "summary": {
            "notion_records": len(notion_records),
            "zotero_records": len(zotero_records),
            "matched": len(matched),
            "operations": len(operations),
            "only_zotero": len(only_zotero),
            "only_notion": len(only_notion),
            "ambiguous": len(ambiguous),
            "review_actions": len(review_actions),
        },
        "matches": matched,
        "operations": operations,
        "only_zotero": only_zotero,
        "only_notion": only_notion,
        "ambiguous": ambiguous,
        "review_actions": review_actions,
    }


def write_sync_plan(plan: dict[str, Any], output_path: str | Path) -> Path:
    """Write *plan* as UTF-8 JSON and return the output path."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


__all__ = ["PLAN_VERSION", "build_sync_plan", "write_sync_plan"]
