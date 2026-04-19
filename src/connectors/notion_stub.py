"""A safe Notion connector stub used during analysis and testing.

This module intentionally does not perform any network I/O. It mirrors the
Notion SDK surface minimally for offline testing.
"""
from __future__ import annotations

from typing import Any


class NotionStubClient:
    def __init__(self, *args, **kwargs):
        pass

    def pages(self):
        raise RuntimeError("NotionStubClient is a test-only stub; do not call live APIs")


def get_stub_client() -> Any:
    return NotionStubClient()
