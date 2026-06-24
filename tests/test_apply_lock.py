"""M1 / T1.3 — test-first contract for the apply lock / session guard (built in M4).

A second acquire while the lock is held must be refused; releasing must allow
re-acquire. Fails for missing implementation until
`notion_zotero.services.sync_lock` exists.
"""
from __future__ import annotations

import pytest


def test_second_acquire_is_blocked(tmp_path):
    from notion_zotero.services import sync_lock

    first = sync_lock.SyncLock(tmp_path)
    with first.acquire():
        other = sync_lock.SyncLock(tmp_path)
        with pytest.raises(sync_lock.SyncLockHeld):
            with other.acquire():
                pass


def test_release_allows_reacquire(tmp_path):
    from notion_zotero.services import sync_lock

    with sync_lock.SyncLock(tmp_path).acquire():
        pass
    # lock released on exit -> a fresh acquire must succeed
    with sync_lock.SyncLock(tmp_path).acquire():
        pass
