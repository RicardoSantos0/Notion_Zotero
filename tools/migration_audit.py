"""Migration audit: compare legacy analysis outputs to new canonical outputs.

This script:
- loads the canonical importer (`notion_zotero.services.reading_list_importer.parse_fixture`)
- temporarily imports the legacy `analysis` package from `legacy/legacy_archive_*`
- for each fixture in `fixtures/reading_list/` runs both pipelines and records
  a per-page comparison (title/authors match, counts)
- writes `migration_audit/migration_report.json` and `migration_audit/summary.csv`
- creates a zip of the legacy archive and removes the original folder (prune)

Run from the project root:
    python tools/migration_audit.py
"""
from __future__ import annotations

import json
import csv
import sys
import importlib
import shutil
import os
import gc
from pathlib import Path
from typing import Any

from notion_zotero.services.reading_list_importer import parse_fixture
from notion_zotero.core.normalize import normalize_title, normalize_authors


def find_legacy_archive(repo_root: Path) -> Path | None:
    legacy_root = repo_root / "legacy"
    if not legacy_root.exists():
        return None
    archives = sorted([p for p in legacy_root.iterdir() if p.is_dir() and p.name.startswith("legacy_archive_")])
    return archives[0] if archives else None


def run_audit():
    repo_root = Path(__file__).resolve().parents[1]
    fixtures_dir = repo_root / "fixtures" / "reading_list"
    out_dir = repo_root / "migration_audit"
    out_dir.mkdir(exist_ok=True)

    legacy_archive = find_legacy_archive(repo_root)
    if not legacy_archive:
        print("No legacy archive found under legacy/ — aborting migration audit.")
        return 2

    print("Using legacy archive:", legacy_archive)

    # Import new canonical importer first
    print("Importing canonical importer...")

    # Prepare to import the legacy `analysis` package by inserting the archive
    old_sys_path = sys.path.copy()
    sys.path.insert(0, str(legacy_archive))
    importlib.invalidate_caches()

    # Some legacy modules expect `dotenv` to be present; provide a minimal stub
    # so the legacy package can be imported offline for auditing.
    if "dotenv" not in sys.modules:
        import types

        dotenv_stub = types.ModuleType("dotenv")
        dotenv_stub.load_dotenv = lambda *a, **k: None
        sys.modules["dotenv"] = dotenv_stub

    try:
        legacy_analysis = importlib.import_module("analysis")
    except Exception as e:
        print("Failed to import legacy analysis package:", e)
        sys.path[:] = old_sys_path
        if "analysis" in sys.modules:
            del sys.modules["analysis"]
        return 3

    entries: list[dict[str, Any]] = []

    files = sorted(fixtures_dir.glob("*.json"))
    if not files:
        print("No fixtures found at", fixtures_dir)
    for f in files:
        try:
            page = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue

        # Legacy path: records_from_pages -> build_summary_table
        legacy_records = []
        try:
            legacy_records = legacy_analysis.records_from_pages([page])
            legacy_summary = legacy_analysis.build_summary_table(legacy_records)
            legacy_first = legacy_summary[0] if legacy_summary else (legacy_records[0] if legacy_records else {})
        except Exception as e:
            legacy_first = {"error": str(e)}

        # Canonical path
        try:
            page_id, canon = parse_fixture(f)
            canon_ref = (canon.get("references") or [None])[0]
        except Exception as e:
            page_id = f.stem
            canon = {}
            canon_ref = {"error": str(e)}

        # Compare titles/authors
        ltitle = str(legacy_first.get("Title") or legacy_first.get("title") or legacy_first.get("Name") or "")
        ntitle = str((canon_ref or {}).get("title") or "")
        title_match = normalize_title(ltitle).strip().lower() == normalize_title(ntitle).strip().lower()

        lauth = legacy_first.get("Authors") or legacy_first.get("authors") or ""
        nauth = (canon_ref or {}).get("authors") or ""
        lauth_s = normalize_authors(lauth) if lauth else ""
        nauth_s = normalize_authors(nauth) if nauth else ""

        entry = {
            "page_id": page_id,
            "fixture": str(f.relative_to(repo_root)),
            "legacy_title": ltitle,
            "canonical_title": ntitle,
            "title_match": bool(title_match),
            "legacy_authors": lauth_s,
            "canonical_authors": nauth_s,
            "legacy_records_count": len(legacy_records) if isinstance(legacy_records, list) else 0,
            "canonical_extractions_count": len((canon.get("task_extractions") or [])),
            "legacy_first_summary": legacy_first,
            "canonical_reference": canon_ref,
        }
        entries.append(entry)

    # Restore sys.path and unload legacy 'analysis' module
    sys.path[:] = old_sys_path
    if "analysis" in sys.modules:
        del sys.modules["analysis"]

    # Unload any modules that were loaded from the legacy archive path so
    # Windows can remove files (avoids open file handles preventing deletion).
    legacy_archive_str = str(legacy_archive.resolve())
    for mod_name in list(sys.modules.keys()):
        try:
            mod = sys.modules.get(mod_name)
            mod_file = getattr(mod, "__file__", None)
            if mod_file and legacy_archive_str in str(Path(mod_file).resolve()):
                del sys.modules[mod_name]
        except Exception:
            # ignore failures when probing modules
            pass

    # Write JSON report
    rpt = out_dir / "migration_report.json"
    rpt.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    print("WROTE:", rpt)

    # Write summary CSV
    csv_path = out_dir / "summary.csv"
    keys = ["page_id", "fixture", "title_match", "legacy_records_count", "canonical_extractions_count"]
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys)
        writer.writeheader()
        for e in entries:
            writer.writerow({k: e.get(k) for k in keys})
    print("WROTE:", csv_path)

    # Zip and remove legacy archive (prune)
    zip_base = repo_root / "legacy" / legacy_archive.name
    zip_path = shutil.make_archive(str(zip_base), "zip", root_dir=str(legacy_archive))
    print("Created archive:", zip_path)
    # Attempt robust removal: clear GC, make files writable, then rmtree
    try:
        gc.collect()
        for root, dirs, files in os.walk(legacy_archive, topdown=False):
            for fname in files:
                p = Path(root) / fname
                try:
                    p.chmod(0o666)
                except Exception:
                    pass
            for dname in dirs:
                dp = Path(root) / dname
                try:
                    dp.chmod(0o777)
                except Exception:
                    pass
        shutil.rmtree(legacy_archive)
        print("Removed legacy folder:", legacy_archive)
    except Exception as e:
        print("Failed to remove legacy folder:", e)

    return 0


if __name__ == "__main__":
    rc = run_audit()
    raise SystemExit(rc)
