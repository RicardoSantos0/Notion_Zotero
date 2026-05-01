# Usage Modes

Three modes cover different stages of the research workflow.

---

## Analysis Mode

Analysis Mode operates entirely on local fixture files. No live Notion or Zotero
connection is required. It is the primary mode for Sprint 1 and Sprint 2 work.

### Entry point

```bash
notion-zotero <subcommand> [options]
# or
python -m notion_zotero.cli <subcommand>
```

### Pipeline commands

| Command | Purpose |
|---|---|
| `parse-fixtures` | Parse raw Notion export JSON files into per-page canonical bundles |
| `merge-canonical` | Merge per-page canonical bundles into a single array file |
| `dedupe-canonical` | Deduplicate the merged file by DOI or title+authors |
| `validate-fixtures` | Validate canonical bundle files; exits with code 1 on error |
| `list-domain-packs` | List all registered domain packs |
| `list-templates` | List all registered extraction templates |
| `zotero-citation` | Print an APA-style citation for a canonical bundle or Zotero item |

### Typical workflow

```bash
# 1. Parse local snapshots into canonical form
notion-zotero parse-fixtures \
    --input fixtures/reading_list \
    --out fixtures/canonical \
    --domain-pack education_learning_analytics

# 2. Merge into a single file
notion-zotero merge-canonical \
    --input fixtures/canonical \
    --out fixtures/canonical_merged.json

# 3. Deduplicate
notion-zotero dedupe-canonical \
    --input fixtures/canonical_merged.json \
    --out fixtures/canonical_merged.dedup.json

# 4. Validate the output
notion-zotero validate-fixtures --input fixtures/canonical
```

### Domain pack selection

The `--domain-pack` flag on `parse-fixtures` selects which pack drives task
extraction. If the requested pack is not found, the importer falls back to
`education_learning_analytics` with a warning.

```bash
notion-zotero list-domain-packs   # show available pack IDs
```

### QA and provenance

Every canonical bundle is stamped with a `provenance` block recording the
domain pack ID and version used during import:

```json
{
  "provenance": {
    "domain_pack_id": "education_learning_analytics",
    "domain_pack_version": "1.0"
  }
}
```

The `flatten_bundles()` helper (importable from `notion_zotero.services`) reads
a merged canonical file and yields flat dicts suitable for tabular QA — counting
tasks per paper, checking DOI coverage, and inspecting workflow states — without
any network calls.

---

## Migration / Audit Mode

Migration Mode is used when comparing a legacy Notion export against a
freshly-generated canonical output to find regressions or data loss during the
v2-to-v3 schema transition.

### Entry point

```bash
python tools/migration_audit.py \
  --legacy fixtures/canonical_old \
  --new    fixtures/canonical_new \
  --report docs/v3_gap_analysis_auto.md
```

The `run_audit()` function (exposed by `tools/migration_audit.py`) loads both
directories, matches pages by a stable key (DOI when present, else
normalised-title + first-author), and produces a diff report.

### Five diff categories

| Category | What is checked |
|---|---|
| Missing references | Pages present in the legacy output that have no match in the new output |
| Missing extractions | `task_extractions` present in legacy but absent from the matched canonical bundle |
| Field loss | Canonical scalar fields (`title`, `authors`, `year`, `doi`, `journal`, etc.) present in legacy but empty or absent in the new bundle |
| Provenance loss | Objects that carry provenance in the new output but had no equivalent provenance block in the legacy output (reported as coverage gain, not loss) |
| Workflow state mismatch | `WorkflowState.state` values that differ between legacy and new for the same page |

### Interpreting the report

- **Missing references** require manual triage: the page may have been excluded
  by a domain-pack filter or may be genuinely new.
- **Field loss** rows indicate importer regressions and should be fixed before
  promoting canonical output to staging.
- **Workflow state mismatches** are expected when `status_mapping.py` rules are
  updated; review and confirm or revert the mapping change.

### Related artefacts

- `docs/v3_gap_analysis.md` — field-level comparison written at migration time
- `docs/migration_diffs_v2_v3.csv` — raw diff rows as a spreadsheet
- `docs/migration_report_v2_to_v3.md` — narrative summary of the v2-to-v3 pass

---

## Live Pull Mode

Live Pull Mode connects directly to the Notion and Zotero APIs, fetches all
records, and saves them as canonical bundles under `data/pulled/`. It replaces
the previous "Analysis Mode" fixture-based workflow for day-to-day use.

### Prerequisites

Set in `.env` (loaded automatically):
```
NOTION_API_KEY=secret_...
NOTION_DATABASE_ID=...
ZOTERO_API_KEY=...
ZOTERO_LIBRARY_ID=...   # use --detect-library-id if unknown
```

### Commands

```bash
# Pull all Notion pages
notion-zotero pull-notion

# Pull all Zotero items
notion-zotero pull-zotero

# Auto-detect ZOTERO_LIBRARY_ID from your API key
notion-zotero pull-zotero --detect-library-id

# Check sync status between pulled sources
notion-zotero status
```

### Output layout

```
data/pulled/
  notion/   ← one .canonical.json per Notion page
  zotero/   ← one .canonical.json per Zotero item
```

### Reliability

- **Pagination**: Notion uses cursor-based pagination (`has_more` / `next_cursor`);
  Zotero uses offset-based pagination (`start` / `limit`, terminates via
  `Total-Results` response header).
- **Retry**: Both connectors use tenacity (3 attempts). Notion reads `retry_after`
  from 429 JSON body; Zotero reads the `Backoff` response header.
- **Atomic write**: Data is written to a `_staging` directory and swapped into
  place only on full success. A failed pull leaves the previous data intact.

### Current status

| Component | Status |
|---|---|
| Notion read connector (`connectors/notion/reader.py`) | Implemented |
| Zotero read connector (`connectors/zotero/reader.py`) | Implemented |
| `pull-notion` CLI command | Implemented |
| `pull-zotero` CLI command | Implemented (+ `--detect-library-id`) |
| `status` command | Implemented |
| Diff engine (`services/diff_engine.py`) | Implemented |
| `diff` CLI command | Implemented |
| Notion write client (`connectors/notion/client.py`) | Implemented |
| Zotero write client (`connectors/zotero/client.py`) | Implemented |
| `sync` CLI command (dry-run default, `--apply` for live writes) | Implemented |
