#!/usr/bin/env python3
"""CLI entrypoint for the notion_zotero package."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Sequence

log = logging.getLogger(__name__)


def _call_func_with_argv(func, argv: Sequence[str]):
    old_argv = sys.argv
    try:
        sys.argv = [old_argv[0]] + list(argv)
        func()
    finally:
        sys.argv = old_argv


def cmd_export_snapshot(args):
    # Delegate to the existing analysis package under `src.analysis`
    try:
        from notion_zotero.analysis import export_database_snapshot
    except Exception:
        raise RuntimeError("export-snapshot is not available: legacy analysis code not present")

    export_database_snapshot(args.out, args.db)


def cmd_parse_fixtures(args):
    from notion_zotero.services.reading_list_importer import main as _rl_main

    argv = []
    if args.input:
        argv += ["--input", args.input]
    if args.out:
        argv += ["--out", args.out]
    if args.force:
        argv += ["--force"]
    if getattr(args, "domain_pack", None):
        argv += ["--domain-pack", args.domain_pack]
        log.info("parse-fixtures: using domain pack %s", args.domain_pack)
    _call_func_with_argv(_rl_main, argv)


def _load_canonical_bundles(in_dir: str) -> list[dict[str, Any]]:
    p = Path(in_dir)
    if not p.exists():
        raise FileNotFoundError(f"Input directory not found: {in_dir}")
    bundles: list[dict[str, Any]] = []
    for f in sorted(p.glob("*.canonical.json")):
        try:
            bundles.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            continue
    return bundles


def _write_json(obj: Any, out_path: str) -> None:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_merge_canonical(args):
    in_dir = args.input or "fixtures/canonical"
    out_path = args.out or "fixtures/canonical_merged.json"
    bundles = _load_canonical_bundles(in_dir)
    _write_json(bundles, out_path)
    print(f"Loaded {len(bundles)} bundles from {in_dir}")
    print("WROTE:", out_path)


def _dedupe_bundles(bundles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mapping: dict[str, dict] = {}
    for b in bundles:
        refs = b.get("references") or []
        ref = refs[0] if refs else {}
        doi = (ref.get("doi") or "")
        if doi:
            key = f"doi:{doi.strip().lower()}"
        else:
            title = ref.get("title") or ""
            authors = ref.get("authors") or []
            if isinstance(authors, list):
                authors_str = ", ".join(str(a) for a in authors)
            else:
                authors_str = str(authors)
            # lazy import to avoid heavy imports at module load
            from notion_zotero.core.normalize import normalize_title, normalize_authors

            key = f"ta:{normalize_title(title)}|{normalize_authors(authors_str)}"

        if key in mapping:
            existing = mapping[key]
            score_new = len(b.get("task_extractions", [])) + len(b.get("annotations", [])) + len(b.get("tasks", []))
            score_existing = len(existing.get("task_extractions", [])) + len(existing.get("annotations", [])) + len(existing.get("tasks", []))
            if score_new > score_existing:
                mapping[key] = b
        else:
            mapping[key] = b

    return list(mapping.values())


def cmd_dedupe_canonical(args):
    in_path = args.input or "fixtures/canonical_merged.json"
    out_path = args.out or "fixtures/canonical_merged.dedup.json"
    p = Path(in_path)
    if not p.exists():
        raise FileNotFoundError(f"Input file not found: {in_path}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        data = [data]
    deduped = _dedupe_bundles(data)
    _write_json(deduped, out_path)
    print(f"Input bundles: {len(data)}; deduped: {len(deduped)}")
    print("WROTE:", out_path)


def cmd_list_domain_packs(args):
    from notion_zotero.schemas.task_registry import list_domain_packs
    packs = list_domain_packs()
    if not packs:
        print("No domain packs registered.")
        return
    print("Available domain packs:")
    for p in packs:
        print(f"  {p}")


def cmd_list_templates(args):
    from notion_zotero.schemas.templates.generic import TEMPLATES
    if not TEMPLATES:
        print("No templates registered.")
        return
    print("Available templates:")
    for tid, tmpl in TEMPLATES.items():
        print(f"  {tid}  —  {tmpl.display_name}")


def cmd_validate_fixtures(args):
    from notion_zotero.schemas.templates.generic import TEMPLATES
    from notion_zotero.schemas.task_registry import list_domain_packs
    in_dir = Path(args.input or "fixtures/canonical")
    if not in_dir.exists():
        print(f"Input directory not found: {in_dir}", file=sys.stderr)
        sys.exit(1)
    files = sorted(in_dir.glob("*.canonical.json"))
    if not files:
        print(f"No *.canonical.json files found in {in_dir}")
        return
    errors = 0
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                print(f"  WARN  {f.name}: root is not an object")
                errors += 1
            else:
                print(f"  OK    {f.name}")
        except Exception as exc:
            print(f"  ERROR {f.name}: {exc}")
            errors += 1
    log.info("validate-fixtures: %d files, %d errors", len(files), errors)
    if errors:
        sys.exit(1)


def cmd_zotero_citation(args):
    f = Path(args.file).resolve() if args.file else None
    if not f or not f.exists():
        raise FileNotFoundError(f"Zotero item file not found: {args.file}")
    data = json.loads(f.read_text(encoding="utf-8"))
    if isinstance(data, dict) and data.get("references"):
        item = data.get("references")[0]
    elif isinstance(data, list) and data and isinstance(data[0], dict) and data[0].get("references"):
        item = data[0].get("references")[0]
    else:
        item = data

    from notion_zotero.core.citation import citation_from_reference
    from notion_zotero.core.models import Reference

    # If item is a dict representing a Reference, convert to the dataclass
    if isinstance(item, dict):
        ref = Reference(**{k: v for k, v in item.items() if k in Reference.__annotations__})
    else:
        ref = item

    print(citation_from_reference(ref))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="notion-zotero")
    sub = parser.add_subparsers(dest="cmd")

    e = sub.add_parser("export-snapshot", help="Export a Notion database snapshot to JSON")
    e.add_argument("--out", default="fixtures/canonical_merged.json")
    e.add_argument("--db", default=None)
    e.set_defaults(func=cmd_export_snapshot)

    p = sub.add_parser("parse-fixtures", help="Parse local fixture JSONs into canonical files")
    p.add_argument("--input", default="fixtures/reading_list")
    p.add_argument("--out", default="fixtures/canonical")
    p.add_argument("--force", action="store_true")
    p.add_argument("--domain-pack", default=None, help="Domain pack ID to apply during parsing")
    p.set_defaults(func=cmd_parse_fixtures)

    m = sub.add_parser("merge-canonical", help="Merge per-page canonical JSONs into a single array")
    m.add_argument("--input", default="fixtures/canonical")
    m.add_argument("--out", default="fixtures/canonical_merged.json")
    m.set_defaults(func=cmd_merge_canonical)

    d = sub.add_parser("dedupe-canonical", help="Deduplicate a merged canonical JSON by DOI or title+authors")
    d.add_argument("--input", default="fixtures/canonical_merged.json")
    d.add_argument("--out", default="fixtures/canonical_merged.dedup.json")
    d.set_defaults(func=cmd_dedupe_canonical)

    z = sub.add_parser("zotero-citation", help="Print a human citation for a Zotero item or canonical bundle")
    z.add_argument("--file", required=True)
    z.set_defaults(func=cmd_zotero_citation)

    lp = sub.add_parser("list-domain-packs", help="List registered domain packs")
    lp.set_defaults(func=cmd_list_domain_packs)

    lt = sub.add_parser("list-templates", help="List registered extraction templates")
    lt.set_defaults(func=cmd_list_templates)

    vf = sub.add_parser("validate-fixtures", help="Validate canonical fixture JSON files")
    vf.add_argument("--input", default="fixtures/canonical")
    vf.set_defaults(func=cmd_validate_fixtures)

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
