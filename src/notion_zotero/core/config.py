"""Project configuration helpers for the Notion/Zotero CLI."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping


DEFAULT_CONFIG_FILENAMES = (
    "notion_zotero.config.json",
    ".notion-zotero.json",
    "notion-zotero.json",
)


class ConfigError(ValueError):
    """Raised when a project configuration file is invalid."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in config file {path}: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"Could not read config file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"Config file {path} must contain a JSON object")
    return data


def find_config_path(explicit_path: str | Path | None = None) -> Path | None:
    """Return the explicit/env/default project config path if one exists."""
    if explicit_path:
        path = Path(explicit_path)
        if not path.exists():
            raise ConfigError(f"Config file not found: {path}")
        return path

    env_path = os.environ.get("NOTION_ZOTERO_CONFIG")
    if env_path:
        path = Path(env_path)
        if not path.exists():
            raise ConfigError(f"Config file not found: {path}")
        return path

    for name in DEFAULT_CONFIG_FILENAMES:
        path = Path(name)
        if path.exists():
            return path
    return None


def load_project_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load a project config file, returning an empty dict when none is present."""
    config_path = find_config_path(path)
    if config_path is None:
        return {}
    return _read_json(config_path)


def config_get(config: Mapping[str, Any], dotted_key: str, default: Any = None) -> Any:
    """Read a dotted key from a nested config mapping."""
    value: Any = config
    for part in dotted_key.split("."):
        if not isinstance(value, Mapping) or part not in value:
            return default
        value = value[part]
    return value


__all__ = [
    "ConfigError",
    "DEFAULT_CONFIG_FILENAMES",
    "config_get",
    "find_config_path",
    "load_project_config",
]
