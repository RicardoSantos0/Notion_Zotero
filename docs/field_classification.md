# Field classification — Notion → Canonical model mapping

Purpose: record deterministic mappings from Notion page properties, blocks and tables to the project's canonical Pydantic models. This file is the authoritative reference for Phase‑0 → Phase‑1 transformations.

## Canonical models referenced
- `Reference` (id, title, authors, year, journal, doi, url, zotero_key, abstract, item_type, tags)
- `Task` (id, name, aliases)
- `ReferenceTask` (id, reference_id, task_id, provenance)
- `TaskExtraction` (id, reference_task_id, schema_name, extracted, provenance, revision_status)
- `WorkflowState` (id, reference_id, state)
- `Annotation` (id, reference_id, text, provenance)

## Page-level Notion properties → Reference
- page_id (fixture top-level)  → `Reference.id`
- page title (Notion page title block) → `Reference.title`
- Authors (property name: "Authors") → `Reference.authors` (list of strings)
- Journal (property name: "Journal") → `Reference.journal` (string)
- DOI (property name: "DOI") → `Reference.doi` (string)
- URL (property name: "URL") → `Reference.url` (string)
- Zotero Key (property name: "Zotero Key") → `Reference.zotero_key` (string)
- Year: if a numeric property named "Year" exists, map to `Reference.year` (int); otherwise leave `None`.
- Abstract: if there is a dedicated property or a recognized block for abstract, populate `Reference.abstract`.

Normalization rules for properties:
- `title`, `rich_text`: concatenate `plain_text` segments into a single string.
- `select`: use the `name` string as-is.
- `multi_select`: map to list of `name` strings.
- `url`: use string value or `None`.
- `date`: use `date.start` string or `None`.
- `number`: keep numeric value.
- `people`: map to list of person `name` strings.
- Fallback: if a property contains `rich_text` or `title`, prefer those over absent typed fields.

## Blocks → Annotations
- Paragraph blocks with `text` → create `Annotation` with `text` set to the paragraph string and provenance `{page_id}`.

## Tables → Tasks, ReferenceTasks, TaskExtractions
Mapping rules:
- Detect a table block as an exported fixture entry under `tables` with `heading` and `rows`.
- If the `heading` contains the substring "summary table" (case-insensitive), attempt to extract a `task_name` from the heading by splitting on `:` or `-` and trimming the right-hand part. Example headings supported:
  - "Summary Table: Data Extraction"
  - "Summary table - Reading Progress"

When a `task_name` is detected:
- Create a `Task` with `name = task_name` and `id = slugify(task_name)` (lowercase, non-alphanumerics → `_`).
- Create a `ReferenceTask` linking the `Reference.id` and `Task.id`. Populate provenance `{"page_id": <page_id>, "table_block_id": <block_id>}`.
- Create a `TaskExtraction` with:
  - `id`: `ex_` + 8 hex chars
  - `reference_task_id`: the ReferenceTask id
  - `schema_name`: `task_name` (fallback: the table heading or "table")
  - `extracted`: a list-of-row-dicts parsed from the table (header = first row; each subsequent row → dict(header[i] -> cell_value)).
  - `provenance`: `{"page_id": <page_id>, "block_index": <index>}`
  - `revision_status`: `None`

When no `task_name` is detected:
- Create a `TaskExtraction` with `reference_task_id = None` and `schema_name` set to the heading or "table".

Row parsing rules:
- The first row in `rows` is treated as the header. Subsequent rows are zipped to header to form dicts.
- If a row is shorter than the header, it is padded with empty strings.
- Preserve raw cell strings; let downstream normalization handle type coercion.

## Workflow state (Status)
- Preferred property: `Status` (Notion select). Fallback: `Status_1` if `Status` is missing.
- Map the selected string value directly to `WorkflowState.state` (preserve raw label). Example: "Reading Progress", "To Read", "In Progress".
- Create `WorkflowState` record with `id = ws_` + 8 hex chars and `reference_id = Reference.id`.
- Recommendation (Phase‑1): map raw labels to a controlled vocabulary for `reading_progress` (e.g., `to_read`, `reading`, `done`) and record the normalized value in a future `normalized_state` field.

## ID generation & provenance
- `Task.id` = slugify(task name)
- `ReferenceTask.id` = "rt_" + 8 hex chars
- `TaskExtraction.id` = "ex_" + 8 hex chars
- `Annotation.id` = "an_" + 8 hex chars
- `WorkflowState.id` = "ws_" + 8 hex chars
- Always include provenance with page-level identifiers and table block identifiers when available.

## Example (fixture → canonical)
Fixture snippet (simplified):

```json
{
  "page_id": "003e69cb-...",
  "title": "A sample paper",
  "properties": { "Authors": {"type": "multi_select", "multi_select": [{"name": "Smith"}]}, "Status_1": {"type": "select", "select": {"name": "Reading Progress"}} },
  "tables": [ {"heading": "Summary table: Data Extraction", "rows": [["Field","Value"],["X","1"]], "block_id": "b1", "index": 0} ],
  "blocks": [{"type":"paragraph","text":"Quick note"}]
}
```

Canonical output (high-level):

```json
{
  "references": [{"id":"003e69cb-...","title":"A sample paper","authors":["Smith"]}],
  "tasks": [{"id":"data_extraction","name":"Data Extraction","aliases":[]}],
  "reference_tasks": [{"id":"rt_...","reference_id":"003e69cb-...","task_id":"data_extraction","provenance":{"page_id":"003e69cb-...","table_block_id":"b1"}}],
  "task_extractions": [{"id":"ex_...","reference_task_id":"rt_...","schema_name":"Data Extraction","extracted":[{"Field":"X","Value":"1"}],"provenance":{"page_id":"003e69cb-...","block_index":0}}],
  "annotations": [{"id":"an_...","reference_id":"003e69cb-...","text":"Quick note","provenance":{"page_id":"003e69cb-..."}}],
  "workflow_states": [{"id":"ws_...","reference_id":"003e69cb-...","state":"Reading Progress"}]
}
```

## Notes & next steps
- These mappings reflect the current behavior implemented in src/services/reading_list_importer.py.
- Short-term policy: preserve raw values (do not normalize status labels yet) to avoid accidental data loss.
- Medium-term (Phase‑1): adopt controlled vocabularies for `WorkflowState.state` and canonical type coercions for extraction fields.
