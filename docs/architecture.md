# Architecture

`notion_zotero` is a reference-management and evidence-extraction toolkit for
literature reviews. It keeps bibliographic metadata, workflow state, and
extraction evidence in canonical JSON bundles that can be pulled from live APIs,
parsed from offline exports, analysed locally, and synchronized through a
review-first plan.

## Package layout

```
src/notion_zotero/
  analysis/      # Notebook/report helpers and paper-facing summary tables
  connectors/    # Live Notion and Zotero read/write client adapters
  core/          # Pydantic canonical models, normalization, citation, exceptions
  schemas/       # Template library, domain packs, task registry, status mapping
  services/      # Importer, diff engine, sync planner/applier, QA/report services
  writers/       # Notion/Zotero write paths, ownership filtering, write logs
  cli.py         # argparse command-line interface
  scripts/       # Standalone helper scripts
```

## Data flow

```
Notion / Zotero / raw Notion exports
        │
        ├─ connectors/*/reader.py        # live pull mode
        └─ services/reading_list_importer.py  # offline fixture mode
        ▼
core/models.py
        │  Reference, Task, ReferenceTask, TaskExtraction, WorkflowState, Annotation
        ▼
data/pulled/**/*.canonical.json
        │
        ├─ analysis/*                    # reports and paper summary tables
        ├─ services/sync_planner.py       # review-first sync_plan.json
        └─ services/sync_plan_applier.py  # dry-run/apply reviewed Notion updates
```

## Three-layer design

### Layer 1 — Core canonical model (`core/`)
Generic Pydantic v2 models that do not depend on any specific domain:
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

## Sync Safety

Zotero owns bibliographic metadata, Notion owns workflow/extraction fields, and
system fields are managed by the pipeline. Field ownership is enforced before
write operations are generated.

The recommended sync workflow is:

1. `pull-notion` and `pull-zotero` write local canonical snapshots.
2. `plan-sync` creates `data/sync_plans/sync_plan.json`.
3. `apply-plan` previews executable Notion metadata updates.
4. `apply-plan --apply` writes reviewed updates and appends NDJSON write logs.

Matching uses strong keys (`zotero_key`, DOI, title+authors) and weak title-only
matches when years are compatible. Ambiguous candidates are review-only.

## Design Principles

1. **Core stays generic** — no domain-specific hardcoding in `core/`.
2. **Templates are reusable structures** — not domain vocabulary.
3. **Domain packs provide the mapping** — one pack per review domain.
4. **Importer orchestrates** — it does not invent semantics.
5. **Review before writes** — generated plans are inspected before apply mode.
6. **Legacy code is reference-only** — `legacy/` is not authoritative.
7. **Provenance is mandatory** — every canonical bundle records its origin.
