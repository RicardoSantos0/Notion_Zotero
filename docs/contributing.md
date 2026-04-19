# Contributing

## Dev setup

```bash
git clone <repo>
cd Notion_Zotero
pip install -e ".[test]"
pytest tests/
```

## Coding standards

- **Style:** `ruff` for linting, `black` for formatting.
- **Types:** Type annotations on all public functions.
- **Models:** Use the dataclasses in `core/models.py`. Do not add Pydantic models to `core/`.
- **No sys.path hacks:** All imports must use the `notion_zotero.*` namespace.
- **No bare exceptions:** Catch and raise typed exceptions from `core/exceptions.py`.

## Running tests

```bash
pytest tests/ -v
```

Tests require an editable install. The test suite does not hit live Notion or Zotero APIs.

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

- [ ] Tests pass (`pytest tests/ -v`)
- [ ] No new `src.*` imports
- [ ] Provenance fields populated on any new canonical objects
- [ ] Domain-specific vocabulary stays in a domain pack, not core
- [ ] Updated relevant docs in `docs/`
