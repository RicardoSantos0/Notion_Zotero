#!/usr/bin/env python3
"""CLI entrypoint for the notion_zotero package."""
from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
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
    log.info("loaded %d bundles from %s", len(bundles), in_dir)
    log.info("WROTE: %s", out_path)


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
    log.info("input bundles: %d; deduped: %d", len(data), len(deduped))
    log.info("WROTE: %s", out_path)


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

    if isinstance(item, dict):
        ref = Reference(**{k: v for k, v in item.items() if k in Reference.__annotations__})
    else:
        ref = item
    print(citation_from_reference(ref))


# ---------------------------------------------------------------------------
# Analysis reports (Sprint 2, M2-T2)
# ---------------------------------------------------------------------------

def cmd_report_by_year(args):
    from notion_zotero.services.flattener import flatten_bundles
    import polars as pl
    dfs = flatten_bundles(args.input or "fixtures/canonical")
    df = dfs["references"]
    if df.is_empty() or "year" not in df.columns:
        print("No references found.")
        return
    counts = (
        df.group_by("year").agg(pl.len().alias("count"))
        .sort("year", descending=True)
    )
    print(f"{'Year':<8} {'Count':>6}")
    print("-" * 16)
    for row in counts.iter_rows(named=True):
        print(f"{str(row['year']):<8} {row['count']:>6}")
    print(f"\nTotal: {len(df)} references")


def cmd_report_by_journal(args):
    from notion_zotero.services.flattener import flatten_bundles
    import polars as pl
    dfs = flatten_bundles(args.input or "fixtures/canonical")
    df = dfs["references"]
    if df.is_empty() or "journal" not in df.columns:
        print("No references found.")
        return
    counts = (
        df.filter(pl.col("journal").is_not_null())
        .group_by("journal").agg(pl.len().alias("count"))
        .sort("count", descending=True)
    )
    print(f"{'Journal':<60} {'Count':>6}")
    print("-" * 68)
    for row in counts.iter_rows(named=True):
        label = str(row["journal"])[:58]
        print(f"{label:<60} {row['count']:>6}")
    total_with = counts["count"].sum()
    print(f"\nTotal: {len(df)} references, {total_with} with journal")


def cmd_report_doi_coverage(args):
    from notion_zotero.services.flattener import flatten_bundles
    import polars as pl
    dfs = flatten_bundles(args.input or "fixtures/canonical")
    df = dfs["references"]
    if df.is_empty():
        print("No references found.")
        return
    total = len(df)
    with_doi = int(df.filter(pl.col("doi").is_not_null())["doi"].len()) if "doi" in df.columns else 0
    pct = (with_doi / total * 100) if total else 0
    print(f"Total references : {total}")
    print(f"With DOI         : {with_doi}")
    print(f"DOI coverage     : {pct:.1f}%")


def cmd_report_task_counts(args):
    from notion_zotero.services.flattener import flatten_bundles
    import polars as pl
    dfs = flatten_bundles(args.input or "fixtures/canonical")
    refs = dfs["references"]
    rts = dfs["reference_tasks"]
    exs = dfs["task_extractions"]
    print(f"References       : {len(refs)}")
    print(f"Reference-tasks  : {len(rts)}")
    if not exs.is_empty() and "template_id" in exs.columns:
        print("\nExtractions by template:")
        counts = (
            exs.with_columns(pl.col("template_id").fill_null("(none)"))
            .group_by("template_id").agg(pl.len().alias("count"))
            .sort("count", descending=True)
        )
        for row in counts.iter_rows(named=True):
            print(f"  {str(row['template_id']):<40} {row['count']:>5}")
    else:
        print("No task extractions found.")


def cmd_pull_zotero(args):
    from dotenv import load_dotenv
    load_dotenv()

    if getattr(args, "detect_library_id", False):
        import requests as _req
        api_key = os.environ.get("ZOTERO_API_KEY", "")
        resp = _req.get(f"https://api.zotero.org/keys/{api_key}", timeout=10)
        resp.raise_for_status()
        user_id = str(resp.json().get("userID", ""))
        print(f"Detected Zotero Library ID: {user_id}")
        confirm = input("Use this ID? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            sys.exit(0)
        os.environ["ZOTERO_LIBRARY_ID"] = user_id

    try:
        from notion_zotero.connectors.zotero.reader import ZoteroReader, ConfigurationError
    except ImportError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        reader = ZoteroReader()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    page_size = args.limit if args.limit is not None else 100
    try:
        items = reader.get_items(limit=page_size)
    except Exception as exc:
        print(f"Error fetching from Zotero: {exc}", file=sys.stderr)
        sys.exit(1)

    final_dir = Path(args.output or "data/pulled/zotero")
    staging_dir = final_dir.parent / (final_dir.name + "_staging")
    shutil.rmtree(staging_dir, ignore_errors=True)
    staging_dir.mkdir(parents=True, exist_ok=True)

    try:
        saved = 0
        total = len(items)
        for n, item in enumerate(items, start=1):
            try:
                ref = reader.to_reference(item)
            except Exception:
                continue
            bundle = {
                "references": [ref.model_dump()],
                "tasks": [],
                "reference_tasks": [],
                "task_extractions": [],
                "workflow_states": [],
                "annotations": [],
            }
            key = ref.zotero_key or ref.id
            out_file = staging_dir / f"{key}.canonical.json"
            out_file.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
            saved += 1
            if n % 50 == 0:
                print(f"  fetched page {n}/{total}...")
    except Exception:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise

    shutil.rmtree(final_dir, ignore_errors=True)
    shutil.move(str(staging_dir), str(final_dir))
    print(f"Pulled {saved} references from Zotero -> {final_dir}")


def cmd_pull_notion(args):
    from dotenv import load_dotenv
    load_dotenv()

    try:
        from notion_zotero.connectors.notion.reader import NotionReader, ConfigurationError
    except ImportError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    database_id = getattr(args, "database_id", None) or os.environ.get("NOTION_DATABASE_ID")
    if not database_id:
        print(
            "Error: Notion database ID required. Use --database-id or set NOTION_DATABASE_ID.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        reader = NotionReader()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        pages = reader.get_database_pages(database_id)
    except Exception as exc:
        print(f"Error fetching from Notion: {exc}", file=sys.stderr)
        sys.exit(1)

    final_dir = Path(args.output or "data/pulled/notion")
    staging_dir = final_dir.parent / (final_dir.name + "_staging")
    shutil.rmtree(staging_dir, ignore_errors=True)
    staging_dir.mkdir(parents=True, exist_ok=True)

    try:
        saved = 0
        total = len(pages)
        for n, page in enumerate(pages, start=1):
            try:
                ref = reader.to_reference(page)
            except Exception:
                continue
            bundle = {
                "references": [ref.model_dump()],
                "tasks": [],
                "reference_tasks": [],
                "task_extractions": [],
                "workflow_states": [],
                "annotations": [],
            }
            out_file = staging_dir / f"{ref.id}.canonical.json"
            out_file.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
            saved += 1
            if n % 50 == 0:
                print(f"  fetched page {n}/{total}...")
    except Exception:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise

    shutil.rmtree(final_dir, ignore_errors=True)
    shutil.move(str(staging_dir), str(final_dir))
    print(f"Pulled {saved} references from Notion -> {final_dir}")


def cmd_status(args):
    from dotenv import load_dotenv
    load_dotenv()

    import os
    from notion_zotero.connectors.zotero.reader import ZoteroReader
    from notion_zotero.connectors.notion.reader import NotionReader

    # Pull Zotero
    zotero_count = 0
    zotero_keys: set[str] = set()
    try:
        z_reader = ZoteroReader()
        limit = getattr(args, "zotero_limit", None) or 500
        items = z_reader.get_items(limit=limit)
        for item in items:
            try:
                ref = z_reader.to_reference(item)
                zotero_keys.add(ref.zotero_key or ref.id)
            except Exception:
                pass
        zotero_count = len(zotero_keys)
    except Exception as exc:
        print(f"Warning: could not reach Zotero: {exc}", file=sys.stderr)

    # Pull Notion
    notion_count = 0
    notion_keys: set[str] = set()
    database_id = getattr(args, "notion_database_id", None) or os.environ.get("NOTION_DATABASE_ID")
    if not database_id:
        print("Warning: NOTION_DATABASE_ID not set — skipping Notion.", file=sys.stderr)
    else:
        try:
            n_reader = NotionReader()
            pages = n_reader.get_database_pages(database_id)
            for page in pages:
                try:
                    ref = n_reader.to_reference(page)
                    notion_keys.add(ref.zotero_key if ref.zotero_key else ref.id)
                except Exception:
                    pass
            notion_count = len(notion_keys)
        except Exception as exc:
            print(f"Warning: could not reach Notion: {exc}", file=sys.stderr)

    matched = zotero_keys & notion_keys
    only_zotero = zotero_keys - notion_keys
    only_notion = notion_keys - zotero_keys

    print(f"Zotero library:   {zotero_count:>4} items")
    print(f"Notion database:  {notion_count:>4} pages")
    print()
    print(f"Matched (in both): {len(matched)}")
    print(f"Only in Zotero:    {len(only_zotero)}  (not yet synced to Notion)")
    print(f"Only in Notion:    {len(only_notion)}  (no Zotero key — manual entries or missing link)")
    print()
    print("Run 'notion-zotero pull-zotero' and 'notion-zotero pull-notion' to save locally.")
    print("Run 'notion-zotero report-by-year --input data/pulled/zotero' to analyse.")


def cmd_report_provenance(args):
    from notion_zotero.services.flattener import flatten_bundles
    dfs = flatten_bundles(args.input or "fixtures/canonical")
    required = ("source_id", "domain_pack_id", "domain_pack_version")
    totals: dict[str, int] = {}
    complete: dict[str, int] = {}
    for entity in ("references", "task_extractions", "workflow_states"):
        df = dfs[entity]
        if df.is_empty() or "provenance" not in df.columns:
            continue
        totals[entity] = len(df)
        ok = 0
        for prov_raw in df["provenance"].to_list():
            try:
                prov = json.loads(prov_raw) if isinstance(prov_raw, str) else (prov_raw or {})
            except Exception:
                prov = {}
            if all(prov.get(k) for k in required):
                ok += 1
        complete[entity] = ok
    if not totals:
        print("No provenance data found.")
        return
    print(f"{'Entity':<24} {'Complete':>9} {'Total':>7} {'Coverage':>10}")
    print("-" * 54)
    for entity in totals:
        t = totals[entity]
        c = complete.get(entity, 0)
        pct = (c / t * 100) if t else 0
        print(f"{entity:<24} {c:>9} {t:>7} {pct:>9.1f}%")


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

    ry = sub.add_parser("report-by-year", help="Reference counts by publication year")
    ry.add_argument("--input", default="fixtures/canonical")
    ry.set_defaults(func=cmd_report_by_year)

    rj = sub.add_parser("report-by-journal", help="Reference counts by journal/venue")
    rj.add_argument("--input", default="fixtures/canonical")
    rj.set_defaults(func=cmd_report_by_journal)

    rd = sub.add_parser("report-doi-coverage", help="DOI coverage rate across bundles")
    rd.add_argument("--input", default="fixtures/canonical")
    rd.set_defaults(func=cmd_report_doi_coverage)

    rt_p = sub.add_parser("report-task-counts", help="Tasks per reference and extractions per template")
    rt_p.add_argument("--input", default="fixtures/canonical")
    rt_p.set_defaults(func=cmd_report_task_counts)

    rp = sub.add_parser("report-provenance", help="Provenance completeness across bundles")
    rp.add_argument("--input", default="fixtures/canonical")
    rp.set_defaults(func=cmd_report_provenance)

    pz = sub.add_parser("pull-zotero", help="Pull items from Zotero and save as canonical bundles")
    pz.add_argument("--output", default=None, help="Output directory (default: data/pulled/zotero)")
    pz.add_argument("--limit", type=int, default=None, help="Page size for Zotero API (default: 100)")
    pz.add_argument("--detect-library-id", dest="detect_library_id", action="store_true",
                    help="Auto-detect ZOTERO_LIBRARY_ID from API key")
    pz.set_defaults(func=cmd_pull_zotero)

    pn = sub.add_parser("pull-notion", help="Pull pages from a Notion database and save as canonical bundles")
    pn.add_argument("--database-id", dest="database_id", default=None, help="Notion database ID")
    pn.add_argument("--output", default=None, help="Output directory (default: data/pulled/notion)")
    pn.set_defaults(func=cmd_pull_notion)

    st = sub.add_parser("status", help="Show sync status between Zotero and Notion")
    st.add_argument("--zotero-limit", dest="zotero_limit", type=int, default=None)
    st.add_argument("--notion-database-id", dest="notion_database_id", default=None)
    st.set_defaults(func=cmd_status)

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
