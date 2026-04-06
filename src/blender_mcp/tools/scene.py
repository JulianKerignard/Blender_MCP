"""Scene management tools."""

from blender_mcp.server import mcp, _exec_json, _error_json


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


@mcp.tool()
def clear_scene(keep_camera: bool = True, keep_light: bool = True) -> str:
    """Delete all objects in the scene, optionally keeping camera and light.

    Purges orphan data afterwards to clean up unused datablocks.

    Args:
        keep_camera: If True, keep camera objects.
        keep_light: If True, keep light objects.
    """
    code = f"""
import bpy

keep_camera = {keep_camera!r}
keep_light = {keep_light!r}

kept = []
deleted_count = 0

bpy.ops.object.select_all(action='SELECT')

for obj in bpy.context.scene.objects:
    if keep_camera and obj.type == 'CAMERA':
        obj.select_set(False)
        kept.append(obj.name)
    elif keep_light and obj.type == 'LIGHT':
        obj.select_set(False)
        kept.append(obj.name)

deleted_count = len([obj for obj in bpy.context.scene.objects if obj.select_get()])
bpy.ops.object.delete()

bpy.ops.outliner.orphans_purge(do_recursive=True)

result = {{
    "deleted_count": deleted_count,
    "kept_objects": kept,
}}
"""
    return _exec_json(code)


@mcp.tool()
def boolean_operation(
    target_name: str,
    tool_name: str,
    operation: str = "DIFFERENCE",
    apply: bool = True,
) -> str:
    """Perform a boolean operation between two mesh objects.

    Args:
        target_name: Name of the object to modify.
        tool_name: Name of the object used as the boolean tool.
        operation: Boolean operation type: DIFFERENCE, UNION, or INTERSECT.
        apply: If True, apply the modifier and delete the tool object.
    """
    op = operation.strip().upper()
    if op not in ("DIFFERENCE", "UNION", "INTERSECT"):
        return _error_json(f"Unknown operation: {operation}. Valid: DIFFERENCE, UNION, INTERSECT")

    code = f"""
import bpy

target = bpy.data.objects.get({target_name!r})
tool_obj = bpy.data.objects.get({tool_name!r})

if target is None:
    result = {{"error": "Target object " + {target_name!r} + " not found"}}
elif tool_obj is None:
    result = {{"error": "Tool object " + {tool_name!r} + " not found"}}
else:
    mod = target.modifiers.new(name="Boolean", type='BOOLEAN')
    mod.operation = {op!r}
    mod.object = tool_obj

    if {apply!r}:
        bpy.context.view_layer.objects.active = target
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(tool_obj, do_unlink=True)

    mesh = target.data
    result = {{
        "object": target.name,
        "operation": {op!r},
        "applied": {apply!r},
        "vertices": len(mesh.vertices),
        "faces": len(mesh.polygons),
    }}
"""
    return _exec_json(code)


@mcp.tool()
def align_objects(
    names: list[str],
    align_axis: str = "X",
    align_mode: str = "CENTER",
) -> str:
    """Align objects along an axis.

    Args:
        names: List of object names to align.
        align_axis: Axis to align on: X, Y, or Z.
        align_mode: CENTER (average), MIN (align to lowest), or MAX (align to highest).
    """
    axis = align_axis.strip().upper()
    if axis not in ("X", "Y", "Z"):
        return _error_json(f"Unknown axis: {align_axis}. Valid: X, Y, Z")
    mode = align_mode.strip().upper()
    if mode not in ("CENTER", "MIN", "MAX"):
        return _error_json(f"Unknown align_mode: {align_mode}. Valid: CENTER, MIN, MAX")

    code = f"""
import bpy

names = {names!r}
axis = {axis!r}
mode = {mode!r}
axis_index = {{"X": 0, "Y": 1, "Z": 2}}[axis]

objects = []
not_found = []
for n in names:
    obj = bpy.data.objects.get(n)
    if obj:
        objects.append(obj)
    else:
        not_found.append(n)

if len(objects) < 2:
    result = {{"error": "Need at least 2 objects to align", "not_found": not_found}}
else:
    positions = [obj.location[axis_index] for obj in objects]

    if mode == "CENTER":
        target = sum(positions) / len(positions)
    elif mode == "MIN":
        target = min(positions)
    else:
        target = max(positions)

    aligned = []
    for obj in objects:
        obj.location[axis_index] = target
        aligned.append({{"name": obj.name, "location": list(obj.location)}})

    result = {{
        "aligned": aligned,
        "axis": axis,
        "mode": mode,
        "target_value": target,
        "not_found": not_found,
    }}
"""
    return _exec_json(code)


@mcp.tool()
def distribute_objects(
    names: list[str],
    axis: str = "X",
    spacing: float = 2.0,
) -> str:
    """Distribute objects evenly along an axis with a given spacing.

    Objects are sorted by their current position on the axis. The first object
    stays in place and each subsequent object is placed at the previous
    object's position plus the spacing.

    Args:
        names: List of object names to distribute.
        axis: Axis to distribute along: X, Y, or Z.
        spacing: Distance between each object along the axis.
    """
    ax = axis.strip().upper()
    if ax not in ("X", "Y", "Z"):
        return _error_json(f"Unknown axis: {axis}. Valid: X, Y, Z")

    code = f"""
import bpy

names = {names!r}
axis = {ax!r}
spacing = {spacing!r}
axis_index = {{"X": 0, "Y": 1, "Z": 2}}[axis]

objects = []
not_found = []
for n in names:
    obj = bpy.data.objects.get(n)
    if obj:
        objects.append(obj)
    else:
        not_found.append(n)

if len(objects) < 2:
    result = {{"error": "Need at least 2 objects to distribute", "not_found": not_found}}
else:
    objects.sort(key=lambda o: o.location[axis_index])

    distributed = []
    for i, obj in enumerate(objects):
        if i > 0:
            obj.location[axis_index] = objects[0].location[axis_index] + spacing * i
        distributed.append({{"name": obj.name, "location": list(obj.location)}})

    result = {{
        "distributed": distributed,
        "axis": axis,
        "spacing": spacing,
        "not_found": not_found,
    }}
"""
    return _exec_json(code)


@mcp.tool()
def mirror_object(
    name: str,
    axis: str = "X",
    copy: bool = True,
) -> str:
    """Mirror an object along an axis.

    Args:
        name: Name of the object to mirror.
        axis: Axis to mirror across: X, Y, or Z.
        copy: If True, duplicate the object first and mirror the copy.
    """
    ax = axis.strip().upper()
    if ax not in ("X", "Y", "Z"):
        return _error_json(f"Unknown axis: {axis}. Valid: X, Y, Z")

    code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
else:
    axis = {ax!r}
    axis_index = {{"X": 0, "Y": 1, "Z": 2}}[axis]

    if {copy!r}:
        new_obj = obj.copy()
        if obj.data:
            new_obj.data = obj.data.copy()
        bpy.context.collection.objects.link(new_obj)
        target = new_obj
    else:
        target = obj

    target.scale[axis_index] *= -1

    bpy.context.view_layer.objects.active = target
    bpy.ops.object.select_all(action='DESELECT')
    target.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    result = {{
        "mirrored_object": target.name,
        "axis": axis,
        "is_copy": {copy!r},
    }}
"""
    return _exec_json(code)
