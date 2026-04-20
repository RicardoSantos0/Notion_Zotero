# Notion_Zotero

[![Regenerate sanitized summary](https://github.com/RicardoSantos0/Notion_Zotero/actions/workflows/regenerate-sanitized-summary.yml/badge.svg?branch=main)](https://github.com/RicardoSantos0/Notion_Zotero/actions/workflows/regenerate-sanitized-summary.yml)

Domain-agnostic reference management and evidence-extraction toolkit for PhD literature reviews. Converts Notion reading list exports into versioned canonical bundles via pluggable domain packs.

## Quick start

```powershell
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -e .
```

```bash
# Parse a Notion snapshot into canonical bundles
notion-zotero parse-fixtures --input fixtures/reading_list --out fixtures/canonical

# Apply a specific domain pack
notion-zotero parse-fixtures --input fixtures/reading_list --out fixtures/canonical \
  --domain-pack education_learning_analytics

# Merge and deduplicate
notion-zotero merge-canonical --input fixtures/canonical --out fixtures/canonical_merged.json
notion-zotero dedupe-canonical --input fixtures/canonical_merged.json \
  --out fixtures/canonical_merged.dedup.json

# Inspect available domain packs and templates
notion-zotero list-domain-packs
notion-zotero list-templates

# Validate output
notion-zotero validate-fixtures --input fixtures/canonical
```

See [docs/cli.md](docs/cli.md) for all subcommands and options.

## Architecture

Three-layer design:

```
Domain Pack  →  extraction rules + task aliases (pluggable per research area)
Templates    →  generic row schemas for each task type
Core models  →  canonical Reference + WorkflowState + ReferenceTask bundles
```

Each canonical bundle is stamped with provenance (`domain_pack_id`, `domain_pack_version`) so consumers can detect when re-extraction is needed after a pack upgrade.

## Testing

```bash
pytest -q                          # full suite
pytest --cov=notion_zotero -q      # with coverage (CI enforces ≥ 70%)
```

## Notes

- `fixtures/canonical_merged.json` is gitignored — regenerate with `merge-canonical`.
- Raw Notion exports go in `fixtures/reading_list/`; canonical bundles in `fixtures/canonical/`.
- Environment variables: `NOTION_API_KEY`, `NOTION_DATABASE_ID` (see `.env.example`).
