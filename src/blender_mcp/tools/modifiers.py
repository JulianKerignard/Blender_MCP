"""Modifier tools for adding and managing Blender modifiers."""

from blender_mcp.server import mcp, _exec_json

_COLLECT_MOD_PROPS = """
mod_props = {}
for prop in mod.bl_rna.properties:
    if prop.identifier in ('rna_type',):
        continue
    try:
        val = getattr(mod, prop.identifier)
        if hasattr(val, '__iter__') and not isinstance(val, str):
            val = list(val)
        mod_props[prop.identifier] = val
    except Exception:
        pass
"""


@mcp.tool()
def add_modifier(
    name: str,
    modifier_type: str,
    modifier_name: str = "",
    properties: dict | None = None,
) -> str:
    """Add a modifier to a Blender object.

    Args:
        name: Name of the object to add the modifier to.
        modifier_type: Blender modifier type identifier. Common types:
            SUBSURF, BEVEL, BOOLEAN, ARRAY, MIRROR, SOLIDIFY, DECIMATE,
            WIREFRAME, SMOOTH, SIMPLE_DEFORM, REMESH, SHRINKWRAP, SCREW.
        modifier_name: Optional display name for the modifier.
            If empty, Blender assigns a default name.
        properties: Optional dict of modifier properties to set
            (e.g. {"levels": 2, "render_levels": 3} for SUBSURF).

    Returns:
        JSON with the modifier info and current properties.
    """
    props = properties or {}
    mod_type = modifier_type.upper()

    code = f"""
import bpy

obj = bpy.data.objects[{name!r}]
mod = obj.modifiers.new(name={modifier_name!r} or {mod_type!r}, type={mod_type!r})
"""
    if modifier_name:
        code += f"mod.name = {modifier_name!r}\n"

    # Set each property on the modifier
    for key, value in props.items():
        code += f"mod[{key!r}] = {value!r}\n"
        # Also try setting as attribute for non-custom properties
        code += f"""
try:
    setattr(mod, {key!r}, {value!r})
except (AttributeError, TypeError):
    pass
"""

    code += _COLLECT_MOD_PROPS

    code += """
result = {
    "object": obj.name,
    "modifier_name": mod.name,
    "modifier_type": mod.type,
    "properties": mod_props,
}
"""
    return _exec_json(code)


@mcp.tool()
def set_modifier_properties(
    name: str,
    modifier_name: str,
    properties: dict,
) -> str:
    """Set properties on an existing modifier.

    Args:
        name: Name of the object that has the modifier.
        modifier_name: Name of the modifier to update.
        properties: Dict of property names to values to set on the modifier.

    Returns:
        JSON with the updated modifier properties.
    """
    code = f"""
import bpy

obj = bpy.data.objects[{name!r}]
mod = obj.modifiers[{modifier_name!r}]
"""

    for key, value in properties.items():
        code += f"""
try:
    setattr(mod, {key!r}, {value!r})
except (AttributeError, TypeError):
    mod[{key!r}] = {value!r}
"""

    code += _COLLECT_MOD_PROPS

    code += """
result = {
    "object": obj.name,
    "modifier_name": mod.name,
    "modifier_type": mod.type,
    "properties": mod_props,
}
"""
    return _exec_json(code)


@mcp.tool()
def apply_modifier(name: str, modifier_name: str) -> str:
    """Apply a modifier to permanently alter the mesh.

    This bakes the modifier's effect into the mesh geometry and removes
    the modifier from the stack.

    Args:
        name: Name of the object that has the modifier.
        modifier_name: Name of the modifier to apply.

    Returns:
        JSON with the result after applying the modifier.
    """
    code = f"""
import bpy

obj = bpy.data.objects[{name!r}]
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
bpy.context.view_layer.objects.active = obj

# Record modifier type before applying
mod = obj.modifiers[{modifier_name!r}]
mod_type = mod.type

bpy.ops.object.modifier_apply(modifier={modifier_name!r})

remaining_modifiers = [m.name for m in obj.modifiers]

result = {{
    "object": obj.name,
    "applied_modifier": {modifier_name!r},
    "applied_type": mod_type,
    "vertex_count": len(obj.data.vertices) if obj.type == 'MESH' else None,
    "face_count": len(obj.data.polygons) if obj.type == 'MESH' else None,
    "remaining_modifiers": remaining_modifiers,
}}
"""
    return _exec_json(code)
