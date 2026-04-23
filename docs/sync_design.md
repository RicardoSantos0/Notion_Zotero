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

## Conflict Resolution Decision Tree

For each diff entry produced by the diff engine:

1. Get field owner: `get_owner(field)`
2. If owner == `"zotero"`: Zotero value wins. Write to Notion via NotionWriter (to push the authoritative bibliographic value).
3. If owner == `"notion"`: Notion value preserved. Skip write.
4. If owner == `"system"`: Never written by sync. Skip.
5. If owner == `"unknown"`: Log warning, skip write, flag for human review.

## Deletion Handling

**Decision: quarantine, not hard-delete.**

When an entity is removed from Zotero (it appears in the baseline bundle but not in the updated bundle), the sync pipeline sets `sync_metadata.quarantined = true` on the canonical model and marks the Notion page accordingly. The entity is NOT hard-deleted from Notion.

Rationale: researchers may have added Notion-side annotations, inclusion decisions, and extraction results on that page. Hard deletion would destroy those annotations permanently. Quarantine preserves researcher work while marking the entry as no longer active in Zotero.

The diff engine emits a `removed` DiffEntry for each field of a removed entity. The writers detect quarantine candidates (all fields of an entity removed) and route to quarantine logic rather than a field-by-field update.

## Partial Failure Handling

Each write operation is logged to the write log before execution with `status: planned`. The log entry is then updated based on outcome:

- On success: update log entry to `status: applied`. Update `sync_metadata.last_write` on the canonical entity.
- On failure: update log entry to `status: failed`, populate `error_message`. Leave `sync_metadata.last_write` unchanged.

A failed batch is NOT retried automatically. Recovery is handled by the `replay` CLI command (future work), which re-executes entries whose status is not `applied`.

`sync_metadata.last_write` on the entity is only updated on success to ensure it accurately reflects the last known-good sync state.

## Rate Limits

- **Notion API**: 3 requests/second. Enforced via a 0.35 s sleep between consecutive API calls in `NotionWriter`.
- **Zotero API**: No hard rate limit is documented. A conservative 1.0 s sleep between calls is applied in `ZoteroWriter`.

Back-off and retry are deferred to a future sprint; the current implementation uses simple fixed-delay throttling.

## Dry-Run Mode

Both writers default to `dry_run=True`. In this mode:

- All planned operations are logged at INFO level with the prefix `[DRY-RUN]`
- No network calls are made
- The list of planned operation strings is returned for inspection

Apply mode is active as of Sprint 4. Passing `dry_run=False` without a client raises `ValueError("client required for apply mode")`.

## Open Questions

- **Concurrent edits**: If both Zotero and Notion update a field between sync runs the last-writer-wins rule above applies, which may silently discard one edit. A vector-clock or last-modified-timestamp check is a future improvement.
- **Rollback**: A `replay` CLI command will handle recovery from partial failures, but the full rollback infrastructure (rollback_ref linking) is not yet implemented.
- **Compression**: NDJSON write logs can grow large; gzip rotation after 7 days is a candidate improvement.
- **Concurrent sync runs**: No locking mechanism prevents two sync processes from running simultaneously against the same bundle snapshot. A file-lock or database-backed session registry is needed before running scheduled sync.
