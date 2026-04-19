# Handoff: Staging Notion Writes (Safe procedure)

Purpose: provide a concise, auditable checklist and commands to migrate canonical bundles
to a staging Notion workspace for verification before any production writes.

## Preconditions
- Ensure you have a current backup of `fixtures/canonical` and `fixtures/canonical_v3`.
- Confirm you have a staging Notion integration and credentials (set `NOTION_API_KEY`, `NOTION_DATABASE_ID`).
- Do not run any write operations against production Notion until staging validation completes.

## Artifacts produced by this repo
- `docs/migration_report_v2_to_v3.md` — human-readable summary of changes.
- `docs/migration_diffs_v2_v3.csv` — per-file CSV for reviewer tooling.
- `fixtures/canonical_v3/` — regenerated canonical bundles (v3) used for staging imports.

## Dry-run and validation commands
Run these locally (in the repo root) using the project virtualenv.

```bash
# Generate/update the migration CSV (writes docs/migration_diffs_v2_v3.csv)
python -m src.services.generate_migration_csv --left fixtures/canonical --right fixtures/canonical_v3 --out docs/migration_diffs_v2_v3.csv

# Run the unit tests (read-only; ensures importer + registry behave)
python -m pytest -q
```

## Validation checklist (manual)
1. Open `docs/migration_diffs_v2_v3.csv` and sample the top changed bundles.
2. For 10–20 changed bundles, inspect `fixtures/canonical/NAME` vs `fixtures/canonical_v3/NAME`.
   - Check IDs, `provenance` fields, and that semantic fields (tasks, extractions) are correct.
3. Confirm that registry parsers (Summary, Methods, Dataset, Findings, Metrics, Population, Conclusions, Limitations) produced sensible extractions.
4. Share `docs/migration_diffs_v2_v3.csv` with domain reviewers and collect sign-off.

## Staging write guidelines (after sign-off)
- Switch to a staging Notion workspace and set `NOTION_API_KEY` and `NOTION_DATABASE_ID` to the staging credentials.
- Replace the Notion connector stub with the real connector in a controlled environment (or run exporter script with a `--dry-run` flag if available).
- Run the staging import using a one-off script that:
  - Reads `fixtures/canonical_v3/`
  - Maps canonical fields to Notion properties (verify mapping first)
  - Uses batched writes with idempotency keys from `provenance` to avoid duplicates

## Rollback plan
- If staging writes reveal issues, stop immediately and restore staging workspace from a snapshot (Notion export or workspace snapshot if available).
- Track all staging changes in an audit log; record the provenance IDs used for writes.

## Contacts
- Repo maintainer: check `README.md` and the project roster for the owner.

## Notes
- This handoff intentionally does not include code to write to Notion. Implementers should follow the idempotency and batching guidance above and require explicit human sign-off before production migration.
