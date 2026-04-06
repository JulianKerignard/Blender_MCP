"""Configuration management for Blender MCP."""

import json
import os
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = {
    "tcp_host": "127.0.0.1",
    "tcp_port": 9876,
    "sketchfab_api_token": "",
    "download_dir": "",
}

# Module-level config cache with mtime-based invalidation
_cached_config: dict[str, Any] | None = None
_config_mtime: float = 0.0


def get_config_path() -> Path:
    """Get the config file path."""
    config_dir = Path.home() / ".blender_mcp"
    config_dir.mkdir(exist_ok=True)
    return config_dir / "config.json"


def load_config() -> dict[str, Any]:
    """Load configuration from file, with defaults. Cached by file mtime."""
    global _cached_config, _config_mtime

    config_path = get_config_path()
    try:
        mtime = config_path.stat().st_mtime
    except OSError:
        mtime = 0.0

    if _cached_config is not None and mtime == _config_mtime:
        return dict(_cached_config)

    config = dict(DEFAULT_CONFIG)
    if config_path.exists():
        try:
            with open(config_path) as f:
                file_config = json.load(f)
            config.update(file_config)
        except (json.JSONDecodeError, OSError):
            pass

    _cached_config = config
    _config_mtime = mtime
    return dict(config)


def save_config(config: dict[str, Any]) -> None:
    """Save configuration to file and invalidate cache."""
    global _cached_config, _config_mtime

    config_path = get_config_path()
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    # Invalidate cache so next load_config picks up new values
    _cached_config = None
    _config_mtime = 0.0


def get_sketchfab_token(config: dict[str, Any] | None = None) -> str:
    """Get SketchFab API token from environment or config.

    Args:
        config: Pre-loaded config dict to avoid redundant disk reads.
    """
    env_token = os.environ.get("SKETCHFAB_API_TOKEN", "")
    if env_token:
        return env_token

    if config is None:
        config = load_config()
    return config.get("sketchfab_api_token", "")


def get_download_dir(config: dict[str, Any] | None = None) -> Path:
    """Get the download directory for 3D assets.

    Args:
        config: Pre-loaded config dict to avoid redundant disk reads.
    """
    if config is None:
        config = load_config()
    download_dir = config.get("download_dir", "")

    if download_dir:
        path = Path(download_dir).expanduser()
    else:
        path = Path.home() / ".blender_mcp" / "downloads"

    path.mkdir(parents=True, exist_ok=True)
    return path
