# Notion_Zotero

[![Regenerate sanitized summary](https://github.com/RicardoSantos0/Notion_Zotero/actions/workflows/regenerate-sanitized-summary.yml/badge.svg?branch=main)](https://github.com/RicardoSantos0/Notion_Zotero/actions/workflows/regenerate-sanitized-summary.yml)

Reference management and evidence-extraction toolkit for PhD literature reviews. Pulls live data from Notion and Zotero, converts it into versioned canonical bundles, and provides analysis reports — all from the command line.

---

## Install

```powershell
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -e .
```

> **OneDrive users:** `uv` fails on this path with a hardlink error (OS error 396). Use
> standard `pip` as shown above — do not use `uv run pytest` or `uv venv`.
> If the venv gets wiped, run `python.exe -m ensurepip` first to bootstrap pip.

Copy `.env.example` to `.env` and fill in your API keys:

```
NOTION_API_KEY=secret_...
NOTION_DATABASE_ID=...          # the ID of your Notion reading list database
ZOTERO_API_KEY=...
ZOTERO_LIBRARY_ID=...           # your Zotero user ID (see zotero.org/settings/keys)
```

---

## Workflows

### 1 — Pull live data from Notion and Zotero

Fetch all pages/items from the live APIs and save them as canonical bundles under `data/pulled/`.

```bash
# Pull all pages from your Notion reading list database
notion-zotero pull-notion

# Pull all items from your Zotero library
notion-zotero pull-zotero

# If you don't know your ZOTERO_LIBRARY_ID, detect it automatically
notion-zotero pull-zotero --detect-library-id
```

Both commands use **atomic write**: data is staged to a temporary directory first and only swapped into place on full success. A failed mid-pull leaves the previous data intact.

Pulled data lands in:
```
data/pulled/notion/learning_analytics_review/   ← one .canonical.json per Notion page
data/pulled/zotero/                             ← one .canonical.json per Zotero item
```

After pulling, check sync status between the two sources:

```bash
notion-zotero status
```

To review proposed metadata changes before any live write path is enabled, build
a read-only sync plan from local snapshots:

```bash
notion-zotero plan-sync
```

This writes `data/sync_plans/sync_plan.json` with matched records, unmatched
records, ambiguous matches, and proposed Zotero-owned metadata updates for
Notion. It also lists review-only actions for Zotero records that may need new
Notion pages. The command does not call live APIs.

To inspect executable plan operations without writing to Notion:

```bash
notion-zotero apply-plan
```

After reviewing the JSON plan, apply the executable Notion metadata updates with:

```bash
notion-zotero apply-plan --apply
```

Apply mode requires `NOTION_API_KEY` and writes an append-only session log under
`logs/write_logs/`. Notion page creation for Zotero-only records is intentionally
left as a review action in the plan, not an automatic write.

---

### 2 — Analysis reports (no network required)

Run reports against previously pulled data. Works offline once data is local.

```bash
# Reference counts by publication year
notion-zotero report-by-year

# Reference counts by journal/venue
notion-zotero report-by-journal

# DOI coverage rate
notion-zotero report-doi-coverage

# Tasks per reference and extractions per template
notion-zotero report-task-counts

# Provenance completeness
notion-zotero report-provenance
```

All report commands default to `data/pulled/notion/learning_analytics_review`. Pass `--input <path>` to point at a different directory.

The Jupyter notebook `original_db_summary_analysis.ipynb` also loads from `data/pulled/notion/learning_analytics_review/` and provides an interactive exploration view. Run `pull-notion` first.

The notebook now also builds paper-facing summary tables from the cleaned task
tables. These tables are intended for manuscript review/supplement use rather
than raw extraction auditing:

```python
from notion_zotero.analysis.paper_tables import build_paper_summary_dataframes

paper_task_tables, paper_task_audit = build_paper_summary_dataframes(
    cleaned_dfs,
    task_tables={"PRED": "PRED", "DESC": "DESC", "KT": "KT", "REC": "ERS"},
    include_title=True,
)
```

The exported workbook is:

```
data/analysis_outputs/paper_task_summary_tables.xlsx
```

It contains one sheet per task (`PRED`, `DESC`, `KT`, `ERS`) plus an `audit`
sheet. Rows are paper-level contribution summaries: the same paper can appear
more than once in the same task sheet when it reports distinct task-specific
methods, targets, or evidence.

Paper-table display policy includes:

- year-first, study-label-second sorting;
- standardized algorithms/models, features, assessment strategies, results, and limitations;
- explicit RecSys algorithm/model extraction from recommender type, method notes,
  initialization details, update details, preprocessing details, and comments;
- split prediction columns: `Prediction task type` and `Prediction target / timing`;
- KT-specific columns for prior-model limitations, new contribution, and study limitations.

---

### 3 — Offline / raw-export mode

Work with local Notion export snapshots without any API keys. Useful for reproducible pipelines or when credentials are unavailable.

Raw page exports are staged in `data/raw/notion/` and parsed into `data/pulled/notion/learning_analytics_review/`.

```bash
# Parse a local Notion export into canonical bundles
notion-zotero parse-fixtures --input data/raw/notion \
  --out data/pulled/notion/learning_analytics_review

# Apply a specific domain pack during parsing
notion-zotero parse-fixtures --input data/raw/notion \
  --out data/pulled/notion/learning_analytics_review \
  --domain-pack education_learning_analytics

# Merge all canonical bundles into a single file
notion-zotero merge-canonical

# Deduplicate the merged file by DOI or title+authors
notion-zotero dedupe-canonical

# Validate canonical bundle files
notion-zotero validate-fixtures
```

All three commands above default to `data/pulled/notion/learning_analytics_review` (or its derived files). Pass `--input` / `--out` to override.

To export a fresh raw snapshot from Notion for offline use:

```bash
notion-zotero export-snapshot
```

This writes raw page exports to `data/raw/notion/`.

---

### 4 — Schema migration / audit

Compare a legacy canonical directory against a new one to detect regressions or data loss.

```bash
python tools/migration_audit.py \
  --legacy data/pulled/notion/learning_analytics_review_old \
  --new    data/pulled/notion/learning_analytics_review \
  --report docs/migration_report.md
```

Legacy scripts have been archived to `archive/Notion_Zotero-legacy/` — use `tools/migration_audit.py` to run audits against an extracted legacy archive placed under `legacy/legacy_archive_*`.

---

## All commands

| Command | Default paths | Purpose |
|---------|--------------|---------|
| `pull-notion` | → `data/pulled/notion/<name>/` | Pull live Notion database pages |
| `pull-zotero` | → `data/pulled/zotero/` | Pull live Zotero library items |
| `status` | reads `data/pulled/` | Show sync status between Notion and Zotero data |
| `plan-sync` | `data/pulled/notion/learning_analytics_review` + `data/pulled/zotero` → `data/sync_plans/sync_plan.json` | Build a read-only review plan before synchronization |
| `apply-plan` | `data/sync_plans/sync_plan.json` | Dry-run or apply reviewed sync-plan operations |
| `report-by-year` | `data/pulled/notion/learning_analytics_review` | Reference counts by publication year |
| `report-by-journal` | `data/pulled/notion/learning_analytics_review` | Reference counts by journal/venue |
| `report-doi-coverage` | `data/pulled/notion/learning_analytics_review` | DOI coverage rate across bundles |
| `report-task-counts` | `data/pulled/notion/learning_analytics_review` | Tasks per reference and extractions per template |
| `report-provenance` | `data/pulled/notion/learning_analytics_review` | Provenance completeness across bundles |
| `export-snapshot` | → `data/pulled/notion/canonical_merged.json` | Export and merge Notion pages to a single JSON |
| `parse-fixtures` | `data/raw/notion` → `data/pulled/notion/learning_analytics_review` | Parse raw Notion exports into canonical bundles (offline) |
| `merge-canonical` | `data/pulled/notion/learning_analytics_review` → `canonical_merged.json` | Merge per-page bundles into a single array file |
| `dedupe-canonical` | `canonical_merged.json` → `canonical_merged.dedup.json` | Deduplicate a merged file by DOI or title+authors |
| `validate-fixtures` | `data/pulled/notion/learning_analytics_review` | Validate canonical bundle files (exits 1 on error) |
| `zotero-citation` | — | Print an APA citation for a canonical bundle or Zotero item |
| `list-domain-packs` | — | List registered domain packs |
| `list-templates` | — | List registered extraction templates |

---

## Data directory layout

```
data/
  analysis_outputs/
    paper_task_summary_tables.xlsx  ← manuscript-oriented task summary workbook
    data_source_summary.xlsx        ← normalized data-source summary output
  pulled/
    notion/
      learning_analytics_review/   ← one .canonical.json per Notion page (gitignored)
      canonical_merged.json         ← merged array (produced by merge-canonical, gitignored)
    zotero/                         ← one .canonical.json per Zotero item (gitignored)
  raw/
    notion/                         ← raw Notion page exports for offline parsing (gitignored)
  sync_plans/
    sync_plan.json                  ← generated review plan from plan-sync (gitignored)
logs/
  write_logs/                       ← append-only NDJSON logs for apply mode (gitignored)
tests/
  fixtures/
    golden/                         ← curated canonical bundles for regression tests (tracked)
    sample_page.json                ← minimal raw page for smoke tests (tracked)
```

`data/` is fully gitignored — it is ephemeral working data regenerated by `pull-notion` / `pull-zotero`. `tests/fixtures/` is tracked and contains only small, hand-crafted test inputs.

---

## Architecture

```
connectors/
  notion/reader.py    ← live Notion API, cursor pagination, tenacity retry
  zotero/reader.py    ← live Zotero API, offset pagination, tenacity retry
analysis/
  paper_tables.py     ← paper-facing task summary tables + display policy
  visualization.py    ← reusable, domain-agnostic notebook plotting helpers
  table_normalization.py ← task/value normalization helpers driven by domain packs
core/
  models.py           ← canonical Reference + WorkflowState + ReferenceTask
  text_utils.py       ← reusable text cleanup, typo fixes, search-string normalization
  exceptions.py       ← ConfigurationError, NotionZoteroError
schemas/
  domain_packs/       ← pluggable extraction rule sets (education_learning_analytics, ...)
  task_registry.py    ← domain pack loading, task resolution
services/
  reading_list_importer.py  ← raw page export → canonical pipeline (offline mode)
  sync_planner.py           ← local Notion/Zotero snapshot matching + review plan
  sync_plan_applier.py      ← dry-run/apply reviewed plan operations
writers/
  notion_properties.py      ← typed Notion property serialization
  notion_writer.py          ← Notion apply path with write-log support
  zotero_writer.py          ← Zotero apply path with version guards
cli.py                ← all subcommands (argparse)
```

Each canonical bundle is a JSON file containing `references`, `tasks`, `reference_tasks`, `task_extractions`, `workflow_states`, and `annotations`. Every bundle is stamped with `provenance` (`source_id`, `source_system`, `domain_pack_id`, `domain_pack_version`) so consumers can detect when re-extraction is needed.

Rate limiting is handled automatically: the Notion connector reads `retry_after` from 429 response bodies; the Zotero connector reads the `Backoff` response header. Both use [tenacity](https://github.com/jd/tenacity) with 3 retry attempts.

---

## Sync safety model

The package uses a review-first sync workflow:

1. `pull-notion` and `pull-zotero` create local canonical snapshots.
2. `plan-sync` compares those snapshots and writes a JSON plan.
3. `apply-plan` previews executable operations without network writes.
4. `apply-plan --apply` applies reviewed Notion metadata updates and writes an
   append-only NDJSON write log.

Current executable plan operations update Notion bibliographic metadata from
Zotero-owned fields. Zotero-only records are surfaced as `needs_review` actions
for possible Notion page creation; they are not automatically created. Zotero
writes use item version guards when version metadata is available.

---

## Suggested next improvements

The package is now in a solid review-first state. The highest-value next steps are:

- **Schema-driven Notion mapping:** fetch the active Notion database schema and
  use it to configure property names/types instead of relying on default field
  names.
- **Reviewed page creation:** add an explicit `create-page` operation for
  Zotero-only records, with duplicate checks and a required review marker.
- **Typed sync-plan models:** represent plans and operations with Pydantic models
  so malformed or old plan versions fail early with clear messages.
- **Plan review reports:** generate a Markdown or Excel review report from
  `sync_plan.json` for easier inspection before apply mode.
- **Restore/rollback helper:** read write logs and produce a human-reviewable
  rollback plan for recently applied Notion updates.
- **Configuration file:** add a project config file for default paths, domain
  pack, Notion property schema, and sync policy.
- **Notebook pipeline command:** expose the paper-table workbook generation as a
  CLI command so the notebook and command-line workflow stay aligned.
- **CI polish:** run focused sync-plan tests separately from the full suite and
  add fixture-based regression plans for common Notion/Zotero drift cases.

---

## Testing

```bash
pytest -q                          # full suite
pytest --cov=src/notion_zotero -q  # with coverage (CI enforces >= 80%)
```

Integration tests (marked `pytest.mark.integration`) require live API credentials or pre-populated `data/pulled/` directories. Run unit tests only with `pytest -q --ignore=tests/integration`.

On this OneDrive path, if the project `.venv` or `uv run` hangs, use an
external throwaway environment outside the repository:

```powershell
py -3.12 -m venv C:\Users\ricar\Documents\codex-test-env-notion-zotero
C:\Users\ricar\Documents\codex-test-env-notion-zotero\Scripts\python.exe -m pip install -e ".[test,analysis]"
$env:PYTHONPATH='src'
C:\Users\ricar\Documents\codex-test-env-notion-zotero\Scripts\python.exe -m pytest tests -q
```

Latest external-env suite result: **395 passed, 84.02% coverage**.

---

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `NOTION_API_KEY` | For `pull-notion`, `export-snapshot` | Notion integration token |
| `NOTION_DATABASE_ID` | For `pull-notion` | ID of the Notion database to pull |
| `ZOTERO_API_KEY` | For `pull-zotero` | Zotero API key |
| `ZOTERO_LIBRARY_ID` | For `pull-zotero` | Zotero user/group library ID |

Set in `.env` (loaded automatically) or as shell environment variables. Use `--detect-library-id` with `pull-zotero` to look up `ZOTERO_LIBRARY_ID` from your API key.

---

## Notes

- `data/` is gitignored entirely — regenerate with `pull-notion` / `pull-zotero`.
- `data/raw/notion/` is where raw Notion page exports go for offline `parse-fixtures` use.
- `tests/fixtures/` is tracked git — it holds curated test data, not live working data.
- See [docs/cli.md](docs/cli.md) for full subcommand option reference.
- See [docs/modes.md](docs/modes.md) for detailed workflow guidance.
