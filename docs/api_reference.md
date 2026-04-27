# API Reference

## `notion_zotero.core.models`

### `Reference`
Canonical representation of a bibliographic item.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Deterministic canonical ID |
| `title` | `str \| None` | Normalised title |
| `authors` | `list[str]` | Author strings |
| `year` | `int \| None` | Publication year |
| `journal` | `str \| None` | Journal / venue |
| `doi` | `str \| None` | DOI |
| `url` | `str \| None` | URL |
| `zotero_key` | `str \| None` | Zotero item key |
| `abstract` | `str \| None` | Abstract text (text only — not checkbox) |
| `item_type` | `str \| None` | Item type (journal-article, etc.) |
| `tags` | `list[str]` | Tags / keywords |
| `search_terms` | `str \| None` | Search strategy string |
| `search_date` | `str \| None` | Date of retrieval |
| `database` | `str \| None` | Source database / platform |
| `journal_quartile` | `str \| None` | Journal quartile or SJR tier |
| `validation_status` | `ValidationStatus` | Validation state enum |
| `sync_metadata` | `dict` | Notion sync metadata (see below) |
| `provenance` | `dict` | Origin metadata |

**`sync_metadata` sub-keys:**

| Key | Description |
|-----|-------------|
| `notion_properties` | Workflow status fields (`Status`, `Status_1`) |
| `domain_properties` | Domain-specific Notion properties extracted via the active domain pack's `notion_properties` list (e.g. reading workflow checkboxes, Learner Population, Work Nature) |

### `Task`
A canonical task (analysis dimension) defined by a domain pack.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Canonical task ID |
| `name` | `str` | Human-facing name |
| `aliases` | `list[str]` | Heading aliases |
| `template_id` | `str \| None` | Associated extraction template |
| `family` | `str \| None` | Task family grouping |
| `domain_pack` | `str \| None` | Source domain pack ID |

### `ReferenceTask`, `TaskExtraction`, `WorkflowState`, `Annotation`
See `src/notion_zotero/core/models.py` for full field definitions.

---

## `notion_zotero.core.normalize`

```python
normalize_title(title: str) -> str
normalize_authors(authors: str | list[str]) -> str
normalize_doi(doi: str) -> str
```

---

## `notion_zotero.core.citation`

```python
citation_from_reference(ref: Reference, style: str = "apa") -> str
```

---

## `notion_zotero.core.exceptions`

| Exception | When raised |
|-----------|-------------|
| `NotionZoteroError` | Base class |
| `ImportError` | Page parsing fails |
| `FieldMappingError(field, source)` | Required field cannot be mapped |
| `SchemaValidationError(model, details)` | Canonical object fails validation |
| `DomainPackError(pack_id, reason)` | Domain pack load/resolve failure |
| `TemplateError(template_id, reason)` | Template missing or invalid |
| `ProvenanceError` | Required provenance missing |

---

## `notion_zotero.schemas.task_registry`

### Functions

```python
list_domain_packs() -> list[str]
```
Returns the IDs of all registered domain packs (e.g. `["education_learning_analytics"]`).

```python
load_domain_pack(name: str) -> dict | None
```
Returns the domain pack dict for `name`, or `None` if not registered.

```python
resolve_task_alias(domain_pack: dict, heading: str | None) -> str | None
```
Resolves a Notion heading to a task ID using substring alias matching against the provided pack. Returns `None` if no alias matches; logs a `WARNING` when the heading is non-empty but unmatched.

```python
match_heading_to_task(heading: str | None) -> str | None
```
Convenience wrapper — resolves `heading` against the built-in `education_learning_analytics` pack.

```python
get_applicable_tasks(item: dict) -> list[tuple[str, callable]]
```
Returns `[(task_id, parser), ...]` for the given item dict. `item` must contain `"heading"` (str) and optionally `"_domain_pack"` (dict) to override the default pack. Logs a warning when `heading` is non-empty and matches no task.

### Domain Pack Dict Schema

```python
{
    "id": str,          # unique pack identifier
    "version": str,     # semantic version string, e.g. "1.1"
    "name": str,        # human-facing display name
    "tasks": {
        "<task_id>": {
            "name": str,              # human-facing task name
            "aliases": list[str],     # heading substrings to match (case-insensitive)
            "template_id": str,       # key in schemas.templates.generic.TEMPLATES
        },
        ...
    },
    "notion_properties": list[str],   # Notion property names to extract into sync_metadata["domain_properties"]
    "task_labels": dict[str, str],    # task_id -> short label (used by task_label_fn)
}
```

**Canonical bundle provenance** — each bundle produced by the importer includes:
```python
{
    "provenance": {
        "domain_pack_id": str,      # pack ID used at import time
        "domain_pack_version": str, # pack version used at import time
    },
    ...
}
```

---

## `notion_zotero.schemas.templates.generic`

```python
TEMPLATES: dict[str, ExtractionTemplate]
```

Keys: `prediction_modeling`, `descriptive_analysis`, `recommendation_system`, `sequence_tracing`, `generic_systematic_review`, `summary_table`, `methods_table`, `dataset_table`, `findings_table`, `conclusions_table`, `metrics_table`, `population_table`, `limitations_table`.

---

## `notion_zotero.analysis`

```python
load_canonical_records(canonical_dir: str | Path) -> list[dict]
```
Load all `*.canonical.json` bundles from a directory.

```python
build_summary_tables(bundles, task_label_fn=None) -> dict[str, list[dict]]
```
Build one list of row-dicts per task label. Always includes `"Reading List"` key. Rows include both `notion_properties` and `domain_properties` spread as named columns.

```python
build_summary_dataframes(bundles, task_label_fn=None) -> dict[str, pd.DataFrame]
```
Same as above, wrapped in `pd.DataFrame`. Requires `pandas`.

```python
clean_table(df, typo_fixes=None, value_map=None, search_strategy_columns=None) -> tuple[pd.DataFrame, dict]
```
Clean a summary DataFrame: normalise typos, apply value maps, standardise search strings.

```python
run_analysis(canonical_dir, task_label_fn=None, typo_fixes=None, value_map=None, search_strategy_columns=None) -> tuple[raw_dfs, clean_dfs, norm_log]
```
Full pipeline: load → summarise → clean.

```python
is_accepted(bundle: dict) -> bool
```
Returns `True` if the bundle's workflow state or Status property contains `"accepted"`. Returns `True` when no status is found (include-by-default). Pandas-free.

```python
task_label_fn(task_name: str | None) -> str
```
Maps a task name to a short display label using the `education_learning_analytics` pack's `task_labels` dict. Falls back to the raw name if no match. Pandas-free.

---

## CLI

```
notion-zotero pull-notion                # pull live Notion DB into canonical bundles
  --name <subfolder>                     #   target subfolder under data/pulled/notion
  --database-id <id>                     #   override NOTION_DATABASE_ID from .env
  --skip-blocks                          #   metadata-only (faster, no tables/blocks)
notion-zotero list-domain-packs          # list registered domain packs
notion-zotero list-templates             # list registered extraction templates
notion-zotero parse-fixtures             # parse reading list fixtures
notion-zotero validate-fixtures          # validate canonical fixture files
notion-zotero merge-canonical            # merge per-page canonical files
notion-zotero dedupe-canonical           # deduplicate merged canonical
notion-zotero zotero-citation --file F   # print citation for item
notion-zotero export-snapshot            # export Notion DB snapshot
```
