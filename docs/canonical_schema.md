# Canonical schema

This document describes the canonical JSON bundles produced by the importer.

Top-level keys:
- `references`: list of bibliographic references
- `tasks`: list of task definitions (task id, name, aliases)
- `reference_tasks`: assignments of tasks to references
- `task_extractions`: extracted data for tasks
- `annotations`: free-text annotations
- `workflow_states`: recorded status changes

All canonical objects MUST include a `provenance` field describing origin.
