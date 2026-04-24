"""NDJSON-backed write log for sync operations.

One file per session: write_log_{timestamp}_{session_id}.ndjson
Timestamp is a compact UTC ISO-8601 string, e.g. 20260424T153000Z.
Default log directory: logs/write_logs/ relative to CWD (configurable).

Required fields on every append (except rollback_ref and error_message,
which are nullable):
    operation_id, session_id, timestamp, entity_type, entity_id, field,
    old_value, new_value, actor, status
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


_REQUIRED_KEYS = frozenset({
    "operation_id",
    "session_id",
    "timestamp",
    "entity_type",
    "entity_id",
    "field",
    "old_value",
    "new_value",
    "actor",
    "status",
})


def _compact_utc_now() -> str:
    """Return current UTC time as compact ISO-8601: 20260424T153000Z."""
    return datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _parse_filename_timestamp(path: Path) -> datetime | None:
    """Extract and parse the embedded timestamp from a write_log filename.

    Filename format: write_log_{timestamp}_{session_id}.ndjson
    where timestamp is YYYYMMDDTHHMMSSz.
    Returns None if timestamp cannot be parsed.
    """
    stem = path.stem  # e.g. write_log_20260424T153000Z_sess-abc
    # strip the "write_log_" prefix
    if not stem.startswith("write_log_"):
        return None
    rest = stem[len("write_log_"):]
    # timestamp is the first 16 chars: YYYYMMDDTHHMMSSz
    ts_str = rest[:16]
    try:
        return datetime.strptime(ts_str, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


class WriteLog:
    """Append-only NDJSON write log for a single sync session."""

    def __init__(
        self,
        session_id: str,
        log_dir: str | Path = "logs/write_logs",
    ) -> None:
        self.session_id = session_id
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._timestamp = _compact_utc_now()
        self._log_file = self.log_dir / f"write_log_{self._timestamp}_{session_id}.ndjson"

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def append(self, entry: dict) -> None:
        """Validate *entry*, stamp session_id, write one NDJSON line, fsync."""
        entry = dict(entry)
        entry.setdefault("session_id", self.session_id)
        entry.setdefault("error_message", None)
        entry.setdefault("rollback_ref", None)

        missing = _REQUIRED_KEYS - entry.keys()
        if missing:
            raise ValueError(
                f"WriteLog.append: entry is missing required keys: {sorted(missing)}"
            )

        line = json.dumps(entry, ensure_ascii=False, default=str)
        with open(self._log_file, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def entries_for_session(self, session_id: str) -> list[dict]:
        """Return all entries whose session_id matches *session_id*."""
        entries: list[dict] = []
        for path in sorted(self.log_dir.glob("write_log_*_" + session_id + ".ndjson")):
            entries.extend(_read_ndjson(path))
        return entries

    def all_entries(self) -> list[dict]:
        """Read and return all entries across every session file in log_dir."""
        entries: list[dict] = []
        for path in sorted(self.log_dir.glob("write_log_*.ndjson")):
            entries.extend(_read_ndjson(path))
        return entries

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def prune(self, days: int = 90) -> int:
        """Delete NDJSON files whose embedded timestamp is older than *days* days.

        Parses the timestamp from the filename — does not use filesystem mtime.
        Returns count deleted.
        """
        cutoff = datetime.now(tz=timezone.utc).timestamp() - days * 86400
        deleted = 0
        for path in sorted(self.log_dir.glob("write_log_*.ndjson")):
            ts = _parse_filename_timestamp(path)
            if ts is not None and ts.timestamp() < cutoff:
                path.unlink()
                deleted += 1
        return deleted


def _read_ndjson(path: Path) -> list[dict]:
    entries: list[dict] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    except OSError:
        pass
    return entries


__all__ = ["WriteLog"]
