"""Apply / session lock (M4) — prevents concurrent mutating sync runs.

A file-based lock at ``<lock_dir>/.<name>.lock``. ``acquire()`` is a context
manager that raises :class:`SyncLockHeld` if another holder is active; the lock is
released on exit. A lock older than ``stale_after_seconds`` is treated as stale and
reclaimed (so a crashed run can't wedge the workflow forever) — deliberately
PID-free to stay portable across Windows/POSIX.
"""
from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


class SyncLockHeld(RuntimeError):
    """Raised when a sync lock is already held by an active run."""


class SyncLock:
    def __init__(self, lock_dir: str | Path, name: str = "sync",
                 stale_after_seconds: float = 6 * 3600) -> None:
        self.lock_dir = Path(lock_dir)
        self.name = name
        self.stale_after_seconds = stale_after_seconds
        self.lock_path = self.lock_dir / f".{name}.lock"

    def is_held(self) -> bool:
        """True if a non-stale lock file is present."""
        if not self.lock_path.exists():
            return False
        try:
            age = time.time() - self.lock_path.stat().st_mtime
        except OSError:
            return False
        return age < self.stale_after_seconds

    @contextmanager
    def acquire(self):
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        if self.is_held():
            raise SyncLockHeld(
                f"sync lock already held: {self.lock_path} "
                f"(another apply/replay run is in progress)"
            )
        self.lock_path.write_text(
            json.dumps({"pid": os.getpid(),
                        "acquired_at": datetime.now(timezone.utc).isoformat()}),
            encoding="utf-8",
        )
        try:
            yield self
        finally:
            try:
                self.lock_path.unlink()
            except FileNotFoundError:
                pass


__all__ = ["SyncLock", "SyncLockHeld"]
