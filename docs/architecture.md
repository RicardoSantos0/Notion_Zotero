# Architecture

`notion_zotero` is a domain-agnostic reference-management and evidence-extraction toolkit structured around three layers.

## Package layout

```
src/notion_zotero/
  core/          # Canonical data model, normalization, citation helpers, exceptions
  schemas/       # Template library, domain packs, task registry, status mapping
  services/      # Reading list importer
  cli.py         # Command-line interface
  scripts/       # Standalone helper scripts
  legacy/        # Reference-only copy of pre-migration code
```

## Data flow

```
Source (Notion Reading List)
        │  read-only
        ▼
services/reading_list_importer.py
        │  decodes properties, resolves tasks via domain pack
        ▼
core/models.py   (Reference, Task, ReferenceTask, TaskExtraction, WorkflowState, Annotation)
        │  canonical JSON bundles
        ▼
fixtures/canonical/   (*.canonical.json)
        │  merge + dedupe
        ▼
fixtures/canonical_merged.dedup.json
```

## Three-layer design

### Layer 1 — Core canonical model (`core/`)
Generic Python dataclasses that do not depend on any specific domain:
`Reference`, `Task`, `ReferenceTask`, `TaskExtraction`, `WorkflowState`, `Annotation`.

Helpers: `normalize.py` (title/author/DOI), `citation.py` (APA-style), `enums.py` (workflow states), `exceptions.py` (typed error hierarchy).

### Layer 2 — Template library (`schemas/templates/`)
Reusable structured extraction templates. Each template describes:
- expected column names + aliases
- required vs optional columns

Templates are domain-agnostic (e.g. `prediction_modeling`, `descriptive_analysis`). They do not know about educational or any other domain vocabulary.

### Layer 3 — Domain packs (`schemas/domain_packs/`)
Thin mapping layers that connect project-specific terminology to generic templates.

A domain pack declares:
- canonical task IDs
- human-facing names
- heading aliases (for matching table headers)
- `Status` / `Status_1` alias lists
- mapping from task ID → template ID

The importer selects a domain pack at runtime. Core logic stays unchanged.

## Design principles

1. **Core stays generic** — no domain-specific hardcoding in `core/`.
2. **Templates are reusable structures** — not domain vocabulary.
3. **Domain packs provide the mapping** — one pack per review domain.
4. **Importer orchestrates** — it does not invent semantics.
5. **Reading List is immutable** — all imports are read-only.
6. **Legacy code is reference-only** — `legacy/` is not authoritative.
7. **Provenance is mandatory** — every object records its origin.
