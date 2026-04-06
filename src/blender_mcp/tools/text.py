"""Text object tools for creating and editing text in Blender."""

from blender_mcp.server import mcp, _exec_json, _error_json


@mcp.tool()
def create_text(
    text: str = "Text",
    name: str = "",
    location: list[float] | None = None,
    rotation: list[float] | None = None,
    size: float = 1.0,
    extrude: float = 0.0,
    bevel_depth: float = 0.0,
    bevel_resolution: int = 0,
    align_x: str = "LEFT",
    align_y: str = "TOP_BASELINE",
    font_path: str = "",
) -> str:
    """Create a text object in Blender.

    Rotation is specified in degrees and converted to radians internally.
    Use extrude to give the text 3D depth, and bevel_depth for rounded edges.

    Args:
        text: The text content to display.
        name: Optional name for the object. If empty, Blender assigns a default.
        location: XYZ position as [x, y, z]. Defaults to origin [0, 0, 0].
        rotation: XYZ rotation in degrees. Defaults to [0, 0, 0].
        size: Font size. Default 1.0.
        extrude: 3D extrusion depth. Default 0.0 (flat).
        bevel_depth: Bevel depth for rounded edges. Default 0.0.
        bevel_resolution: Bevel curve resolution. Default 0.
        align_x: Horizontal alignment: LEFT, CENTER, RIGHT, JUSTIFY, FLUSH.
        align_y: Vertical alignment: TOP_BASELINE, TOP, CENTER, BOTTOM_BASELINE, BOTTOM.
        font_path: Optional path to a .ttf or .otf font file to load.

    Returns:
        JSON with the created text object's name, content, size, and dimensions.
    """
    code = f"""
import bpy
import math

loc = {location!r}
if loc is None:
    loc = [0, 0, 0]

rot_deg = {rotation!r}
if rot_deg is None:
    rot_deg = [0, 0, 0]
rot_rad = [math.radians(a) for a in rot_deg]

bpy.ops.object.text_add(location=loc, rotation=rot_rad)
obj = bpy.context.active_object
"""
    if name:
        code += f"obj.name = {name!r}\n"

    code += f"""
obj.data.body = {text!r}
obj.data.size = {size!r}
obj.data.extrude = {extrude!r}
obj.data.bevel_depth = {bevel_depth!r}
obj.data.bevel_resolution = {bevel_resolution!r}
obj.data.align_x = {align_x!r}
obj.data.align_y = {align_y!r}

font_path = {font_path!r}
if font_path:
    obj.data.font = bpy.data.fonts.load(font_path)

result = {{
    "name": obj.name,
    "text": obj.data.body,
    "size": obj.data.size,
    "extrude": obj.data.extrude,
    "bevel_depth": obj.data.bevel_depth,
    "bevel_resolution": obj.data.bevel_resolution,
    "align_x": obj.data.align_x,
    "align_y": obj.data.align_y,
    "dimensions": list(obj.dimensions),
}}
"""
    return _exec_json(code)


@mcp.tool()
def set_text_content(name: str, text: str) -> str:
    """Set the text content of an existing text (font) object.

    Args:
        name: Name of the text object.
        text: New text content to display.

    Returns:
        JSON with the updated object name and text content.
    """
    code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
elif obj.type != 'FONT':
    result = {{"error": "Object " + {name!r} + " is not a text object (type: " + obj.type + ")"}}
else:
    obj.data.body = {text!r}
    result = {{
        "name": obj.name,
        "text": obj.data.body,
        "size": obj.data.size,
        "dimensions": list(obj.dimensions),
    }}
"""
    return _exec_json(code)


@mcp.tool()
def set_text_properties(
    name: str,
    size: float | None = None,
    extrude: float | None = None,
    bevel_depth: float | None = None,
    bevel_resolution: int | None = None,
    align_x: str | None = None,
    align_y: str | None = None,
    font_path: str | None = None,
) -> str:
    """Set properties on an existing text (font) object.

    Only the provided (non-None) values are modified; omitted values stay as-is.

    Args:
        name: Name of the text object.
        size: Font size.
        extrude: 3D extrusion depth.
        bevel_depth: Bevel depth for rounded edges.
        bevel_resolution: Bevel curve resolution.
        align_x: Horizontal alignment: LEFT, CENTER, RIGHT, JUSTIFY, FLUSH.
        align_y: Vertical alignment: TOP_BASELINE, TOP, CENTER, BOTTOM_BASELINE, BOTTOM.
        font_path: Path to a .ttf or .otf font file to load.

    Returns:
        JSON with the updated text properties.
    """
    code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
elif obj.type != 'FONT':
    result = {{"error": "Object " + {name!r} + " is not a text object (type: " + obj.type + ")"}}
else:
    size = {size!r}
    extrude = {extrude!r}
    bevel_depth = {bevel_depth!r}
    bevel_resolution = {bevel_resolution!r}
    align_x = {align_x!r}
    align_y = {align_y!r}
    font_path = {font_path!r}

    if size is not None:
        obj.data.size = size
    if extrude is not None:
        obj.data.extrude = extrude
    if bevel_depth is not None:
        obj.data.bevel_depth = bevel_depth
    if bevel_resolution is not None:
        obj.data.bevel_resolution = bevel_resolution
    if align_x is not None:
        obj.data.align_x = align_x
    if align_y is not None:
        obj.data.align_y = align_y
    if font_path is not None and font_path:
        obj.data.font = bpy.data.fonts.load(font_path)

    result = {{
        "name": obj.name,
        "text": obj.data.body,
        "size": obj.data.size,
        "extrude": obj.data.extrude,
        "bevel_depth": obj.data.bevel_depth,
        "bevel_resolution": obj.data.bevel_resolution,
        "align_x": obj.data.align_x,
        "align_y": obj.data.align_y,
        "dimensions": list(obj.dimensions),
    }}
"""
    return _exec_json(code)


@mcp.tool()
def text_to_mesh(name: str) -> str:
    """Convert a text object to a mesh object.

    This is a one-way operation: the text will no longer be editable as text
    after conversion. Useful for further mesh editing or boolean operations.

    Args:
        name: Name of the text object to convert.

    Returns:
        JSON with the resulting mesh info (name, vertex count, face count).
    """
    code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
elif obj.type != 'FONT':
    result = {{"error": "Object " + {name!r} + " is not a text object (type: " + obj.type + ")"}}
else:
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.object.convert(target='MESH')

    obj = bpy.context.active_object
    result = {{
        "name": obj.name,
        "type": obj.type,
        "vertex_count": len(obj.data.vertices),
        "face_count": len(obj.data.polygons),
        "dimensions": list(obj.dimensions),
    }}
"""
    return _exec_json(code)
