# CLI (notion_zotero) — commands and examples

Run via the installed entrypoint or the module runner:

```bash
notion-zotero <subcommand> [options]
# or
python -m notion_zotero.cli <subcommand> [options]
```

---

## Subcommands

### `parse-fixtures`
Parse local fixture JSON files (Notion snapshots) into per-page canonical JSON bundles.

```bash
notion-zotero parse-fixtures --input fixtures/reading_list --out fixtures/canonical
```

Options:
- `--input PATH` — directory containing raw Notion export JSON files
- `--out PATH` — output directory for canonical bundles
- `--force` — overwrite existing canonical bundles
- `--domain-pack PACK_ID` — apply a specific domain pack for task extraction. Falls back to `education_learning_analytics` with a warning if the requested pack is not found.

Each output bundle is stamped with provenance:
```json
{
  "provenance": {
    "domain_pack_id": "education_learning_analytics",
    "domain_pack_version": "1.0"
  }
}
```

---

### `merge-canonical`
Merge per-page canonical JSON files into a single array file.

```bash
notion-zotero merge-canonical --input fixtures/canonical --out fixtures/canonical_merged.json
```

---

### `dedupe-canonical`
Deduplicate canonical bundles by DOI or title+authors.

```bash
notion-zotero dedupe-canonical --input fixtures/canonical_merged.json --out fixtures/canonical_merged.dedup.json
```

---

### `validate-fixtures`
Validate canonical bundle files in a directory. Exits with code 1 if any bundles are malformed.

```bash
notion-zotero validate-fixtures --input fixtures/canonical
```

---

### `list-domain-packs`
List all registered domain packs.

```bash
notion-zotero list-domain-packs
```

---

### `list-templates`
List all registered extraction templates.

```bash
notion-zotero list-templates
```

---

### `export-snapshot`
Export a live Notion database snapshot to JSON (requires `NOTION_API_KEY` and `NOTION_DATABASE_ID`).

```bash
notion-zotero export-snapshot
```

---

### `zotero-citation`
Print a human citation string for a canonical bundle file.

```bash
notion-zotero zotero-citation --file fixtures/canonical/<page>.canonical.json
```

---

## Logging

All operational output (file writes, updates, warnings) uses Python's standard `logging` module, not `print`. Set `logging.basicConfig(level=logging.INFO)` in calling code, or use the `LOGLEVEL` env var if configured.
