"""Configuration management and shared utilities for Blender MCP."""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9876
MAX_MESSAGE_SIZE = 100 * 1024 * 1024  # 100 MB

DEFAULT_CONFIG = {
    "tcp_host": DEFAULT_HOST,
    "tcp_port": DEFAULT_PORT,
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

    # Restrict permissions (owner read/write only) to protect API tokens
    try:
        os.chmod(config_path, 0o600)
    except OSError:
        if sys.platform != "win32":
            logger.warning("Failed to restrict config file permissions: %s", config_path)

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


# ---------------------------------------------------------------------------
# Shared HTTP client
# ---------------------------------------------------------------------------

_http_client: httpx.Client | None = None


def get_http_client(timeout: int = 30, headers: dict[str, str] | None = None) -> httpx.Client:
    """Get or create a shared HTTP client, reusing the instance across calls.

    Args:
        timeout: Request timeout in seconds.
        headers: Default headers for the client.
    """
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers=headers or {},
        )
    return _http_client
