"""3D cursor tools for positioning and snapping."""

from blender_mcp.server import mcp, _exec_json, _error_json


@mcp.tool()
def set_cursor_location(location: list[float]) -> str:
    """Set the 3D cursor to a specific location.

    Args:
        location: [x, y, z] position in Blender units.
    """
    code = f"""
import bpy

loc = {location!r}
bpy.context.scene.cursor.location = (loc[0], loc[1], loc[2])

result = {{
    "cursor_location": list(bpy.context.scene.cursor.location),
}}
"""
    return _exec_json(code)


@mcp.tool()
def get_cursor_location() -> str:
    """Get the current 3D cursor location and rotation."""
    code = """
import bpy
import math

cursor = bpy.context.scene.cursor

result = {
    "location": list(cursor.location),
    "rotation_euler_degrees": [math.degrees(a) for a in cursor.rotation_euler],
}
"""
    return _exec_json(code)


@mcp.tool()
def snap_cursor_to_object(name: str) -> str:
    """Snap the 3D cursor to an object's location.

    Args:
        name: Name of the target object.
    """
    code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
else:
    bpy.context.scene.cursor.location = obj.location.copy()

    result = {{
        "name": obj.name,
        "cursor_location": list(bpy.context.scene.cursor.location),
    }}
"""
    return _exec_json(code)


@mcp.tool()
def snap_object_to_cursor(name: str) -> str:
    """Snap an object to the 3D cursor's location.

    Args:
        name: Name of the object to move.
    """
    code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
else:
    obj.location = bpy.context.scene.cursor.location.copy()

    result = {{
        "name": obj.name,
        "location": list(obj.location),
    }}
"""
    return _exec_json(code)
