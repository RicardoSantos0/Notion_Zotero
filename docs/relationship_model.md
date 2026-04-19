# Relationship model

This file documents links between canonical objects. Key relationships:

- `reference_tasks.reference_id` -> `references[id]`
- `reference_tasks.task_id` -> `tasks[id]`
- `task_extractions.reference_task_id` -> `reference_tasks[id]`
- `annotations.reference_id` -> `references[id]`
- `workflow_states.reference_id` -> `references[id]`

Relationship cardinalities and expected uniqueness constraints should be
recorded here.
