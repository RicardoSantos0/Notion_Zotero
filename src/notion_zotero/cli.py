#!/usr/bin/env python3
"""CLI entrypoint for the notion_zotero package."""
from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import time
import sys
from pathlib import Path
from typing import Any, Sequence

log = logging.getLogger(__name__)


def _load_dotenv_for_cli() -> None:
    """Load .env for normal CLI use, but not during pytest isolation."""
    if os.environ.get("PYTEST_CURRENT_TEST") and not os.environ.get("NOTION_ZOTERO_LOAD_DOTENV_IN_TESTS"):
        return
    from dotenv import load_dotenv
    load_dotenv()


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
    in_dir = args.input or "data/pulled/notion/learning_analytics_review"
    out_path = args.out or "data/pulled/notion/canonical_merged.json"
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
    in_path = args.input or "data/pulled/notion/canonical_merged.json"
    out_path = args.out or "data/pulled/notion/canonical_merged.dedup.json"
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
    in_dir = Path(args.input or "data/pulled/notion/learning_analytics_review")
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
    dfs = flatten_bundles(args.input or "data/pulled/notion/learning_analytics_review")
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
    dfs = flatten_bundles(args.input or "data/pulled/notion/learning_analytics_review")
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
    dfs = flatten_bundles(args.input or "data/pulled/notion/learning_analytics_review")
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
    dfs = flatten_bundles(args.input or "data/pulled/notion/learning_analytics_review")
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


def cmd_paper_summary_tables(args):
    from notion_zotero.analysis import run_analysis, task_label_fn, write_paper_summary_workbook

    _raw_dfs, clean_dfs, _norm_log = run_analysis(
        args.input or "data/pulled/notion/learning_analytics_review",
        task_label_fn=task_label_fn,
    )
    out_path = write_paper_summary_workbook(
        clean_dfs,
        args.out,
        include_title=not getattr(args, "no_title", False),
    )
    print(f"Paper summary workbook written: {out_path}")


def cmd_pull_zotero(args):
    _load_dotenv_for_cli()

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
        from notion_zotero.connectors.zotero.reader import ZoteroReader, ConfigurationError  # noqa: F401
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
    # If final_dir still exists after attempted removal, move staging to an alternate location
    if final_dir.exists():
        alt_name = getattr(args, "alt_output_name", None)
        if alt_name:
            alt_base = final_dir.parent / alt_name
            alt = alt_base
            i = 1
            while alt.exists():
                alt = final_dir.parent / f"{alt_name}_{i}"
                i += 1
        else:
            alt = final_dir.parent / f"{final_dir.name}_pulled_{int(time.time())}"
        shutil.move(str(staging_dir), str(alt))
        print(f"Pulled {saved} references from Zotero -> {alt} (final location {final_dir} contains conflicting data and was left in place)")
        return

    try:
        shutil.move(str(staging_dir), str(final_dir))
    except shutil.Error:
        # fallback: remove any nested conflict and retry once
        conflict = final_dir / staging_dir.name
        if conflict.exists():
            shutil.rmtree(conflict, ignore_errors=True)
        if conflict.exists():
            alt_name = getattr(args, "alt_output_name", None)
            if alt_name:
                alt_base = final_dir.parent / alt_name
                alt = alt_base
                i = 1
                while alt.exists():
                    alt = final_dir.parent / f"{alt_name}_{i}"
                    i += 1
            else:
                alt = final_dir.parent / f"{final_dir.name}_pulled_{int(time.time())}"
            shutil.move(str(staging_dir), str(alt))
            print(f"Pulled {saved} references from Zotero -> {alt} (final location {final_dir} contains conflicting data and was left in place)")
            return
        shutil.rmtree(final_dir, ignore_errors=True)
        shutil.move(str(staging_dir), str(final_dir))

    print(f"Pulled {saved} references from Zotero -> {final_dir}")


def _blocks_to_fixture_parts(blocks: list[dict], reader: Any) -> tuple[list[dict], list[dict]]:
    """Convert Notion block objects into fixture-format tables and text blocks.

    Returns a 2-tuple: (tables, text_blocks).

    - tables: list of dicts with keys ``heading``, ``rows`` (list of lists),
      ``block_id``
    - text_blocks: list of dicts with keys ``type``, ``text``, ``id``

    For ``table`` blocks the function fetches child rows via
    ``reader.get_page_blocks`` on the table block id.
    """
    tables: list[dict] = []
    text_blocks: list[dict] = []
    current_heading: str = ""

    for block in blocks:
        btype = block.get("type", "")

        if btype in ("heading_1", "heading_2", "heading_3"):
            content = block.get(btype, {})
            rt = content.get("rich_text", [])
            current_heading = "".join(r.get("plain_text", "") for r in rt)

        elif btype == "table":
            table_id = block.get("id", "")
            has_col_header = (block.get("table", {}) or {}).get("has_column_header", False)
            rows: list[list[str]] = []
            try:
                row_blocks = reader.get_page_blocks(table_id)
                for rb in row_blocks:
                    if rb.get("type") == "table_row":
                        cells = rb.get("table_row", {}).get("cells", [])
                        row = [
                            "".join(r.get("plain_text", "") for r in cell)
                            for cell in cells
                        ]
                        rows.append(row)
            except Exception:
                pass
            if rows:
                tables.append({
                    "heading": current_heading,
                    "rows": rows,
                    "block_id": table_id,
                    "has_column_header": has_col_header,
                })

        elif btype == "paragraph":
            content = block.get("paragraph", {})
            rt = content.get("rich_text", [])
            text = "".join(r.get("plain_text", "") for r in rt)
            if text:
                text_blocks.append({
                    "type": "paragraph",
                    "text": text,
                    "id": block.get("id", ""),
                })

    return tables, text_blocks


def cmd_pull_notion(args):
    _load_dotenv_for_cli()

    try:
        from notion_zotero.connectors.notion.reader import NotionReader, ConfigurationError  # noqa: F401
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

    skip_blocks: bool = getattr(args, "skip_blocks", False)

    # Fetch schema once before the page loop (used for generic property extraction)
    schema: dict | None = None
    if not skip_blocks:
        try:
            fetched = reader.get_database_schema(database_id)
            schema = fetched if fetched else None  # empty dict → None → legacy mapping path
        except Exception as exc:
            log.warning("Could not fetch database schema: %s -- falling back to hardcoded mapping", exc)

    try:
        pages = reader.get_database_pages(database_id)
    except Exception as exc:
        print(f"Error fetching from Notion: {exc}", file=sys.stderr)
        sys.exit(1)

    base_output = Path(args.output or "data/pulled/notion")
    if getattr(args, "pull_name", None):
        final_dir = base_output / args.pull_name
    else:
        final_dir = base_output
    staging_dir = final_dir.parent / (final_dir.name + "_staging")
    shutil.rmtree(staging_dir, ignore_errors=True)
    staging_dir.mkdir(parents=True, exist_ok=True)

    try:
        from notion_zotero.services.reading_list_importer import parse_fixture_from_dict
    except ImportError:
        parse_fixture_from_dict = None  # type: ignore[assignment]

    try:
        saved = 0
        total = len(pages)
        for n, page in enumerate(pages, start=1):
            try:
                ref = reader.to_reference(page, schema=schema)
            except Exception:
                continue

            page_id = page.get("id", ref.id)

            if skip_blocks or parse_fixture_from_dict is None:
                # Fast metadata-only pull: minimal bundle
                bundle = {
                    "references": [ref.model_dump()],
                    "tasks": [],
                    "reference_tasks": [],
                    "task_extractions": [],
                    "workflow_states": [],
                    "annotations": [],
                }
            else:
                # Full bundle: fetch blocks, parse tables, produce canonical bundle
                try:
                    blocks = reader.get_page_blocks(page_id)
                    tables, text_blocks = _blocks_to_fixture_parts(blocks, reader)
                except Exception:
                    blocks = []
                    tables = []
                    text_blocks = []

                fixture_dict = {
                    "page_id": page_id,
                    "title": ref.title or page_id,
                    "properties": page.get("properties", {}),
                    "tables": tables,
                    "blocks": text_blocks,
                }

                try:
                    _, bundle = parse_fixture_from_dict(fixture_dict)
                    # Merge sync_metadata sub-dicts from the schema-enriched ref into
                    # the bundle reference so extra Notion props are preserved.
                    if bundle.get("references"):
                        ref_sm = ref.sync_metadata or {}
                        existing_sm = bundle["references"][0].get("sync_metadata") or {}
                        for key in ("notion_properties", "domain_properties"):
                            val = ref_sm.get(key)
                            if val:
                                existing_sm[key] = val
                        bundle["references"][0]["sync_metadata"] = existing_sm
                except Exception:
                    # Fallback to minimal bundle on parse error
                    bundle = {
                        "references": [ref.model_dump()],
                        "tasks": [],
                        "reference_tasks": [],
                        "task_extractions": [],
                        "workflow_states": [],
                        "annotations": [],
                    }

            out_file = staging_dir / f"{ref.id}.canonical.json"
            staging_dir.mkdir(parents=True, exist_ok=True)  # OneDrive may evict the dir mid-pull
            out_file.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
            saved += 1
            if n % 50 == 0:
                print(f"  fetched page {n}/{total}...")
    except Exception:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise

    shutil.rmtree(final_dir, ignore_errors=True)
    # If final_dir still exists after attempted removal, move staging to an alternate location
    if final_dir.exists():
        alt_name = getattr(args, "alt_output_name", None)
        if alt_name:
            alt_base = final_dir.parent / alt_name
            alt = alt_base
            i = 1
            while alt.exists():
                alt = final_dir.parent / f"{alt_name}_{i}"
                i += 1
        else:
            alt = final_dir.parent / f"{final_dir.name}_pulled_{int(time.time())}"
        shutil.move(str(staging_dir), str(alt))
        print(f"Pulled {saved} references from Notion -> {alt} (final location {final_dir} contains conflicting data and was left in place)")
        return

    try:
        shutil.move(str(staging_dir), str(final_dir))
    except shutil.Error:
        # fallback: remove any nested conflict and retry once
        conflict = final_dir / staging_dir.name
        if conflict.exists():
            shutil.rmtree(conflict, ignore_errors=True)
        if conflict.exists():
            alt_name = getattr(args, "alt_output_name", None)
            if alt_name:
                alt_base = final_dir.parent / alt_name
                alt = alt_base
                i = 1
                while alt.exists():
                    alt = final_dir.parent / f"{alt_name}_{i}"
                    i += 1
            else:
                alt = final_dir.parent / f"{final_dir.name}_pulled_{int(time.time())}"
            shutil.move(str(staging_dir), str(alt))
            print(f"Pulled {saved} references from Notion -> {alt} (final location {final_dir} contains conflicting data and was left in place)")
            return
        shutil.rmtree(final_dir, ignore_errors=True)
        shutil.move(str(staging_dir), str(final_dir))

    print(f"Pulled {saved} references from Notion -> {final_dir}")


def cmd_status(args):
    _load_dotenv_for_cli()

    import os
    from notion_zotero.connectors.zotero.reader import ZoteroReader
    from notion_zotero.connectors.notion.reader import NotionReader
    from notion_zotero.services.sync_planner import compare_references

    # Pull Zotero
    zotero_refs: list[dict[str, Any]] = []
    try:
        z_reader = ZoteroReader()
        limit = getattr(args, "zotero_limit", None) or 500
        items = z_reader.get_items(limit=limit)
        for item in items:
            try:
                ref = z_reader.to_reference(item)
                zotero_refs.append(ref.model_dump())
            except Exception:
                pass
    except Exception as exc:
        print(f"Warning: could not reach Zotero: {exc}", file=sys.stderr)

    # Pull Notion
    notion_refs: list[dict[str, Any]] = []
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
                    notion_refs.append(ref.model_dump())
                except Exception:
                    pass
        except Exception as exc:
            print(f"Warning: could not reach Notion: {exc}", file=sys.stderr)

    summary = compare_references(notion_refs, zotero_refs)["summary"]

    print(f"Zotero library:   {len(zotero_refs):>4} items")
    print(f"Notion database:  {len(notion_refs):>4} pages")
    print()
    print(f"Matched (in both): {summary['matched']}")
    print(f"Only in Zotero:    {summary['only_zotero']}  (not yet synced to Notion)")
    print(f"Only in Notion:    {summary['only_notion']}  (no Zotero key — manual entries or missing link)")
    print(f"Ambiguous matches: {summary['ambiguous']}  (review duplicate candidate matches)")
    print()
    print("Run 'notion-zotero pull-zotero' and 'notion-zotero pull-notion' to save locally.")
    print("Run 'notion-zotero report-by-year --input data/pulled/zotero' to analyse.")


def cmd_diff(args):
    from notion_zotero.services.diff_engine import diff_dirs
    reports = diff_dirs(Path(args.baseline), Path(args.updated))
    for report in reports:
        print(report.summary())
    print(f"Total: {len(reports)} bundle(s) compared.")


def cmd_plan_sync(args):
    from notion_zotero.services.sync_planner import build_sync_plan, write_sync_plan

    plan = build_sync_plan(args.notion_dir, args.zotero_dir)
    output_path = write_sync_plan(plan, args.out)
    summary = plan["summary"]

    print(f"Sync plan written: {output_path}")
    print(
        "Plan summary: "
        f"{summary['matched']} matched, "
        f"{summary['operations']} operation(s), "
        f"{summary['only_zotero']} only in Zotero, "
        f"{summary['only_notion']} only in Notion, "
        f"{summary['ambiguous']} ambiguous."
    )


def cmd_review_plan(args):
    from notion_zotero.core.sync_plan_models import SyncPlanValidationError
    from notion_zotero.services.sync_plan_report import write_sync_plan_report_from_file

    try:
        output_path = write_sync_plan_report_from_file(args.plan, args.out, max_rows=args.max_rows)
    except SyncPlanValidationError as exc:
        print(f"Error: invalid sync plan: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"Sync plan review written: {output_path}")


def cmd_apply_plan(args):
    _load_dotenv_for_cli()

    from notion_zotero.core.sync_plan_models import SyncPlanValidationError
    from notion_zotero.services.sync_plan_applier import apply_sync_plan

    plan_path = Path(args.plan)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    if args.apply:
        notion_api_key = os.environ.get("NOTION_API_KEY")
        if not notion_api_key:
            print("Error: NOTION_API_KEY is required for apply-plan --apply", file=sys.stderr)
            sys.exit(1)
        from notion_zotero.connectors.notion.client import NotionClientAdapter
        from notion_zotero.connectors.notion.reader import NotionReader
        from notion_zotero.writers.notion_properties import build_property_schema_from_notion_schema
        from notion_zotero.writers.write_log import WriteLog

        property_schema = None
        database_id = getattr(args, "notion_database_id", None) or os.environ.get("NOTION_DATABASE_ID")
        existing_notion_titles: set[str] = set()
        if database_id:
            try:
                notion_reader = NotionReader(api_key=notion_api_key)
                notion_schema = notion_reader.get_database_schema(database_id)
                property_schema = build_property_schema_from_notion_schema(notion_schema)
                if getattr(args, "include_reviewed_creates", False):
                    for page in notion_reader.get_database_pages(database_id):
                        try:
                            ref = notion_reader.to_reference(page, schema=notion_schema)
                            if ref.title:
                                existing_notion_titles.add(ref.title)
                        except Exception:
                            continue
            except Exception as exc:
                print(f"Error: could not fetch Notion database schema: {exc}", file=sys.stderr)
                sys.exit(1)

        from notion_zotero.services.sync_lock import SyncLock, SyncLockHeld
        try:
            with SyncLock(args.write_log_dir).acquire():
                write_log = WriteLog(session_id=f"apply-plan-{int(time.time())}", log_dir=args.write_log_dir)
                notion_client = NotionClientAdapter(notion_api_key)
                try:
                    ops = apply_sync_plan(
                        plan,
                        dry_run=False,
                        notion_client=notion_client,
                        write_log=write_log,
                        property_schema=property_schema,
                        include_reviewed_creates=getattr(args, "include_reviewed_creates", False),
                        notion_database_id=database_id,
                        existing_notion_titles=existing_notion_titles,
                    )
                except (SyncPlanValidationError, ValueError) as exc:
                    print(f"Error: invalid sync plan: {exc}", file=sys.stderr)
                    sys.exit(1)
                print(f"[APPLY MODE] Applied {len(ops)} operation(s) from {plan_path}.")
                print(f"Write log directory: {args.write_log_dir}")
                return
        except SyncLockHeld as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)

    try:
        ops = apply_sync_plan(
            plan,
            dry_run=True,
            include_reviewed_creates=getattr(args, "include_reviewed_creates", False),
            notion_database_id=getattr(args, "notion_database_id", None) or os.environ.get("NOTION_DATABASE_ID"),
        )
    except (SyncPlanValidationError, ValueError) as exc:
        print(f"Error: invalid sync plan: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"[DRY-RUN] Planned {len(ops)} executable operation(s) from {plan_path}.")
    for op in ops:
        print(op)


def cmd_rollback_plan(args):
    from notion_zotero.services.rollback_planner import build_rollback_plan, write_rollback_plan

    plan = build_rollback_plan(args.write_log_dir, session_id=args.session_id)
    output_path = write_rollback_plan(plan, args.out)
    summary = plan["summary"]

    print(f"Rollback plan written: {output_path}")
    print(
        "Plan summary: "
        f"{summary['rollback_operations']} rollback operation(s), "
        f"{summary['skipped']} skipped, "
        f"{summary['applied_entries']} applied log entry(s), "
        f"{summary['sessions']} session(s)."
    )


def _current_values_for_rollback_operations(args, plan, notion_api_key: str):
    from notion_zotero.connectors.notion.reader import NotionReader
    from notion_zotero.writers.notion_properties import build_property_schema_from_notion_schema

    database_id = getattr(args, "notion_database_id", None) or os.environ.get("NOTION_DATABASE_ID")
    notion_reader = NotionReader(api_key=notion_api_key)
    notion_schema = None
    property_schema = None
    if database_id:
        notion_schema = notion_reader.get_database_schema(database_id)
        property_schema = build_property_schema_from_notion_schema(notion_schema)

    current_values: dict[str, dict[str, Any]] = {}
    for operation in plan.get("operations") or []:
        page_id = str(operation.get("notion_reference_id") or "")
        field = str(operation.get("field") or "")
        if not page_id or not field:
            continue
        page = notion_reader.get_page(page_id)
        ref = notion_reader.to_reference(page, schema=notion_schema)
        current_values.setdefault(page_id, {})[field] = getattr(ref, field, None)

    return current_values, property_schema


def cmd_apply_rollback_plan(args):
    _load_dotenv_for_cli()

    from notion_zotero.services.rollback_applier import (
        RollbackPlanValidationError,
        apply_rollback_plan,
    )

    plan_path = Path(args.plan)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    if args.apply:
        notion_api_key = os.environ.get("NOTION_API_KEY")
        if not notion_api_key:
            print("Error: NOTION_API_KEY is required for apply-rollback-plan --apply", file=sys.stderr)
            sys.exit(1)
        from notion_zotero.connectors.notion.client import NotionClientAdapter
        from notion_zotero.writers.write_log import WriteLog

        try:
            current_values, property_schema = _current_values_for_rollback_operations(args, plan, notion_api_key)
        except Exception as exc:
            print(f"Error: could not fetch current Notion values: {exc}", file=sys.stderr)
            sys.exit(1)

        from notion_zotero.services.sync_lock import SyncLock, SyncLockHeld
        try:
            with SyncLock(args.write_log_dir).acquire():
                write_log = WriteLog(session_id=f"apply-rollback-{int(time.time())}", log_dir=args.write_log_dir)
                notion_client = NotionClientAdapter(notion_api_key)
                try:
                    ops = apply_rollback_plan(
                        plan,
                        dry_run=False,
                        notion_client=notion_client,
                        write_log=write_log,
                        property_schema=property_schema,
                        current_values=current_values,
                    )
                except (RollbackPlanValidationError, ValueError) as exc:
                    print(f"Error: invalid rollback plan: {exc}", file=sys.stderr)
                    sys.exit(1)
                print(f"[APPLY MODE] Applied {len(ops)} rollback operation(s) from {plan_path}.")
                print(f"Write log directory: {args.write_log_dir}")
                return
        except SyncLockHeld as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)

    try:
        ops = apply_rollback_plan(plan, dry_run=True)
    except RollbackPlanValidationError as exc:
        print(f"Error: invalid rollback plan: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"[DRY-RUN] Planned {len(ops)} rollback operation(s) from {plan_path}.")
    for op in ops:
        print(op)


def cmd_sync(args):
    _load_dotenv_for_cli()

    from pathlib import Path as _Path
    from notion_zotero.services.diff_engine import diff_dirs
    from notion_zotero.writers.notion_writer import NotionWriter
    from notion_zotero.writers.zotero_writer import ZoteroWriter
    from notion_zotero.core.models import Reference

    notion_dir = getattr(args, "notion_dir", None) or "data/pulled/notion"
    zotero_dir = getattr(args, "zotero_dir", None) or "data/pulled/zotero"  # noqa: F841
    baseline_dir = getattr(args, "baseline_dir", None) or "data/sync_baseline"
    apply = getattr(args, "apply", False)

    if apply:
        print("[APPLY MODE] Writing changes to live APIs.")
        notion_api_key = os.environ.get("NOTION_API_KEY")
        zotero_api_key = os.environ.get("ZOTERO_API_KEY")
        zotero_library_id = os.environ.get("ZOTERO_LIBRARY_ID")
        missing = [k for k, v in [
            ("NOTION_API_KEY", notion_api_key),
            ("ZOTERO_API_KEY", zotero_api_key),
            ("ZOTERO_LIBRARY_ID", zotero_library_id),
        ] if not v]
        if missing:
            print(f"Error: missing required env vars for apply mode: {', '.join(missing)}", file=sys.stderr)
            sys.exit(1)

        from notion_zotero.connectors.notion.client import NotionClientAdapter
        from notion_zotero.connectors.zotero.client import ZoteroClientAdapter
        from notion_zotero.writers.write_log import WriteLog
        write_log = WriteLog(session_id=f"sync-{int(time.time())}", log_dir=args.write_log_dir)
        notion_client = NotionClientAdapter(notion_api_key)
        zotero_client = ZoteroClientAdapter(zotero_api_key, zotero_library_id)
        notion_writer = NotionWriter(dry_run=False, client=notion_client, write_log=write_log)
        zotero_writer = ZoteroWriter(dry_run=False, client=zotero_client, write_log=write_log)
    else:
        print("[DRY-RUN] sync")
        notion_writer = NotionWriter(dry_run=True, write_log=None)
        zotero_writer = ZoteroWriter(dry_run=True, write_log=None)

    baseline_path = _Path(baseline_dir)
    notion_path = _Path(notion_dir)

    if not baseline_path.exists():
        baseline_path.mkdir(parents=True, exist_ok=True)

    reports = diff_dirs(baseline_path, notion_path)

    total_ops = 0
    for report in reports:
        ref = Reference(id=report.bundle_id)
        ops = notion_writer.write_reference(ref, report)
        ops += zotero_writer.write_reference(ref, report)
        total_ops += len(ops)

    if apply:
        staging = _Path(baseline_dir + "_staging")
        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True, exist_ok=True)
        for f in sorted(notion_path.glob("*.canonical.json")):
            shutil.copy2(str(f), str(staging / f.name))
        shutil.rmtree(baseline_path, ignore_errors=True)
        shutil.move(str(staging), str(baseline_path))

    mode_word = "applied" if apply else "planned"
    print(f"Sync complete: {len(reports)} bundle(s) processed, {total_ops} operation(s) {mode_word}.")


def cmd_report_provenance(args):
    from notion_zotero.services.flattener import flatten_bundles
    dfs = flatten_bundles(args.input or "data/pulled/notion/learning_analytics_review")
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


def _read_write_log_entries(log_dir: str) -> list[dict]:
    """Read all write-log NDJSON entries under *log_dir* (read-only; no side effects)."""
    d = Path(log_dir)
    entries: list[dict] = []
    if not d.exists():
        return entries
    for f in sorted(d.glob("write_log_*.ndjson")):
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    continue
    return entries


def _snapshot_age_days(in_dir: str) -> float | None:
    """Age in days of the newest canonical snapshot file in *in_dir*, or None."""
    import time
    p = Path(in_dir)
    files = list(p.glob("*.canonical.json")) if p.exists() else []
    if not files:
        return None
    newest = max(f.stat().st_mtime for f in files)
    return round((time.time() - newest) / 86400, 2)


def cmd_mvp_health(args):
    """Produce the MVP reference-health report (JSON + Markdown). Read-only."""
    from notion_zotero.analysis import mvp_health
    in_dir = args.input or "data/pulled/notion/learning_analytics_review"
    bundles = _load_canonical_bundles(in_dir) if Path(in_dir).exists() else []
    entries = _read_write_log_entries(args.write_log_dir or "logs/write_logs")
    rollback_available = any(e.get("status") in ("applied", "succeeded") for e in entries)
    report = mvp_health.build_health_report(
        bundles,
        snapshot_age_days=_snapshot_age_days(in_dir),
        write_log_entries=entries,
        rollback_available=rollback_available,
    )
    out_json = args.out_json or "data/sync_plans/mvp_health.json"
    out_md = args.out_md or "data/sync_plans/mvp_health.md"
    Path(out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(out_json).write_text(mvp_health.render_json(report), encoding="utf-8")
    Path(out_md).parent.mkdir(parents=True, exist_ok=True)
    Path(out_md).write_text(mvp_health.render_markdown(report), encoding="utf-8")
    print(f"Total records          : {report['total_records']}")
    print(f"Duplicate candidates   : {len(report['duplicate_candidates'])}")
    print(f"Source-only records    : {len(report['source_only_records'])}")
    print(f"Planned/failed writes  : {len(report['pending_or_failed_writes'])}")
    print(f"Snapshot age (days)    : {report['stale_snapshot_age_days']}")
    print(f"Wrote {out_json} and {out_md}")


def cmd_replay_log(args):
    """Replay planned/failed write-log entries. Dry-run by default; --apply guards with the sync lock."""
    from notion_zotero.services.write_log_replay import plan_replay
    log_dir = args.write_log_dir or "logs/write_logs"
    entries = _read_write_log_entries(log_dir)
    result = plan_replay(entries, apply=args.apply)
    print(f"Replay candidates (planned/failed): {result['count']}")
    for c in result["candidates"][: getattr(args, "max_rows", 25)]:
        print(f"  {c.get('operation_id')} [{c.get('status')}] "
              f"{c.get('entity_type')}:{c.get('entity_id')} {c.get('field')}")
    if not args.apply:
        print("(dry-run; pass --apply to re-execute under the sync lock)")
        return 0
    from notion_zotero.services.sync_lock import SyncLock, SyncLockHeld
    try:
        with SyncLock(log_dir).acquire():
            print(f"[APPLY MODE] Sync lock acquired; {result['count']} entr(ies) eligible for replay.")
            print("Re-execution reuses the apply-plan writer path (requires NOTION_API_KEY); "
                  "no live writes performed in this invocation.")
    except SyncLockHeld as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    from notion_zotero.core.config import ConfigError, config_get, load_project_config

    early = argparse.ArgumentParser(add_help=False)
    early.add_argument("--config", default=None, help="Path to notion_zotero JSON project config")
    early_args, _ = early.parse_known_args(argv)
    try:
        project_config = load_project_config(early_args.config)
    except ConfigError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    def cfg(key: str, default: Any = None) -> Any:
        return config_get(project_config, key, default)

    parser = argparse.ArgumentParser(prog="notion-zotero", parents=[early])
    sub = parser.add_subparsers(dest="cmd")

    e = sub.add_parser("export-snapshot", help="Export a Notion database snapshot to JSON")
    e.add_argument("--out", default=cfg("paths.canonical_merged", "data/pulled/notion/canonical_merged.json"))
    e.add_argument("--db", default=cfg("notion.database_id"))
    e.set_defaults(func=cmd_export_snapshot)

    p = sub.add_parser("parse-fixtures", help="Parse local fixture JSONs into canonical files")
    p.add_argument("--input", default=cfg("paths.raw_notion_dir", "data/raw/notion"))
    p.add_argument("--out", default=cfg("paths.notion_review_dir", "data/pulled/notion/learning_analytics_review"))
    p.add_argument("--force", action="store_true")
    p.add_argument("--domain-pack", default=cfg("domain_pack"), help="Domain pack ID to apply during parsing")
    p.set_defaults(func=cmd_parse_fixtures)

    m = sub.add_parser("merge-canonical", help="Merge per-page canonical JSONs into a single array")
    m.add_argument("--input", default=cfg("paths.notion_review_dir", "data/pulled/notion/learning_analytics_review"))
    m.add_argument("--out", default=cfg("paths.canonical_merged", "data/pulled/notion/canonical_merged.json"))
    m.set_defaults(func=cmd_merge_canonical)

    d = sub.add_parser("dedupe-canonical", help="Deduplicate a merged canonical JSON by DOI or title+authors")
    d.add_argument("--input", default=cfg("paths.canonical_merged", "data/pulled/notion/canonical_merged.json"))
    d.add_argument("--out", default=cfg("paths.canonical_deduped", "data/pulled/notion/canonical_merged.dedup.json"))
    d.set_defaults(func=cmd_dedupe_canonical)

    z = sub.add_parser("zotero-citation", help="Print a human citation for a Zotero item or canonical bundle")
    z.add_argument("--file", required=True)
    z.set_defaults(func=cmd_zotero_citation)

    lp = sub.add_parser("list-domain-packs", help="List registered domain packs")
    lp.set_defaults(func=cmd_list_domain_packs)

    lt = sub.add_parser("list-templates", help="List registered extraction templates")
    lt.set_defaults(func=cmd_list_templates)

    vf = sub.add_parser("validate-fixtures", help="Validate canonical fixture JSON files")
    vf.add_argument("--input", default=cfg("paths.notion_review_dir", "data/pulled/notion/learning_analytics_review"))
    vf.set_defaults(func=cmd_validate_fixtures)

    ry = sub.add_parser("report-by-year", help="Reference counts by publication year")
    ry.add_argument("--input", default=cfg("paths.notion_review_dir", "data/pulled/notion/learning_analytics_review"))
    ry.set_defaults(func=cmd_report_by_year)

    rj = sub.add_parser("report-by-journal", help="Reference counts by journal/venue")
    rj.add_argument("--input", default=cfg("paths.notion_review_dir", "data/pulled/notion/learning_analytics_review"))
    rj.set_defaults(func=cmd_report_by_journal)

    rd = sub.add_parser("report-doi-coverage", help="DOI coverage rate across bundles")
    rd.add_argument("--input", default=cfg("paths.notion_review_dir", "data/pulled/notion/learning_analytics_review"))
    rd.set_defaults(func=cmd_report_doi_coverage)

    rt_p = sub.add_parser("report-task-counts", help="Tasks per reference and extractions per template")
    rt_p.add_argument("--input", default=cfg("paths.notion_review_dir", "data/pulled/notion/learning_analytics_review"))
    rt_p.set_defaults(func=cmd_report_task_counts)

    pst = sub.add_parser("paper-summary-tables", help="Write manuscript-oriented task summary workbook")
    pst.add_argument("--input", default=cfg("paths.notion_review_dir", "data/pulled/notion/learning_analytics_review"))
    pst.add_argument("--out", default=cfg("paths.paper_summary_workbook", "data/analysis_outputs/paper_task_summary_tables.xlsx"))
    pst.add_argument("--no-title", action="store_true", default=False,
                     help="Omit Paper title column from task sheets")
    pst.set_defaults(func=cmd_paper_summary_tables)

    rp = sub.add_parser("report-provenance", help="Provenance completeness across bundles")
    rp.add_argument("--input", default=cfg("paths.notion_review_dir", "data/pulled/notion/learning_analytics_review"))
    rp.set_defaults(func=cmd_report_provenance)

    mh = sub.add_parser("mvp-health", help="Reference-health report (completeness, duplicates, source-only, writes) as JSON+Markdown")
    mh.add_argument("--input", default=cfg("paths.notion_review_dir", "data/pulled/notion/learning_analytics_review"))
    mh.add_argument("--write-log-dir", dest="write_log_dir", default=cfg("paths.write_log_dir", "logs/write_logs"))
    mh.add_argument("--out-json", dest="out_json", default="data/sync_plans/mvp_health.json")
    mh.add_argument("--out-md", dest="out_md", default="data/sync_plans/mvp_health.md")
    mh.set_defaults(func=cmd_mvp_health)

    rl = sub.add_parser("replay-log", help="Replay planned/failed write-log entries (dry-run default; --apply guards with the sync lock)")
    rl.add_argument("--write-log-dir", dest="write_log_dir", default=cfg("paths.write_log_dir", "logs/write_logs"))
    rl.add_argument("--apply", action="store_true", default=False)
    rl.add_argument("--max-rows", dest="max_rows", type=int, default=25)
    rl.set_defaults(func=cmd_replay_log)

    pz = sub.add_parser("pull-zotero", help="Pull items from Zotero and save as canonical bundles")
    pz.add_argument("--output", default=cfg("paths.zotero_dir"), help="Output directory (default: data/pulled/zotero)")
    pz.add_argument("--limit", type=int, default=cfg("zotero.limit"), help="Page size for Zotero API (default: 100)")
    pz.add_argument("--detect-library-id", dest="detect_library_id", action="store_true",
                    help="Auto-detect ZOTERO_LIBRARY_ID from API key")
    pz.add_argument("--alt-output-name", dest="alt_output_name", default=None,
                    help="Alternate folder name to use if the final target conflicts (e.g. mypull)")
    pz.set_defaults(func=cmd_pull_zotero)

    pn = sub.add_parser("pull-notion", help="Pull pages from a Notion database and save as canonical bundles")
    pn.add_argument("--database-id", dest="database_id", default=cfg("notion.database_id"), help="Notion database ID")
    pn.add_argument("--output", default=cfg("paths.notion_pull_root", "data/pulled/notion"), help="Output directory (default: data/pulled/notion)")
    pn.add_argument("--name", dest="pull_name", default=cfg("notion.pull_name"), help="Subfolder name under output to store this pull (e.g. learning_analytics_review)")
    pn.add_argument("--alt-output-name", dest="alt_output_name", default=None,
                    help="Alternate folder name to use if the final target conflicts (e.g. mypull)")
    pn.add_argument("--skip-blocks", dest="skip_blocks", action="store_true",
                    help="Skip block/table fetching and produce minimal metadata-only bundles (faster)")
    pn.set_defaults(func=cmd_pull_notion)

    df = sub.add_parser("diff", help="Diff two canonical bundle directories")
    df.add_argument("--baseline", required=True)
    df.add_argument("--updated", required=True)
    df.set_defaults(func=cmd_diff)

    ps = sub.add_parser("plan-sync", help="Build a read-only sync plan from local Notion and Zotero snapshots")
    ps.add_argument("--notion-dir", dest="notion_dir", default=cfg("paths.notion_review_dir", "data/pulled/notion/learning_analytics_review"))
    ps.add_argument("--zotero-dir", dest="zotero_dir", default=cfg("paths.zotero_dir", "data/pulled/zotero"))
    ps.add_argument("--out", default=cfg("paths.sync_plan", "data/sync_plans/sync_plan.json"))
    ps.set_defaults(func=cmd_plan_sync)

    rv = sub.add_parser("review-plan", help="Write a Markdown review report from a sync plan")
    rv.add_argument("--plan", default=cfg("paths.sync_plan", "data/sync_plans/sync_plan.json"))
    rv.add_argument("--out", default=cfg("paths.sync_plan_review", "data/sync_plans/sync_plan_review.md"))
    rv.add_argument("--max-rows", dest="max_rows", type=int, default=cfg("reports.max_rows", 25))
    rv.set_defaults(func=cmd_review_plan)

    ap = sub.add_parser("apply-plan", help="Dry-run or apply a reviewed sync plan")
    ap.add_argument("--plan", default=cfg("paths.sync_plan", "data/sync_plans/sync_plan.json"))
    ap.add_argument("--apply", action="store_true", default=False)
    ap.add_argument("--write-log-dir", dest="write_log_dir", default=cfg("paths.write_log_dir", "logs/write_logs"))
    ap.add_argument("--notion-database-id", dest="notion_database_id", default=cfg("notion.database_id"),
                    help="Fetch live Notion database schema for property names/types in apply mode")
    ap.add_argument("--include-reviewed-creates", dest="include_reviewed_creates",
                    action="store_true", default=bool(cfg("sync.include_reviewed_creates", False)),
                    help="Apply approved create_notion_page_from_zotero_record review actions")
    ap.set_defaults(func=cmd_apply_plan)

    rb = sub.add_parser("rollback-plan", help="Build a review-only rollback plan from write logs")
    rb.add_argument("--write-log-dir", dest="write_log_dir", default=cfg("paths.write_log_dir", "logs/write_logs"))
    rb.add_argument("--out", default=cfg("paths.rollback_plan", "data/sync_plans/rollback_plan.json"))
    rb.add_argument("--session-id", dest="session_id", default=None,
                    help="Limit rollback planning to a single write-log session")
    rb.set_defaults(func=cmd_rollback_plan)

    arb = sub.add_parser("apply-rollback-plan", help="Dry-run or apply a reviewed rollback plan")
    arb.add_argument("--plan", default=cfg("paths.rollback_plan", "data/sync_plans/rollback_plan.json"))
    arb.add_argument("--apply", action="store_true", default=False)
    arb.add_argument("--write-log-dir", dest="write_log_dir", default=cfg("paths.write_log_dir", "logs/write_logs"))
    arb.add_argument("--notion-database-id", dest="notion_database_id", default=cfg("notion.database_id"),
                     help="Fetch live Notion database schema for rollback value checks and writes")
    arb.set_defaults(func=cmd_apply_rollback_plan)

    sy = sub.add_parser("sync", help="Sync canonical bundles to Notion and Zotero")
    sy.add_argument("--notion-dir", dest="notion_dir", default=cfg("paths.notion_pull_root", "data/pulled/notion"))
    sy.add_argument("--zotero-dir", dest="zotero_dir", default=cfg("paths.zotero_dir", "data/pulled/zotero"))
    sy.add_argument("--baseline-dir", dest="baseline_dir", default=cfg("paths.sync_baseline", "data/sync_baseline"))
    sy.add_argument("--write-log-dir", dest="write_log_dir", default=cfg("paths.write_log_dir", "logs/write_logs"))
    sy.add_argument("--apply", action="store_true", default=False)
    sy.set_defaults(func=cmd_sync)

    st = sub.add_parser("status", help="Show sync status between Zotero and Notion")
    st.add_argument("--zotero-limit", dest="zotero_limit", type=int, default=cfg("zotero.status_limit"))
    st.add_argument("--notion-database-id", dest="notion_database_id", default=cfg("notion.database_id"))
    st.set_defaults(func=cmd_status)

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
