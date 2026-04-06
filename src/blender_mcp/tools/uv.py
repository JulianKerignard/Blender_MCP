"""UV mapping tools for unwrapping and managing UV layers in Blender."""

from blender_mcp.server import mcp, _exec_json, _error_json

UV_UNWRAP_METHODS = ("smart_project", "unwrap", "cube_project", "cylinder_project", "sphere_project")


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
        angle_limit: Angle limit in degrees for smart_project (0-89). Default 66.0.
        island_margin: Margin between UV islands (0-1). Default 0.02.
    """
    m = method.lower()
    if m not in UV_UNWRAP_METHODS:
        return _error_json(f"Unknown UV method: {method}. Must be one of: {', '.join(UV_UNWRAP_METHODS)}")

    if m == "smart_project":
        uv_op = f"bpy.ops.uv.smart_project(angle_limit=radians({angle_limit}), island_margin={island_margin})"
    elif m == "unwrap":
        uv_op = f"bpy.ops.uv.unwrap(method='ANGLE_BASED', margin={island_margin})"
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

    try:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        {uv_op}
    finally:
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
    """
    code = f"""
import bpy
import bmesh

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
elif obj.type != 'MESH':
    result = {{"error": "Object " + {name!r} + " is not a mesh"}}
else:
    bpy.context.view_layer.objects.active = obj

    try:
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        bm.edges.ensure_lookup_table()

        if {clear!r}:
            for e in bm.edges:
                e.seam = False

        edge_indices = {edge_indices!r}
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
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')

    result = {{
        "object": obj.name,
        "seam_count": seam_count,
        "cleared": {clear!r},
    }}
"""
    return _exec_json(code)


@mcp.tool()
def get_uv_info(name: str) -> str:
    """Get information about all UV layers on a mesh object.

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
    uv_layers = []
    for uv in mesh.uv_layers:
        uv_layers.append({{"name": uv.name, "active": uv.active}})

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
        result = {{"error": "UV layer " + {uv_layer_name!r} + " not found", "available_uv_layers": available}}
    else:
        mesh.uv_layers[{uv_layer_name!r}].active = True
        result = {{"object": obj.name, "active_uv_layer": {uv_layer_name!r}}}
"""
    return _exec_json(code)


@mcp.tool()
def auto_mark_seams(name: str, angle_threshold: float = 30.0, clear_existing: bool = False) -> str:
    """Automatically mark UV seams on edges where the angle between adjacent faces exceeds a threshold.

    For a cube (90 degree edges), a threshold of 30 will mark all edges as seams.
    Boundary edges (with only one face) and non-manifold edges are always marked.

    Args:
        name: Name of the mesh object.
        angle_threshold: Angle in degrees (0-180). Edges sharper than this become seams. Default 30.
        clear_existing: If True, clear all existing seams first. Default False.
    """
    if not (0.0 <= angle_threshold <= 180.0):
        return _error_json("angle_threshold must be between 0 and 180 degrees")

    code = f"""
import bpy
import bmesh
from math import radians

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
elif obj.type != 'MESH':
    result = {{"error": "Object " + {name!r} + " is not a mesh"}}
else:
    bpy.context.view_layer.objects.active = obj

    try:
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        bm.edges.ensure_lookup_table()

        if {clear_existing!r}:
            for e in bm.edges:
                e.seam = False

        threshold_rad = radians({angle_threshold})
        marked = 0
        total_seams = 0

        for edge in bm.edges:
            if len(edge.link_faces) == 2:
                angle = edge.calc_face_angle(0.0)
                if angle > threshold_rad:
                    edge.seam = True
                    marked += 1
            elif len(edge.link_faces) != 1 or len(edge.link_faces) == 0:
                edge.seam = True
                marked += 1
            if edge.seam:
                total_seams += 1

        bmesh.update_edit_mesh(obj.data)
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')

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
    m = method.lower()
    if m not in ("smart_project", "unwrap"):
        return _error_json(f"Invalid method: {method}. Must be 'smart_project' or 'unwrap'.")

    uv_op = "bpy.ops.uv.smart_project()" if m == "smart_project" else "bpy.ops.uv.unwrap(method='ANGLE_BASED')"

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

    try:
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
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')

    result = {{
        "object": obj.name,
        "faces_unwrapped": selected_count,
        "method": {m!r},
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
        result = {{"object": obj.name, "removed": {uv_layer_name!r}, "remaining_uv_layers": remaining}}
"""
    return _exec_json(code)


@mcp.tool()
def scale_uv(name: str, scale: list[float], pivot: str = "CENTER") -> str:
    """Scale UV coordinates of a mesh.

    Useful for adjusting texture tiling -- larger UVs = finer texture detail,
    smaller UVs = larger texture pattern.

    Args:
        name: Name of the mesh object.
        scale: Scale factors as [u, v]. E.g. [2.0, 2.0] doubles the UV size.
        pivot: Pivot point for scaling. "CENTER" (average of all UVs) or "ORIGIN" (UV 0,0). Default "CENTER".
    """
    if not isinstance(scale, list) or len(scale) != 2:
        return _error_json("scale must be a list of exactly 2 floats: [u, v]")

    p = pivot.upper()
    if p not in ("CENTER", "ORIGIN"):
        return _error_json(f"Invalid pivot: {pivot}. Must be 'CENTER' or 'ORIGIN'.")

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
        count = len(uv_layer.data)

        # Use foreach_get/foreach_set for performance on large meshes
        import numpy as np
        uvs = np.empty(count * 2, dtype=np.float64)
        uv_layer.data.foreach_get("uv", uvs)
        uvs = uvs.reshape(-1, 2)

        pivot = {p!r}
        if pivot == "CENTER" and count > 0:
            center = uvs.mean(axis=0)
        else:
            center = np.array([0.0, 0.0])

        scale_arr = np.array([scale_u, scale_v])
        uvs = center + (uvs - center) * scale_arr

        uv_layer.data.foreach_set("uv", uvs.ravel())
        mesh.update()

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
    """Get UV bounding box and size statistics.

    Args:
        name: Name of the mesh object.
    """
    code = f"""
import bpy
import numpy as np

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
        count = len(uv_layer.data)
        if count == 0:
            result = {{"object": obj.name, "uv_layer": uv_layer.name, "bounds": None, "uv_point_count": 0}}
        else:
            uvs = np.empty(count * 2, dtype=np.float64)
            uv_layer.data.foreach_get("uv", uvs)
            uvs = uvs.reshape(-1, 2)

            min_uv = uvs.min(axis=0)
            max_uv = uvs.max(axis=0)
            size = max_uv - min_uv

            result = {{
                "object": obj.name,
                "uv_layer": uv_layer.name,
                "bounds": {{
                    "min_u": round(float(min_uv[0]), 4),
                    "min_v": round(float(min_uv[1]), 4),
                    "max_u": round(float(max_uv[0]), 4),
                    "max_v": round(float(max_uv[1]), 4),
                }},
                "size": [round(float(size[0]), 4), round(float(size[1]), 4)],
                "bounding_box_area": round(float(size[0] * size[1]), 4),
                "uv_point_count": count,
            }}
"""
    return _exec_json(code)


@mcp.tool()
def pack_uv_islands(name: str, margin: float = 0.01) -> str:
    """Pack UV islands to fill the UV space efficiently without overlapping.

    Run this after unwrapping to arrange all UV islands neatly within the 0-1 UV space.

    Args:
        name: Name of the mesh object.
        margin: Space between islands (0-1). Default 0.01.
    """
    code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
elif obj.type != 'MESH':
    result = {{"error": "Object " + {name!r} + " is not a mesh"}}
else:
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    try:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.pack_islands(margin={margin})
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')

    result = {{
        "object": obj.name,
        "margin": {margin},
        "success": True,
    }}
"""
    return _exec_json(code)
