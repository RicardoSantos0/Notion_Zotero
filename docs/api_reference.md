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
| `abstract` | `str \| None` | Abstract text |
| `item_type` | `str \| None` | Item type (journal-article, etc.) |
| `tags` | `list[str]` | Tags / keywords |
| `provenance` | `dict` | Origin metadata |

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
    "version": str,     # semantic version string, e.g. "1.0"
    "name": str,        # human-facing display name
    "tasks": {
        "<task_id>": {
            "name": str,              # human-facing task name
            "aliases": list[str],     # heading substrings to match (case-insensitive)
            "template_id": str,       # key in schemas.templates.generic.TEMPLATES
        },
        ...
    },
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

## CLI

```
notion-zotero list-domain-packs          # list registered domain packs
notion-zotero list-templates             # list registered extraction templates
notion-zotero parse-fixtures             # parse reading list fixtures
notion-zotero validate-fixtures          # validate canonical fixture files
notion-zotero merge-canonical            # merge per-page canonical files
notion-zotero dedupe-canonical           # deduplicate merged canonical
notion-zotero zotero-citation --file F   # print citation for item
notion-zotero export-snapshot            # export Notion DB snapshot
```
