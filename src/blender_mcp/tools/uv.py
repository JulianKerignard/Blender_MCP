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
