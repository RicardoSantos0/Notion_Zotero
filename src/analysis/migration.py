"""migration.py — migration helpers for internal analysis DB writes.

These are thin shims used by the importer to persist intermediate migration
metadata when running local testing or dry-runs.
"""

from __future__ import annotations

from typing import Any


def mark_migration_version(record: dict, version: int) -> dict:
    record = dict(record)
    record["migration_version"] = int(version)
    return record


def needs_migration(record: dict, target_version: int) -> bool:
    return int(record.get("migration_version", 0)) < int(target_version)

    resolved_database_id = _resolve_required_id(
        database_id or NOTION_PAPER_SUMMARIES_DB_ID,
        "NOTION_PAPER_SUMMARIES_DB_ID not set in .env or passed as argument",
    )

    client = get_notion_client()
    if hasattr(summaries_df, "to_dict") and hasattr(summaries_df, "columns"):
        prepared_df = summaries_df.fillna("")
    else:
        prepared_df = extract_summaries_to_paper_summaries_db(summaries_df)

    data_source_id = _get_platform_ds_id(client, resolved_database_id)

    schema_properties: dict[str, Any] = {}
    if data_source_id:
        data_source = _call_with_retry(
            f"data_sources.retrieve({data_source_id})",
            lambda: client.data_sources.retrieve(data_source_id=data_source_id),
        )
        schema_properties = data_source.get("properties") or {}

    key_map = _build_property_key_map(schema_properties)
    summary_row_id_key = key_map.get("Summary Row ID", "Summary Row ID")
    relation_key = key_map.get("Paper", "Paper")

    existing_ids: set[str] = set()
    if data_source_id:
        existing_ids = _collect_existing_title_values(client, data_source_id, summary_row_id_key)

    records = prepared_df.to_dict("records")
    if max_rows is not None:
        records = records[:max_rows]

    created = 0
    skipped_existing = 0
    missing_paper_relation = 0
    failures: list[dict[str, Any]] = []

    for index, row in enumerate(records):
        summary_row_id = str(row.get("Summary Row ID", "")).strip()
        if not summary_row_id:
            failures.append(
                {
                    "row_index": index,
                    "error": "missing Summary Row ID",
                    "cause": None,
                }
            )
            continue

        if summary_row_id in existing_ids:
            skipped_existing += 1
            continue

        paper_name = str(row.get("Paper Name", "")).strip()
        paper_page_id = paper_title_to_id.get(paper_name)
        if not paper_page_id:
            missing_paper_relation += 1
            failures.append(
                {
                    "row_index": index,
                    "error": f"paper relation not found for '{paper_name}'",
                    "cause": None,
                }
            )
            continue

        try:
            row_for_props = dict(row)
            row_for_props.pop("Last Edited By", None)
            properties = _build_page_properties_from_row(
                row_for_props,
                title_column="Summary Row ID",
                select_columns={"Task Type"},
                date_columns={"Last Modified"},
            )
            properties[relation_key] = {"relation": [{"id": paper_page_id}]}
            properties = _remap_properties_to_schema_keys(properties, key_map)

            _call_with_retry(
                f"pages.create(summary_row={summary_row_id})",
                lambda: client.pages.create(
                    parent={"data_source_id": data_source_id} if data_source_id else {"database_id": resolved_database_id},
                    properties=properties,
                ),
            )
            created += 1
            existing_ids.add(summary_row_id)
        except Exception as exc:
            cause = getattr(exc, "__cause__", None)
            failures.append(
                {
                    "row_index": index,
                    "error": str(exc),
                    "cause": str(cause) if cause else None,
                }
            )

    return {
        "created": created,
        "skipped_existing": skipped_existing,
        "missing_paper_relation": missing_paper_relation,
        "failed": len(failures),
        "data_source_id": data_source_id,
        "failures": failures,
    }


def import_dataframe_to_notion_database(
    database_id: str,
    dataframe,
    *,
    title_column: str,
    data_source_id: str | None = None,
    select_columns: set[str] | None = None,
    date_columns: set[str] | None = None,
    max_rows: int | None = None,
    skip_existing_by_title: bool = False,
) -> dict[str, Any]:
    """Import dataframe rows into a Notion database."""
    client = get_notion_client()

    # Resolve a platform data_source id, waiting briefly if provisioning is in progress
    resolved_data_source_id = data_source_id or _get_platform_ds_id(client, database_id)
    if not resolved_data_source_id:
        resolved_data_source_id = _wait_for_platform_ds(client, database_id)

    schema_properties: dict[str, Any] = {}
    if resolved_data_source_id:
        ds = _call_with_retry(
            f"data_sources.retrieve({resolved_data_source_id})",
            lambda: client.data_sources.retrieve(data_source_id=resolved_data_source_id),
        )
        schema_properties = ds.get("properties") or {}

    property_key_map = _build_property_key_map(schema_properties)
    title_property_key = property_key_map.get(title_column, title_column)

    records = dataframe.to_dict("records")
    if max_rows is not None:
        records = records[:max_rows]

    existing_title_values: set[str] = set()
    if skip_existing_by_title and resolved_data_source_id:
        existing_title_values = _collect_existing_title_values(
            client,
            resolved_data_source_id,
            title_property_key,
        )

    created = 0
    skipped_existing = 0
    failures: list[dict[str, Any]] = []

    # Determine which columns in the DS schema are of type `status` so we
    # can emit the correct payload when building page properties.
    status_columns: set[str] = set()
    if schema_properties:
        for defn in schema_properties.values():
            if isinstance(defn, dict) and "status" in defn:
                name = defn.get("name")
                if name:
                    status_columns.add(name)

    for index, row in enumerate(records):
        row_title = row.get(title_column)
        if skip_existing_by_title and row_title and str(row_title) in existing_title_values:
            skipped_existing += 1
            continue

        try:
            properties = _build_page_properties_from_row(
                row,
                title_column=title_column,
                select_columns=select_columns,
                date_columns=date_columns,
                status_columns=status_columns,
            )
            properties = _remap_properties_to_schema_keys(properties, property_key_map)

            try:
                _call_with_retry(
                    f"pages.create(database={database_id}, row={index})",
                    lambda: client.pages.create(
                        parent={"data_source_id": resolved_data_source_id} if resolved_data_source_id else {"database_id": database_id},
                        properties=properties,
                    ),
                )
            except Exception as exc:
                # On certain errors (missing data_source / 404) attempt to re-resolve DS and retry once
                err_text = str(exc)
                retried = False
                if "Could not find" in err_text or "404" in err_text or "data_source" in err_text:
                    try:
                        new_ds = _wait_for_platform_ds(client, database_id)
                        if new_ds and new_ds != resolved_data_source_id:
                            resolved_data_source_id = new_ds
                            _call_with_retry(
                                f"pages.create(database={database_id}, row={index})-retry",
                                lambda: client.pages.create(
                                    parent={"data_source_id": resolved_data_source_id},
                                    properties=properties,
                                ),
                            )
                            retried = True
                    except Exception:
                        retried = False

                if not retried:
                    cause = getattr(exc, "__cause__", None)
                    failures.append(
                        {
                            "row_index": index,
                            "error": str(exc),
                            "cause": str(cause) if cause else None,
                        }
                    )
                    continue

            created += 1
            if skip_existing_by_title and row_title:
                existing_title_values.add(str(row_title))
        except Exception as exc:
            cause = getattr(exc, "__cause__", None)
            failures.append(
                {
                    "row_index": index,
                    "error": str(exc),
                    "cause": str(cause) if cause else None,
                }
            )

    return {
        "created": created,
        "skipped_existing": skipped_existing,
        "failed": len(failures),
        "data_source_id": resolved_data_source_id,
        "failures": failures,
    }


def publish_reading_list_v2_to_notion(
    paper_summaries_df,
    *,
    parent_page_id: str | None = None,
    workspace_page_title: str = "Reading List v2 (Relational)",
    existing_v2_page_id: str | None = None,
    existing_paper_summaries_database_id: str | None = None,
    existing_paper_summaries_data_source_id: str | None = None,
    dry_run: bool = False,
    max_rows: int | None = None,
) -> dict[str, Any]:
    """
    Publish migration data to Notion in a separate V2 page.
    This function never modifies existing Reading List content.
    """
    from ._client import get_page_id

    target_parent_page_id = get_page_id(parent_page_id)

    paper_props = _build_database_properties_from_dataframe(
        paper_summaries_df,
        title_column="Summary Row ID",
        select_columns={"Task Type"},
        date_columns={"Last Modified"},
    )

    result: dict[str, Any] = {
        "dry_run": dry_run,
        "parent_page_id": target_parent_page_id,
        "paper_summaries_rows": int(len(paper_summaries_df)),
    }

    if dry_run:
        result["planned"] = {
            "workspace_page_title": workspace_page_title,
            "databases": ["Paper Summaries"],
            "paper_summaries_properties": list(paper_props.keys()),
            "reuse": {
                "existing_v2_page_id": existing_v2_page_id,
                "existing_paper_summaries_database_id": existing_paper_summaries_database_id,
                "existing_paper_summaries_data_source_id": existing_paper_summaries_data_source_id,
            },
            "max_rows": max_rows,
        }
        return result

    if existing_v2_page_id:
        v2_page_id = existing_v2_page_id
    else:
        v2_page = create_notion_child_page(target_parent_page_id, workspace_page_title)
        v2_page_id = v2_page.get("id")

    if existing_paper_summaries_database_id:
        paper_db = {"id": existing_paper_summaries_database_id}
        paper_data_source_id = existing_paper_summaries_data_source_id
    else:
        paper_db_bundle = create_notion_database(v2_page_id, "Paper Summaries", paper_props)
        paper_db = paper_db_bundle.get("database", {})
        paper_data_source_id = paper_db_bundle.get("data_source", {}).get("id")

    paper_import = import_dataframe_to_notion_database(
        paper_db.get("id"),
        paper_summaries_df,
        title_column="Summary Row ID",
        data_source_id=paper_data_source_id,
        select_columns={"Task Type"},
        date_columns={"Last Modified"},
        max_rows=max_rows,
        skip_existing_by_title=True,
    )

    result["created"] = {
        "v2_page_id": v2_page_id,
        "paper_summaries_database_id": paper_db.get("id"),
        "paper_summaries_data_source_id": paper_import.get("data_source_id"),
        "reused_existing_page": bool(existing_v2_page_id),
        "reused_existing_database": bool(existing_paper_summaries_database_id),
    }
    result["import"] = {
        "paper_summaries": paper_import,
    }
    return result


# ---------------------------------------------------------------------------
# Archive
# ---------------------------------------------------------------------------

def archive_database(database_id: str) -> dict[str, Any]:
    """Move a Notion database to trash (soft-delete)."""
    client = get_notion_client()
    return _call_with_retry(
        f"pages.update(in_trash={database_id})",
        lambda: client.pages.update(page_id=database_id, in_trash=True),
    )


# ---------------------------------------------------------------------------
# V3 property helpers
# ---------------------------------------------------------------------------

def _to_rt(val: Any, max_len: int = 2000) -> dict:
    if not val or str(val).strip() in ("", "nan", "None", "NaT"):
        return {"rich_text": []}
    return {"rich_text": [{"text": {"content": str(val)[:max_len]}}]}


def _to_ms(val: Any) -> dict:
    if not val:
        return {"multi_select": []}
    if isinstance(val, list):
        return {"multi_select": [{"name": str(v)[:100]} for v in val if v]}
    s = str(val).strip()
    if s.startswith("["):
        try:
            items = ast.literal_eval(s)
            return {"multi_select": [{"name": str(v)[:100]} for v in items if v]}
        except Exception:
            pass
    return {"multi_select": [{"name": s[:100]}] if s else []}


def _to_sel(val: Any) -> dict:
    if not val or str(val).strip() in ("", "nan", "None"):
        return {"select": None}
    return {"select": {"name": str(val)[:100]}}


def _to_num(val: Any) -> dict:
    if val is None or str(val).strip() in ("", "nan", "None"):
        return {"number": None}
    try:
        return {"number": int(float(str(val)))}
    except (ValueError, TypeError):
        return {"number": None}


def _to_chk(val: Any) -> dict:
    if isinstance(val, bool):
        return {"checkbox": val}
    return {"checkbox": str(val).lower() in ("true", "1", "yes")}


def _to_dt(val: Any) -> dict:
    s = str(val).strip() if val else ""
    if not s or s in ("nan", "None", "NaT"):
        return {"date": None}
    return {"date": {"start": s[:10]}}


def _to_status(val: Any) -> dict:
    s = str(val).strip() if val else ""
    if not s or s in ("nan", "None", "N\\A", "N/A"):
        return {"status": None}
    return {"status": {"name": s}}


def _to_url(val: Any) -> dict:
    s = str(val).strip() if val else ""
    if not s or s in ("nan", "None"):
        return {"url": None}
    return {"url": s}


def build_v3_page_properties(record: dict[str, Any]) -> dict[str, Any]:
    """Build Notion page property payload for Paper DB v3 from a v1 record dict."""
    title = str(record.get("Name") or record.get("Title") or "").strip()
    return {
        "Title": {"title": [{"text": {"content": title[:2000]}}]},
        "Author": _to_rt(record.get("Author")),
        "Year": _to_num(record.get("Year")),
        "Journal": _to_rt(record.get("Journal")),
        "Status": _to_status(record.get("Status")),
        "Reading Progress": _to_status(record.get("Status_1")),
        "Type": _to_ms(record.get("Type")),
        "Article Type": _to_ms(record.get("Article Type")),
        "Keywords": _to_ms(record.get("Keywords/Type")),
        "Work Nature": _to_ms(record.get("Work Nature")),
        "Learner Representation": _to_ms(record.get("Learner Representation")),
        "Learner Population": _to_sel(record.get("Learner Population")),
        "Deployed/Deployable": _to_sel(record.get("Deployed/ Deployable")),
        "Course-Agnostic Approach": _to_chk(record.get("Course-Agnostic Approach")),
        "Platform": _to_rt(record.get("Platform")),
        "Search Strategy": _to_rt(record.get("Search Strategy")),
        "Date of Retrieval": _to_dt(record.get("Date of Retrieval")),
        "Completed": _to_dt(record.get("Completed")),
        "Motive For Exclusion": _to_rt(record.get("Motive For Exclusion")),
        "Abstract ✓": _to_chk(record.get("Abstract")),
        "Introduction ✓": _to_chk(record.get("Introduction")),
        "Methods ✓": _to_chk(record.get("Methods")),
        "Results ✓": _to_chk(record.get("Results")),
        "Discussion ✓": _to_chk(record.get("Discussion")),
        "Conclusion ✓": _to_chk(record.get("Conclusion")),
        "Related Work ✓": _to_chk(record.get("Related Work")),
        "Limitations ✓": _to_chk(record.get("Limitations")),
        "AI Summary": _to_rt(record.get("AI summary")),
    }


# ---------------------------------------------------------------------------
# V3 migration functions
# ---------------------------------------------------------------------------

def migrate_papers_from_reading_list(
    v1_db_id: str,
    v3_db_id: str,
    *,
    status_filter: list[str] | None = None,
) -> dict[str, Any]:
    """
    Migrate all papers from Reading List v1 into Paper DB v3.

    Returns:
        {created, skipped_existing, failed, failures, title_to_v3_id}
        title_to_v3_id maps paper title → v3 Notion page ID (used later for relations).
    """
    client = get_notion_client()
    v3_ds_id = _get_platform_ds_id(client, v3_db_id)
    allowed_status_options: dict[str, set[str]] = {"Status": set(), "Reading Progress": set()}
    existing_titles: set[str] = set()
    if v3_ds_id:
        v3_schema = _call_with_retry(
            f"data_sources.retrieve({v3_ds_id})",
            lambda: client.data_sources.retrieve(data_source_id=v3_ds_id),
        ).get("properties", {})
        for prop_name in ("Status", "Reading Progress"):
            prop_def = v3_schema.get(prop_name, {})
            options = (((prop_def.get("status") or {}).get("options")) or [])
            allowed_status_options[prop_name] = {
                option.get("name", "").strip()
                for option in options
                if option.get("name")
            }
        existing_titles = _collect_existing_title_values(client, v3_ds_id, "Title")

    v1_pages = fetch_database(v1_db_id)
    v1_records = pages_to_records(v1_pages)

    if status_filter:
        allowed = {s.strip() for s in status_filter}
        v1_records = [
            r for r in v1_records
            if str(r.get("Status") or "").strip() in allowed
        ]

    created = 0
    skipped = 0
    failures: list[dict] = []
    title_to_v3_id: dict[str, str] = {}

    for record in v1_records:
        title = str(record.get("Name") or record.get("Title") or "").strip()
        if not title:
            failures.append({"title": "", "error": "empty title"})
            continue

        if title in existing_titles:
            skipped += 1
            continue

        try:
            props = build_v3_page_properties(record)
            for prop_name, prop_payload in list(props.items()):
                if not isinstance(prop_payload, dict):
                    continue
                if "select" in prop_payload and prop_payload["select"] is None:
                    props.pop(prop_name, None)
                elif "status" in prop_payload and prop_payload["status"] is None:
                    props.pop(prop_name, None)
                elif "date" in prop_payload and prop_payload["date"] is None:
                    props.pop(prop_name, None)
                elif "url" in prop_payload and prop_payload["url"] is None:
                    props.pop(prop_name, None)
            for prop_name in ("Status", "Reading Progress"):
                status_name = (
                    props.get(prop_name, {}).get("status", {}).get("name", "").strip()
                )
                if not status_name:
                    continue
                allowed = allowed_status_options.get(prop_name) or set()
                if allowed and status_name not in allowed:
                    props.pop(prop_name, None)
            page = _call_with_retry(
                f"pages.create({title[:60]})",
                lambda p=props: client.pages.create(
                    parent={"data_source_id": v3_ds_id} if v3_ds_id else {"database_id": v3_db_id},
                    properties=p,
                ),
            )
            page_id = page["id"]
            title_to_v3_id[title] = page_id
            existing_titles.add(title)
            created += 1
            time.sleep(0.35)
        except Exception as exc:
            failures.append({"title": title, "error": str(exc)})

    return {
        "created": created,
        "skipped_existing": skipped,
        "failed": len(failures),
        "failures": failures,
        "title_to_v3_id": title_to_v3_id,
    }


def extract_reading_notes_from_page(page_id: str) -> str:
    """
    Extract free-text reading notes from a paper page.
    Collects all text blocks before the first 'Summary Table' heading.
    Returns plain text (section headings prefixed with ##).
    """
    blocks = list_block_children(page_id)
    parts: list[str] = []

    for block in blocks:
        btype = block.get("type", "")
        payload = block.get(btype, {})

        if btype in ("heading_1", "heading_2", "heading_3"):
            text = _extract_plain_text(payload.get("rich_text", []))
            if "Summary Table" in text:
                break
            if text.strip():
                parts.append(f"## {text.strip()}")

        elif btype == "paragraph":
            text = _extract_plain_text(payload.get("rich_text", []))
            if text.strip():
                parts.append(text.strip())

        elif btype in ("bulleted_list_item", "numbered_list_item"):
            text = _extract_plain_text(payload.get("rich_text", []))
            if text.strip():
                prefix = "• " if btype == "bulleted_list_item" else "1. "
                parts.append(f"{prefix}{text.strip()}")

    return "\n\n".join(parts)


def backfill_reading_notes_to_paper_db(
    v3_db_id: str,
    v1_db_id: str,
    title_to_v3_id: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    For each accepted paper: extract reading notes from v1 page blocks
    and write them into the Reading Notes field of the v3 Paper DB.

    Only fills empty Reading Notes fields (never overwrites).
    """
    client = get_notion_client()

    if title_to_v3_id is None:
        title_to_v3_id = build_paper_title_id_map(v3_db_id, title_column="Title")

    v1_pages = fetch_database(v1_db_id)
    v1_records = pages_to_records(v1_pages)

    accepted = [r for r in v1_records if str(r.get("Status", "")).startswith("Accepted")]

    updated = 0
    skipped = 0
    failures: list[dict] = []

    for record in accepted:
        title = str(record.get("Name") or "").strip()
        v3_page_id = title_to_v3_id.get(title)
        if not v3_page_id:
            skipped += 1
            continue

        try:
            notes = extract_reading_notes_from_page(record["notion_page_id"])
            if not notes.strip():
                skipped += 1
                continue

            _call_with_retry(
                f"pages.update(reading_notes={title[:40]})",
                lambda pid=v3_page_id, n=notes: client.pages.update(
                    page_id=pid,
                    properties={"Reading Notes": _to_rt(n, max_len=2000)},
                ),
            )
            updated += 1
            time.sleep(0.35)
        except Exception as exc:
            failures.append({"title": title, "error": str(exc)})

    return {"updated": updated, "skipped": skipped, "failed": len(failures), "failures": failures}


def migrate_summaries_from_reading_list(
    v1_db_id: str,
    v3_summaries_db_id: str,
    title_to_v3_paper_id: dict[str, str],
) -> dict[str, Any]:
    """
    Extract summary tables from v1 page blocks and insert into Paper Summaries DB v3.
    One row per (paper × task_type × data_row). Sets the Paper relation correctly.
    """
    client = get_notion_client()
    ds_id = _get_platform_ds_id(client, v3_summaries_db_id)

    v1_pages = fetch_database(v1_db_id)
    v1_records = pages_to_records(v1_pages)
    accepted = [r for r in v1_records if str(r.get("Status", "")).startswith("Accepted")]

    existing_ids: set[str] = set()
    if ds_id:
        existing_ids = _collect_existing_title_values(client, ds_id, "Summary Row ID")

    created = 0
    skipped = 0
    no_relation = 0
    no_relation_titles: list[str] = []
    failures: list[dict] = []
    row_counter = 1

    for record in accepted:
        title = str(record.get("Name") or "").strip()
        author = str(record.get("Author") or "").strip()
        v3_paper_id = title_to_v3_paper_id.get(title)
        page_id = record.get("notion_page_id", "")

        try:
            blocks = extract_page_blocks(page_id)
            tables_by_type = _collect_summary_rows_from_blocks(blocks)
        except Exception as exc:
            failures.append({"title": title, "error": f"block fetch: {exc}"})
            continue

        for task_type, task_rows in tables_by_type.items():
            for source_row_idx, row_data in enumerate(task_rows, start=1):
                summary_id = f"SR-{row_counter:05d}"
                row_counter += 1

                if summary_id in existing_ids:
                    skipped += 1
                    continue

                if not v3_paper_id:
                    no_relation += 1
                    if title not in no_relation_titles:
                        no_relation_titles.append(title)

                try:
                    props: dict[str, Any] = {
                        "Summary Row ID": {"title": [{"text": {"content": summary_id}}]},
                        "Task Type": {"select": {"name": task_type}},
                        "Source Row": {"number": source_row_idx},
                        "Paper Name": _to_rt(title),
                        "Author": _to_rt(author),
                    }

                    if v3_paper_id:
                        props["Paper"] = {"relation": [{"id": v3_paper_id}]}

                    # v1 table columns that are already covered by explicit props above
                    # or that simply don't exist in the v3 schema must be skipped/renamed.
                    _COL_RENAME = {
                        "Task": "Task Type",
                        "Thereotical Model": "Theoretical Model",
                    }
                    _COL_SKIP = {"Paper", "Author", "Title", "Paper Name"}
                    for col, val in row_data.items():
                        col = _COL_RENAME.get(col, col)
                        if col and val and col not in props and col not in _COL_SKIP:
                            props[col] = _to_rt(val)

                    props["Last Modified"] = _to_dt(datetime.utcnow().strftime("%Y-%m-%d"))
                    props["Revision Notes"] = _to_rt("Migrated from v1 page blocks")

                    _call_with_retry(
                        f"pages.create(summary={summary_id})",
                        lambda p=props: client.pages.create(
                            parent={"data_source_id": ds_id} if ds_id else {"database_id": v3_summaries_db_id},
                            properties=p,
                        ),
                    )
                    created += 1
                    existing_ids.add(summary_id)
                    time.sleep(0.35)
                except Exception as exc:
                    failures.append({"title": title, "task": task_type, "row": source_row_idx, "error": str(exc)})

    return {
        "created": created,
        "skipped_existing": skipped,
        "no_paper_relation": no_relation,
        "no_relation_titles": no_relation_titles,
        "failed": len(failures),
        "failures": failures,
    }
