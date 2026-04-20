# Domain Packs

A domain pack is a thin mapping layer that connects project-specific terminology to the generic template and task system.

## Built-in packs

| Pack ID | Description | Version |
|---------|-------------|---------|
| `education_learning_analytics` | Tasks and status aliases for educational data mining / learning analytics reviews | 1.0 |

## Domain pack structure

```python
domain_pack = {
    "id": "education_learning_analytics",        # unique identifier
    "version": "1.0",                            # semantic version string
    "name": "Education / Learning Analytics",    # human-facing name
    "tasks": {
        "performance_prediction": {
            "name": "Performance Prediction",
            "aliases": ["prediction", "performance prediction", "predictive"],
            "template_id": "prediction_modeling",   # maps to a generic template
        },
        # ... more tasks
    },
}
```

The `version` field is required. It is stamped into every canonical bundle's `provenance` block, allowing consumers to detect pack upgrades and re-run extraction when needed.

## How the importer uses a domain pack

1. The importer resolves the pack via `task_registry.load_domain_pack(pack_id)`. If the pack is not found, it logs a warning and falls back to `education_learning_analytics`.
2. For each table heading in a page, it calls `task_registry.resolve_task_alias(pack, heading)` to get a canonical task ID. Unrecognised headings emit a warning and are skipped.
3. It looks up the task's `template_id` and validates extracted rows against that template.
4. Only tasks defined in the pack are created — no ad hoc inference from headings.

The active pack and its version are written into every output bundle:
```json
{
  "provenance": {
    "domain_pack_id": "education_learning_analytics",
    "domain_pack_version": "1.0"
  }
}
```

## Selecting a pack at parse time

Pass `--domain-pack <pack_id>` to `parse-fixtures`:

```bash
notion-zotero parse-fixtures --input fixtures/reading_list --out fixtures/canonical \
  --domain-pack education_learning_analytics
```

## Creating a new domain pack

1. Create `src/notion_zotero/schemas/domain_packs/<your_pack>.py`.
2. Define a `domain_pack` dict following the structure above (include `version`).
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
