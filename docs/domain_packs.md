# Domain Packs

A domain pack is a thin mapping layer that connects project-specific terminology to the generic template and task system.

## Built-in packs

| Pack ID | Description |
|---------|-------------|
| `education_learning_analytics` | Tasks and status aliases for educational data mining / learning analytics reviews |

## Domain pack structure

```python
domain_pack = {
    "id": "education_learning_analytics",        # unique identifier
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

## How the importer uses a domain pack

1. The importer loads the selected pack via `task_registry.load_domain_pack(pack_id)`.
2. For each table heading in a page, it calls `task_registry.resolve_task_alias(pack, heading)` to get a canonical task ID.
3. It looks up the task's `template_id` and validates extracted rows against that template.
4. Only tasks defined in the pack are created — no ad hoc inference from headings.

## Creating a new domain pack

1. Create `src/notion_zotero/schemas/domain_packs/<your_pack>.py`.
2. Define a `domain_pack` dict following the structure above.
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
