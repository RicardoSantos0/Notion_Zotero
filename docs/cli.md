# CLI (`notion-zotero`)

Run commands through the installed entrypoint or module runner:

```bash
notion-zotero <subcommand> [options]
python -m notion_zotero.cli <subcommand> [options]
```

On the Windows/OneDrive development path, prefer `python -m notion_zotero.cli`
and `python -m pytest`; this avoids PATH shims that may point at a different
Python environment.

## Project Config

Most path and policy defaults can be supplied from a JSON config:

```bash
notion-zotero --config notion_zotero.config.json plan-sync
notion-zotero --config notion_zotero.config.json apply-plan
```

If `--config` is omitted, the CLI looks for `NOTION_ZOTERO_CONFIG` and then for
`notion_zotero.config.json`, `.notion-zotero.json`, or `notion-zotero.json` in
the working directory. CLI flags override config values. See
`notion_zotero.config.example.json` for the supported keys.

## Live Pull And Sync

### `pull-notion`
Pull pages from a live Notion database into canonical bundle files.

```bash
notion-zotero pull-notion --name learning_analytics_review
notion-zotero pull-notion --database-id <id> --skip-blocks
```

Options:
- `--database-id ID` overrides `NOTION_DATABASE_ID`.
- `--output PATH` defaults to `data/pulled/notion`.
- `--name NAME` stores the pull under `data/pulled/notion/<NAME>/`.
- `--skip-blocks` writes metadata-only bundles without fetching page blocks.
- `--alt-output-name NAME` is used when OneDrive leaves a conflicting target.

### `pull-zotero`
Pull Zotero items into canonical bundle files.

```bash
notion-zotero pull-zotero
notion-zotero pull-zotero --detect-library-id
```

Options:
- `--output PATH` defaults to `data/pulled/zotero`.
- `--limit N` sets the Zotero API page size.
- `--detect-library-id` looks up `ZOTERO_LIBRARY_ID` from the API key.
- `--alt-output-name NAME` is used when the final target conflicts.

### `status`
Compare live Zotero and Notion records and print matched, only-Zotero,
only-Notion, and ambiguous counts. Matching uses the same policy as
`plan-sync`: Zotero key, DOI, and title+authors are strong keys; title-only
matches are weak and require compatible years.

```bash
notion-zotero status
notion-zotero status --zotero-limit 200 --notion-database-id <id>
```

### `plan-sync`
Build a read-only JSON sync plan from local pulled snapshots.

```bash
notion-zotero plan-sync \
  --notion-dir data/pulled/notion/learning_analytics_review \
  --zotero-dir data/pulled/zotero \
  --out data/sync_plans/sync_plan.json
```

The plan includes `matches`, executable `operations`, source-only records,
ambiguous candidates, review actions, and `match_confidence` for each match.

### `apply-plan`
Preview or apply reviewed plan operations. Dry-run is the default and performs
no network writes.

```bash
notion-zotero review-plan --plan data/sync_plans/sync_plan.json \
  --out data/sync_plans/sync_plan_review.md
notion-zotero apply-plan --plan data/sync_plans/sync_plan.json
notion-zotero apply-plan --plan data/sync_plans/sync_plan.json --apply
notion-zotero apply-plan --plan data/sync_plans/sync_plan.json --apply \
  --notion-database-id <id>
notion-zotero apply-plan --plan data/sync_plans/sync_plan.json --apply \
  --include-reviewed-creates --notion-database-id <id>
```

`review-plan` writes a Markdown report with summary counts, executable
operations, matches, ambiguous candidates, review actions, and Notion-only
records. Use `--max-rows` to control how many rows appear in each section.
`review-plan` and `apply-plan` validate plan version and executable operations
before rendering or applying the file.

Apply mode requires `NOTION_API_KEY`, writes Notion bibliographic metadata from
Zotero-owned fields, and appends NDJSON entries under `logs/write_logs/`.
Zotero-only records remain review actions; Notion pages are not created
automatically. If `--notion-database-id` or `NOTION_DATABASE_ID` is set, apply
mode fetches the live database schema and uses actual Notion property names and
types while serializing updates.

Zotero-only page creation is opt-in. Edit selected
`create_notion_page_from_zotero_record` review actions in `sync_plan.json` from
`needs_review` to `approved`, then pass `--include-reviewed-creates` with a
database ID. Approved creates are duplicate-checked against current Notion page
titles before writing.

### `rollback-plan`
Build a non-mutating rollback plan from applied Notion write-log entries.

```bash
notion-zotero rollback-plan \
  --write-log-dir logs/write_logs \
  --out data/sync_plans/rollback_plan.json
notion-zotero rollback-plan --session-id apply-plan-1234567890
notion-zotero apply-rollback-plan --plan data/sync_plans/rollback_plan.json
notion-zotero apply-rollback-plan --plan data/sync_plans/rollback_plan.json \
  --apply --notion-database-id <id>
```

The output reverses applied Notion reference-field writes into
`rollback_notion_reference_field` operations and skips planned, failed, Zotero,
or malformed entries. `apply-rollback-plan` previews by default. Apply mode
requires `NOTION_API_KEY`, fetches current Notion page values, and writes only
when they still match `expected_current_value` in the rollback plan.

### `diff` and `sync`
`diff` compares two canonical bundle directories. `sync` is the lower-level
writer workflow against a baseline directory; it remains available for writer
tests and controlled dry-run/apply experiments.

```bash
notion-zotero diff --baseline data/sync_baseline --updated data/pulled/notion
notion-zotero sync --notion-dir data/pulled/notion --baseline-dir data/sync_baseline
notion-zotero sync --apply
```

## Offline Fixture Workflow

### `parse-fixtures`
Parse local Notion export JSON files into per-page canonical bundles.

```bash
notion-zotero parse-fixtures \
  --input data/raw/notion \
  --out data/pulled/notion/learning_analytics_review \
  --domain-pack education_learning_analytics
```

Options:
- `--input PATH` directory containing raw Notion page exports.
- `--out PATH` output directory for canonical bundles.
- `--force` overwrite existing canonical bundles.
- `--domain-pack PACK_ID` chooses the task/domain mapping.

### `merge-canonical`, `dedupe-canonical`, `validate-fixtures`

```bash
notion-zotero merge-canonical
notion-zotero dedupe-canonical
notion-zotero validate-fixtures
```

These commands default to the current `data/pulled/notion/learning_analytics_review`
layout and accept `--input` / `--out` overrides where relevant.

## Reports And Registry

Analysis reports read local canonical bundles and do not require network access:

```bash
notion-zotero report-by-year
notion-zotero report-by-journal
notion-zotero report-doi-coverage
notion-zotero report-task-counts
notion-zotero report-provenance
```

To generate the manuscript-oriented task workbook used by the notebook:

```bash
notion-zotero paper-summary-tables
notion-zotero paper-summary-tables --input data/pulled/notion/learning_analytics_review \
  --out data/analysis_outputs/paper_task_summary_tables.xlsx
```

The workbook contains one sheet per paper-facing task plus an `audit` sheet.
Use `--no-title` to omit the `Paper title` column from task sheets.

Registry/helper commands:

```bash
notion-zotero list-domain-packs
notion-zotero list-templates
notion-zotero zotero-citation --file <bundle-or-item.json>
notion-zotero export-snapshot
```

`export-snapshot` requires Notion credentials and is retained for compatibility;
the preferred live workflow is `pull-notion`.
