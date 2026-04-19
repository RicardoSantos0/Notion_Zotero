# Detailed Patch Plan for `Notion_Zotero`

## Purpose

This document gives a **file-by-file implementation plan** for continuing the refactor from the original `Literature Review Analysis` repository into `Notion_Zotero`.

It is designed to be given to an agent or agent network.

The plan is grounded in the **current repository state** and adds one important architectural correction:

> The package should become **domain-agnostic at the core**, while allowing **domain-specific review architectures** to be represented through **domain packs** and **reusable extraction templates**.

That means the package should not hardcode Ricardo's current review into the core logic, even though the current review is the first and most important implementation case.

---

## 1. Current repository state

The current `Notion_Zotero` repository has:

- `docs/constraints.md`
- `docs/source_of_truth.md`
- `fixtures/reading_list/`
- `fixtures/canonical/`
- `fixtures/canonical_merged.json`
- `pyproject.toml`
- `scripts/export_reading_list.py`
- `src/__init__.py`
- `src/cli.py`
- `src/core/models.py`
- `src/services/reading_list_importer.py`
- `src/analysis/` copied from the legacy repo
- a small test suite in `tests/`

### What is good already

- There is a separate target repo.
- The repo acknowledges Reading List as source-of-truth.
- There is an early canonical model.
- There is an importer and a CLI.
- There are fixtures and smoke tests.

### What is not correct yet

- The package layout is not a proper installed Python package.
- Console script entrypoints point to `src.*` and are likely to break after installation.
- The core model is too thin.
- The importer is too generic in the wrong way.
- The importer treats task semantics as string fragments rather than modeling them explicitly.
- The importer is not domain-agnostic; it is currently **under-specified**, not properly generalized.
- `src/analysis/` is still implicitly shaping the new code instead of being isolated as legacy.
- There is no real separation yet between:
  - reusable extraction template library
  - domain-specific review pack
  - generic core model

---

## 2. Architectural correction to apply now

## 2.1 What the core package should be

The core package should be **generic** and centered on these first-class entities:

- `Reference`
- `Task`
- `ReferenceTask`
- `TaskExtraction`
- `WorkflowState`
- `Annotation`

These should not encode a specific research domain.

## 2.2 What should carry domain specificity

Domain specificity should live in **domain packs** and **template mappings**.

### A. Extraction template library
Reusable extraction template families such as:

- `prediction_modeling`
- `descriptive_analysis`
- `recommendation_system`
- `sequence_tracing`
- `generic_systematic_review`
- `qualitative_synthesis`
- `intervention_study`

These are **not domain names**. They are reusable structural templates.

### B. Domain packs
A domain pack maps a specific review's semantics into the generic core.

A domain pack should define:

- canonical task ids
- human-facing task names
- aliases from headings
- aliases from status labels
- mappings from task ids to template ids
- workflow interpretation rules if needed

Your current review should become one domain pack, for example:

- `education_learning_analytics`

Later, new packs could be added such as:

- `migration_policy_review`
- `health_systematic_review`
- `marketing_literature_review`

## 2.3 The governing rule

> Core model stores the truth.
> Domain packs decide what headings/statuses mean.
> Templates decide what structured extraction columns are expected.
> Importers only orchestrate.

---

## 3. Target package structure

The current `src/` layout should evolve into a real package rooted at `notion_zotero`.

### Target structure

```text
src/
  notion_zotero/
    __init__.py
    cli.py
    core/
      models.py
      enums.py
      normalize.py
      citation.py
    schemas/
      task_registry.py
      status_mapping.py
      templates/
        base.py
        generic.py
      domain_packs/
        education_learning_analytics.py
    services/
      reading_list_importer.py
      migration_audit.py
    connectors/
      notion/
      zotero/
    scripts/
      export_reading_list.py
    legacy/
      analysis/
```

### Important note

The current `src/analysis/` should be moved under `legacy/analysis/` and clearly marked as **legacy reference code only**.

---

## 4. File-by-file patch plan

## Patch Group A — Fix package layout and installability

### 4.1 `pyproject.toml`

### Current problem

The project is named `notion_zotero`, but the console scripts still point to `src.*` modules:

```toml
[project.scripts]
export-reading-list = "src.scripts.export_reading_list:main"
import-reading-list = "src.services.reading_list_importer:main"
notion-zotero = "src.cli:main"
```

This is fragile and incorrect for a proper installed package.

### Patch

Change the package entrypoints to use a real package root.

#### Target form

```toml
[tool.setuptools.packages.find]
where = ["src"]

[project.scripts]
export-reading-list = "notion_zotero.scripts.export_reading_list:main"
import-reading-list = "notion_zotero.services.reading_list_importer:main"
notion-zotero = "notion_zotero.cli:main"
```

### Done when

- `pip install -e .` succeeds
- `notion-zotero --help` works
- `export-reading-list --help` works
- `import-reading-list --help` works

---

### 4.2 Create package root

### Create

- `src/notion_zotero/__init__.py`

### Move

- `src/cli.py` → `src/notion_zotero/cli.py`
- `src/core/` → `src/notion_zotero/core/`
- `src/services/` → `src/notion_zotero/services/`

### Later move

- `src/analysis/` → `src/notion_zotero/legacy/analysis/`

### Why

The repo should stop treating `src` as the package.

---

### 4.3 Move script into the package

### Create

- `src/notion_zotero/scripts/__init__.py`
- `src/notion_zotero/scripts/export_reading_list.py`

### Move

- `scripts/export_reading_list.py` into that package path

### Why

Console scripts should import real package modules, not top-level loose scripts.

---

## Patch Group B — Create missing architecture folders

### 4.4 Create these directories

- `src/notion_zotero/schemas/`
- `src/notion_zotero/schemas/templates/`
- `src/notion_zotero/schemas/domain_packs/`
- `src/notion_zotero/connectors/`
- `src/notion_zotero/connectors/notion/`
- `src/notion_zotero/connectors/zotero/`
- `src/notion_zotero/legacy/`

### Why

The current repo has no correct place yet for:

- generic template definitions
- domain pack definitions
- future Notion/Zotero connectors
- legacy code

---

## Patch Group C — Strengthen the core model

### 4.5 `src/notion_zotero/core/models.py`

### Current problem

The models are too thin to support:

- provenance-rich imports
- task template assignment
- domain pack identity
- extraction validation results
- annotation kinds

### Patch

Keep the six core entities, but expand them.

#### `Reference`
Add or retain:
- `id`
- `title`
- `authors`
- `year`
- `journal`
- `doi`
- `url`
- `zotero_key`
- `abstract`
- `item_type`
- `tags`
- `provenance`

#### `Task`
Add:
- `id`
- `name`
- `aliases`
- `template_id`
- `family`
- `domain_pack`

#### `ReferenceTask`
Add:
- `assignment_source`
- `inclusion_decision_for_task`
- `relevance_notes`
- `created_from_source`
- `provenance`

#### `TaskExtraction`
Add:
- `template_id`
- `schema_name`
- `raw_headers`
- `validation`
- `provenance`
- `revision_status`

#### `WorkflowState`
Add:
- `state`
- `source_field`
- `provenance`

#### `Annotation`
Add:
- `kind`
- `text`
- `provenance`

### Why

The importer needs to preserve more than raw content. It needs to preserve meaning and traceability.

---

### 4.6 Create `src/notion_zotero/core/enums.py`

### Add enums/constants for

- workflow states
- annotation kinds
- assignment decisions
- extraction validation statuses

### Why

This prevents string drift between importer, tests, and future services.

---

### 4.7 Create `src/notion_zotero/core/normalize.py`

### Add helpers for

- title normalization
- author normalization
- DOI normalization
- heading normalization
- status normalization
- URL normalization

### Why

The new package should stop importing normalization helpers from legacy code.

---

### 4.8 Create `src/notion_zotero/core/citation.py`

### Add

- lightweight citation formatting for canonical references

### Why

`cli.py` currently imports citation logic from legacy code. That should be local to the new package.

---

## Patch Group D — Add generic extraction templates

This is the key change that makes the package genuinely reusable.

### 4.9 Create `src/notion_zotero/schemas/templates/base.py`

### Add base classes or typed structures for

- `ExtractionTemplate`
- `ColumnDefinition`
- `TemplateMatchRule`

### Each template should define

- `template_id`
- display name
- expected columns
- column aliases
- required vs optional fields
- validation rules

### Why

Templates become reusable across domains.

---

### 4.10 Create `src/notion_zotero/schemas/templates/generic.py`

### Add generic reusable templates such as

- `prediction_modeling`
- `descriptive_analysis`
- `recommendation_system`
- `sequence_tracing`
- `generic_systematic_review`
- `qualitative_synthesis`
- `intervention_study`

### Why

These templates represent **structures**, not specific disciplines.

---

## Patch Group E — Add a domain-pack mechanism

### 4.11 Create `src/notion_zotero/schemas/domain_packs/education_learning_analytics.py`

### This file should define

- canonical task ids for the current review
- human-facing task names
- aliases from Reading List headings
- aliases from Reading List statuses
- mapping from task id → template id
- any special status interpretation rules

### Example mapping idea

- `descriptive_modelling` → `descriptive_analysis`
- `performance_prediction` → `prediction_modeling`
- `recommender_systems` → `recommendation_system`
- `knowledge_tracing` → `sequence_tracing`

### Why

This lets the current project be represented faithfully without hardcoding it into the core package.

---

### 4.12 Create `src/notion_zotero/schemas/task_registry.py`

### Add a registry loader that can

- list available domain packs
- load one domain pack
- resolve task aliases
- resolve template ids
- match heading text to canonical task ids

### Why

The importer should rely on the registry, not on inline string hacks.

---

### 4.13 Create `src/notion_zotero/schemas/status_mapping.py`

### Add explicit rules for interpreting

- `Status`
- `Status_1`

### It should map labels into

- workflow states
- task assignments
- rejection/exclusion decisions
- ambiguity notes when mapping is unclear

### Why

Status semantics are too important to be embedded informally in the importer.

---

## Patch Group F — Rewrite importer around templates and domain packs

### 4.14 `src/notion_zotero/services/reading_list_importer.py`

This is the most important file to patch.

### Current problems

- imports using `sys.path` hacks
- imports `src.core.models`
- does not use a task registry
- does not use templates
- infers task names by splitting headings on `:` and `-`
- merges `Status` and `Status_1`
- creates random ids
- treats any task table as a loose row dictionary

### Patch

#### A. Fix imports
Replace:

```python
sys.path.insert(0, ...)
from src.core.models import ...
```

with package imports such as:

```python
from notion_zotero.core.models import ...
from notion_zotero.schemas.task_registry import ...
from notion_zotero.schemas.status_mapping import ...
from notion_zotero.schemas.templates.generic import ...
```

#### B. Add proper property decoding
Extend `prop_value()` to support:

- `status`
- `checkbox`
- title aliases
- rich_text aliases
- multi_select
- select
- url
- date
- number
- people

Also support canonical field extraction from aliases like:

- `Title` / `Name`
- `Author` / `Authors`
- `Abstract` / `Abstract Text`
- `Keywords` / `Keywords/Type`
- `URL`
- `Zotero Key`
- `Article Type`

#### C. Add domain pack argument
The importer should accept an active domain pack, for example:

```bash
--domain-pack education_learning_analytics
```

The importer should not assume only one review architecture forever.

#### D. Stop fake task inference
Delete the current logic that turns any `Summary Table ...` suffix into a direct task name.

Instead:
- normalize heading
- ask the active domain pack whether the heading maps to a known task
- if yes, create the correct canonical task and template assignment
- if no, store the table as unclassified extraction with provenance

#### E. Separate workflow from task assignment
Do not do this anymore:

```python
status = prop_value(props.get("Status") or props.get("Status_1"))
```

Instead:
- decode `Status`
- decode `Status_1`
- run both through `status_mapping.py`
- emit separately:
  - `WorkflowState`
  - `ReferenceTask`
  - ambiguity notes if needed

#### F. Make `ReferenceTask` the center
Importer order should be:
1. build `Reference`
2. resolve task assignments from statuses/headings/domain pack
3. create `ReferenceTask`
4. create `TaskExtraction` attached to a `ReferenceTask`
5. create `Annotation` for free text

#### G. Replace random IDs with deterministic IDs
Do not use `uuid.uuid4()` fragments.

Use deterministic ids based on:
- page id
- canonical task id
- table index
- row index
- block index

### Why

This one file currently determines whether the new architecture becomes semantically trustworthy.

---

### 4.15 Add a `main()` that supports domain-pack choice

### Update
The importer CLI should support:

- `--domain-pack`
- `--input`
- `--out`
- `--force`

### Why

This turns the importer into a configurable entrypoint rather than a one-off script.

---

## Patch Group G — Update the CLI to use the new package only

### 4.16 `src/notion_zotero/cli.py`

### Current problem

The current CLI still imports from legacy code:

- `src.analysis.export_database_snapshot`
- `src.analysis.normalize_title`
- `src.analysis.normalize_authors`
- `src.analysis.citation_from_item`

### Patch

Replace those imports with new package equivalents:

- `notion_zotero.core.normalize`
- `notion_zotero.core.citation`
- future `notion_zotero.connectors.notion.reader`

### Also add CLI support for

- `list-domain-packs`
- `parse-fixtures --domain-pack ...`
- `validate-canonical`

### Why

A canonical CLI should not depend on legacy Notion-specific code.

---

## Patch Group H — Add missing docs

### 4.17 Create these markdown docs

- `docs/field_classification.md`
- `docs/task_registry.md`
- `docs/canonical_schema.md`
- `docs/relationship_model.md`
- `docs/reading_list_to_canonical_mapping.md`
- `docs/status_mapping_rules.md`
- `docs/domain_packs.md`
- `docs/template_library.md`

### These docs should explain

- what belongs to the generic core
- what belongs to template definitions
- what belongs to domain packs
- how statuses are interpreted
- how Reading List maps into canonical objects

### Why

Without this, future agents will keep hardcoding semantics into code.

---

## Patch Group I — Curate fixtures for semantic testing

### 4.18 Create curated fixture folders

- `fixtures/reading_list/golden/`
- `fixtures/canonical/golden/`

### Add representative cases

- one `DESC` paper
- one `PRED` paper
- one `REC` paper
- one `KT` paper
- one multi-task paper
- one paper using `Status_1`
- one malformed or partial table
- one paper with only narrative notes

### Why

The current fixture set is too broad for semantic debugging.

---

## Patch Group J — Rewrite tests around semantic correctness

### 4.19 Replace weak smoke tests with semantic tests

### Update
- `tests/test_reading_list_importer.py`
- `tests/test_cli.py`

### Add
- `tests/test_task_registry.py`
- `tests/test_status_mapping.py`
- `tests/test_template_matching.py`
- `tests/test_extraction_validation.py`
- `tests/test_canonical_ids.py`

### Test for

- correct mapping from heading → canonical task
- correct mapping from `Status` / `Status_1`
- correct workflow extraction
- correct bibliographic field extraction
- correct template assignment
- deterministic ids
- provenance presence
- graceful handling of unclassified tables
- no fake generic tasks created from arbitrary headings

### Why

The current tests only prove that code runs, not that it is right.

---

## Patch Group K — Isolate legacy code

### 4.20 Move `src/analysis/` into legacy

### Move

- `src/analysis/` → `src/notion_zotero/legacy/analysis/`

### Add clear module note

This code is:
- legacy reference code only
- useful for understanding old behavior
- not authoritative for new semantics

### Why

The old implementation should remain available, but it should not keep silently driving the new architecture.

---

## Patch Group L — Add migration audit later, but not too late

### 4.21 Create `src/notion_zotero/services/migration_audit.py`

### Add
A semantic comparison tool that compares:

- Reading List–derived canonical objects
- v3-derived objects or fixtures

### Compare

- reference field coverage
- task assignment differences
- workflow differences
- extraction count differences
- naming drift
- flattened semantics

### Why

This is the tool that will explain **why v3 felt wrong**, not just that it differs.

---

## 5. Execution order

Use this exact order.

1. Fix package root and entrypoints
2. Create architecture folders
3. Strengthen core models and helpers
4. Add generic templates
5. Add current-review domain pack
6. Add task registry and status mapping
7. Rewrite importer around domain pack + template registry
8. Update CLI to remove legacy dependencies
9. Add docs
10. Curate golden fixtures
11. Rewrite tests around semantics
12. Move legacy code under `legacy/`
13. Add migration audit

---

## 6. What not to implement yet

Do **not** start these before the above is done:

- two-way sync
- Notion webhook handling
- live Notion writing
- staging writer for production-like use
- Zotero write-back
- Reflex UI
- MCP integration
- dashboards

These all depend on a correct canonical semantic layer.

---

## 7. Agent execution brief

Use this brief for the next implementation wave.

```text
Goal:
Refactor Notion_Zotero into a domain-agnostic canonical package with pluggable domain packs and reusable extraction templates.

Critical design rule:
Do not hardcode Ricardo's current review into the core package.
Instead:
- keep the core generic
- add reusable extraction templates
- represent the current review as a domain pack

Execute in this order:
1. Fix packaging and rename the importable package to notion_zotero
2. Create schemas/, connectors/, legacy/, and scripts/ inside the package
3. Strengthen core models and move normalization/citation helpers into core
4. Add generic extraction templates in schemas/templates/
5. Add one domain pack for the current Reading List review in schemas/domain_packs/
6. Rewrite reading_list_importer.py to use the selected domain pack and templates
7. Separate workflow from task assignment
8. Add deterministic ids and provenance
9. Update CLI to use the new package only
10. Add semantic docs
11. Add golden fixtures and semantic tests
12. Move old analysis code under legacy
13. Add migration_audit.py

Constraints:
- do not modify Reading List
- do not write to live Notion
- do not build sync/webhooks/UI/MCP yet
- do not create generic fake tasks from arbitrary headings
```

---

## 8. Final implementation rule

For the next version, make this relationship explicit:

- **domain pack** decides **what a heading/status means**
- **template** decides **what columns/structure are expected**
- **core model** stores the result
- **importer** orchestrates

This gives the project exactly the right shape:

- faithful to your current literature-review architecture
- but reusable beyond your current review

