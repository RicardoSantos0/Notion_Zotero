"""Connectors package. Contains safe, offline-friendly connector stubs.

Do NOT implement live writes here. Connector implementations must be gated
behind explicit user action and separate staging tooling.
"""

__all__ = ["notion_stub"]
