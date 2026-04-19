"""Migration audit utilities.

Compare two sets of canonical bundles (v2 vs v3) and report diffs.
This module is intentionally read-only and does not touch live Notion.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any


def load_bundle(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compare_dirs(left: Path, right: Path) -> Dict[str, Any]:
    """Compare JSON files present in both directories and return a summary.

    Summary includes lists of unchanged, changed, only_left, only_right filenames.
    """
    left_files = {p.name: p for p in left.glob("*.canonical.json")}
    right_files = {p.name: p for p in right.glob("*.canonical.json")}

    common = set(left_files).intersection(set(right_files))
    only_left = sorted(set(left_files) - set(right_files))
    only_right = sorted(set(right_files) - set(left_files))

    changed = []
    unchanged = []
    for name in sorted(common):
        l = load_bundle(left_files[name])
        r = load_bundle(right_files[name])
        if l == r:
            unchanged.append(name)
        else:
            changed.append(name)

    return {
        "only_left": only_left,
        "only_right": only_right,
        "changed": changed,
        "unchanged": unchanged,
        "left_count": len(left_files),
        "right_count": len(right_files),
    }


def print_summary(summary: Dict[str, Any]) -> None:
    print(f"Left count: {summary['left_count']}")
    print(f"Right count: {summary['right_count']}")
    print(f"Unchanged: {len(summary['unchanged'])}")
    print(f"Changed: {len(summary['changed'])}")
    if summary['changed']:
        for c in summary['changed'][:20]:
            print(" -", c)
