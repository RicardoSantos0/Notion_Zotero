"""Small CLI helper to run the integrated analysis module.

Usage:
    python tools/run_analysis.py --fixtures fixtures/reading_list --canonical fixtures/canonical
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--fixtures", default="fixtures/reading_list")
    p.add_argument("--canonical", default="fixtures/canonical")
    p.add_argument("--use-notion", action="store_true")
    args = p.parse_args(argv)

    # Ensure package src is importable when running from the repo root
    root = Path(__file__).resolve().parents[1]
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    from notion_zotero.analysis import run_analysis

    adfs, clean, log = run_analysis(use_notion_api=args.use_notion, fixtures_dir=Path(args.fixtures), canonical_dir=Path(args.canonical))
    print("Analysis complete")
    for k, v in adfs.items():
        print(f" - {k}: {len(v)} rows")


if __name__ == '__main__':
    main()
