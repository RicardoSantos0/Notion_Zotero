"""_client.py — Notion HTTP client, retry infrastructure, and ID resolvers.

Private module. Do not import this directly from outside src.analysis; use the
public facades (notion_fetch, notion_upload) or notion_utils for backward compatibility.
"""

from __future__ import annotations

import os
import re
import time
from typing import Any, Callable, TypeVar

from dotenv import load_dotenv
from notion_client import Client
from notion_client.errors import APIResponseError

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MAX_RETRIES = 3
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
PAGE_SIZE = 100
MAX_BACKOFF_SECONDS = 8
DEFAULT_RETRY_SECONDS = 2

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Private env helpers
# ---------------------------------------------------------------------------

def _clean_env_value(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip().strip('"').strip("'")


def _normalize_notion_id(value: str) -> str:
    compact_value = value.replace("-", "")
    if re.fullmatch(r"[0-9a-fA-F]{32}", compact_value):
        return (
            f"{compact_value[0:8]}-"
            f"{compact_value[8:12]}-"
            f"{compact_value[12:16]}-"
            f"{compact_value[16:20]}-"
            f"{compact_value[20:32]}"
        )
    return value


def _get_notion_token() -> str:
    token = _clean_env_value(os.environ.get("NOTION_TOKEN"))
    if not token:
        raise ValueError("NOTION_TOKEN not set in .env")
    return token


def _resolve_required_id(raw_value: str | None, error_message: str) -> str:
    cleaned_value = _clean_env_value(raw_value)
    if not cleaned_value:
        raise ValueError(error_message)
    return _normalize_notion_id(cleaned_value)


def _extract_plain_text(parts: list[dict[str, Any]]) -> str:
    return "".join(part.get("plain_text", "") for part in parts)


def _backoff_seconds(attempt: int) -> int:
    return min(2**attempt, MAX_BACKOFF_SECONDS)


# ---------------------------------------------------------------------------
# Client construction
# ---------------------------------------------------------------------------

def get_notion_client() -> Client:
    """Build an authenticated Notion SDK client."""
    return Client(auth=_get_notion_token())


def get_headers() -> dict[str, str]:
    """Backward-compatible helper; prefer using get_notion_client()."""
    return {"Authorization": f"Bearer {_get_notion_token()}"}


# ---------------------------------------------------------------------------
# Retry infrastructure
# ---------------------------------------------------------------------------

def _is_retryable_exception(exc: Exception) -> bool:
    status = getattr(exc, "status", None)
    response = getattr(exc, "response", None)
    response_status = getattr(response, "status_code", None)

    return (
        status in RETRYABLE_STATUS_CODES
        or response_status in RETRYABLE_STATUS_CODES
        or getattr(exc, "code", None) == "rate_limited"
    )


def _call_with_retry(
    action_name: str,
    call: Callable[[], T],
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> T:
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return call()
        except Exception as exc:
            last_error = exc
            if attempt >= max_retries or (
                isinstance(exc, APIResponseError) and not _is_retryable_exception(exc)
            ):
                break
            time.sleep(_backoff_seconds(attempt))

    detail = f"{type(last_error).__name__}: {last_error}" if last_error else "unknown error"
    raise RuntimeError(
        f"Notion action failed after {max_retries + 1} attempts: {action_name}. Last error: {detail}"
    ) from last_error


# ---------------------------------------------------------------------------
# ID resolvers
# ---------------------------------------------------------------------------

def get_database_id(database_id: str | None = None) -> str:
    return _resolve_required_id(
        database_id or os.environ.get("NOTION_DATABASE_ID"),
        "NOTION_DATABASE_ID not set in .env or passed as argument",
    )


def get_page_id(page_id: str | None = None) -> str:
    return _resolve_required_id(
        page_id or os.environ.get("NOTION_PAGE_ID"),
        "Set NOTION_PAGE_ID in .env or pass page_id explicitly",
    )


def get_block_id(block_id: str | None = None) -> str:
    """Resolve a block ID, falling back to NOTION_PAGE_ID when absent."""
    return get_page_id(block_id)


# ---------------------------------------------------------------------------
# Low-level HTTP wrappers
# ---------------------------------------------------------------------------

def _sdk_request(
    client: Client,
    method: str,
    path: str,
    *,
    query: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _call_with_retry(
        f"{method} {path}",
        lambda: client.request(
            path=path.lstrip("/"),
            method=method,
            query=query or {},
            body=body or {},
        ),
    )


def notion_get(path: str, params: dict | None = None) -> dict[str, Any]:
    """Compatibility wrapper around the SDK low-level request API."""
    return _sdk_request(get_notion_client(), "GET", path, query=params)


def notion_post(path: str, payload: dict | None = None) -> dict[str, Any]:
    """Compatibility wrapper around the SDK low-level request API."""
    return _sdk_request(get_notion_client(), "POST", path, body=payload)


# ---------------------------------------------------------------------------
# Pagination helper
# ---------------------------------------------------------------------------

def _collect_paginated_results(
    fetch_chunk: Callable[[str | None], dict[str, Any]],
) -> list[dict]:
    results: list[dict] = []
    start_cursor: str | None = None

    while True:
        response = fetch_chunk(start_cursor)
        results.extend(response.get("results", []))

        if not response.get("has_more"):
            break
        start_cursor = response.get("next_cursor")

    return results


# ---------------------------------------------------------------------------
# Platform data source helper
# ---------------------------------------------------------------------------

def _get_platform_ds_id(client: Client, database_id: str) -> str | None:
    """Return the active (non-archived) data source ID for a database."""
    database = _call_with_retry(
        f"databases.retrieve({database_id})",
        lambda: client.databases.retrieve(database_id=database_id),
    )
    for ds in database.get("data_sources") or []:
        ds_id = ds.get("id")
        if not ds_id:
            continue
        ds_data = _call_with_retry(
            f"data_sources.retrieve({ds_id})",
            lambda _id=ds_id: client.data_sources.retrieve(data_source_id=_id),
        )
        if not ds_data.get("in_trash") and not ds_data.get("archived"):
            return ds_id
    return None


def _resolve_query_target_id(client: Client, database_id: str) -> str:
    """Resolve the most compatible query target for the installed Notion API version."""
    data_source_id = _get_platform_ds_id(client, database_id)
    if data_source_id:
        return _normalize_notion_id(data_source_id)
    return database_id


def _wait_for_platform_ds(client: Client, database_id: str, max_wait_seconds: int = 30) -> str | None:
    """Poll until the platform `data_source` for `database_id` is available or timeout."""
    try:
        max_wait = int(os.getenv("NOTION_DS_WAIT_SECONDS", str(max_wait_seconds)))
    except Exception:
        max_wait = max_wait_seconds

    deadline = time.time() + max_wait
    attempt = 0
    while time.time() < deadline:
        try:
            ds_id = _get_platform_ds_id(client, database_id)
            if ds_id:
                return ds_id
        except Exception:
            # swallow transient errors and retry until deadline
            pass
        time.sleep(_backoff_seconds(attempt))
        attempt += 1
    return None
