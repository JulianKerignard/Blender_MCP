# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Blender MCP is a Model Context Protocol server that lets AI assistants control Blender for 3D modeling, scene composition, materials, lighting, rendering, animation, and asset management. It exposes 98+ tools across 21 categories.

## Architecture

```
+---------------+     TCP/JSON      +------------------+     MCP/stdio     +---------+
|   Blender     | <---------------> |   MCP Server     | <---------------> |  Claude |
|   (Addon)     |   port 9876      |   (Python)       |                    |  Code   |
+---------------+                   +------------------+                    +---------+
```

**Two-process design:**
- **`addon/__init__.py`** -- Blender addon (runs inside Blender). Opens a TCP server on port 9876, receives JSON commands from the MCP server, and executes Python code on Blender's main thread via `bpy.app.timers`. Commands are queued from a background accept thread and processed on the main thread to satisfy Blender's threading model.
- **`src/blender_mcp/`** -- Standalone MCP server (Python process). Communicates with Claude via stdio (MCP protocol) and with Blender via TCP. All tool implementations generate Python code strings that are sent to the addon for execution via `exec()`.

**Key communication pattern:** Every MCP tool in `src/blender_mcp/tools/*.py` builds a Python code string containing `bpy` calls, then calls `_exec_json(code)` or `_exec_and_read_image(code)` from `server.py`. The addon executes the code and returns results via a length-prefixed JSON TCP protocol (4-byte big-endian length header + JSON payload).

**Connection lifecycle:** `server.py` maintains a singleton `BlenderConnection` that lazy-connects on first tool call. The addon's `BlenderMCPServer` accepts one client at a time and processes commands sequentially via a timer-based queue.

## Commands

```bash
# Install (editable mode)
pip install -e .

# Run the MCP server standalone
python -m blender_mcp

# Install addon in Blender
# Edit > Preferences > Add-ons > Install > select addon/__init__.py
```

There are no tests, linter, or build commands configured.

## Code Organization

- `src/blender_mcp/server.py` -- FastMCP server instance, connection management, helper functions (`_exec`, `_exec_json`, `_exec_and_read_image`, `_error_json`), tool registration
- `src/blender_mcp/connection.py` -- `BlenderConnection` TCP client (length-prefixed JSON protocol)
- `src/blender_mcp/config.py` -- Config file management (`~/.blender_mcp/config.json`), mtime-based caching, SketchFab token resolution
- `src/blender_mcp/tools/` -- 21 tool modules, each importing `mcp` from `server.py` and registering tools via `@mcp.tool()` decorator
- `addon/__init__.py` -- Complete Blender addon: TCP server, code execution engine, UI panel, preferences
- `.claude/skills/` -- Claude Code skill files for guided workflows (modeling, animation, texturing, etc.)

## Adding a New Tool

1. Create or edit a file in `src/blender_mcp/tools/`
2. Import helpers: `from blender_mcp.server import mcp, _exec_json, _error_json`
3. Define a function with `@mcp.tool()` decorator
4. Build a Python code string that uses `bpy` and sets a `result` variable
5. Return `_exec_json(code)` (for JSON results) or use `_exec_and_read_image(code)` (for image results via `Image`)
6. If it's a new module, add it to the import list in `server.py:_register_tools()`

The executed code runs in a shared globals dict (`bpy`, `math`, `json` pre-imported). The code must set `result = ...` for the return value to be captured.

## Configuration

- Config file: `~/.blender_mcp/config.json` (tcp_host, tcp_port, sketchfab_api_token, download_dir)
- Environment: `SKETCHFAB_API_TOKEN` overrides config file
- Addon preferences in Blender: TCP port, SketchFab token
- Default TCP: `127.0.0.1:9876`

## Dependencies

- `mcp>=1.0.0` (FastMCP framework)
- `httpx>=0.27.0` (HTTP client for SketchFab/PolyHaven APIs)
- `numpy>=1.24.0`
- Python 3.10+, Blender 4.0+ (addon manifest requires 4.2+)
