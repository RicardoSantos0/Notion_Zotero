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

```python
list_domain_packs() -> list[str]
load_domain_pack(name: str) -> dict | None
resolve_task_alias(domain_pack: dict, heading: str) -> str | None
match_heading_to_task(heading: str) -> str | None   # uses education pack
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
