# canonical import path — no legacy heuristic calls
"""New importer implementation that uses the `notion_zotero` canonical core
and the domain-pack / template registry.

This implementation is intentionally conservative: it mirrors the legacy
fixture parsing behaviour but produces `notion_zotero.core` model instances
and uses deterministic IDs from `notion_zotero.schemas.idgen`.
"""
from __future__ import annotations

import json
import logging
import argparse
from pathlib import Path
from typing import Any

from notion_zotero.core.models import Reference, Task, ReferenceTask, TaskExtraction, Annotation, WorkflowState
from notion_zotero.core.enums import ValidationStatus
from notion_zotero.schemas import task_registry
from notion_zotero.schemas.status_mapping import map_status
from notion_zotero.core.normalize import normalize_title

# reuse deterministic id helper from the package-local schemas
from notion_zotero.schemas.idgen import deterministic_short_id

log = logging.getLogger(__name__)


def prop_value(prop: dict | None):
    if not prop:
        return None
    t = prop.get("type")
    if t == "title":
        return "".join(p.get("plain_text", "") for p in prop.get("title", []))
    if t == "rich_text":
        return "".join(p.get("plain_text", "") for p in prop.get("rich_text", []))
    if t == "multi_select":
        return [s.get("name") for s in prop.get("multi_select", [])]
    if t == "select":
        sel = prop.get("select")
        return sel.get("name") if sel else None
    if t == "url":
        return prop.get("url")
    if t == "date":
        d = prop.get("date")
        return d.get("start") if d else None
    if t == "number":
        return prop.get("number")
    if t == "checkbox":
        return prop.get("checkbox")
    if t == "people":
        return [p.get("name") for p in prop.get("people", [])]
    if t == "status":
        s = prop.get("status")
        return s.get("name") if s else None
    # fallback
    if "rich_text" in prop:
        return "".join(p.get("plain_text", "") for p in prop.get("rich_text", []))
    if "title" in prop:
        return "".join(p.get("plain_text", "") for p in prop.get("title", []))
    return None


def _coerce_authors(val) -> list:
    if not val:
        return []
    if isinstance(val, list):
        return [str(a) for a in val if a]
    return [a.strip() for a in str(val).split(";") if a.strip()]


def slugify(s: str | None) -> str:
    return "".join(c if c.isalnum() else "_" for c in (s or "")).strip("_").lower()


def _build_provenance(
    page_id: str,
    domain_pack_id: str | None,
    domain_pack_version: str | None,
    **extra: Any,
) -> dict:
    """Return a provenance dict that always contains the three canonical keys."""
    base = {
        "source_id": page_id,
        "domain_pack_id": domain_pack_id,
        "domain_pack_version": domain_pack_version,
    }
    base.update(extra)
    return base


def _parse_fixture_dict(d: dict, domain_pack_id: str | None = None):
    """Core parsing logic: accepts a fixture dict and returns (page_id, bundle_dict).

    This is the single source of truth for fixture parsing.  Both
    :func:`parse_fixture` (file-based) and :func:`parse_fixture_from_dict`
    (in-memory) delegate here.
    """
    page_id = d.get("page_id")
    title = d.get("title") or page_id
    props = d.get("properties", {})

    # Resolve which domain pack to use
    active_pack = None
    active_pack_version: str | None = None
    if domain_pack_id:
        active_pack = task_registry.load_domain_pack(domain_pack_id)
        if active_pack is None:
            log.warning("domain pack '%s' not found; falling back to default", domain_pack_id)
    if active_pack is None:
        from notion_zotero.schemas.domain_packs import education_learning_analytics as _ela
        active_pack = _ela.domain_pack
    active_pack_id: str = active_pack.get("id") or ""
    active_pack_version = active_pack.get("version")

    # Case-insensitive property lookup helper
    _props_lower = {k.lower(): v for k, v in props.items()}

    def _prop(name: str):
        return prop_value(props.get(name)) or prop_value(_props_lower.get(name.lower()))

    _year_raw = _prop("Year") or _prop("Publication Year")
    _year_int: int | None = None
    try:
        _year_int = int(_year_raw) if _year_raw is not None else None
    except (TypeError, ValueError):
        pass

    # journal_quartile: Article Type (multi_select) or Quartile/SJR (select/rich_text)
    _jq_raw = (_prop("Article Type") or _prop("Quartile")
               or _prop("Journal Quartile") or _prop("SJR Quartile"))
    _jq: str | None = (_jq_raw[0] if isinstance(_jq_raw, list) and _jq_raw else _jq_raw) or None

    # Status fields may encode separate task decisions; keep every signal.
    status_values: dict[str, Any] = {}
    for status_field in ("Status", "Status_1"):
        status_value = _prop(status_field)
        if status_value not in (None, "", [], {}):
            status_values[status_field] = status_value

    # Domain-specific properties declared by the active domain pack.
    # Stored separately so analysis layers can surface them as named columns.
    domain_properties: dict[str, Any] = {}
    for field_name in active_pack.get("notion_properties", []):
        val = _prop(field_name)
        if val not in (None, "", [], {}):
            domain_properties[field_name] = val

    sync_meta: dict[str, Any] = {}
    if status_values:
        sync_meta["notion_properties"] = status_values
    if domain_properties:
        sync_meta["domain_properties"] = domain_properties

    _abstract_raw = _prop("Abstract")
    ref = Reference(
        id=page_id,
        title=title,
        authors=_coerce_authors(prop_value(props.get("Authors")) or prop_value(props.get("Author"))),
        year=_year_int,
        journal=_prop("Journal") or None,
        doi=_prop("DOI") or None,
        url=_prop("URL") or None,
        zotero_key=_prop("Zotero Key") or _prop("Zotero_Key") or None,
        abstract=(_abstract_raw or None) if isinstance(_abstract_raw, str) else None,
        # SLR provenance fields
        search_terms=_prop("Search Strategy") or _prop("Search Terms") or None,
        search_date=_prop("Date of Retrieval") or _prop("Search Date") or None,
        database=_prop("Database") or _prop("Source Database") or _prop("Platform") or None,
        journal_quartile=_jq,
        provenance=_build_provenance(page_id, active_pack_id, active_pack_version),
        validation_status=ValidationStatus.UNKNOWN,
        sync_metadata=sync_meta,
    )

    tasks: list[Task] = []
    reference_tasks: list[ReferenceTask] = []
    extractions: list[TaskExtraction] = []
    annotations: list[Annotation] = []
    workflow_states: list[WorkflowState] = []

    for tb in d.get("tables", []):
        heading = tb.get("heading") or ""
        rows = tb.get("rows", [])
        parsed: list[dict[str, Any]] = []
        if rows:
            header = rows[0]
            for r in rows[1:]:
                if len(r) < len(header):
                    r = r + ["" for _ in range(len(header) - len(r))]
                parsed.append(dict(zip(header, r)))

        item = {
            "page_id": page_id,
            "heading": heading,
            "rows": parsed,
            "properties": props,
            "title": title,
            "_domain_pack": active_pack,
        }

        applicable = task_registry.get_applicable_tasks(item)
        if applicable:
            for tname, parser in applicable:
                task_id = slugify(tname)
                if not any(t.id == task_id for t in tasks):
                    tasks.append(Task(
                        id=task_id,
                        name=tname,
                        aliases=[],
                        provenance=_build_provenance(page_id, active_pack_id, active_pack_version),
                        validation_status=ValidationStatus.UNKNOWN,
                        sync_metadata={},
                    ))
                rt_id = deterministic_short_id("rt", page_id, task_id)
                reference_tasks.append(ReferenceTask(
                    id=rt_id,
                    reference_id=ref.id,
                    task_id=task_id,
                    provenance=_build_provenance(
                        page_id, active_pack_id, active_pack_version,
                        table_block_id=tb.get("block_id"),
                    ),
                    validation_status=ValidationStatus.UNKNOWN,
                    sync_metadata={},
                ))
                parsed_out = parser(item) or {}
                schema_name = parsed_out.get("schema_name") or "table"
                ex_id = deterministic_short_id("ex", page_id, task_id, str(tb.get("index")))
                extractions.append(TaskExtraction(
                    id=ex_id,
                    reference_task_id=rt_id,
                    template_id=schema_name,
                    schema_name=schema_name,
                    raw_headers=(list(parsed[0].keys()) if parsed else None),
                    extracted=parsed,
                    provenance=_build_provenance(
                        page_id, active_pack_id, active_pack_version,
                        block_index=tb.get("index"),
                    ),
                    revision_status=None,
                    validation_status=ValidationStatus.UNKNOWN,
                    sync_metadata={},
                ))
        else:
            # Unclassified table: create an unlinked TaskExtraction.
            # No legacy heuristic calls are made.
            ex_id = deterministic_short_id("ex", page_id, heading or "table", str(tb.get("index")))
            extractions.append(TaskExtraction(
                id=ex_id,
                reference_task_id=None,
                template_id=None,
                schema_name=heading or "table",
                raw_headers=(list(parsed[0].keys()) if parsed else None),
                extracted=parsed,
                provenance=_build_provenance(
                    page_id, active_pack_id, active_pack_version,
                    block_index=tb.get("index"),
                ),
                revision_status=None,
                validation_status=ValidationStatus.UNKNOWN,
                sync_metadata={},
            ))

    for b in d.get("blocks", []):
        if b.get("type") == "paragraph" and b.get("text"):
            block_key = b.get("id") or (b.get("text") or "")[:40]
            annotations.append(Annotation(
                id=deterministic_short_id("an", page_id, block_key),
                reference_id=ref.id,
                kind="note",
                text=b.get("text"),
                provenance=_build_provenance(page_id, active_pack_id, active_pack_version),
                validation_status=ValidationStatus.UNKNOWN,
                sync_metadata={},
            ))

    # WorkflowState from every status field extracted above.
    for source_field, status_raw in status_values.items():
        status = map_status(status_raw)
        if status:
            workflow_states.append(WorkflowState(
                id=deterministic_short_id("ws", page_id, source_field, status),
                reference_id=ref.id,
                state=status,
                source_field=source_field,
                provenance=_build_provenance(page_id, active_pack_id, active_pack_version),
                validation_status=ValidationStatus.UNKNOWN,
                sync_metadata={},
            ))

    def _dump(obj):
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "dict"):
            return obj.dict()
        return obj

    out = {
        "provenance": {
            "source_id": page_id,
            "domain_pack_id": active_pack_id,
            "domain_pack_version": active_pack_version,
        },
        "references": [_dump(ref)],
        "tasks": [_dump(t) for t in tasks],
        "reference_tasks": [_dump(rt) for rt in reference_tasks],
        "task_extractions": [_dump(e) for e in extractions],
        "annotations": [_dump(a) for a in annotations],
        "workflow_states": [_dump(w) for w in workflow_states],
    }
    return page_id, out


def parse_fixture(path: Path, domain_pack_id: str | None = None):
    """Parse a fixture JSON file on disk and return (page_id, bundle_dict)."""
    d = json.loads(path.read_text(encoding="utf-8"))
    return _parse_fixture_dict(d, domain_pack_id=domain_pack_id)


def parse_fixture_from_dict(d: dict, domain_pack_id: str | None = None):
    """Parse a fixture dict in memory and return (page_id, bundle_dict).

    Accepts the same structure as a fixture file (keys: ``page_id``, ``title``,
    ``properties``, ``tables``, ``blocks``).  This allows the pull-notion CLI
    command to build full canonical bundles without writing intermediate files.
    """
    return _parse_fixture_dict(d, domain_pack_id=domain_pack_id)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="data/raw/notion")
    p.add_argument("--out", default="data/pulled/notion/learning_analytics_review")
    p.add_argument("--force", action="store_true", help="overwrite existing canonical files even if content unchanged")
    p.add_argument("--domain-pack", default=None, help="domain pack ID to use for task resolution")
    args = p.parse_args()
    domain_pack_id: str | None = getattr(args, "domain_pack", None)
    if domain_pack_id:
        log.info("using domain pack: %s", domain_pack_id)
    input_dir = Path(args.input)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in sorted(input_dir.glob("*.json")):
        page_id, canon = parse_fixture(f, domain_pack_id=domain_pack_id)
        out_path = out_dir / f"{page_id}.canonical.json"
        new_text = json.dumps(canon, ensure_ascii=False, indent=2)
        if out_path.exists() and not args.force:
            old_text = out_path.read_text(encoding="utf-8")
            if old_text == new_text:
                log.info("UNCHANGED: %s", out_path)
                continue
            else:
                out_path.write_text(new_text, encoding="utf-8")
                log.info("UPDATED: %s", out_path)
        else:
            out_path.write_text(new_text, encoding="utf-8")
            log.info("WROTE: %s", out_path)


if __name__ == '__main__':
    main()
