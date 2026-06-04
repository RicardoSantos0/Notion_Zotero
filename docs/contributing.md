# Contributing

## Dev setup

```bash
git clone <repo>
cd Notion_Zotero
pip install -e ".[test]"
python -m pytest
```

## Coding standards

- **Style:** keep changes local and consistent with existing code; add `ruff` /
  `black` only when a project config is introduced.
- **Types:** Type annotations on all public functions.
- **Models:** Use the Pydantic v2 models in `core/models.py`.
- **No sys.path hacks:** All imports must use the `notion_zotero.*` namespace.
- **No bare exceptions:** Catch and raise typed exceptions from `core/exceptions.py`.

## Running tests

```bash
python -m pytest
python -m pytest tests --ignore=tests/integration -q -o addopts=''
python -m pytest tests/test_sync_drift_regressions.py tests/test_sync_planner.py -q -o addopts=''
```

Tests require an editable install. `python -m pytest` is the authoritative
coverage gate from `pyproject.toml`; use `-o addopts=''` for focused local test
slices that should not invoke coverage. Unit tests do not hit live Notion or
Zotero APIs. Keep integration tests marked with `pytest.mark.integration` and
run them separately when credentials or pre-populated pull data are available.

The GitHub Actions workflow runs the same standards in separate jobs: unit
tests, local integration tests, sync-drift regressions, and full coverage.

## Adding a new domain pack

1. Create `src/notion_zotero/schemas/domain_packs/<name>.py` following the structure in `education_learning_analytics.py`.
2. Register the pack in `task_registry.py` `DOMAIN_PACKS` dict.
3. Add at least one golden fixture under `tests/fixtures/golden/`.
4. Verify with `notion-zotero list-domain-packs`.
5. See `docs/domain_packs.md` for the full guide.

## Adding a new extraction template

1. Add an `ExtractionTemplate` instance to `schemas/templates/generic.py`.
2. Add it to the `TEMPLATES` dict at the bottom of that file.
3. Verify with `notion-zotero list-templates`.

## Key design rules

1. Core stays generic — no domain vocabulary in `core/`.
2. Templates describe structure, not domain language.
3. Domain packs provide the mapping.
4. Importer orchestrates; it does not invent semantics.
5. Reading List is immutable — never write to the source.
6. Legacy code under `legacy/` is reference-only.
7. Provenance is mandatory on every canonical object.

## PR checklist

- [ ] Tests pass (`python -m pytest`)
- [ ] No new `src.*` imports
- [ ] Provenance fields populated on any new canonical objects
- [ ] Domain-specific vocabulary stays in a domain pack, not core
- [ ] Updated relevant docs in `docs/`
