# Notion_Zotero — Detailed Development Plan

## 1) Executive summary

`Notion_Zotero` should evolve from an **early scaffold** into a **domain-agnostic reference-management and evidence-extraction toolkit** with:

- a generic canonical data model
- reusable extraction templates
- pluggable domain packs
- a read-only importer from existing source systems like Reading List
- safe future connectors for Notion and Zotero

At the current repo state, the package is still very early:

- only two architecture docs exist
- the canonical models are thin
- the importer is deterministic but semantically shallow
- the package layout still uses `src.*` imports in code and entrypoints
- the CLI still depends on legacy code in `src/analysis`
- there is no generic template library yet
- there are no domain packs yet

This plan assumes the following product principle:

> The **core package must stay generic**.  
> Ricardo’s current literature review should be represented as **one domain pack**, not hardcoded into the core.

---

## 2) Product vision

### 2.1 Core mission

Build a Python package that can:

1. ingest literature-review source data from systems like Notion,
2. reconstruct canonical research objects,
3. preserve provenance,
4. support multiple analytical task types,
5. remain reusable across other domains and review designs.

### 2.2 Target architecture

The package should eventually support three layers:

#### A. Core canonical model
Generic entities that do not depend on a specific domain.

- `Reference`
- `Task`
- `ReferenceTask`
- `TaskExtraction`
- `WorkflowState`
- `Annotation`

#### B. Template library
Reusable structured extraction templates.

Examples:
- `prediction_modeling`
- `descriptive_analysis`
- `recommendation_system`
- `sequence_tracing`
- `generic_systematic_review`
- `qualitative_synthesis`

#### C. Domain packs
Thin mapping layers that connect domain-specific nomenclature to generic templates.

Examples:
- `education_learning_analytics`
- `generic_literature_review`
- future: `migration_policy_review`
- future: `health_systematic_review`

---

## 3) Current repo state

Based on the current uploaded `Notion_Zotero.zip`, the repo currently contains:

### Present
- `docs/constraints.md`
- `docs/source_of_truth.md`
- `src/core/models.py`
- `src/services/reading_list_importer.py`
- `src/cli.py`
- `src/analysis/` (legacy code copied from old package)
- basic tests for CLI and importer

### Missing or incomplete
- no real package namespace like `src/notion_zotero/...`
- no `schemas/` layer
- no `connectors/` layer
- no `legacy/` layer separate from old code
- no domain packs
- no extraction template library
- no status mapping rules module
- no robust importer semantics
- no provenance standard
- no deterministic canonical IDs
- no migration audit module

### Immediate technical problems
- `pyproject.toml` console scripts point to `src.*` import paths
- `src/cli.py` imports helpers from legacy `src.analysis`
- `reading_list_importer.py` uses `sys.path` hacks and imports from `src.core.models`
- the importer does not decode `status` properties
- the importer merges `Status` and `Status_1` incorrectly
- the importer only handles simplistic `Summary Table` parsing

---

## 4) Development principles

### 4.1 Source-of-truth policy
- **Reading List remains immutable**.
- All migrations are read-only from Reading List.
- New structures are built from imported canonical objects.

### 4.2 Core-generic policy
- The core package must not be shaped around Ricardo’s current review.
- Domain-specific behavior must live in domain packs.
- Extraction structures must be reusable via templates.

### 4.3 Provenance-first policy
Every imported object should preserve:
- source page id
- source property names
- source heading/block
- row index when extracted from tables
- parser notes for ambiguities

### 4.4 Rule-driven semantics
Meaning should come from:
- domain packs
- template definitions
- explicit status mapping rules

not from ad hoc string hacks scattered across importer logic.

### 4.5 Legacy containment
The old `src/analysis` code should be preserved only as:
- a reference implementation
- a migration aid
- a fallback for audit/debugging

It should not define the new package semantics.

---

## 5) Detailed roadmap

# Phase 1 — Package boundary and developer ergonomics

## Goal
Make the package installable, importable, and structurally sane before deeper semantic work.

## Why this phase first
The current repo still behaves like a partially migrated codebase. If agents build on top of the current import layout, they will entrench confusion.

## Tasks

### 5.1 Create a real package namespace

#### Target layout
```text
src/
  notion_zotero/
    __init__.py
    cli.py
    core/
    services/
    schemas/
    connectors/
    legacy/
    scripts/
```

#### Actions
- move `src/core/` to `src/notion_zotero/core/`
- move `src/services/` to `src/notion_zotero/services/`
- move `src/cli.py` to `src/notion_zotero/cli.py`
- move `scripts/export_reading_list.py` into `src/notion_zotero/scripts/export_reading_list.py`
- move `src/analysis/` to `src/notion_zotero/legacy/analysis/`

### 5.2 Update `pyproject.toml`

#### Required changes
Use the real package namespace for console scripts.

Example target:
```toml
[tool.setuptools.packages.find]
where = ["src"]

[project.scripts]
export-reading-list = "notion_zotero.scripts.export_reading_list:main"
import-reading-list = "notion_zotero.services.reading_list_importer:main"
notion-zotero = "notion_zotero.cli:main"
```

### 5.3 Remove path hacks from code

#### Replace
- `sys.path.insert(...)`
- imports like `from src.core.models import ...`

#### With
- `from notion_zotero.core.models import ...`

### 5.4 Fix test import behavior

#### Add
Either:
- `pythonpath = src` to `pytest.ini`, or
- a documented editable-install-only test flow

#### Prefer
A simple `pytest.ini` plus `pip install -e .` in dev instructions.

## Deliverables
- package import works with `pip install -e .`
- `notion-zotero --help` works
- `import-reading-list --help` works
- no code imports from `src.*`

## Exit criteria
The repo behaves like a normal Python package.

---

# Phase 2 — Strengthen the core canonical model

## Goal
Turn the current thin models into a stable generic foundation.

## Files
- `src/notion_zotero/core/models.py`
- `src/notion_zotero/core/enums.py` (new)
- `src/notion_zotero/core/normalize.py` (new)
- `src/notion_zotero/core/citation.py` (new)

## Tasks

### 6.1 Expand `models.py`

#### Keep entities
- `Reference`
- `Task`
- `ReferenceTask`
- `TaskExtraction`
- `WorkflowState`
- `Annotation`

#### Add fields

### `Reference`
- `item_type`
- `tags`
- `provenance`

### `Task`
- `template_id`
- `family`
- `domain_pack`
- `aliases`

### `ReferenceTask`
- `assignment_source`
- `inclusion_decision_for_task`
- `relevance_notes`
- `created_from_source`
- `provenance`

### `TaskExtraction`
- `template_id`
- `schema_name`
- `raw_headers`
- `validation`
- `revision_status`
- `provenance`

### `WorkflowState`
- `source_field`
- `parser_notes`

### `Annotation`
- `kind`
- `provenance`

### 6.2 Add `core/enums.py`
Define enums/constants for:
- workflow states
- assignment decisions
- annotation kinds
- validation statuses

### 6.3 Add `core/normalize.py`
Move canonical normalization logic here:
- normalize titles
- normalize author strings
- normalize DOI
- normalize headings
- normalize statuses

### 6.4 Add `core/citation.py`
Move lightweight citation formatting here so CLI no longer depends on legacy code.

## Deliverables
- enriched typed models
- no reliance on legacy helpers for canonical operations

## Exit criteria
The canonical layer is strong enough to model multiple domains.

---

# Phase 3 — Introduce a generic template library

## Goal
Make extraction structures reusable across domains.

## Why
You want the package to be agnostic. The right place to encode structural variation is the template layer, not the core and not ad hoc importer code.

## Files
- `src/notion_zotero/schemas/templates/base.py`
- `src/notion_zotero/schemas/templates/generic.py`
- `docs/template_library.md`

## Tasks

### 7.1 Create `templates/base.py`
Define base classes such as:
- `ColumnDefinition`
- `ExtractionTemplate`
- `TemplateMatchRule`
- `TemplateValidationResult`

Each template should support:
- template id
- display name
- expected columns
- required vs optional columns
- column aliases
- validation rules
- normalization rules

### 7.2 Create `templates/generic.py`
Add reusable templates such as:
- `prediction_modeling`
- `descriptive_analysis`
- `recommendation_system`
- `sequence_tracing`
- `generic_systematic_review`
- `qualitative_synthesis`

### 7.3 Keep templates genuinely reusable
Templates should describe the structure of extraction, not the exact domain vocabulary.

Example:
- `prediction_modeling` should describe columns like target, features, models, evaluation, metrics, comments, limitations
- not just educational review language

## Deliverables
- reusable template library
- documentation of available templates

## Exit criteria
A new project could reuse the templates without modifying core code.

---

# Phase 4 — Add domain packs

## Goal
Map project/domain-specific nomenclature into generic tasks and templates.

## Files
- `src/notion_zotero/schemas/domain_packs/education_learning_analytics.py`
- `src/notion_zotero/schemas/domain_packs/generic_literature_review.py`
- `src/notion_zotero/schemas/task_registry.py`
- `src/notion_zotero/schemas/status_mapping.py`
- `docs/domain_packs.md`
- `docs/task_registry.md`
- `docs/status_mapping_rules.md`

## Tasks

### 8.1 Create `education_learning_analytics.py`
This pack should contain:
- canonical task ids
- human names
- aliases from headings
- aliases from `Status`
- aliases from `Status_1`
- mapping from task id to template id

Example mappings:
- `descriptive_modelling` → `descriptive_analysis`
- `performance_prediction` → `prediction_modeling`
- `recommender_systems` → `recommendation_system`
- `knowledge_tracing` → `sequence_tracing`

### 8.2 Create `generic_literature_review.py`
A generic starter pack for other projects.

This pack should support:
- generic summary tables
- generic review workflow states
- minimal default mappings

### 8.3 Create `task_registry.py`
The registry should:
- list domain packs
- load a selected domain pack
- resolve tasks by alias
- resolve templates by task id
- expose a clean API to the importer

### 8.4 Create `status_mapping.py`
Make this the only place that interprets:
- `Status`
- `Status_1`

It should decide whether each label implies:
- workflow state
- task assignment
- exclusion decision
- ambiguity note

## Deliverables
- at least two domain packs
- registry-based task and status resolution

## Exit criteria
The importer can operate with different domain packs without changing core logic.

---

# Phase 5 — Rewrite the importer around domain packs and templates

## Goal
Turn the importer into a robust semantic orchestrator.

## File
- `src/notion_zotero/services/reading_list_importer.py`

## Tasks

### 9.1 Replace direct imports and path hacks
Use:
- `notion_zotero.core.models`
- `notion_zotero.schemas.task_registry`
- `notion_zotero.schemas.status_mapping`
- `notion_zotero.schemas.templates`

### 9.2 Improve property decoding
Extend `prop_value()` to support:
- `status`
- `checkbox`
- richer text variants if needed

### 9.3 Expand field mapping
Map all of these:
- `Title` or `Name` → `Reference.title`
- `Author` or `Authors` → `Reference.authors`
- `Year` → `Reference.year`
- `Journal` → `Reference.journal`
- `DOI` → `Reference.doi`
- `URL` → `Reference.url`
- `Zotero Key` → `Reference.zotero_key`
- `Abstract Text` or `Abstract` → `Reference.abstract`
- `Article Type` → `Reference.item_type`
- `Keywords`, `Keywords/Type`, or analogous fields → `Reference.tags`

### 9.4 Build importer flow around canonical semantics
New flow should be:

1. build `Reference`
2. interpret `Status`
3. interpret `Status_1`
4. create `WorkflowState`
5. create `ReferenceTask`s from domain-pack rules
6. parse tables
7. match each table heading to a task and template
8. validate extracted table against template
9. attach `TaskExtraction` to the correct `ReferenceTask`
10. convert paragraphs/free text into `Annotation`

### 9.5 Remove fake task inference
Do **not** create tasks from arbitrary text like `Summary`, `Methods`, or `Dataset` unless the selected domain pack explicitly defines them.

### 9.6 Add deterministic IDs
Replace random UUID fragments with stable IDs based on:
- page id
- task id
- table index
- row index

### 9.7 Add provenance everywhere
Every object should capture provenance consistently.

## Deliverables
- a domain-pack-driven importer
- stable canonical JSON output

## Exit criteria
Running the importer twice on the same fixture produces semantically correct and stable output.

---

# Phase 6 — Improve the CLI and local workflows

## Goal
Make the package pleasant to use locally and clearly generic.

## File
- `src/notion_zotero/cli.py`

## Tasks

### 10.1 Stop importing canonical logic from legacy
Remove direct dependencies on:
- `src.analysis.normalize_title`
- `src.analysis.normalize_authors`
- `src.analysis.citation_from_item`

Replace with:
- `notion_zotero.core.normalize`
- `notion_zotero.core.citation`

### 10.2 Add domain-pack and template visibility
Add commands like:
- `list-domain-packs`
- `list-templates`
- `parse-fixtures --domain-pack ...`
- `validate-fixtures --domain-pack ...`

### 10.3 Keep export/import orchestration clean
CLI should orchestrate, not contain business logic.

## Deliverables
- clearer CLI
- visible generic architecture from the command line

## Exit criteria
A new user can discover domain packs and templates from the CLI.

---

# Phase 7 — Documentation pass

## Goal
Make the architecture understandable to contributors and agents.

## Files to create
- `docs/field_classification.md`
- `docs/canonical_schema.md`
- `docs/relationship_model.md`
- `docs/reading_list_to_canonical_mapping.md`
- `docs/template_library.md`
- `docs/domain_packs.md`
- `docs/task_registry.md`
- `docs/status_mapping_rules.md`

## Tasks
Document:
- what each canonical entity means
- how templates differ from domain packs
- how Reading List maps into the canonical schema
- how workflow differs from task assignment
- what provenance fields are required

## Deliverables
A contributor can understand the design without reverse engineering code.

## Exit criteria
Docs explain both the generic architecture and the current domain-pack implementation.

---

# Phase 8 — Fixtures and semantic test suite

## Goal
Make correctness testable.

## Directories
- `fixtures/reading_list/golden/`
- `fixtures/canonical/golden/`

## Add golden fixture cases
- one `DESC` paper
- one `PRED` paper
- one `REC` paper
- one `KT` paper
- one multi-task paper
- one paper using `Status_1`
- one malformed table case
- one no-table page

## Tests to add/update
- `tests/test_task_registry.py`
- `tests/test_status_mapping.py`
- `tests/test_template_validation.py`
- `tests/test_reading_list_importer.py`
- `tests/test_cli.py`

## What tests should assert
- correct mapping from heading to canonical task
- correct mapping from `Status` / `Status_1`
- no fake tasks from arbitrary headings
- correct extraction of bibliographic fields
- deterministic IDs
- provenance presence
- template validation behavior

## Deliverables
- a semantic regression suite

## Exit criteria
The test suite fails when meaning breaks, not just when syntax breaks.

---

# Phase 9 — Legacy containment and migration audit

## Goal
Keep the old system available as reference, but prevent it from defining the new package.

## Files
- `src/notion_zotero/legacy/analysis/...`
- `src/notion_zotero/services/migration_audit.py`
- `docs/v3_gap_analysis.md`

## Tasks

### 13.1 Move old code fully under `legacy/`
Mark it clearly as:
- reference implementation
- migration aid
- not authoritative for new semantics

### 13.2 Add `migration_audit.py`
Compare:
- canonical objects derived from Reading List
- the old migrated v3 structures

Audit should compare:
- reference field coverage
- task assignment coverage
- extraction coverage
- workflow preservation
- provenance completeness
- naming drift

## Deliverables
- legacy isolated
- semantic migration audit

## Exit criteria
You can explain why v3 felt wrong and what the new model preserves better.

---

# Phase 10 — Future-ready connector layer (later)

## Goal
Prepare for future Notion/Zotero integration without building the full sync engine yet.

## Files
- `src/notion_zotero/connectors/notion/`
- `src/notion_zotero/connectors/zotero/`

## Scope now
Only create stubs/interfaces and simple readers where needed.
Do **not** build:
- full two-way sync
- webhooks
- MCP
- dashboard UI

## Why later
The canonical importer and semantic model must be correct first.

---

## 6) Workstream breakdown for agents

### Workstream A — Packaging and structure
Owns:
- package namespace
- entrypoints
- editable install
- test import behavior

### Workstream B — Core model and normalization
Owns:
- models
- enums
- normalization
- citation helpers

### Workstream C — Templates and domain packs
Owns:
- template library
- domain packs
- task registry
- status mapping

### Workstream D — Importer
Owns:
- property decoding
- semantic import flow
- provenance
- deterministic IDs

### Workstream E — Docs and tests
Owns:
- architecture docs
- golden fixtures
- semantic test suite

### Workstream F — Legacy audit
Owns:
- legacy isolation
- migration audit
- v3 gap analysis

---

## 7) Recommended implementation order

1. **Phase 1** — package namespace + entrypoints + import cleanup  
2. **Phase 2** — strengthen core model and helpers  
3. **Phase 3** — template base + generic templates  
4. **Phase 4** — domain packs + task registry + status mapping  
5. **Phase 5** — importer rewrite around templates/domain packs  
6. **Phase 6** — CLI cleanup and domain-pack-aware commands  
7. **Phase 7** — docs completion  
8. **Phase 8** — golden fixtures + semantic tests  
9. **Phase 9** — legacy isolation + migration audit  
10. **Phase 10** — connector stubs only

---

## 8) Detailed acceptance criteria by milestone

### Milestone A — “Real package”
- repo installs with `pip install -e .`
- `notion-zotero --help` works
- no imports from `src.*`

### Milestone B — “Generic core”
- models are richer and generic
- normalization and citation helpers live in core
- CLI no longer depends on legacy for canonical behavior

### Milestone C — “Template system exists”
- generic templates are available
- domain pack can map tasks to templates

### Milestone D — “Semantic importer”
- importer decodes real Reading List fields
- workflow is separate from task assignment
- deterministic IDs are used
- provenance is attached to all objects

### Milestone E — “Contributor-ready package”
- docs explain architecture
- tests enforce semantics
- domain packs are discoverable from CLI

### Milestone F — “Legacy contained”
- old code lives under `legacy/`
- migration audit explains differences meaningfully

---

## 9) What not to do yet

Do **not** spend time on these until the package reaches Milestone D or E:

- full Notion writer / staging projection
- full Zotero sync engine
- two-way sync
- webhook processing
- MCP support
- dashboard / Reflex UI
- production writes to live systems

These all depend on a stable semantic core.

---

## 10) Key design rules to keep repeating

1. **Core stays generic.**  
2. **Templates are reusable structures.**  
3. **Domain packs provide domain-specific mappings.**  
4. **Importer orchestrates; it does not invent semantics.**  
5. **Reading List remains immutable.**  
6. **Legacy code is reference-only.**  
7. **Provenance is mandatory.**

---

## 11) Suggested first 3 sprints

### Sprint 1
- package namespace cleanup
- pyproject fix
- move core/services/cli into `notion_zotero`
- add `schemas/`, `legacy/`, `connectors/`
- add `core/enums.py`, `core/normalize.py`, `core/citation.py`

### Sprint 2
- build template base
- create generic templates
- build `education_learning_analytics` domain pack
- build `generic_literature_review` domain pack
- add `task_registry.py` and `status_mapping.py`

### Sprint 3
- rewrite importer
- add richer field mapping
- separate workflow/task logic
- add deterministic IDs
- add provenance
- add golden semantic tests

---

## 12) Final success definition

This package development plan is successful when `Notion_Zotero` can be honestly described as:

> A generic Python package for canonicalizing literature-review source data into reusable research objects, using pluggable domain packs and extraction templates, with provenance preserved and legacy migration behavior safely contained.

