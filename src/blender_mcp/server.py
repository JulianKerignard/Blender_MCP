"""Blender MCP Server - Main entry point."""

import json
import logging
import os
from mcp.server.fastmcp import FastMCP

from blender_mcp.connection import BlenderConnection
from blender_mcp.config import load_config

logger = logging.getLogger(__name__)

# Global connection instance (reused across reconnects)
_connection: BlenderConnection | None = None


def get_connection() -> BlenderConnection:
    """Get or create the Blender connection, reusing the instance."""
    global _connection
    if _connection is None:
        config = load_config()
        _connection = BlenderConnection(
            host=config.get("tcp_host", "127.0.0.1"),
            port=config.get("tcp_port", 9876),
        )
    if not _connection.is_connected:
        _connection.connect()
    return _connection


# Create MCP server
mcp = FastMCP(
    "Blender MCP",
    description="Control Blender from AI assistants - modeling, materials, rendering, SketchFab import",
)


def _exec(code: str) -> dict:
    """Execute Python code in Blender and return the response dict.

    Raises RuntimeError with a clean message on Blender errors.
    """
    conn = get_connection()
    return conn.execute_code(code)


def _exec_json(code: str) -> str:
    """Execute Python code in Blender and return a JSON string result.

    Catches connection and runtime errors, returning them as JSON error objects.
    """
    try:
        result = _exec(code)
        return json.dumps(result, indent=2)
    except (ConnectionError, RuntimeError) as e:
        return json.dumps({"error": str(e)}, indent=2)


def _error_json(message: str) -> str:
    """Return a JSON-formatted error string."""
    return json.dumps({"error": message}, indent=2)


def _exec_and_read_image(code: str) -> bytes | None:
    """Execute code in Blender that renders to a temp file, then read the image bytes.

    The executed code must set result = {"output_path": "/path/to/rendered.png"}
    """
    try:
        response = _exec(code)
        result = response.get("result", {})
        if isinstance(result, dict):
            output_path = result.get("output_path", "")
        else:
            return None
        if output_path and os.path.exists(output_path):
            with open(output_path, "rb") as f:
                data = f.read()
            os.unlink(output_path)  # Clean up temp file
            return data
        return None
    except (ConnectionError, RuntimeError):
        return None


# ---------------------------------------------------------------------------
# Register all tools from submodules
# ---------------------------------------------------------------------------

def _register_tools():
    """Import all tool modules to register their @mcp.tool decorators."""
    from blender_mcp.tools import (  # noqa: F401
        scene,
        modeling,
        transforms,
        materials,
        modifiers,
        sketchfab,
        import_export,
        render,
        code_exec,
        lighting,
        camera,
        polyhaven,
        collections,
    )

_register_tools()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    """Run the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
