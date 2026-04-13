 # Notion_Zotero

 Scaffold for Notion ↔ Zotero reference management toolkit.

 Quick start
-----------

 - Install editable: `pip install -e .`
 - Export Notion reading list: `export-reading-list --out fixtures/reading_list`
 - Import canonical fixtures: `import-reading-list --in fixtures/reading_list --out fixtures/canonical`

 Packaging
---------

 This project uses a `src/` layout. To run tests locally:

 ```powershell
 python -m venv .venv
 . .venv/Scripts/Activate.ps1
 pip install -e .
 pytest -q
 ```

 Notes
-----
 - Large aggregated artifact `fixtures/canonical_merged.json` is intentionally ignored by Git. Keep canonical fixtures in `fixtures/canonical/` and raw page exports in `fixtures/reading_list/`.
 - Environment variables (see `.env.example`) are used to store `NOTION_TOKEN` and `ZOTERO_API_KEY` during local runs.
