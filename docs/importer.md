# Reading List Importer

The importer converts a Notion Reading List export (JSON fixtures) into canonical bundles.

## Prerequisites

1. Export your Notion database pages to `fixtures/reading_list/` as JSON files (one file per page).
2. Install the package: `pip install -e .`

## Basic usage

```bash
notion-zotero parse-fixtures --input fixtures/reading_list --out fixtures/canonical
```

Each page produces a `<page-id>.canonical.json` file in the output directory.

## Using a domain pack

```bash
notion-zotero parse-fixtures \
  --input fixtures/reading_list \
  --out fixtures/canonical \
  --domain-pack education_learning_analytics
```

The domain pack controls how table headings are matched to canonical tasks and which template is used for validation.

## Output format

Each canonical bundle is a JSON object:

```json
{
  "references": [ { "id": "...", "title": "...", "authors": [...], ... } ],
  "tasks": [ { "id": "...", "name": "...", "template_id": "..." } ],
  "reference_tasks": [ { "id": "...", "reference_id": "...", "task_id": "..." } ],
  "task_extractions": [ { "id": "...", "template_id": "...", "extracted": [...] } ],
  "workflow_states": [ { "id": "...", "state": "..." } ],
  "annotations": [ { "id": "...", "kind": "...", "text": "..." } ]
}
```

## Provenance

Every object carries a `provenance` dict recording:

| Field | Meaning |
|-------|---------|
| `source_page_id` | Notion page ID |
| `source_property` | Notion property name |
| `parser_notes` | Ambiguity notes from the parser |

## Merging and deduplication

After parsing, merge all canonical files into one array:

```bash
notion-zotero merge-canonical --input fixtures/canonical --out fixtures/canonical_merged.json
notion-zotero dedupe-canonical --input fixtures/canonical_merged.json --out fixtures/canonical_merged.dedup.json
```

Deduplication uses DOI as the primary key, falling back to normalised title + authors.

## Validating output

```bash
notion-zotero validate-fixtures --input fixtures/canonical
```
