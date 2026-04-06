"""Modeling tools for creating and editing meshes in Blender."""

from blender_mcp.server import mcp, _exec_json, _error_json


@mcp.tool()
def create_primitive(
    primitive_type: str,
    name: str = "",
    location: list[float] | None = None,
    size: float = 1.0,
    segments: int | None = None,
    ring_count: int | None = None,
    vertices: int | None = None,
    depth: float | None = None,
    major_radius: float | None = None,
    minor_radius: float | None = None,
) -> str:
    """Create a primitive mesh object in Blender.

    Args:
        primitive_type: Type of primitive. One of: cube, sphere, uv_sphere,
            ico_sphere, cylinder, cone, torus, plane, circle, grid, monkey.
        name: Optional name for the object. If empty, Blender assigns a default.
        location: XYZ position as [x, y, z]. Defaults to origin [0, 0, 0].
        size: Size or radius of the primitive. Default 1.0.
        segments: Number of segments (for cylinder, cone, sphere, circle, torus).
        ring_count: Number of ring segments (for uv_sphere, torus).
        vertices: Number of vertices (for circle, cylinder, cone, ico_sphere).
        depth: Depth/height (for cylinder, cone).
        major_radius: Major radius (for torus).
        minor_radius: Minor radius (for torus).
    """
    loc = location or [0.0, 0.0, 0.0]

    kwargs_parts = [f"location=({loc[0]}, {loc[1]}, {loc[2]})"]

    size_param_map = {
        "cube": "size",
        "sphere": "radius",
        "uv_sphere": "radius",
        "ico_sphere": "radius",
        "cylinder": "radius",
        "cone": "radius",
        "torus": None,
        "plane": "size",
        "circle": "radius",
        "grid": "size",
        "monkey": "size",
    }

    ptype = primitive_type.lower()
    if ptype == "sphere":
        ptype = "uv_sphere"

    if ptype not in size_param_map:
        return _error_json(f"Unknown primitive type: {primitive_type}. Valid: {', '.join(size_param_map.keys())}")

    size_param = size_param_map.get(ptype)
    if size_param:
        kwargs_parts.append(f"{size_param}={size}")

    if segments is not None and ptype in ("cylinder", "cone", "uv_sphere", "circle", "torus"):
        kwargs_parts.append(f"segments={segments}")
    if ring_count is not None and ptype in ("uv_sphere", "torus"):
        kwargs_parts.append(f"ring_count={ring_count}")
    if vertices is not None and ptype in ("circle", "cylinder", "cone", "ico_sphere"):
        kwargs_parts.append(f"vertices={vertices}")
    if depth is not None and ptype in ("cylinder", "cone"):
        kwargs_parts.append(f"depth={depth}")
    if ptype == "torus":
        if major_radius is not None:
            kwargs_parts.append(f"major_radius={major_radius}")
        else:
            kwargs_parts.append(f"major_radius={size}")
        if minor_radius is not None:
            kwargs_parts.append(f"minor_radius={minor_radius}")

    kwargs_str = ", ".join(kwargs_parts)

    code = f"""
import bpy

bpy.ops.mesh.primitive_{ptype}_add({kwargs_str})
obj = bpy.context.active_object
"""
    if name:
        code += f"obj.name = {name!r}\n"

    code += """
result = {
    "name": obj.name,
    "type": obj.type,
    "location": list(obj.location),
    "dimensions": list(obj.dimensions),
    "vertex_count": len(obj.data.vertices),
    "face_count": len(obj.data.polygons),
}
"""
    return _exec_json(code)


@mcp.tool()
def create_mesh(
    name: str,
    vertices: list[list[float]],
    edges: list[list[int]] | None = None,
    faces: list[list[int]] | None = None,
) -> str:
    """Create a mesh object from raw vertex, edge, and face data.

    Args:
        name: Name for the new mesh object.
        vertices: List of vertex positions, each as [x, y, z].
        edges: Optional list of edges, each as [vertex_index_1, vertex_index_2].
        faces: Optional list of faces, each as a list of vertex indices.
    """
    edges_data = edges or []
    faces_data = faces or []

    code = f"""
import bpy

verts = {vertices!r}
edges = {edges_data!r}
faces = {faces_data!r}

mesh = bpy.data.meshes.new({name!r})
mesh.from_pydata(verts, edges, faces)
mesh.update()

obj = bpy.data.objects.new({name!r}, mesh)
bpy.context.collection.objects.link(obj)
bpy.context.view_layer.objects.active = obj
obj.select_set(True)

result = {{
    "name": obj.name,
    "type": obj.type,
    "vertex_count": len(mesh.vertices),
    "edge_count": len(mesh.edges),
    "face_count": len(mesh.polygons),
    "location": list(obj.location),
}}
"""
    return _exec_json(code)


@mcp.tool()
def edit_mesh(
    name: str,
    operation: str,
    offset: float | None = None,
    width: float | None = None,
    segments: int | None = None,
    thickness: float | None = None,
    cuts: int | None = None,
    edge_index: int | None = None,
) -> str:
    """Edit a mesh using BMesh operations.

    Args:
        name: Name of the mesh object to edit.
        operation: The edit operation. One of:
            - "extrude_faces": Extrude selected faces by an offset amount.
            - "bevel": Bevel edges with given width and segments.
            - "inset": Inset faces with given thickness.
            - "subdivide": Subdivide the mesh with given number of cuts.
            - "loop_cut": Add a loop cut at the given edge index.
        offset: Extrude offset distance (for extrude_faces).
        width: Bevel width (for bevel).
        segments: Number of bevel segments (for bevel). Default 1.
        thickness: Inset thickness (for inset).
        cuts: Number of cuts (for subdivide, loop_cut). Default 1.
        edge_index: Edge index for loop_cut placement.
    """
    op = operation.lower()

    if op == "extrude_faces":
        extrude_offset = offset if offset is not None else 1.0
        code = f"""
import bpy
import bmesh

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
else:
    bpy.context.view_layer.objects.active = obj
    try:
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()

        selected = [f for f in bm.faces if f.select]
        if not selected:
            for f in bm.faces:
                f.select = True
            selected = list(bm.faces)

        ret = bmesh.ops.extrude_discrete_faces(bm, faces=selected)
        extruded_faces = [e for e in ret['faces']]
        for f in extruded_faces:
            for v in f.verts:
                v.co += f.normal * {extrude_offset}

        bmesh.update_edit_mesh(obj.data)
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')

    result = {{
        "object": obj.name,
        "operation": "extrude_faces",
        "faces_extruded": len(extruded_faces),
        "offset": {extrude_offset},
        "vertex_count": len(obj.data.vertices),
        "face_count": len(obj.data.polygons),
    }}
"""

    elif op == "bevel":
        bevel_width = width if width is not None else 0.1
        bevel_segments = segments if segments is not None else 1
        code = f"""
import bpy
import bmesh

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
else:
    bpy.context.view_layer.objects.active = obj
    try:
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        bm.edges.ensure_lookup_table()

        selected = [e for e in bm.edges if e.select]
        if not selected:
            for e in bm.edges:
                e.select = True
            selected = list(bm.edges)

        bmesh.ops.bevel(bm, geom=selected, offset={bevel_width}, segments={bevel_segments}, affect='EDGES')
        bmesh.update_edit_mesh(obj.data)
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')

    result = {{
        "object": obj.name,
        "operation": "bevel",
        "width": {bevel_width},
        "segments": {bevel_segments},
        "vertex_count": len(obj.data.vertices),
        "face_count": len(obj.data.polygons),
    }}
"""

    elif op == "inset":
        inset_thickness = thickness if thickness is not None else 0.1
        code = f"""
import bpy
import bmesh

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
else:
    bpy.context.view_layer.objects.active = obj
    try:
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()

        selected = [f for f in bm.faces if f.select]
        if not selected:
            for f in bm.faces:
                f.select = True
            selected = list(bm.faces)

        bmesh.ops.inset_individual(bm, faces=selected, thickness={inset_thickness})
        bmesh.update_edit_mesh(obj.data)
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')

    result = {{
        "object": obj.name,
        "operation": "inset",
        "thickness": {inset_thickness},
        "vertex_count": len(obj.data.vertices),
        "face_count": len(obj.data.polygons),
    }}
"""

    elif op == "subdivide":
        num_cuts = cuts if cuts is not None else 1
        code = f"""
import bpy
import bmesh

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
else:
    bpy.context.view_layer.objects.active = obj
    try:
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        bm.edges.ensure_lookup_table()

        selected = [e for e in bm.edges if e.select]
        if not selected:
            for e in bm.edges:
                e.select = True
            selected = list(bm.edges)

        bmesh.ops.subdivide_edges(bm, edges=selected, cuts={num_cuts})
        bmesh.update_edit_mesh(obj.data)
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')

    result = {{
        "object": obj.name,
        "operation": "subdivide",
        "cuts": {num_cuts},
        "vertex_count": len(obj.data.vertices),
        "face_count": len(obj.data.polygons),
    }}
"""

    elif op == "loop_cut":
        num_cuts = cuts if cuts is not None else 1
        e_index = edge_index if edge_index is not None else 0
        code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
else:
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    try:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.loopcut_slide(
            MESH_OT_loopcut={{"number_cuts": {num_cuts}, "edge_index": {e_index}}},
            TRANSFORM_OT_edge_slide={{"value": 0.0}},
        )
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')

    result = {{
        "object": obj.name,
        "operation": "loop_cut",
        "cuts": {num_cuts},
        "edge_index": {e_index},
        "vertex_count": len(obj.data.vertices),
        "face_count": len(obj.data.polygons),
    }}
"""
    else:
        return _error_json(f"Unknown operation: {operation}")

    return _exec_json(code)


@mcp.tool()
def join_objects(names: list[str]) -> str:
    """Join multiple objects into a single object.

    The first object in the list becomes the active object. All objects
    are joined into it.

    Args:
        names: List of object names to join. First name becomes the active object.
    """
    code = f"""
import bpy

names = {names!r}
bpy.ops.object.select_all(action='DESELECT')

not_found = []
for obj_name in names:
    obj = bpy.data.objects.get(obj_name)
    if obj:
        obj.select_set(True)
    else:
        not_found.append(obj_name)

if not_found:
    result = {{"error": "Objects not found: " + str(not_found)}}
else:
    bpy.context.view_layer.objects.active = bpy.data.objects.get(names[0])
    bpy.ops.object.join()

    obj = bpy.context.active_object
    result = {{
        "name": obj.name,
        "type": obj.type,
        "vertex_count": len(obj.data.vertices) if obj.type == 'MESH' else None,
        "face_count": len(obj.data.polygons) if obj.type == 'MESH' else None,
        "joined_count": len(names),
    }}
"""
    return _exec_json(code)


@mcp.tool()
def separate_mesh(name: str, mode: str = "SELECTED") -> str:
    """Separate a mesh into distinct objects.

    Args:
        name: Name of the mesh object to separate.
        mode: Separation mode. One of: SELECTED, MATERIAL, LOOSE.
    """
    mode_upper = mode.upper()
    code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
else:
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    try:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.separate(type={mode_upper!r})
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')

    separated = [o.name for o in bpy.context.selected_objects]

    result = {{
        "original_name": {name!r},
        "mode": {mode_upper!r},
        "resulting_objects": separated,
        "count": len(separated),
    }}
"""
    return _exec_json(code)


@mcp.tool()
def set_origin(name: str, origin_type: str = "ORIGIN_GEOMETRY") -> str:
    """Set the origin point of an object.

    Args:
        name: Name of the object.
        origin_type: Origin type. One of: ORIGIN_GEOMETRY, ORIGIN_CENTER_OF_MASS,
            ORIGIN_CENTER_OF_VOLUME, GEOMETRY_ORIGIN, ORIGIN_CURSOR.
    """
    code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
else:
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.object.origin_set(type={origin_type!r})

    result = {{
        "name": obj.name,
        "origin_type": {origin_type!r},
        "location": list(obj.location),
    }}
"""
    return _exec_json(code)


@mcp.tool()
def set_smooth_shading(name: str, smooth: bool = True) -> str:
    """Set smooth or flat shading on a mesh object.

    Args:
        name: Name of the mesh object.
        smooth: True for smooth shading, False for flat shading.
    """
    shade_op = "shade_smooth" if smooth else "shade_flat"
    code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
else:
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.object.{shade_op}()

    result = {{
        "name": obj.name,
        "shading": "{'smooth' if smooth else 'flat'}",
    }}
"""
    return _exec_json(code)


@mcp.tool()
def get_vertices(name: str, limit: int = 500) -> str:
    """Get vertex positions of a mesh object in local and world space.

    Essential for precise modeling -- lets Claude see exactly where geometry is.

    Args:
        name: Name of the mesh object.
        limit: Maximum vertices to return. Default 500.
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
    world_matrix = obj.matrix_world
    total = len(mesh.vertices)
    limit = min({limit!r}, total)

    verts = []
    for i in range(limit):
        v = mesh.vertices[i]
        world_co = world_matrix @ v.co
        verts.append({{
            "index": i,
            "local": [round(v.co.x, 5), round(v.co.y, 5), round(v.co.z, 5)],
            "world": [round(world_co.x, 5), round(world_co.y, 5), round(world_co.z, 5)],
        }})

    result = {{
        "object": obj.name,
        "total_vertices": total,
        "returned": limit,
        "vertices": verts,
    }}
"""
    return _exec_json(code)


@mcp.tool()
def set_vertices(name: str, vertex_data: list[dict]) -> str:
    """Set vertex positions on a mesh for precise vertex-level modeling.

    Args:
        name: Name of the mesh object.
        vertex_data: List of dicts with "index" and "co" keys.
            Example: [{"index": 0, "co": [1.0, 2.0, 3.0]}]
            Coordinates are in local space.
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
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    try:
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()

        vertex_data = {vertex_data!r}
        moved = 0
        for vd in vertex_data:
            idx = vd.get("index")
            co = vd.get("co")
            if idx is not None and co is not None and 0 <= idx < len(bm.verts):
                bm.verts[idx].co = co
                moved += 1

        bmesh.update_edit_mesh(obj.data)
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')

    result = {{
        "object": obj.name,
        "vertices_moved": moved,
    }}
"""
    return _exec_json(code)


@mcp.tool()
def get_faces(name: str, limit: int = 500) -> str:
    """Get face data: vertex indices, normal, area, material index, center.

    Args:
        name: Name of the mesh object.
        limit: Maximum faces to return. Default 500.
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
    total = len(mesh.polygons)
    limit = min({limit!r}, total)

    faces = []
    for i in range(limit):
        f = mesh.polygons[i]
        faces.append({{
            "index": i,
            "vertices": list(f.vertices),
            "normal": [round(f.normal.x, 4), round(f.normal.y, 4), round(f.normal.z, 4)],
            "area": round(f.area, 6),
            "material_index": f.material_index,
            "center": [round(f.center.x, 4), round(f.center.y, 4), round(f.center.z, 4)],
        }})

    result = {{
        "object": obj.name,
        "total_faces": total,
        "returned": limit,
        "faces": faces,
    }}
"""
    return _exec_json(code)


@mcp.tool()
def select_vertices(name: str, vertex_indices: list[int]) -> str:
    """Select specific vertices before operations like extrude or delete.

    Args:
        name: Name of the mesh object.
        vertex_indices: List of vertex indices to select.
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
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    try:
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bpy.ops.mesh.select_all(action='DESELECT')

        indices = {vertex_indices!r}
        selected = 0
        for idx in indices:
            if 0 <= idx < len(bm.verts):
                bm.verts[idx].select = True
                selected += 1

        bmesh.update_edit_mesh(obj.data)
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')

    result = {{"object": obj.name, "selected": selected}}
"""
    return _exec_json(code)


@mcp.tool()
def select_faces(name: str, face_indices: list[int]) -> str:
    """Select specific faces before extrude, inset, delete, or material assignment.

    Args:
        name: Name of the mesh object.
        face_indices: List of face indices to select.
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
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    try:
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        bpy.ops.mesh.select_all(action='DESELECT')

        indices = {face_indices!r}
        selected = 0
        for idx in indices:
            if 0 <= idx < len(bm.faces):
                bm.faces[idx].select = True
                selected += 1

        bmesh.update_edit_mesh(obj.data)
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')

    result = {{"object": obj.name, "selected": selected}}
"""
    return _exec_json(code)


@mcp.tool()
def delete_geometry(
    name: str,
    vertex_indices: list[int] | None = None,
    face_indices: list[int] | None = None,
) -> str:
    """Delete specific vertices or faces from a mesh.

    Args:
        name: Name of the mesh object.
        vertex_indices: Vertex indices to delete (removes connected edges/faces too).
        face_indices: Face indices to delete (only removes the faces).
    """
    if vertex_indices is None and face_indices is None:
        return _error_json("Provide vertex_indices or face_indices to delete.")

    delete_type = "VERT" if vertex_indices is not None else "FACE"
    indices = vertex_indices if vertex_indices is not None else face_indices

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

    verts_before = len(obj.data.vertices)
    faces_before = len(obj.data.polygons)

    try:
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        bpy.ops.mesh.select_all(action='DESELECT')

        delete_type = {delete_type!r}
        indices = {indices!r}

        if delete_type == "VERT":
            bm.verts.ensure_lookup_table()
            for idx in indices:
                if 0 <= idx < len(bm.verts):
                    bm.verts[idx].select = True
        else:
            bm.faces.ensure_lookup_table()
            for idx in indices:
                if 0 <= idx < len(bm.faces):
                    bm.faces[idx].select = True

        bmesh.update_edit_mesh(obj.data)
        bpy.ops.mesh.delete(type=delete_type)
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')

    result = {{
        "object": obj.name,
        "vertices_before": verts_before,
        "vertices_after": len(obj.data.vertices),
        "faces_before": faces_before,
        "faces_after": len(obj.data.polygons),
    }}
"""
    return _exec_json(code)
