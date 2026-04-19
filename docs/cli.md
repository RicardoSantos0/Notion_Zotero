# CLI (notion_zotero) — commands and examples

This document shows the supported `notion_zotero` CLI subcommands and quick
examples using the package entrypoint.

Run the CLI using Python's `-m` module runner:

```bash
python -m notion_zotero.cli <subcommand> [options]
```

Available subcommands (seeded):

- `export-snapshot` — Export a Notion database snapshot to JSON.
  - Note: this requires an `analysis` implementation under `notion_zotero.analysis`.
    If the package does not include that module, the command will raise an
    informative runtime error.

- `parse-fixtures` — Parse local fixture JSON files (Notion snapshots) into
  per-page canonical JSON bundles.

- `merge-canonical` — Merge per-page canonical JSON files into a single
  array file (useful prior to deduplication).

- `dedupe-canonical` — Deduplicate canonical bundles by DOI or title+authors.

- `zotero-citation` — Print a human citation string for a Zotero item or a
  canonical bundle file.

Examples

1) Parse fixtures into canonical files:

```bash
python -m notion_zotero.cli parse-fixtures --input fixtures/reading_list --out fixtures/canonical
```

2) Merge canonical bundles into a single file:

```bash
python -m notion_zotero.cli merge-canonical --input fixtures/canonical --out fixtures/canonical_merged.json
```

3) Deduplicate merged canonical file:

```bash
python -m notion_zotero.cli dedupe-canonical --input fixtures/canonical_merged.json --out fixtures/canonical_merged.dedup.json
```

4) Print a citation from a canonical bundle:

```bash
python -m notion_zotero.cli zotero-citation --file fixtures/canonical/<page>.canonical.json
```

Notes & tips

- If `export-snapshot` is missing, implement the database export function in
  `notion_zotero.analysis` or restore the legacy analysis module into the
  package.
- Use `--force` with `parse-fixtures` to overwrite canonical bundle files.
