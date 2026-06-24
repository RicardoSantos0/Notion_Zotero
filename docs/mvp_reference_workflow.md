# MVP Reference-Management Workflow

The daily, review-first loop for keeping a Notion reading list in sync with a Zotero
library. **Every external write is dry-run by default** — nothing touches Notion or
Zotero unless you explicitly pass `--apply`, and every applied change is logged and
reversible.

```
pull  ->  health  ->  plan  ->  review  ->  apply  ->  recover
```

## 1. Pull local snapshots

```bash
notion-zotero pull-zotero            # Zotero items -> data/pulled/zotero
notion-zotero pull-notion --name learning_analytics_review
```

Both require API keys in `.env` (`ZOTERO_API_KEY`, `NOTION_API_KEY`). Pulls are reads.

## 2. Health check

```bash
notion-zotero mvp-health
```

Writes `data/sync_plans/mvp_health.json` and `.md`: metadata completeness (DOI, title,
authors, year, journal, Zotero key), duplicate candidates, ambiguous matches,
source-only records, snapshot age, and any planned/failed writes. Read-only.

## 3. Plan the sync

```bash
notion-zotero plan-sync
```

Builds a read-only `data/sync_plans/sync_plan.json` from the local snapshots. No writes.

## 4. Review

```bash
notion-zotero review-plan
```

Renders `data/sync_plans/sync_plan_review.md` — executable updates, approved creates,
ambiguous/blocked actions, and items needing human review — so you can approve or reject
before anything is written.

## 5. Apply (guarded)

```bash
notion-zotero apply-plan                 # DRY-RUN: prints what would change
notion-zotero apply-plan --apply         # writes approved Notion updates, logged
```

`apply-plan` is dry-run unless `--apply` is given. In apply mode it acquires a **sync
lock** (`logs/write_logs/.sync.lock`) and refuses to run if another apply/replay session
holds it — no concurrent writers. Approved Zotero-only creates require
`--include-reviewed-creates` and are duplicate-checked before creation. Every operation
is recorded to the NDJSON write log.

## 6. Recover

```bash
notion-zotero rollback-plan              # build a rollback plan from the write log
notion-zotero apply-rollback-plan --apply  # revert applied changes (lock-guarded)
notion-zotero replay-log                 # DRY-RUN: list planned/failed entries
notion-zotero replay-log --apply         # re-run incomplete writes, under the lock
```

`replay-log` re-drives entries that were left `planned` or `failed`. Like apply, it is
dry-run by default and acquires the sync lock before any write.

## Safety model (non-negotiable)

- **Dry-run default** for every mutating command; `--apply` is always explicit.
- **Sync lock** serialises `apply-plan`, `apply-rollback-plan`, and `replay-log --apply`.
- **Write log** (NDJSON) records every operation for audit, rollback, and replay.
- **Field ownership**: Zotero owns bibliographic metadata; Notion owns workflow/extraction
  state. Sync never overwrites across that boundary.
