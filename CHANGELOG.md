# Changelog

All notable changes to notion_zotero are documented here.

---

## [2026-04-27] Fixtures cleanup: unified data directory, path consolidation

### Breaking changes

- **`fixtures/` directory removed as a concept.** All CLI commands that previously
  defaulted to `fixtures/canonical`, `fixtures/canonical_merged.json`, or
  `fixtures/reading_list` now default to paths under `data/`:

  | Old default | New default |
  |-------------|-------------|
  | `fixtures/canonical` | `data/pulled/notion/learning_analytics_review` |
  | `fixtures/canonical_merged.json` | `data/pulled/notion/canonical_merged.json` |
  | `fixtures/canonical_merged.dedup.json` | `data/pulled/notion/canonical_merged.dedup.json` |
  | `fixtures/reading_list` | `data/raw/notion` |

  Affected commands: `merge-canonical`, `dedupe-canonical`, `validate-fixtures`,
  `parse-fixtures`, `export-snapshot`, `report-by-year`, `report-by-journal`,
  `report-doi-coverage`, `report-task-counts`, `report-provenance`.

  Pass `--input` / `--out` explicitly to override any default.

- **`fixtures/` is no longer a recognised path anywhere in the package.** The directory
  was gitignored and empty after the previous session; it is now formally retired.
  `data/raw/notion/` is the new staging area for raw Notion page exports used with
  `parse-fixtures` in offline mode.

### What stays the same

- `tests/fixtures/` — the tracked test-data directory inside `tests/` — is **not**
  affected. It holds curated golden canonical files and sample pages for unit/integration
  tests and has nothing to do with live data.

### Quality

- `tests/test_semantic_mappings.py` removed — its only test asserted that
  `fixtures/reading_list` was populated at runtime, which is not a property the test
  suite can guarantee.
- `tests/integration/test_reading_list_importer.py::test_parse_single_fixture` removed
  for the same reason.
- `tests/integration/test_cli.py::test_merge_canonical_smoke` rewritten to be fully
  self-contained using `tmp_path` (no longer requires a pre-populated data directory).
- `tests/test_analysis_layer.py::test_export_database_snapshot_writes_file` updated to
  create `data/raw/notion` under `tmp_path` instead of `fixtures/reading_list`.
- Suite result: **304 passed, 81.68% coverage** (up from 304 / same tests, all green).

### Notion reader

- `connectors/notion/reader.py`: added handling for Notion `status` property type
  (previously only `select` was handled for status-like fields).

### Importer

- `services/reading_list_importer.py`: both `Status` and `Status_1` properties are now
  preserved independently in `sync_metadata` and produce separate `WorkflowState`
  entries, each carrying its source field name. Previously only one status field was
  kept and the other was silently dropped.

---

## [2026-04-25] Live pull connectors, retry, atomic write, CLI reports

### New features

- **`pull-notion` command** (`cli.py`, `connectors/notion/reader.py`):
  Pulls all pages from a live Notion database via the Notion API. Handles cursor-based
  pagination (`has_more` / `next_cursor`). Writes one `.canonical.json` per page to
  `data/pulled/notion/` using atomic write (staging swap on success; staging removed
  on failure). Progress output every 50 pages.

- **`pull-zotero` command** (`cli.py`, `connectors/zotero/reader.py`):
  Pulls all items from a live Zotero library via the Zotero Web API. Handles offset
  pagination (`start`/`limit` params, terminates via `Total-Results` header). Same
  atomic write pattern as `pull-notion`.

- **`--detect-library-id` flag** on `pull-zotero`:
  Auto-detects `ZOTERO_LIBRARY_ID` from your API key via `GET /keys/{api_key}`.
  Opt-in with explicit confirmation — never silent.

- **Tenacity retry** for both connectors:
  - Notion: reads `retry_after` from 429 JSON response body; retries up to 3 times.
  - Zotero: reads `Backoff` header from 429 responses; retries up to 3 times.
  - Wait functions implemented as `wait_base` subclasses (`_NotionRetryWait`,
    `_ZoteroRetryWait`) — compatible with tenacity v9+ (see bug fix below).

- **`status` command** (`cli.py`): Shows sync status between pulled Notion and
  Zotero data.

- **Analysis report commands** (`cli.py`):
  `report-by-year`, `report-by-journal`, `report-doi-coverage`, `report-task-counts`,
  `report-provenance` — all operate on previously pulled canonical data, no network
  required.

- **Unmapped field warnings** (`connectors/zotero/reader.py`):
  `to_reference()` now logs a warning for any Zotero item field not in
  `_KNOWN_ZOTERO_FIELDS`, making schema drift visible without breaking the pipeline.

- **`ZOTERO_LIBRARY_ID` error message** improved with link to `zotero.org/settings/keys`.

### Bug fixes

- **tenacity v9 compatibility** (`connectors/notion/reader.py`,
  `connectors/zotero/reader.py`): `wait_callable()` was removed in tenacity v9.
  Both readers were initially implemented using `wait_callable()`; corrected to
  `wait_base` subclasses which are the supported pattern in v9+.

### Quality

- **Coverage gate raised to 80%** (`pyproject.toml`): `--cov-fail-under=80` enforced
  by pytest. Sprint result: 83.75% coverage (251 passed, 20 skipped, 0 failed).

- **New test files** (19 tests across 3 files):
  - `tests/test_notion_reader.py` — 6 tests: pagination, 429-retry, field mapping
  - `tests/test_zotero_reader.py` — 8 tests: pagination, fallback termination,
    429-retry, retry-exhausted, unmapped field warning, missing library ID error
  - `tests/test_pull_cli.py` — 5 tests: pull writes files, atomic write on failure,
    missing ID exits

- **Notebook updated** (`original_db_summary_analysis.ipynb`): Loads exclusively
  from `data/pulled/notion/`; raises `FileNotFoundError` with `pull-notion`
  instruction if the directory is empty. No fallback to `fixtures/`.

- **Dependencies** (`pyproject.toml`): `tenacity>=8.0` and `requests>=2.28` promoted
  from test-only to main `[project].dependencies`.

---

## [2026-04-20] Hardening pass: domain pack bugs, provenance, logging, tests, CI

### Bug fixes

- **`--domain-pack` flag now functional** (`services/reading_list_importer.py`):
  Previously the CLI accepted `--domain-pack` but silently ignored it. The importer
  now resolves the requested pack via `task_registry.load_domain_pack()`, falls back
  to `education_learning_analytics` with a warning if not found, and stamps the active
  pack and its version into every output bundle's `provenance` block.

- **Unrecognised heading warning** (`schemas/task_registry.py`):
  `get_applicable_tasks()` now emits `log.warning(...)` when a page heading matches
  no domain pack task, instead of silently producing no tasks.

- **`Any` import missing** (`schemas/task_registry.py`):
  Added `Any` to the `typing` import (was used in `get_applicable_tasks` signature
  but not imported — latent `NameError` in some environments).

### New features

- **Domain pack versioning** (`schemas/domain_packs/education_learning_analytics.py`):
  `domain_pack` now includes `"version": "1.0"`. All packs must declare a version.

- **Provenance stamping**: Every canonical bundle produced by `parse-fixtures` now
  includes a top-level `provenance` dict: `{domain_pack_id, domain_pack_version}`.

- **New CLI commands** (`cli.py`): `validate-fixtures`, `list-domain-packs`, `list-templates`.

### Quality

- **`print()` → `log.info()`**: All operational print calls in `reading_list_importer.py`,
  `cli.py` (`cmd_merge_canonical`, `cmd_dedupe_canonical`), and `analysis/__init__.py`
  replaced with structured logging.

- **Coverage floor**: CI (`test.yml`) now enforces `--cov-fail-under=70`; builds fail
  if branch coverage drops below 70%.

- **New tests** (`tests/test_cli_new_commands.py`): 10 tests covering the three new
  commands, `--domain-pack` flag, fallback behaviour, and provenance stamping.

### Docs

- `docs/cli.md` — rewritten to cover all subcommands including new ones, `--domain-pack`
  option, provenance output, and logging guidance.
- `docs/domain_packs.md` — added versioning requirement, provenance output format,
  `--domain-pack` CLI usage, and unrecognised-heading warning behaviour.
- `docs/api_reference.md` — expanded `task_registry` section with full function
  signatures, domain pack dict schema, and canonical bundle provenance format.

### Housekeeping

- `.gitignore` — fixed leading-space bug that was causing `__pycache__/` and `*.pyc`
  patterns to be ignored by git (directory names matched literally rather than as glob).
  All previously tracked `.pyc` / `__pycache__` files removed from the index.
- `notion_zotero_detailed_patch_plan.md` — removed (planning document, fully implemented).
