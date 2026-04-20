# Changelog

All notable changes to notion_zotero are documented here.

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
