"""UV mapping tools for unwrapping and managing UV layers in Blender."""

from blender_mcp.server import mcp, _exec_json, _error_json


@mcp.tool()
def unwrap_uv(
    name: str,
    method: str = "smart_project",
    angle_limit: float = 66.0,
    island_margin: float = 0.02,
) -> str:
    """Unwrap a mesh object's UVs using the specified projection method.

    Args:
        name: Name of the mesh object to unwrap.
        method: UV unwrapping method. One of:
            - "smart_project": Automatic projection based on face angles.
            - "unwrap": Angle-based unwrap (respects seams).
            - "cube_project": Project UVs from a cube.
            - "cylinder_project": Project UVs from a cylinder.
            - "sphere_project": Project UVs from a sphere.
        angle_limit: Angle limit in degrees for smart_project. Default 66.0.
        island_margin: Margin between UV islands. Default 0.02.

    Returns:
        JSON with the unwrap method used, UV layer name, and success status.
    """
    m = method.lower()
    valid_methods = (
        "smart_project",
        "unwrap",
        "cube_project",
        "cylinder_project",
        "sphere_project",
    )
    if m not in valid_methods:
        return _error_json(
            f"Unknown UV method: {method}. Must be one of: {', '.join(valid_methods)}"
        )

    if m == "smart_project":
        uv_op = (
            f"bpy.ops.uv.smart_project("
            f"angle_limit=radians({angle_limit}), "
            f"island_margin={island_margin})"
        )
    elif m == "unwrap":
        uv_op = (
            f"bpy.ops.uv.unwrap("
            f"method='ANGLE_BASED', margin={island_margin})"
        )
    elif m == "cube_project":
        uv_op = "bpy.ops.uv.cube_project()"
    elif m == "cylinder_project":
        uv_op = "bpy.ops.uv.cylinder_project()"
    else:
        uv_op = "bpy.ops.uv.sphere_project()"

    code = f"""
import bpy
from math import radians

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
elif obj.type != 'MESH':
    result = {{"error": "Object " + {name!r} + " is not a mesh"}}
else:
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')

    {uv_op}

    bpy.ops.object.mode_set(mode='OBJECT')

    uv_layer = obj.data.uv_layers.active
    result = {{
        "object": obj.name,
        "method": {m!r},
        "uv_layer": uv_layer.name if uv_layer else None,
        "success": True,
    }}
"""
    return _exec_json(code)


@mcp.tool()
def mark_seams(
    name: str,
    edge_indices: list[int] | None = None,
    clear: bool = False,
) -> str:
    """Mark or clear UV seams on a mesh object's edges.

    If clear is True, all existing seams are removed first. If edge_indices
    is provided, those edges are marked as seams. If neither is given, the
    currently selected edges in the mesh are marked as seams.

    Args:
        name: Name of the mesh object.
        edge_indices: Optional list of edge indices to mark as seams.
        clear: If True, clear all existing seams before marking new ones.

    Returns:
        JSON with the total seam count after the operation.
    """
    edge_indices_repr = repr(edge_indices) if edge_indices is not None else "None"

    code = f"""
import bpy
import bmesh

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
elif obj.type != 'MESH':
    result = {{"error": "Object " + {name!r} + " is not a mesh"}}
else:
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(obj.data)
    bm.edges.ensure_lookup_table()

    if {clear!r}:
        for e in bm.edges:
            e.seam = False

    edge_indices = {edge_indices_repr}
    if edge_indices is not None:
        for idx in edge_indices:
            if 0 <= idx < len(bm.edges):
                bm.edges[idx].seam = True
    elif not {clear!r}:
        for e in bm.edges:
            if e.select:
                e.seam = True

    seam_count = sum(1 for e in bm.edges if e.seam)

    bmesh.update_edit_mesh(obj.data)
    bpy.ops.object.mode_set(mode='OBJECT')

    result = {{
        "object": obj.name,
        "seam_count": seam_count,
        "cleared": {clear!r},
        "edge_indices_marked": edge_indices if edge_indices is not None else [],
    }}
"""
    return _exec_json(code)


@mcp.tool()
def get_uv_info(name: str) -> str:
    """Get information about all UV layers on a mesh object.

    Args:
        name: Name of the mesh object.

    Returns:
        JSON with a list of UV layers (name, active status), whether the
        mesh has UVs, and the total UV layer count.
    """
    code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
elif obj.type != 'MESH':
    result = {{"error": "Object " + {name!r} + " is not a mesh"}}
else:
    mesh = obj.data
    uv_layers = []
    for uv in mesh.uv_layers:
        uv_layers.append({{
            "name": uv.name,
            "active": uv.active,
        }})

    result = {{
        "object": obj.name,
        "uv_layers": uv_layers,
        "has_uv": len(uv_layers) > 0,
        "uv_layer_count": len(uv_layers),
    }}
"""
    return _exec_json(code)


@mcp.tool()
def set_active_uv_layer(name: str, uv_layer_name: str) -> str:
    """Set the active UV layer on a mesh object.

    Args:
        name: Name of the mesh object.
        uv_layer_name: Name of the UV layer to make active.

    Returns:
        JSON with the now-active UV layer name.
    """
    code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
elif obj.type != 'MESH':
    result = {{"error": "Object " + {name!r} + " is not a mesh"}}
else:
    mesh = obj.data
    uv_layer = mesh.uv_layers.get({uv_layer_name!r})
    if uv_layer is None:
        available = [uv.name for uv in mesh.uv_layers]
        result = {{
            "error": "UV layer " + {uv_layer_name!r} + " not found",
            "available_uv_layers": available,
        }}
    else:
        mesh.uv_layers[{uv_layer_name!r}].active = True
        result = {{
            "object": obj.name,
            "active_uv_layer": {uv_layer_name!r},
        }}
"""
    return _exec_json(code)


@mcp.tool()
def auto_mark_seams(name: str, angle_threshold: float = 30.0) -> str:
    """Automatically mark UV seams on edges where the angle between adjacent faces exceeds a threshold.

    This is the most useful way to prepare a mesh for UV unwrapping.
    For a cube (90 degree edges), a threshold of 30 will mark all edges as seams.

    Args:
        name: Name of the mesh object.
        angle_threshold: Angle in degrees. Edges sharper than this become seams. Default 30.
    """
    code = f"""
import bpy
import bmesh
from math import radians, degrees

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
elif obj.type != 'MESH':
    result = {{"error": "Object " + {name!r} + " is not a mesh"}}
else:
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(obj.data)
    bm.edges.ensure_lookup_table()

    threshold_rad = radians({angle_threshold})
    marked = 0

    for edge in bm.edges:
        if len(edge.link_faces) == 2:
            angle = edge.calc_face_angle()
            if angle > threshold_rad:
                edge.seam = True
                marked += 1
        elif len(edge.link_faces) < 2:
            edge.seam = True
            marked += 1

    bmesh.update_edit_mesh(obj.data)
    bpy.ops.object.mode_set(mode='OBJECT')

    total_seams = sum(1 for e in obj.data.edges if e.use_seam)

    result = {{
        "object": obj.name,
        "angle_threshold": {angle_threshold},
        "seams_marked": marked,
        "total_seams": total_seams,
        "total_edges": len(obj.data.edges),
    }}
"""
    return _exec_json(code)


@mcp.tool()
def unwrap_selected_faces(
    name: str,
    face_indices: list[int],
    method: str = "smart_project",
) -> str:
    """Unwrap only specific faces of a mesh instead of the entire object.

    Args:
        name: Name of the mesh object.
        face_indices: List of face indices to unwrap.
        method: UV method: "smart_project" or "unwrap". Default "smart_project".
    """
    uv_op = "bpy.ops.uv.smart_project()" if method.lower() == "smart_project" else "bpy.ops.uv.unwrap(method='ANGLE_BASED')"

    code = f"""
import bpy
import bmesh

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
elif obj.type != 'MESH':
    result = {{"error": "Object " + {name!r} + " is not a mesh"}}
else:
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')

    bm = bmesh.from_edit_mesh(obj.data)
    bm.faces.ensure_lookup_table()

    face_indices = {face_indices!r}
    selected_count = 0
    for idx in face_indices:
        if 0 <= idx < len(bm.faces):
            bm.faces[idx].select = True
            selected_count += 1

    bmesh.update_edit_mesh(obj.data)

    {uv_op}

    bpy.ops.object.mode_set(mode='OBJECT')

    result = {{
        "object": obj.name,
        "faces_unwrapped": selected_count,
        "method": {method!r},
    }}
"""
    return _exec_json(code)


@mcp.tool()
def create_uv_layer(name: str, uv_layer_name: str, set_active: bool = True) -> str:
    """Create a new UV layer on a mesh object.

    Args:
        name: Name of the mesh object.
        uv_layer_name: Name for the new UV layer.
        set_active: If True, make the new layer the active one. Default True.
    """
    code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
elif obj.type != 'MESH':
    result = {{"error": "Object " + {name!r} + " is not a mesh"}}
else:
    mesh = obj.data
    new_uv = mesh.uv_layers.new(name={uv_layer_name!r})

    if {set_active!r}:
        mesh.uv_layers.active = new_uv

    result = {{
        "object": obj.name,
        "created_uv_layer": new_uv.name,
        "active": new_uv.active,
        "total_uv_layers": len(mesh.uv_layers),
    }}
"""
    return _exec_json(code)


@mcp.tool()
def remove_uv_layer(name: str, uv_layer_name: str) -> str:
    """Remove a UV layer from a mesh object.

    Args:
        name: Name of the mesh object.
        uv_layer_name: Name of the UV layer to remove.
    """
    code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
elif obj.type != 'MESH':
    result = {{"error": "Object " + {name!r} + " is not a mesh"}}
else:
    mesh = obj.data
    uv_layer = mesh.uv_layers.get({uv_layer_name!r})
    if uv_layer is None:
        result = {{"error": "UV layer " + {uv_layer_name!r} + " not found"}}
    else:
        mesh.uv_layers.remove(uv_layer)
        remaining = [uv.name for uv in mesh.uv_layers]
        result = {{
            "object": obj.name,
            "removed": {uv_layer_name!r},
            "remaining_uv_layers": remaining,
        }}
"""
    return _exec_json(code)


@mcp.tool()
def scale_uv(name: str, scale: list[float], pivot: str = "CENTER") -> str:
    """Scale UV coordinates of a mesh.

    Useful for adjusting texture tiling - larger UVs = smaller texture,
    smaller UVs = larger texture.

    Args:
        name: Name of the mesh object.
        scale: Scale factors as [u, v]. E.g. [2.0, 2.0] doubles the UV size.
        pivot: Pivot point: "CENTER", "CURSOR", "INDIVIDUAL_ORIGINS". Default "CENTER".
    """
    code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
elif obj.type != 'MESH':
    result = {{"error": "Object " + {name!r} + " is not a mesh"}}
else:
    mesh = obj.data
    uv_layer = mesh.uv_layers.active
    if uv_layer is None:
        result = {{"error": "No active UV layer on " + {name!r}}}
    else:
        scale_u, scale_v = {scale!r}

        # Calculate center of all UVs for pivot
        total_u = 0.0
        total_v = 0.0
        count = len(uv_layer.data)
        for loop_uv in uv_layer.data:
            total_u += loop_uv.uv[0]
            total_v += loop_uv.uv[1]

        if count > 0:
            center_u = total_u / count
            center_v = total_v / count
        else:
            center_u = 0.5
            center_v = 0.5

        pivot = {pivot!r}
        if pivot == "CURSOR":
            center_u = 0.0
            center_v = 0.0
        elif pivot == "INDIVIDUAL_ORIGINS":
            pass  # scale from each UV's position (effectively no center shift)

        for loop_uv in uv_layer.data:
            u, v = loop_uv.uv
            if pivot == "INDIVIDUAL_ORIGINS":
                loop_uv.uv[0] = u * scale_u
                loop_uv.uv[1] = v * scale_v
            else:
                loop_uv.uv[0] = center_u + (u - center_u) * scale_u
                loop_uv.uv[1] = center_v + (v - center_v) * scale_v

        result = {{
            "object": obj.name,
            "scale": [scale_u, scale_v],
            "pivot": pivot,
            "uv_count": count,
        }}
"""
    return _exec_json(code)


@mcp.tool()
def get_uv_bounds(name: str) -> str:
    """Get UV bounding box, approximate island count, and coverage statistics.

    Args:
        name: Name of the mesh object.
    """
    code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
elif obj.type != 'MESH':
    result = {{"error": "Object " + {name!r} + " is not a mesh"}}
else:
    mesh = obj.data
    uv_layer = mesh.uv_layers.active
    if uv_layer is None:
        result = {{"error": "No active UV layer on " + {name!r}}}
    else:
        min_u = float('inf')
        min_v = float('inf')
        max_u = float('-inf')
        max_v = float('-inf')

        for loop_uv in uv_layer.data:
            u, v = loop_uv.uv
            min_u = min(min_u, u)
            min_v = min(min_v, v)
            max_u = max(max_u, u)
            max_v = max(max_v, v)

        count = len(uv_layer.data)
        if count == 0:
            min_u = min_v = max_u = max_v = 0.0

        width = max_u - min_u
        height = max_v - min_v
        coverage = width * height if count > 0 else 0.0

        result = {{
            "object": obj.name,
            "uv_layer": uv_layer.name,
            "bounds": {{
                "min_u": round(min_u, 4),
                "min_v": round(min_v, 4),
                "max_u": round(max_u, 4),
                "max_v": round(max_v, 4),
            }},
            "size": [round(width, 4), round(height, 4)],
            "coverage_approx": round(coverage, 4),
            "uv_point_count": count,
        }}
"""
    return _exec_json(code)
