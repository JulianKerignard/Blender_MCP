"""Scene management tools."""

from blender_mcp.server import mcp, _exec_json


@mcp.tool()
def get_scene_info() -> str:
    """Get complete scene information.

    Returns scene name, frame range, active camera, world settings,
    and object count broken down by type.
    """
    code = """
import bpy

scene = bpy.context.scene

# Count objects by type
type_counts = {}
for obj in scene.objects:
    t = obj.type
    type_counts[t] = type_counts.get(t, 0) + 1

# World settings
world_info = None
if scene.world:
    w = scene.world
    world_info = {
        "name": w.name,
        "use_nodes": w.use_nodes,
    }
    if w.use_nodes and w.node_tree:
        bg = w.node_tree.nodes.get("Background")
        if bg:
            color_input = bg.inputs.get("Color")
            strength_input = bg.inputs.get("Strength")
            world_info["background_color"] = list(color_input.default_value) if color_input else None
            world_info["background_strength"] = strength_input.default_value if strength_input else None

result = {
    "name": scene.name,
    "frame_start": scene.frame_start,
    "frame_end": scene.frame_end,
    "frame_current": scene.frame_current,
    "fps": scene.render.fps,
    "active_camera": scene.camera.name if scene.camera else None,
    "render_engine": scene.render.engine,
    "resolution_x": scene.render.resolution_x,
    "resolution_y": scene.render.resolution_y,
    "world": world_info,
    "total_objects": len(scene.objects),
    "object_counts_by_type": type_counts,
}
"""
    return _exec_json(code)


@mcp.tool()
def list_objects(object_type: str = "") -> str:
    """List all objects in the scene.

    Optionally filter by type. Returns name, type, visibility, location,
    and parent for each object.

    Args:
        object_type: Filter by Blender object type (MESH, LIGHT, CAMERA,
                     EMPTY, CURVE, ARMATURE, etc). Leave empty for all.
    """
    code = f"""
import bpy

filter_type = {object_type!r}.strip().upper()
objects = []
for obj in bpy.context.scene.objects:
    if filter_type and obj.type != filter_type:
        continue
    objects.append({{
        "name": obj.name,
        "type": obj.type,
        "visible": obj.visible_get(),
        "location": list(obj.location),
        "parent": obj.parent.name if obj.parent else None,
    }})

result = objects
"""
    return _exec_json(code)


@mcp.tool()
def get_object_info(name: str) -> str:
    """Get detailed information about a specific object.

    Returns transform, dimensions, bounding box, mesh data (vertex/edge/face
    count if applicable), materials, modifiers, constraints, and parent/children.

    Args:
        name: The exact name of the object in Blender.
    """
    code = f"""
import bpy
import math

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
else:
    info = {{
        "name": obj.name,
        "type": obj.type,
        "visible": obj.visible_get(),
        "location": list(obj.location),
        "rotation_euler_degrees": [math.degrees(a) for a in obj.rotation_euler],
        "scale": list(obj.scale),
        "dimensions": list(obj.dimensions),
        "bound_box": [list(corner) for corner in obj.bound_box],
        "parent": obj.parent.name if obj.parent else None,
        "children": [c.name for c in obj.children],
    }}

    # Mesh-specific data
    if obj.type == 'MESH' and obj.data:
        mesh = obj.data
        info["mesh"] = {{
            "vertices": len(mesh.vertices),
            "edges": len(mesh.edges),
            "polygons": len(mesh.polygons),
            "has_uv": len(mesh.uv_layers) > 0,
            "uv_layers": [uv.name for uv in mesh.uv_layers],
        }}

    # Materials
    info["materials"] = [slot.material.name if slot.material else None
                         for slot in obj.material_slots]

    # Modifiers
    info["modifiers"] = [
        {{"name": mod.name, "type": mod.type, "show_viewport": mod.show_viewport}}
        for mod in obj.modifiers
    ]

    # Constraints
    info["constraints"] = [
        {{"name": con.name, "type": con.type, "enabled": not con.mute}}
        for con in obj.constraints
    ]

    result = info
"""
    return _exec_json(code)


@mcp.tool()
def select_objects(names: list[str], deselect_others: bool = True) -> str:
    """Select objects by name.

    Optionally deselects all other objects first. Sets the first named object
    as the active object.

    Args:
        names: List of object names to select.
        deselect_others: If True, deselect everything before selecting.
    """
    code = f"""
import bpy

names = {names!r}
deselect_others = {deselect_others!r}

if deselect_others:
    bpy.ops.object.select_all(action='DESELECT')

selected = []
not_found = []
for n in names:
    obj = bpy.data.objects.get(n)
    if obj:
        obj.select_set(True)
        selected.append(n)
    else:
        not_found.append(n)

# Set the first found object as active
if selected:
    bpy.context.view_layer.objects.active = bpy.data.objects[selected[0]]

result = {{
    "selected": selected,
    "not_found": not_found,
    "active": selected[0] if selected else None,
}}
"""
    return _exec_json(code)


@mcp.tool()
def delete_objects(names: list[str]) -> str:
    """Delete objects by name.

    Args:
        names: List of object names to delete.
    """
    code = f"""
import bpy

names = {names!r}
deleted = []
not_found = []

for n in names:
    obj = bpy.data.objects.get(n)
    if obj:
        bpy.data.objects.remove(obj, do_unlink=True)
        deleted.append(n)
    else:
        not_found.append(n)

result = {{
    "deleted": deleted,
    "not_found": not_found,
}}
"""
    return _exec_json(code)


@mcp.tool()
def duplicate_object(name: str, linked: bool = False, new_name: str = "") -> str:
    """Duplicate an object.

    Args:
        name: Name of the object to duplicate.
        linked: If True, the duplicate shares mesh data with the original.
        new_name: Optional name for the duplicate. If empty, Blender assigns one.
    """
    code = f"""
import bpy

src = bpy.data.objects.get({name!r})
if src is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
else:
    if {linked!r}:
        new_obj = src.copy()
    else:
        new_obj = src.copy()
        if src.data:
            new_obj.data = src.data.copy()

    bpy.context.collection.objects.link(new_obj)

    requested_name = {new_name!r}
    if requested_name:
        new_obj.name = requested_name

    result = {{
        "original": src.name,
        "duplicate": new_obj.name,
        "linked": {linked!r},
    }}
"""
    return _exec_json(code)


@mcp.tool()
def set_object_visibility(
    name: str,
    visible: bool | None = None,
    render_visible: bool | None = None,
) -> str:
    """Set the visibility of an object in the viewport and/or render.

    Only provided (non-None) values are changed.

    Args:
        name: Name of the object.
        visible: If True, show in viewport. If False, hide.
        render_visible: If True, show in render. If False, hide from render.
    """
    code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
else:
    visible = {visible!r}
    render_visible = {render_visible!r}

    if visible is not None:
        obj.hide_viewport = not visible
    if render_visible is not None:
        obj.hide_render = not render_visible

    result = {{
        "name": obj.name,
        "visible_viewport": not obj.hide_viewport,
        "visible_render": not obj.hide_render,
    }}
"""
    return _exec_json(code)


@mcp.tool()
def toggle_object_visibility(names: list[str]) -> str:
    """Toggle viewport visibility for one or more objects.

    Each object's visibility is flipped (visible becomes hidden, and vice versa).

    Args:
        names: List of object names to toggle.
    """
    code = f"""
import bpy

names = {names!r}
toggled = []
not_found = []

for n in names:
    obj = bpy.data.objects.get(n)
    if obj:
        obj.hide_viewport = not obj.hide_viewport
        toggled.append({{"name": obj.name, "visible": not obj.hide_viewport}})
    else:
        not_found.append(n)

result = {{"toggled": toggled, "not_found": not_found}}
"""
    return _exec_json(code)
