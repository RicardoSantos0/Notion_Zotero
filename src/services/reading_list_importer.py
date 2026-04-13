#!/usr/bin/env python3
import json
import uuid
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.core.models import Reference, Task, ReferenceTask, TaskExtraction, Annotation, WorkflowState


def prop_value(prop):
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


def slugify(s):
    return "".join(c if c.isalnum() else "_" for c in (s or "")).strip("_").lower()


def parse_fixture(path: Path):
    d = json.loads(path.read_text(encoding="utf-8"))
    page_id = d.get("page_id")
    title = d.get("title") or page_id
    props = d.get("properties", {})
    ref = Reference(id=page_id, title=title,
                    authors=(prop_value(props.get("Authors")) or []),
                    year=None,
                    journal=prop_value(props.get("Journal")) or None,
                    doi=prop_value(props.get("DOI")) or None,
                    url=prop_value(props.get("URL")) or None,
                    zotero_key=prop_value(props.get("Zotero Key")) or None,
                    abstract=None)
    tasks = []
    reference_tasks = []
    extractions = []
    annotations = []
    workflow_states = []
    for tb in d.get("tables", []):
        heading = tb.get("heading") or ""
        task_name = None
        if "summary table" in heading.lower():
            parts = heading.split(":", 1)
            if len(parts) > 1:
                task_name = parts[1].strip()
            else:
                parts = heading.split("-", 1)
                if len(parts) > 1:
                    task_name = parts[1].strip()
        schema = task_name or (heading or "table")
        rows = tb.get("rows", [])
        parsed = []
        if rows:
            header = rows[0]
            for r in rows[1:]:
                if len(r) < len(header):
                    r = r + ["" for _ in range(len(header) - len(r))]
                parsed.append(dict(zip(header, r)))
        if task_name:
            task_id = slugify(task_name)
            tasks.append(Task(id=task_id, name=task_name, aliases=[]))
            rt_id = f"rt_{uuid.uuid4().hex[:8]}"
            reference_tasks.append(ReferenceTask(id=rt_id, reference_id=ref.id, task_id=task_id, provenance={"page_id": page_id, "table_block_id": tb.get("block_id")}))
            ex_id = f"ex_{uuid.uuid4().hex[:8]}"
            extractions.append({
                "id": ex_id,
                "reference_task_id": rt_id,
                "schema_name": schema,
                "extracted": parsed,
                "provenance": {"page_id": page_id, "block_index": tb.get("index")},
                "revision_status": None,
            })
        else:
            ex_id = f"ex_{uuid.uuid4().hex[:8]}"
            extractions.append({
                "id": ex_id,
                "reference_task_id": None,
                "schema_name": schema,
                "extracted": parsed,
                "provenance": {"page_id": page_id, "block_index": tb.get("index")},
                "revision_status": None,
            })
    for b in d.get("blocks", []):
        if b.get("type") == "paragraph" and b.get("text"):
            annotations.append(Annotation(id=f"an_{uuid.uuid4().hex[:8]}", reference_id=ref.id, text=b.get("text"), provenance={"page_id": page_id}))
    status = prop_value(props.get("Status") or props.get("Status_1"))
    if status:
        workflow_states.append(WorkflowState(id=f"ws_{uuid.uuid4().hex[:8]}", reference_id=ref.id, state=status))
    out = {
        "references": [ref.dict()],
        "tasks": [t.dict() for t in tasks],
        "reference_tasks": [rt.dict() for rt in reference_tasks],
        "task_extractions": [e.dict() if hasattr(e, "dict") else e for e in extractions],
        "annotations": [a.dict() for a in annotations],
        "workflow_states": [w.dict() for w in workflow_states]
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
