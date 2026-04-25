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
data/pulled/notion/    ← one .canonical.json per Notion page
data/pulled/zotero/    ← one .canonical.json per Zotero item
```

After pulling, check sync status between the two sources:

```bash
notion-zotero status
```

---

### 2 — Analysis reports (no network required)

Run reports against previously pulled data. Works offline once data is local.

```bash
# Reference counts by publication year
notion-zotero report-by-year --input data/pulled/notion

# Reference counts by journal/venue
notion-zotero report-by-journal --input data/pulled/notion

# DOI coverage rate
notion-zotero report-doi-coverage --input data/pulled/notion

# Tasks per reference and extractions per template
notion-zotero report-task-counts --input data/pulled/notion

# Provenance completeness
notion-zotero report-provenance --input data/pulled/notion
```

The Jupyter notebook `original_db_summary_analysis.ipynb` also loads from `data/pulled/notion/` and provides an interactive exploration view. Run `pull-notion` first.

---

### 3 — Offline / fixture-based mode

Work with local Notion export snapshots without any API keys. Useful for reproducible pipelines or when credentials are unavailable.

```bash
# Parse a local Notion export into canonical bundles
notion-zotero parse-fixtures --input fixtures/reading_list --out fixtures/canonical

# Apply a specific domain pack during parsing
notion-zotero parse-fixtures --input fixtures/reading_list --out fixtures/canonical \
  --domain-pack education_learning_analytics

# Merge and deduplicate
notion-zotero merge-canonical --input fixtures/canonical --out fixtures/canonical_merged.json
notion-zotero dedupe-canonical --input fixtures/canonical_merged.json \
  --out fixtures/canonical_merged.dedup.json

# Validate output
notion-zotero validate-fixtures --input fixtures/canonical
```

To export a fresh Notion snapshot for use as fixtures:

```bash
notion-zotero export-snapshot --output fixtures/reading_list
```

---

### 4 — Schema migration / audit

Compare a legacy canonical directory against a new one to detect regressions or data loss.

```bash
python legacy/migration_audit.py \
    --legacy fixtures/canonical_old \
    --new    fixtures/canonical_new \
    --report docs/v3_gap_analysis_auto.md
```

---

## All commands

| Command | Purpose |
|---------|---------|
| `pull-notion` | Pull live Notion database pages → `data/pulled/notion/` |
| `pull-zotero` | Pull live Zotero library items → `data/pulled/zotero/` |
| `status` | Show sync status between pulled Notion and Zotero data |
| `report-by-year` | Reference counts by publication year |
| `report-by-journal` | Reference counts by journal/venue |
| `report-doi-coverage` | DOI coverage rate across bundles |
| `report-task-counts` | Tasks per reference and extractions per template |
| `report-provenance` | Provenance completeness across bundles |
| `export-snapshot` | Export a live Notion database to local JSON |
| `parse-fixtures` | Parse local fixture JSONs into canonical bundles |
| `merge-canonical` | Merge per-page canonical bundles into a single array file |
| `dedupe-canonical` | Deduplicate a merged file by DOI or title+authors |
| `validate-fixtures` | Validate canonical bundle files (exits 1 on error) |
| `zotero-citation` | Print an APA citation for a canonical bundle or Zotero item |
| `list-domain-packs` | List registered domain packs |
| `list-templates` | List registered extraction templates |

---

## Architecture

```
connectors/
  notion/reader.py    ← live Notion API, cursor pagination, tenacity retry
  zotero/reader.py    ← live Zotero API, offset pagination, tenacity retry
core/
  models.py           ← canonical Reference + WorkflowState + ReferenceTask
  exceptions.py       ← ConfigurationError, NotionZoteroError
schemas/
  domain_packs/       ← pluggable extraction rule sets (education_learning_analytics, ...)
  task_registry.py    ← domain pack loading, task resolution
services/
  reading_list_importer.py  ← fixture → canonical pipeline
cli.py                ← all subcommands (argparse)
```

Each canonical bundle is a JSON file containing `references`, `tasks`, `reference_tasks`, `task_extractions`, `workflow_states`, and `annotations`. Every bundle is stamped with `provenance` (`source_id`, `source_system`, `domain_pack_id`, `domain_pack_version`) so consumers can detect when re-extraction is needed.

Rate limiting is handled automatically: the Notion connector reads `retry_after` from 429 response bodies; the Zotero connector reads the `Backoff` response header. Both use [tenacity](https://github.com/jd/tenacity) with 3 retry attempts.

---

## Testing

```bash
pytest -q                          # full suite (271 tests)
pytest --cov=notion_zotero -q      # with coverage (CI enforces >= 80%)
```

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

- `fixtures/canonical_merged.json` is gitignored — regenerate with `merge-canonical`.
- `data/pulled/` is gitignored — regenerate with `pull-notion` / `pull-zotero`.
- Raw Notion export snapshots go in `fixtures/reading_list/`; canonical bundles from fixtures in `fixtures/canonical/`.
- See [docs/cli.md](docs/cli.md) for full subcommand option reference.
- See [docs/modes.md](docs/modes.md) for detailed workflow guidance.
