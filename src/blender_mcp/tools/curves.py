"""Curve tools for creating and editing curves in Blender."""

from blender_mcp.server import mcp, _exec_json, _error_json


@mcp.tool()
def create_curve(
    curve_type: str = "bezier",
    name: str = "",
    location: list[float] | None = None,
    rotation: list[float] | None = None,
    points: list[list[float]] | None = None,
) -> str:
    """Create a curve object in Blender.

    Rotation is specified in degrees and converted to radians internally.
    Optionally provide custom control points to shape the curve after creation.

    Args:
        curve_type: Type of curve. One of: bezier, nurbs, circle, path.
        name: Optional name for the object. If empty, Blender assigns a default.
        location: XYZ position as [x, y, z]. Defaults to origin [0, 0, 0].
        rotation: XYZ rotation in degrees. Defaults to [0, 0, 0].
        points: Optional list of control points as [[x, y, z], ...].
            For bezier curves, sets bezier_points positions.
            For nurbs/path curves, sets points positions (w=1.0).

    Returns:
        JSON with the created curve's name, type, and point count.
    """
    ctype = curve_type.lower()

    type_map = {
        "bezier": "bezier_curve",
        "nurbs": "nurbs_curve",
        "circle": "bezier_circle",
        "path": "nurbs_path",
    }

    if ctype not in type_map:
        return _error_json(f"Unknown curve_type: {curve_type}. Must be one of: bezier, nurbs, circle, path")

    op_name = type_map[ctype]

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

bpy.ops.curve.primitive_{op_name}_add(location=loc, rotation=rot_rad)
obj = bpy.context.active_object
"""
    if name:
        code += f"obj.name = {name!r}\n"

    code += f"""
points = {points!r}
if points is not None and len(points) > 0:
    spline = obj.data.splines[0]
    curve_type = {ctype!r}
    if curve_type in ("bezier", "circle"):
        # Resize bezier_points to match
        current = len(spline.bezier_points)
        needed = len(points)
        if needed > current:
            spline.bezier_points.add(needed - current)
        for i, pt in enumerate(points):
            if i < len(spline.bezier_points):
                spline.bezier_points[i].co = (pt[0], pt[1], pt[2])
                spline.bezier_points[i].handle_left_type = 'AUTO'
                spline.bezier_points[i].handle_right_type = 'AUTO'
    else:
        # NURBS / path: uses spline.points with (x, y, z, w)
        current = len(spline.points)
        needed = len(points)
        if needed > current:
            spline.points.add(needed - current)
        for i, pt in enumerate(points):
            if i < len(spline.points):
                spline.points[i].co = (pt[0], pt[1], pt[2], 1.0)

spline = obj.data.splines[0]
curve_type = {ctype!r}
if curve_type in ("bezier", "circle"):
    point_count = len(spline.bezier_points)
else:
    point_count = len(spline.points)

result = {{
    "name": obj.name,
    "type": {ctype!r},
    "point_count": point_count,
    "location": list(obj.location),
}}
"""
    return _exec_json(code)


@mcp.tool()
def add_curve_points(
    name: str,
    points: list[list[float]],
    handle_type: str = "AUTO",
) -> str:
    """Add control points to an existing bezier curve.

    Appends new bezier points to the first spline of the curve object
    and sets their positions and handle types.

    Args:
        name: Name of the curve object.
        points: List of positions as [[x, y, z], ...] for the new points.
        handle_type: Handle type for new points. One of: AUTO, VECTOR, ALIGNED, FREE.

    Returns:
        JSON with the total point count after adding.
    """
    code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
elif obj.type != 'CURVE':
    result = {{"error": "Object " + {name!r} + " is not a curve (type: " + obj.type + ")"}}
else:
    spline = obj.data.splines[0]
    points = {points!r}
    handle_type = {handle_type!r}

    if hasattr(spline, 'bezier_points'):
        existing = len(spline.bezier_points)
        spline.bezier_points.add(len(points))
        for i, pt in enumerate(points):
            bp = spline.bezier_points[existing + i]
            bp.co = (pt[0], pt[1], pt[2])
            bp.handle_left_type = handle_type
            bp.handle_right_type = handle_type
        total = len(spline.bezier_points)
    else:
        existing = len(spline.points)
        spline.points.add(len(points))
        for i, pt in enumerate(points):
            spline.points[existing + i].co = (pt[0], pt[1], pt[2], 1.0)
        total = len(spline.points)

    result = {{
        "name": obj.name,
        "points_added": len(points),
        "total_points": total,
        "handle_type": handle_type,
    }}
"""
    return _exec_json(code)


@mcp.tool()
def set_curve_properties(
    name: str,
    extrude: float | None = None,
    bevel_depth: float | None = None,
    bevel_resolution: int | None = None,
    fill_mode: str | None = None,
    resolution_u: int | None = None,
) -> str:
    """Set properties on an existing curve object.

    Only the provided (non-None) values are modified; omitted values stay as-is.

    Args:
        name: Name of the curve object.
        extrude: Extrusion depth along the curve normals.
        bevel_depth: Bevel depth to round the curve profile.
        bevel_resolution: Number of segments for the bevel. Higher is smoother.
        fill_mode: Fill mode for the curve caps. One of: FULL, FRONT, BACK, HALF, NONE.
        resolution_u: Preview resolution along the curve U direction.

    Returns:
        JSON with the updated curve properties.
    """
    code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
elif obj.type != 'CURVE':
    result = {{"error": "Object " + {name!r} + " is not a curve (type: " + obj.type + ")"}}
else:
    extrude = {extrude!r}
    bevel_depth = {bevel_depth!r}
    bevel_resolution = {bevel_resolution!r}
    fill_mode = {fill_mode!r}
    resolution_u = {resolution_u!r}

    if extrude is not None:
        obj.data.extrude = extrude
    if bevel_depth is not None:
        obj.data.bevel_depth = bevel_depth
    if bevel_resolution is not None:
        obj.data.bevel_resolution = bevel_resolution
    if fill_mode is not None:
        obj.data.fill_mode = fill_mode
    if resolution_u is not None:
        obj.data.resolution_u = resolution_u

    result = {{
        "name": obj.name,
        "extrude": obj.data.extrude,
        "bevel_depth": obj.data.bevel_depth,
        "bevel_resolution": obj.data.bevel_resolution,
        "fill_mode": obj.data.fill_mode,
        "resolution_u": obj.data.resolution_u,
    }}
"""
    return _exec_json(code)


@mcp.tool()
def set_curve_point(
    name: str,
    point_index: int,
    co: list[float] | None = None,
    handle_left: list[float] | None = None,
    handle_right: list[float] | None = None,
    handle_type: str | None = None,
) -> str:
    """Set properties of a specific bezier control point on a curve.

    Only the provided (non-None) values are modified; omitted values stay as-is.

    Args:
        name: Name of the curve object.
        point_index: Index of the bezier point to modify.
        co: New position as [x, y, z].
        handle_left: Left handle position as [x, y, z].
        handle_right: Right handle position as [x, y, z].
        handle_type: Handle type to set for both handles. One of: AUTO, VECTOR, ALIGNED, FREE.

    Returns:
        JSON with the updated point info.
    """
    code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
elif obj.type != 'CURVE':
    result = {{"error": "Object " + {name!r} + " is not a curve (type: " + obj.type + ")"}}
else:
    spline = obj.data.splines[0]
    idx = {point_index!r}

    if idx < 0 or idx >= len(spline.bezier_points):
        result = {{"error": "Point index " + str(idx) + " out of range (0-" + str(len(spline.bezier_points) - 1) + ")"}}
    else:
        bp = spline.bezier_points[idx]

        co = {co!r}
        handle_left = {handle_left!r}
        handle_right = {handle_right!r}
        handle_type = {handle_type!r}

        if handle_type is not None:
            bp.handle_left_type = handle_type
            bp.handle_right_type = handle_type
        if co is not None:
            bp.co = (co[0], co[1], co[2])
        if handle_left is not None:
            bp.handle_left = (handle_left[0], handle_left[1], handle_left[2])
        if handle_right is not None:
            bp.handle_right = (handle_right[0], handle_right[1], handle_right[2])

        result = {{
            "name": obj.name,
            "point_index": idx,
            "co": list(bp.co),
            "handle_left": list(bp.handle_left),
            "handle_right": list(bp.handle_right),
            "handle_left_type": bp.handle_left_type,
            "handle_right_type": bp.handle_right_type,
        }}
"""
    return _exec_json(code)


@mcp.tool()
def curve_to_mesh(name: str) -> str:
    """Convert a curve object to a mesh object.

    This is a one-way operation: the curve will no longer be editable as a curve
    after conversion. Useful for further mesh editing or boolean operations.

    Args:
        name: Name of the curve object to convert.

    Returns:
        JSON with the resulting mesh info (name, vertex count, face count).
    """
    code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
elif obj.type != 'CURVE':
    result = {{"error": "Object " + {name!r} + " is not a curve (type: " + obj.type + ")"}}
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
