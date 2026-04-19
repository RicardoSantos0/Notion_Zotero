# Extraction Templates (notion_zotero)

This document describes the built-in extraction templates used by `notion_zotero`.

## Overview

- Templates describe expected columns for tabular extractions (e.g., results,
  methods, datasets) so downstream code can validate and normalize extracted
  rows.
- The code objects are available under `notion_zotero.schemas.templates`.

Key types:

- `ColumnDefinition(name, aliases=[], required=False)` — header matcher for a column.
- `ExtractionTemplate(template_id, display_name, expected_columns, meta={})` — template container.

## Seeded templates

The package provides a small library of reusable templates. Below is a short
summary — see the code in `src/notion_zotero/schemas/templates/generic.py`
for canonical definitions.

- `prediction_modeling`: Prediction / Modeling results
  - expected columns: `Metric`, `Value`

- `descriptive_analysis`: Descriptive analysis / summary statistics
  - expected columns: `Measure`, `Value`

- `recommendation_system`: Recommender system / algorithm results
  - expected columns: `Algorithm`, `Metric`

- `sequence_tracing`: Sequence / tracing tables
  - expected columns: `Event`

- `generic_systematic_review`: Generic key/value review tables
  - expected columns: `Field`

- `summary_table`: Generic summary key/value
  - expected columns: `Key`, `Value`

- `methods_table`: Methods / approach descriptions
  - expected columns: `Method`, `Description`

- `dataset_table`: Dataset / sample descriptions
  - expected columns: `Dataset`, `N`

- `findings_table`: Numeric/measurement results
  - expected columns: `Measure`, `Value`

- `conclusions_table`: Conclusions / takeaways
  - expected columns: `Conclusion`

- `metrics_table`: Named evaluation metrics
  - expected columns: `Metric`, `Value`

- `population_table`: Participant/sample tables
  - expected columns: `Participant`, `N`

- `limitations_table`: Limitations / threats
  - expected columns: `Limitation`

## How templates are used

Typical flow:

1. The task registry maps table headings to canonical task ids (optionally via
   a domain pack).
2. Domain pack entries specify a `template_id` for tasks where a table layout
   is expected.
3. The importer looks up the template and emits a `TaskExtraction` with
   `template_id` and `schema_name`.

Example (Python):

```python
from notion_zotero.schemas.task_registry import match_heading_to_task
from notion_zotero.schemas.domain_packs import education_learning_analytics as ela
from notion_zotero.schemas.templates import get_template

heading = "Prediction results"
tid = match_heading_to_task(heading)
meta = ela.domain_pack["tasks"][tid]
template_id = meta.get("template_id")
t = get_template(template_id)
print(t.template_id, [c.name for c in t.expected_columns])
```

## Adding a new template

1. Create a `ColumnDefinition` list describing expected headers.
2. Add an `ExtractionTemplate` to `src/notion_zotero/schemas/templates/generic.py`.
3. Register the template id in `TEMPLATES`.

## Location

- Template code: `src/notion_zotero/schemas/templates/`
- Domain packs: `src/notion_zotero/schemas/domain_packs/`
