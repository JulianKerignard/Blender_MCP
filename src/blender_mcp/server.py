"""Blender MCP Server - Main entry point."""

import logging
from mcp.server.fastmcp import FastMCP

from blender_mcp.connection import BlenderConnection
from blender_mcp.config import load_config

logger = logging.getLogger(__name__)

# Global connection instance
_connection: BlenderConnection | None = None


def get_connection() -> BlenderConnection:
    """Get or create the Blender connection."""
    global _connection
    if _connection is None or not _connection.is_connected:
        config = load_config()
        _connection = BlenderConnection(
            host=config.get("tcp_host", "127.0.0.1"),
            port=config.get("tcp_port", 9876),
        )
        _connection.connect()
    return _connection


# Create MCP server
mcp = FastMCP(
    "Blender MCP",
    description="Control Blender from AI assistants - modeling, materials, rendering, SketchFab import",
)


def _exec(code: str) -> dict:
    """Shortcut: execute Python code in Blender and return result."""
    conn = get_connection()
    return conn.execute_code(code)


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
