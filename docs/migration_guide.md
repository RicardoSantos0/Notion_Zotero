# Migration Guide

## From legacy `src.*` imports to `notion_zotero`

If you have scripts that import from the old package layout (`from src.core.models import ...`), update them as follows:

| Old import | New import |
|-----------|------------|
| `from src.core.models import Reference` | `from notion_zotero.core.models import Reference` |
| `from src.schemas.task_registry import ...` | `from notion_zotero.schemas.task_registry import ...` |
| `from src.analysis.normalize_title import ...` | `from notion_zotero.core.normalize import normalize_title` |
| `from src.analysis.citation_from_item import ...` | `from notion_zotero.core.citation import citation_from_reference` |

## From the legacy importer (`master_reading_list_importer.py`)

The legacy importer (`legacy/master_reading_list_importer.py`) used ad hoc string matching and hard-coded task names. The new importer is driven by domain packs.

**Key differences:**

| Aspect | Legacy | New |
|--------|--------|-----|
| Task discovery | Regex on headings | Domain pack alias matching |
| Status decoding | Hard-coded strings | `status_mapping.py` rules |
| IDs | Random UUID fragments | Deterministic (page + task + index) |
| Provenance | None | Mandatory on every object |
| Task creation | Any heading → task | Only pack-declared tasks |

**Migration steps:**

1. Install the new package: `pip install -e .`
2. Re-run the importer on your reading list fixtures:
   ```bash
   notion-zotero parse-fixtures --input fixtures/reading_list --out fixtures/canonical_new
   ```
3. Compare output using `tools/migration_audit.py` (legacy archives are stored in `archive/Notion_Zotero-legacy/`; move your legacy archive into `legacy/legacy_archive_*` if needed):
    ```bash
    python tools/migration_audit.py \
       --legacy fixtures/canonical_old \
       --new fixtures/canonical_new \
       --report docs/v3_gap_analysis.md
    ```
4. Review `docs/v3_gap_analysis.md` for field-level differences.

## Editable install

For development work, install in editable mode:

```bash
pip install -e .
```

Tests require the package to be installed (directly or editably):

```bash
pip install -e ".[test]"
pytest tests/
```
