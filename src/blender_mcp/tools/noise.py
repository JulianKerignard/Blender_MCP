"""Noise tools for adding PSX-style imperfections to meshes and UVs."""

from blender_mcp.server import mcp, _exec_json, _error_json


@mcp.tool()
def add_vertex_noise(name: str, strength: float = 0.002, seed: int = 42) -> str:
    """Add random vertex displacement to a mesh for a PSX-style imperfect look.

    Slightly offsets each vertex by a random amount, breaking the geometric
    perfection typical of 3D models. Essential for PS1 aesthetic.

    Args:
        name: Name of the mesh object.
        strength: Maximum displacement per axis. Default 0.002 (subtle).
        seed: Random seed for reproducible results.
    """
    if strength < 0:
        return _error_json("strength must be positive")

    code = f"""
import bpy
import bmesh
import random
from mathutils import Vector

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

        random.seed({seed!r})
        s = {strength!r}
        for v in bm.verts:
            v.co += Vector((
                random.uniform(-s, s),
                random.uniform(-s, s),
                random.uniform(-s, s),
            ))

        bmesh.update_edit_mesh(obj.data)
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')

    result = {{
        "object": obj.name,
        "vertices_affected": len(obj.data.vertices),
        "strength": s,
        "seed": {seed!r},
    }}
"""
    return _exec_json(code)


@mcp.tool()
def add_uv_noise(name: str, strength: float = 0.006, seed: int = 99) -> str:
    """Add random UV coordinate wobble for PSX-style texture warping.

    Slightly offsets each UV coordinate, simulating the texture distortion
    seen on PlayStation 1 due to lack of perspective-correct mapping.

    Args:
        name: Name of the mesh object.
        strength: Maximum UV offset per axis. Default 0.006.
        seed: Random seed for reproducible results.
    """
    if strength < 0:
        return _error_json("strength must be positive")

    code = f"""
import bpy
import bmesh
import random

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
        uv_layer = bm.loops.layers.uv.active

        if uv_layer is None:
            result = {{"error": "No active UV layer on " + {name!r}}}
        else:
            random.seed({seed!r})
            s = {strength!r}
            uv_count = 0
            for face in bm.faces:
                for loop in face.loops:
                    uv = loop[uv_layer].uv
                    uv.x += random.uniform(-s, s)
                    uv.y += random.uniform(-s, s)
                    uv_count += 1

            bmesh.update_edit_mesh(obj.data)

            result = {{
                "object": obj.name,
                "uv_points_affected": uv_count,
                "strength": s,
                "seed": {seed!r},
            }}
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')
"""
    return _exec_json(code)


@mcp.tool()
def add_roughness_noise(
    name: str,
    scale: float = 30.0,
    detail: float = 3.0,
    strength: float = 0.12,
) -> str:
    """Add procedural noise to the roughness of all materials on an object.

    Creates a subtle surface wear effect by varying roughness across the surface.
    Adds Noise Texture nodes connected to the Principled BSDF roughness input.

    Args:
        name: Name of the mesh object.
        scale: Noise texture scale. Higher = finer noise. Default 30.
        detail: Noise detail level (0-16). Default 3.
        strength: How much the noise affects roughness (0-1). Default 0.12.
    """
    code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
else:
    affected = 0
    for slot in obj.material_slots:
        mat = slot.material
        if not mat or not mat.use_nodes:
            continue
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        bsdf = None
        for node in nodes:
            if node.type == 'BSDF_PRINCIPLED':
                bsdf = node
                break
        if not bsdf:
            continue

        base_rough = bsdf.inputs['Roughness'].default_value

        tc = nodes.new('ShaderNodeTexCoord')
        tc.location = (bsdf.location.x - 500, bsdf.location.y - 200)

        nn = nodes.new('ShaderNodeTexNoise')
        nn.location = (bsdf.location.x - 300, bsdf.location.y - 200)
        nn.inputs['Scale'].default_value = {scale!r}
        nn.inputs['Detail'].default_value = {detail!r}

        mx = nodes.new('ShaderNodeMath')
        mx.location = (bsdf.location.x - 100, bsdf.location.y - 200)
        mx.operation = 'MULTIPLY_ADD'
        mx.inputs[1].default_value = {strength!r}
        mx.inputs[2].default_value = base_rough

        links.new(tc.outputs['Object'], nn.inputs['Vector'])
        links.new(nn.outputs['Fac'], mx.inputs[0])
        links.new(mx.outputs['Value'], bsdf.inputs['Roughness'])
        affected += 1

    result = {{
        "object": obj.name,
        "materials_affected": affected,
        "noise_scale": {scale!r},
        "noise_strength": {strength!r},
    }}
"""
    return _exec_json(code)
