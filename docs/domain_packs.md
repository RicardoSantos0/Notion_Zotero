# Domain Packs

A domain pack is a thin mapping layer that connects project-specific terminology to the generic template and task system.

## Built-in packs

| Pack ID | Description | Version |
|---------|-------------|---------|
| `education_learning_analytics` | Tasks and status aliases for educational data mining / learning analytics reviews | 1.1 |

## Domain pack structure

```python
domain_pack = {
    "id": "education_learning_analytics",        # unique identifier
    "version": "1.1",                            # semantic version string
    "name": "Education / Learning Analytics",    # human-facing name
    "tasks": {
        "performance_prediction": {
            "name": "Performance Prediction",
            "aliases": ["prediction", "performance prediction", "predictive"],
            "template_id": "prediction_modeling",   # maps to a generic template
        },
        # ... more tasks
    },
    # Notion property names to extract into sync_metadata["domain_properties"]
    "notion_properties": [
        # reading workflow (checkbox)
        "Introduction", "Related Work", "Methods", "Results",
        "Discussion", "Conclusion", "Limitations", "Completed",
        # domain classification (select / multi_select)
        "Keywords/Type", "Learner Population", "Learner Representation",
        "Course-Agnostic Approach", "Deployed/ Deployable", "Work Nature",
        # screening
        "Motive For Exclusion",
    ],
    # short display labels for task_label_fn
    "task_labels": {
        "performance_prediction": "PRED",
        "descriptive_modelling": "DESC",
        "recommender_systems": "REC",
        "knowledge_tracing": "KT",
    },
}
```

The `version` field is required. It is stamped into every canonical bundle's `provenance` block, allowing consumers to detect pack upgrades and re-run extraction when needed.

The `notion_properties` list drives domain field extraction. During a pull, the importer iterates this list and copies matching Notion property values into `sync_metadata["domain_properties"]` on each `Reference`. These values then appear as named columns in the `"Reading List"` DataFrame produced by `build_summary_tables`.

The `task_labels` dict is consumed by `task_label_fn` (exported from `notion_zotero.analysis`) to map task names to short display labels for notebooks and reports.

## How the importer uses a domain pack

1. The importer resolves the pack via `task_registry.load_domain_pack(pack_id)`. If the pack is not found, it logs a warning and falls back to `education_learning_analytics`.
2. It iterates `notion_properties` and copies matching Notion property values (including checkboxes, selects, multi-selects) into `sync_metadata["domain_properties"]` on each `Reference`.
3. For each table heading in a page, it calls `task_registry.resolve_task_alias(pack, heading)` to get a canonical task ID. Unrecognised headings emit a warning and are stored as unlinked extractions.
4. It looks up the task's `template_id` and validates extracted rows against that template.
5. Only tasks defined in the pack are created — no ad hoc inference from headings.

The active pack and its version are written into every output bundle:
```json
{
  "provenance": {
    "domain_pack_id": "education_learning_analytics",
    "domain_pack_version": "1.1"
  }
}
```

## Selecting a pack at parse time

Pass `--domain-pack <pack_id>` to `parse-fixtures`:

```bash
notion-zotero parse-fixtures --input fixtures/reading_list --out fixtures/canonical \
  --domain-pack education_learning_analytics
```

## Analysis helpers

Two pandas-free helpers are exported from `notion_zotero.analysis` and driven by the active domain pack:

```python
from notion_zotero.analysis import is_accepted, task_label_fn

# filter to accepted papers only
accepted = [b for b in bundles if is_accepted(b)]

# build DataFrames with short task labels
dfs = build_summary_dataframes(accepted, task_label_fn=task_label_fn)
```

- `is_accepted(bundle)` — checks `workflow_states[0].state` (or falls back to `sync_metadata.notion_properties.Status`); returns `True` when no status is found.
- `task_label_fn(task_name)` — maps task names to short labels using `task_labels`; falls back to the raw name.

Domain properties (from `notion_properties`) are spread as named columns into the `"Reading List"` DataFrame automatically — no extra code needed in the notebook.

---

## Creating a new domain pack

1. Create `src/notion_zotero/schemas/domain_packs/<your_pack>.py`.
2. Define a `domain_pack` dict following the structure above (include `version`, `notion_properties`, and `task_labels`).
3. Register it in `src/notion_zotero/schemas/task_registry.py`:

```python
from .domain_packs import your_pack as yp

DOMAIN_PACKS: Dict[str, Dict] = {
    ela.domain_pack["id"]: ela.domain_pack,
    yp.domain_pack["id"]: yp.domain_pack,   # add this line
}
```

4. Verify with `notion-zotero list-domain-packs`.

## Listing available packs

```bash
notion-zotero list-domain-packs
```
