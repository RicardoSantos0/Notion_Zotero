"""Move any `src/legacy_archive_*` folders to a top-level `legacy/` directory.

Run from the repository (this script locates paths relative to itself).
"""
from __future__ import annotations

from pathlib import Path
import shutil


def main():
    repo_root = Path(__file__).resolve().parents[1]
    src_dir = repo_root / "src"
    archives = list(src_dir.glob("legacy_archive_*"))
    if not archives:
        print("No legacy archives found under src/")
        return
    dest_parent = repo_root / "legacy"
    dest_parent.mkdir(parents=True, exist_ok=True)
    for a in archives:
        target = dest_parent / a.name
        if target.exists():
            i = 1
            while (dest_parent / f"{a.name}_{i}").exists():
                i += 1
            target = dest_parent / f"{a.name}_{i}"
        shutil.move(str(a), str(target))
        print("Moved", a, "->", target)


if __name__ == '__main__':
    main()
