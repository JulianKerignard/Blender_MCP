"""Transform tools for positioning, rotating, and scaling objects."""

import json

from blender_mcp.server import mcp, _exec


@mcp.tool()
def set_transform(
    name: str,
    location: list[float] = None,
    rotation: list[float] = None,
    scale: list[float] = None,
) -> str:
    """Set the position, rotation, and/or scale of an object.

    Only the provided values are changed; omitted values stay as-is.
    Rotation is specified in degrees and converted to radians internally.

    Args:
        name: Name of the object to transform.
        location: [x, y, z] position in Blender units.
        rotation: [x, y, z] rotation in degrees.
        scale: [x, y, z] scale factors.
    """
    code = f"""
import bpy
import math

obj = bpy.data.objects.get("{name}")
if obj is None:
    result = {{"error": "Object '{name}' not found"}}
else:
    location = {location!r}
    rotation = {rotation!r}
    scale = {scale!r}

    if location is not None:
        obj.location = location
    if rotation is not None:
        obj.rotation_euler = [math.radians(a) for a in rotation]
    if scale is not None:
        obj.scale = scale

    result = {{
        "name": obj.name,
        "location": list(obj.location),
        "rotation_degrees": [math.degrees(a) for a in obj.rotation_euler],
        "scale": list(obj.scale),
    }}
"""
    result = _exec(code)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_transform(name: str) -> str:
    """Get the current location, rotation, and scale of an object.

    Rotation is returned in degrees.

    Args:
        name: Name of the object.
    """
    code = f"""
import bpy
import math

obj = bpy.data.objects.get("{name}")
if obj is None:
    result = {{"error": "Object '{name}' not found"}}
else:
    result = {{
        "name": obj.name,
        "location": list(obj.location),
        "rotation_degrees": [math.degrees(a) for a in obj.rotation_euler],
        "scale": list(obj.scale),
    }}
"""
    result = _exec(code)
    return json.dumps(result, indent=2)


@mcp.tool()
def apply_transform(
    name: str,
    location: bool = False,
    rotation: bool = True,
    scale: bool = True,
) -> str:
    """Apply (freeze) transforms on an object, making the current values the new identity.

    Equivalent to Ctrl+A in Blender. After applying, the applied channels
    reset to their defaults (location to 0, rotation to 0, scale to 1).

    Args:
        name: Name of the object.
        location: Apply location (move origin to world origin).
        rotation: Apply rotation.
        scale: Apply scale.
    """
    code = f"""
import bpy

obj = bpy.data.objects.get("{name}")
if obj is None:
    result = {{"error": "Object '{name}' not found"}}
else:
    # Select only this object so the operator acts on it
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.object.transform_apply(
        location={location!r},
        rotation={rotation!r},
        scale={scale!r},
    )

    result = {{
        "name": obj.name,
        "applied": {{
            "location": {location!r},
            "rotation": {rotation!r},
            "scale": {scale!r},
        }},
        "new_location": list(obj.location),
        "new_rotation_degrees": [__import__('math').degrees(a) for a in obj.rotation_euler],
        "new_scale": list(obj.scale),
    }}
"""
    result = _exec(code)
    return json.dumps(result, indent=2)
