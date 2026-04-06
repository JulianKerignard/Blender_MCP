# Blender MCP

MCP (Model Context Protocol) server for **Blender** — allows AI assistants like Claude to directly control Blender for 3D modeling, materials, rendering, and asset import from SketchFab.

## Architecture

```
┌─────────────┐     TCP/JSON      ┌──────────────────┐     MCP/stdio     ┌─────────┐
│   Blender   │ ◄──────────────► │   MCP Server     │ ◄───────────────► │  Claude  │
│   (Addon)   │   port 9876      │   (Python)       │                    │  Code   │
└─────────────┘                   └──────────────────┘                    └─────────┘
```

- **Blender Addon**: Runs inside Blender, opens a TCP server, executes `bpy` commands
- **MCP Server**: Standalone Python process exposing 36 tools to Claude via MCP protocol

## Features

- **36 MCP tools** across 9 categories
- **Scene management**: list, inspect, select, delete, duplicate objects
- **Modeling**: primitives, custom meshes, BMesh operations (extrude, bevel, inset, subdivide)
- **Transforms**: position, rotation, scale (get/set/apply)
- **Materials**: Principled BSDF creation, textures, property editing
- **Modifiers**: add/configure/apply (subdivision, bevel, boolean, mirror, array...)
- **SketchFab integration**: search, download, and auto-import 3D models
- **Import/Export**: glTF, GLB, FBX, OBJ, STL, PLY
- **Rendering**: render images, configure settings, viewport screenshots
- **Code execution**: run arbitrary Python in Blender for advanced operations

## Installation

### Prerequisites

- **Blender 4.0+** installed and running
- **Python 3.10+**
- **Claude Code** or any MCP-compatible client

### 1. Install the MCP Server

```bash
cd BlenderMCP
pip install -e .
```

Or with requirements:
```bash
pip install -r requirements.txt
```

### 2. Install the Blender Addon

1. Open Blender
2. Go to **Edit > Preferences > Add-ons**
3. Click **Install...** and select `addon/__init__.py`
4. Enable the addon **"Blender MCP"**

### 3. Configure Claude Code

Add to your Claude Code `settings.json`:

```json
{
  "mcpServers": {
    "blender": {
      "command": "python",
      "args": ["-m", "blender_mcp"],
      "cwd": "/path/to/BlenderMCP"
    }
  }
}
```

## Usage

### Quick Start

1. **Start Blender** and open the MCP panel (View3D sidebar > MCP tab)
2. Click **"Start MCP Server"** in the panel
3. **Start Claude Code** — it will auto-connect to Blender

### SketchFab Setup

To search and import 3D models from SketchFab:

1. Create a free account at [sketchfab.com](https://sketchfab.com)
2. Get your API token at [sketchfab.com/settings/password](https://sketchfab.com/settings/password)
3. Configure via one of:
   - **Blender addon preferences**: Edit > Preferences > Add-ons > Blender MCP
   - **MCP tool**: Ask Claude to run `sketchfab_configure` with your token
   - **Environment variable**: `SKETCHFAB_API_TOKEN=your_token_here`

Then ask Claude to search and import models:
> "Search SketchFab for a medieval castle and import the best result"

## Available Tools

### Scene Management
| Tool | Description |
|------|-------------|
| `get_scene_info` | Get complete scene info |
| `list_objects` | List all objects (with optional type filter) |
| `get_object_info` | Detailed info about a specific object |
| `select_objects` | Select objects by name |
| `delete_objects` | Delete objects |
| `duplicate_object` | Duplicate an object |

### Modeling
| Tool | Description |
|------|-------------|
| `create_primitive` | Create cube, sphere, cylinder, cone, torus, plane, etc. |
| `create_mesh` | Create mesh from vertices/faces data |
| `edit_mesh` | BMesh ops: extrude, bevel, inset, subdivide, loop cut |
| `join_objects` | Join multiple objects into one |
| `separate_mesh` | Separate by selection, material, or loose parts |
| `set_origin` | Set object origin point |
| `set_smooth_shading` | Toggle smooth/flat shading |

### Transforms
| Tool | Description |
|------|-------------|
| `set_transform` | Set position/rotation/scale |
| `get_transform` | Read current transforms |
| `apply_transform` | Apply transforms (Ctrl+A) |

### Materials
| Tool | Description |
|------|-------------|
| `create_material` | Create Principled BSDF material |
| `assign_material` | Assign material to object |
| `set_material_properties` | Edit color, metallic, roughness, etc. |
| `list_materials` | List all materials |
| `add_texture` | Add image texture (diffuse, normal, roughness...) |

### Modifiers
| Tool | Description |
|------|-------------|
| `add_modifier` | Add modifier (subdivision, bevel, boolean, mirror...) |
| `set_modifier_properties` | Configure modifier settings |
| `apply_modifier` | Apply modifier to mesh |

### SketchFab
| Tool | Description |
|------|-------------|
| `sketchfab_search` | Search for 3D models |
| `sketchfab_get_model` | Get model details |
| `sketchfab_download_import` | Download and import into Blender |
| `sketchfab_configure` | Set API token and download directory |

### Import/Export
| Tool | Description |
|------|-------------|
| `import_model` | Import glTF, GLB, FBX, OBJ, STL, PLY |
| `export_model` | Export scene or selection |

### Rendering
| Tool | Description |
|------|-------------|
| `render_image` | Render scene to image |
| `set_render_settings` | Configure engine, resolution, samples |
| `get_viewport_screenshot` | Capture viewport |

### Utility
| Tool | Description |
|------|-------------|
| `execute_blender_code` | Run arbitrary Python in Blender |
| `get_blender_info` | Blender version and status |
| `undo` | Undo last operation |

## Configuration

### Addon Preferences (in Blender)
- **TCP Port**: Port for MCP communication (default: 9876)
- **SketchFab API Token**: For searching and downloading models

### Config File
Location: `~/.blender_mcp/config.json`

```json
{
  "tcp_host": "127.0.0.1",
  "tcp_port": 9876,
  "sketchfab_api_token": "your_token_here",
  "download_dir": "~/.blender_mcp/downloads"
}
```

### Environment Variables
- `SKETCHFAB_API_TOKEN` — SketchFab API token (overrides config file)

## License

MIT
