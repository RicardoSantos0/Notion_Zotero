# Sync Design

## Overview

The notion_zotero sync pipeline moves data between Zotero (bibliographic source of truth) and Notion (workflow and extraction workspace). The canonical models defined in `core/models.py` serve as the neutral interchange format.

## Field Ownership

Every field in the canonical schema is assigned to exactly one owner, defined in `core/field_ownership.py`:

- **zotero** owns bibliographic metadata: `title`, `authors`, `year`, `journal`, `doi`, `url`, `zotero_key`, `abstract`, `item_type`, `tags`
- **notion** owns workflow and extraction fields: `state`, `workflow_state`, `inclusion_decision_for_task`, `extracted`, `relevance_notes`, `kind`, `text`, `assignment_source`
- **system** owns pipeline-internal fields: `id`, `provenance`, `sync_metadata`, `validation_status`, and schema/template identifiers

The `assert_ownership(field, writing_system)` function enforces this at write time and raises `FieldOwnershipViolation` on violations. Unknown fields are not enforced.

## Conflict Resolution

When the same field has different values in Zotero and Notion at sync time:

- **Zotero wins** on all bibliographic fields (ZOTERO_OWNED). The Zotero record is always fresher for these.
- **Notion wins** on all workflow and extraction fields (NOTION_OWNED). User annotations, inclusion decisions, and extraction results are not overwritten by Zotero.
- **System fields** are never written by either connector directly; they are managed by the pipeline.

## Merge Order

The full sync cycle follows this sequence:

1. **Read** canonical state from both systems (NotionReader, ZoteroReader)
2. **Diff** against the last committed bundle snapshot (diff_engine.diff_bundles)
3. **Apply zotero-owned changes** to Zotero via ZoteroWriter (currently dry-run only)
4. **Apply notion-owned changes** to Notion via NotionWriter (currently dry-run only)
5. **Update sync_metadata** on canonical models with timestamps and operation IDs
6. **Persist** the updated bundle snapshot for the next diff cycle

Each writer filters the DiffReport to its own owned fields before generating operations.

## Idempotency

The diff engine compares canonical bundles field-by-field. If there are no differences between the baseline and the updated bundle, no DiffEntry objects are produced and no write operations are planned. Re-running the sync on an unchanged state is a guaranteed no-op.

Bundle snapshots are keyed by entity `id` fields. Reordering of lists within a bundle does not produce spurious diffs.

## Dry-Run Mode

Both writers default to `dry_run=True`. In this mode:

- All planned operations are logged at INFO level with the prefix `[DRY-RUN]`
- No network calls are made
- The list of planned operation strings is returned for inspection

The apply path raises `NotImplementedError` until Sprint 4 completes live API integration.

## Open Questions

- **Deletions**: How should entities removed from Zotero be handled? Options include soft-delete (set a flag), hard-delete (remove from Notion), or quarantine. No decision has been made; deletions are not currently emitted by the diff engine.
- **Partial failures**: If a batch write partially succeeds, the sync_metadata on affected entities will be inconsistent. A transactional approach or per-entity retry queue is needed.
- **Rollback**: There is no rollback mechanism yet. The write_log (see write_log_design.md) will enable replaying to a known-good state, but the infrastructure is not yet in place.
- **Concurrent edits**: If both Zotero and Notion update a field between sync runs the last-writer-wins rule above applies, which may silently discard one edit. A vector-clock or last-modified-timestamp check is a future improvement.
- **Rate limits**: Notion and Zotero both impose API rate limits. The connectors do not yet implement back-off or retry logic.
