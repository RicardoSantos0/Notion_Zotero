"""Archive legacy top-level packages under `src/legacy_archive_<date>`.

Run from the project root (the script will operate on the `src/` folder).
This moves common legacy folders into a single archive directory so the new
`notion_zotero` package can live without accidental imports of the old layout.
"""
from __future__ import annotations

import shutil
import os
from datetime import datetime


ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, "src")

TO_MOVE = [
    "core",
    "schemas",
    "services",
    "analysis",
    "connectors",
    "scripts",
]


def main():
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(SRC, f"legacy_archive_{ts}")
    os.makedirs(dest, exist_ok=True)
    moved = []
    for name in TO_MOVE:
        srcp = os.path.join(SRC, name)
        if os.path.exists(srcp):
            shutil.move(srcp, os.path.join(dest, name))
            moved.append(name)
    print("Archived:", moved)
    print("Archive location:", dest)


if __name__ == '__main__':
    main()
