# Blender MCP

MCP (Model Context Protocol) server for **Blender** -- allows AI assistants like Claude to directly control Blender for 3D modeling, scene composition, materials, lighting, rendering, animation, and asset management.

## Architecture

```
+---------------+     TCP/JSON      +------------------+     MCP/stdio     +---------+
|   Blender     | <---------------> |   MCP Server     | <---------------> |  Claude |
|   (Addon)     |   port 9876      |   (Python)       |                    |  Code   |
+---------------+                   +------------------+                    +---------+
```

- **Blender Addon**: Runs inside Blender, opens a TCP server, executes `bpy` commands
- **MCP Server**: Standalone Python process exposing 72 tools to Claude via MCP protocol

## Features

- **72 MCP tools** across 17 categories
- **Scene management**: list, inspect, select, delete, duplicate objects
- **Modeling**: primitives, custom meshes, BMesh operations (extrude, bevel, inset, subdivide)
- **Transforms**: position, rotation, scale (get/set/apply)
- **Materials**: Principled BSDF creation, textures, property editing
- **Modifiers**: add/configure/apply (subdivision, bevel, boolean, mirror, array...)
- **Lighting**: point, sun, spot, area lights with studio presets
- **Camera**: create, configure, point-at-target, depth of field
- **Rendering**: render images, configure settings, viewport screenshots
- **Vision**: Claude can *see* the scene via viewport snapshots and render previews
- **Collections**: organize objects into collections, control visibility
- **Animation**: keyframes, frame range, timeline control
- **3D Cursor**: position, snap to object, snap object to cursor
- **Text Objects**: create 3D text, edit content and properties, convert to mesh
- **Constraints & Parenting**: parent/child hierarchies, Track To, Copy Location, etc.
- **SketchFab integration**: search, download, and auto-import 3D models
- **Poly Haven integration**: free CC0 HDRIs and PBR textures from polyhaven.com
- **Import/Export**: glTF, GLB, FBX, OBJ, STL, PLY
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
3. **Start Claude Code** -- it will auto-connect to Blender

### Vision (Claude Can See the Scene)

Claude can visually inspect your Blender scene using two tools:

- **`get_scene_snapshot`** -- captures a fast viewport screenshot and returns it as an image
- **`render_preview`** -- renders a quick low-res EEVEE preview with materials and lighting

Ask Claude to "look at the scene" or "check how it looks" and it will use these tools to see and respond to what is on screen.

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

### Poly Haven Setup

[Poly Haven](https://polyhaven.com) provides free CC0-licensed HDRIs and PBR textures. No API key is required.

> "Download an outdoor HDRI from Poly Haven and set it as the environment"

> "Get a brick texture from Poly Haven and apply it to the wall material"

## Available Tools

### Scene Management (6 tools)
| Tool | Description |
|------|-------------|
| `get_scene_info` | Get complete scene info (objects, world, frame range, render engine) |
| `list_objects` | List all objects with optional type filter |
| `get_object_info` | Detailed info about a specific object |
| `select_objects` | Select objects by name |
| `delete_objects` | Delete objects by name |
| `duplicate_object` | Duplicate an object (optionally linked) |

### Modeling (7 tools)
| Tool | Description |
|------|-------------|
| `create_primitive` | Create cube, sphere, cylinder, cone, torus, plane, circle, grid, monkey |
| `create_mesh` | Create mesh from raw vertices, edges, and faces |
| `edit_mesh` | BMesh ops: extrude, bevel, inset, subdivide, loop cut |
| `join_objects` | Join multiple objects into one |
| `separate_mesh` | Separate by selection, material, or loose parts |
| `set_origin` | Set object origin point |
| `set_smooth_shading` | Toggle smooth/flat shading |

### Transforms (3 tools)
| Tool | Description |
|------|-------------|
| `set_transform` | Set position, rotation, and/or scale |
| `get_transform` | Read current transforms |
| `apply_transform` | Apply transforms (freeze current values) |

### Materials (5 tools)
| Tool | Description |
|------|-------------|
| `create_material` | Create Principled BSDF material with color, metallic, roughness, emission |
| `assign_material` | Assign material to object |
| `set_material_properties` | Edit color, metallic, roughness, emission, alpha |
| `list_materials` | List all materials in the scene |
| `add_texture` | Add image texture (diffuse, normal, roughness, metallic, bump, emission) |

### Modifiers (3 tools)
| Tool | Description |
|------|-------------|
| `add_modifier` | Add modifier (SUBSURF, BEVEL, BOOLEAN, ARRAY, MIRROR, SOLIDIFY...) |
| `set_modifier_properties` | Configure modifier settings |
| `apply_modifier` | Apply modifier to permanently alter the mesh |

### Lighting (4 tools)
| Tool | Description |
|------|-------------|
| `create_light` | Create POINT, SUN, SPOT, or AREA light |
| `set_light_properties` | Update energy, color, size, spot angle |
| `list_lights` | List all lights in the scene |
| `setup_studio_lighting` | Preset setups: three_point, outdoor_sun, dramatic, soft |

### Camera (4 tools)
| Tool | Description |
|------|-------------|
| `create_camera` | Create camera with lens, DOF, and position settings |
| `set_camera_properties` | Update lens, DOF, clipping, F-stop |
| `point_camera_at` | Point camera at an object (Track To) or a world coordinate |
| `set_active_camera` | Set the active scene camera |

### Rendering (5 tools)
| Tool | Description |
|------|-------------|
| `render_image` | Render scene to image file (EEVEE, Cycles, Workbench) |
| `set_render_settings` | Configure engine, resolution, samples, denoising |
| `get_viewport_screenshot` | Capture viewport to file |
| `get_scene_snapshot` | Capture viewport and return image for Claude to see |
| `render_preview` | Quick low-res EEVEE render returned as image for Claude to see |

### Collections (4 tools)
| Tool | Description |
|------|-------------|
| `create_collection` | Create a new collection (optionally under a parent) |
| `move_to_collection` | Move objects into a collection |
| `list_collections` | List all collections as a recursive tree |
| `set_collection_visibility` | Set viewport and render visibility |

### Animation (5 tools)
| Tool | Description |
|------|-------------|
| `insert_keyframe` | Insert a keyframe on an object property at a given frame |
| `delete_keyframe` | Delete a keyframe from an object property |
| `set_frame` | Set the current frame in the timeline |
| `set_frame_range` | Set the start and end frame of the scene |
| `get_keyframes` | Get all keyframes for an object |

### 3D Cursor (4 tools)
| Tool | Description |
|------|-------------|
| `set_cursor_location` | Set the 3D cursor position |
| `get_cursor_location` | Get the current 3D cursor position |
| `snap_cursor_to_object` | Snap the 3D cursor to an object's origin |
| `snap_object_to_cursor` | Snap an object to the 3D cursor location |

### Text Objects (4 tools)
| Tool | Description |
|------|-------------|
| `create_text` | Create a 3D text object |
| `set_text_content` | Change the text string of an existing text object |
| `set_text_properties` | Set font size, extrude depth, alignment, etc. |
| `text_to_mesh` | Convert a text object to a mesh |

### Constraints & Parenting (5 tools)
| Tool | Description |
|------|-------------|
| `set_parent` | Set parent-child relationship between objects |
| `clear_parent` | Remove parent from an object |
| `add_constraint` | Add a constraint (Track To, Copy Location, Limit Rotation...) |
| `remove_constraint` | Remove a constraint from an object |
| `list_constraints` | List all constraints on an object |

### SketchFab (4 tools)
| Tool | Description |
|------|-------------|
| `sketchfab_search` | Search for 3D models on SketchFab |
| `sketchfab_get_model` | Get detailed model info |
| `sketchfab_download_import` | Download and import a model into Blender |
| `sketchfab_configure` | Set API token and download directory |

### Poly Haven (4 tools)
| Tool | Description |
|------|-------------|
| `polyhaven_search` | Search for HDRIs, textures, or models on Poly Haven |
| `polyhaven_get_asset` | Get detailed asset info (resolutions, formats) |
| `polyhaven_download_hdri` | Download HDRI and set as world environment |
| `polyhaven_download_texture` | Download PBR texture set and optionally apply to a material |

### Import/Export (2 tools)
| Tool | Description |
|------|-------------|
| `import_model` | Import glTF, GLB, FBX, OBJ, STL, PLY |
| `export_model` | Export scene or selection to file |

### Utility (3 tools)
| Tool | Description |
|------|-------------|
| `execute_blender_code` | Run arbitrary Python code in Blender |
| `get_blender_info` | Blender version, scene, and status |
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
- `SKETCHFAB_API_TOKEN` -- SketchFab API token (overrides config file)

## License

MIT
