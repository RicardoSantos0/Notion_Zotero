"""New importer implementation that uses the `notion_zotero` canonical core
and the domain-pack / template registry.

This implementation is intentionally conservative: it mirrors the legacy
fixture parsing behaviour but produces `notion_zotero.core` model instances
and uses deterministic IDs from `src.schemas.idgen`.
"""
from __future__ import annotations

import json
import argparse
from pathlib import Path
from typing import Any

from notion_zotero.core.models import Reference, Task, ReferenceTask, TaskExtraction, Annotation, WorkflowState
from notion_zotero.schemas import task_registry
from notion_zotero.schemas.status_mapping import map_status
from notion_zotero.core.normalize import normalize_title

# reuse deterministic id helper from the package-local schemas
from notion_zotero.schemas.idgen import deterministic_short_id


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
	if t == "people":
		return [p.get("name") for p in prop.get("people", [])]
	# fallback
	if "rich_text" in prop:
		return "".join(p.get("plain_text", "") for p in prop.get("rich_text", []))
	if "title" in prop:
		return "".join(p.get("plain_text", "") for p in prop.get("title", []))
	return None


def slugify(s: str | None) -> str:
	return "".join(c if c.isalnum() else "_" for c in (s or "")).strip("_").lower()


def parse_fixture(path: Path):
	d = json.loads(path.read_text(encoding="utf-8"))
	page_id = d.get("page_id")
	title = d.get("title") or page_id
	props = d.get("properties", {})

	ref = Reference(
		id=page_id,
		title=title,
		authors=(prop_value(props.get("Authors")) or []),
		year=None,
		journal=prop_value(props.get("Journal")) or None,
		doi=prop_value(props.get("DOI")) or None,
		url=prop_value(props.get("URL")) or None,
		zotero_key=prop_value(props.get("Zotero Key")) or None,
		abstract=None,
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

		item = {"page_id": page_id, "heading": heading, "rows": parsed, "properties": props, "title": title}

		applicable = task_registry.get_applicable_tasks(item)
		if applicable:
			for tname, parser in applicable:
				task_id = slugify(tname)
				if not any(t.id == task_id for t in tasks):
					tasks.append(Task(id=task_id, name=tname, aliases=[]))
				rt_id = deterministic_short_id("rt", page_id, task_id)
				reference_tasks.append(ReferenceTask(id=rt_id, reference_id=ref.id, task_id=task_id, provenance={"page_id": page_id, "table_block_id": tb.get("block_id")}))
				parsed_out = parser(item) or {}
				schema_name = parsed_out.get("schema_name") or "table"
				ex_id = deterministic_short_id("ex", page_id, task_id, str(tb.get("index")))
				extractions.append(TaskExtraction(id=ex_id, reference_task_id=rt_id, template_id=schema_name, schema_name=schema_name, raw_headers=(list(parsed[0].keys()) if parsed else None), extracted=parsed, provenance={"page_id": page_id, "block_index": tb.get("index")}, revision_status=None))
		else:
			# Unclassified table: create an unlinked extraction
			ex_id = deterministic_short_id("ex", page_id, heading or "table", str(tb.get("index")))
			extractions.append(TaskExtraction(id=ex_id, reference_task_id=None, template_id=None, schema_name=heading or "table", raw_headers=(list(parsed[0].keys()) if parsed else None), extracted=parsed, provenance={"page_id": page_id, "block_index": tb.get("index")}, revision_status=None))

	for b in d.get("blocks", []):
		if b.get("type") == "paragraph" and b.get("text"):
			block_key = b.get("id") or (b.get("text") or "")[:40]
			annotations.append(Annotation(id=deterministic_short_id("an", page_id, block_key), reference_id=ref.id, kind="note", text=b.get("text"), provenance={"page_id": page_id}))

	status_raw = prop_value(props.get("Status") or props.get("Status_1"))
	status = map_status(status_raw)
	if status:
		workflow_states.append(WorkflowState(id=deterministic_short_id("ws", page_id, status), reference_id=ref.id, state=status))

	def _dump(obj):
		if hasattr(obj, "model_dump"):
			return obj.model_dump()
		if hasattr(obj, "dict"):
			return obj.dict()
		return obj

	out = {
		"references": [_dump(ref)],
		"tasks": [_dump(t) for t in tasks],
		"reference_tasks": [_dump(rt) for rt in reference_tasks],
		"task_extractions": [_dump(e) for e in extractions],
		"annotations": [_dump(a) for a in annotations],
		"workflow_states": [_dump(w) for w in workflow_states],
	}
	return page_id, out


def main():
	p = argparse.ArgumentParser()
	p.add_argument("--input", default="fixtures/reading_list")
	p.add_argument("--out", default="fixtures/canonical")
	p.add_argument("--force", action="store_true", help="overwrite existing canonical files even if content unchanged")
	args = p.parse_args()
	input_dir = Path(args.input)
	out_dir = Path(args.out)
	out_dir.mkdir(parents=True, exist_ok=True)
	for f in sorted(input_dir.glob("*.json")):
		page_id, canon = parse_fixture(f)
		out_path = out_dir / f"{page_id}.canonical.json"
		new_text = json.dumps(canon, ensure_ascii=False, indent=2)
		if out_path.exists() and not args.force:
			old_text = out_path.read_text(encoding="utf-8")
			if old_text == new_text:
				print("UNCHANGED:", out_path)
				continue
			else:
				out_path.write_text(new_text, encoding="utf-8")
				print("UPDATED:", out_path)
		else:
			out_path.write_text(new_text, encoding="utf-8")
			print("WROTE:", out_path)


if __name__ == '__main__':
	main()
