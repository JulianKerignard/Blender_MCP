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


def get_config_path() -> Path:
    """Get the config file path."""
    config_dir = Path.home() / ".blender_mcp"
    config_dir.mkdir(exist_ok=True)
    return config_dir / "config.json"


def load_config() -> dict[str, Any]:
    """Load configuration from file, with defaults."""
    config = dict(DEFAULT_CONFIG)
    config_path = get_config_path()

    if config_path.exists():
        try:
            with open(config_path) as f:
                file_config = json.load(f)
            config.update(file_config)
        except (json.JSONDecodeError, OSError):
            pass

    return config


def save_config(config: dict[str, Any]) -> None:
    """Save configuration to file."""
    config_path = get_config_path()
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


def get_sketchfab_token() -> str:
    """Get SketchFab API token from config or environment.

    Priority:
    1. Environment variable SKETCHFAB_API_TOKEN
    2. Config file
    """
    env_token = os.environ.get("SKETCHFAB_API_TOKEN", "")
    if env_token:
        return env_token

    config = load_config()
    return config.get("sketchfab_api_token", "")


def get_download_dir() -> Path:
    """Get the download directory for 3D assets."""
    config = load_config()
    download_dir = config.get("download_dir", "")

    if download_dir:
        path = Path(download_dir).expanduser()
    else:
        path = Path.home() / ".blender_mcp" / "downloads"

    path.mkdir(parents=True, exist_ok=True)
    return path
