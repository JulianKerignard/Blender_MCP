"""Material management tools."""

import json

from blender_mcp.server import mcp, _exec


@mcp.tool()
def create_material(
    name: str,
    color: list[float] = None,
    metallic: float = 0.0,
    roughness: float = 0.5,
    emission_color: list[float] = None,
    emission_strength: float = 0.0,
    alpha: float = 1.0,
) -> str:
    """Create a new Principled BSDF material.

    Sets up a clean node tree with Principled BSDF connected to Material Output.

    Args:
        name: Name for the new material.
        color: Base color as [R, G, B] with values 0-1. Defaults to [0.8, 0.8, 0.8].
        metallic: Metallic factor 0-1.
        roughness: Roughness factor 0-1.
        emission_color: Emission color as [R, G, B] with values 0-1.
        emission_strength: Emission strength.
        alpha: Alpha (opacity) 0-1.
    """
    code = f"""
import bpy

mat = bpy.data.materials.new(name={name!r})
mat.use_nodes = True

# Clear existing nodes
nodes = mat.node_tree.nodes
links = mat.node_tree.links
nodes.clear()

# Create Principled BSDF and Material Output
bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
bsdf.location = (0, 0)

output = nodes.new(type='ShaderNodeOutputMaterial')
output.location = (300, 0)

links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

# Set base color
color = {color!r}
if color is None:
    color = [0.8, 0.8, 0.8]
bsdf.inputs['Base Color'].default_value = (*color, 1.0)

# Set other properties
bsdf.inputs['Metallic'].default_value = {metallic!r}
bsdf.inputs['Roughness'].default_value = {roughness!r}
bsdf.inputs['Alpha'].default_value = {alpha!r}

# Emission
emission_color = {emission_color!r}
if emission_color is not None:
    bsdf.inputs['Emission Color'].default_value = (*emission_color, 1.0)
bsdf.inputs['Emission Strength'].default_value = {emission_strength!r}

# Handle transparency
if {alpha!r} < 1.0:
    mat.blend_method = 'BLEND' if hasattr(mat, 'blend_method') else mat.blend_method

result = {{
    "name": mat.name,
    "color": color,
    "metallic": {metallic!r},
    "roughness": {roughness!r},
    "emission_color": emission_color,
    "emission_strength": {emission_strength!r},
    "alpha": {alpha!r},
}}
"""
    result = _exec(code)
    return json.dumps(result, indent=2)


@mcp.tool()
def assign_material(
    object_name: str,
    material_name: str,
    slot_index: int = -1,
) -> str:
    """Assign a material to an object.

    If slot_index is -1, the material is appended as a new slot.
    Otherwise it replaces the material at the given slot index.

    Args:
        object_name: Name of the target object.
        material_name: Name of the material to assign.
        slot_index: Slot index to assign to, or -1 to append.
    """
    code = f"""
import bpy

obj = bpy.data.objects.get({object_name!r})
mat = bpy.data.materials.get({material_name!r})

if obj is None:
    result = {{"error": "Object '{object_name}' not found"}}
elif mat is None:
    result = {{"error": "Material '{material_name}' not found"}}
else:
    slot_index = {slot_index!r}

    if slot_index == -1:
        obj.data.materials.append(mat)
        assigned_slot = len(obj.material_slots) - 1
    else:
        # Ensure enough slots exist
        while len(obj.material_slots) <= slot_index:
            obj.data.materials.append(None)
        obj.material_slots[slot_index].material = mat
        assigned_slot = slot_index

    result = {{
        "object": obj.name,
        "material": mat.name,
        "slot_index": assigned_slot,
        "total_slots": len(obj.material_slots),
    }}
"""
    result = _exec(code)
    return json.dumps(result, indent=2)


@mcp.tool()
def set_material_properties(
    material_name: str,
    color: list[float] = None,
    metallic: float = None,
    roughness: float = None,
    emission_color: list[float] = None,
    emission_strength: float = None,
    alpha: float = None,
) -> str:
    """Update properties of an existing Principled BSDF material.

    Only the provided (non-None) values are modified. The material must
    already have a Principled BSDF node.

    Args:
        material_name: Name of the material to modify.
        color: New base color as [R, G, B] 0-1.
        metallic: New metallic factor 0-1.
        roughness: New roughness factor 0-1.
        emission_color: New emission color as [R, G, B] 0-1.
        emission_strength: New emission strength.
        alpha: New alpha (opacity) 0-1.
    """
    code = f"""
import bpy

mat = bpy.data.materials.get({material_name!r})
if mat is None:
    result = {{"error": "Material '{material_name}' not found"}}
elif not mat.use_nodes or not mat.node_tree:
    result = {{"error": "Material '{material_name}' does not use nodes"}}
else:
    # Find the Principled BSDF node
    bsdf = None
    for node in mat.node_tree.nodes:
        if node.type == 'BSDF_PRINCIPLED':
            bsdf = node
            break

    if bsdf is None:
        result = {{"error": "No Principled BSDF node found in material '{material_name}'"}}
    else:
        updated = []

        color = {color!r}
        if color is not None:
            bsdf.inputs['Base Color'].default_value = (*color, 1.0)
            updated.append("color")

        metallic = {metallic!r}
        if metallic is not None:
            bsdf.inputs['Metallic'].default_value = metallic
            updated.append("metallic")

        roughness = {roughness!r}
        if roughness is not None:
            bsdf.inputs['Roughness'].default_value = roughness
            updated.append("roughness")

        emission_color = {emission_color!r}
        if emission_color is not None:
            bsdf.inputs['Emission Color'].default_value = (*emission_color, 1.0)
            updated.append("emission_color")

        emission_strength = {emission_strength!r}
        if emission_strength is not None:
            bsdf.inputs['Emission Strength'].default_value = emission_strength
            updated.append("emission_strength")

        alpha = {alpha!r}
        if alpha is not None:
            bsdf.inputs['Alpha'].default_value = alpha
            updated.append("alpha")
            if alpha < 1.0 and hasattr(mat, 'blend_method'):
                mat.blend_method = 'BLEND'

        result = {{
            "material": mat.name,
            "updated_properties": updated,
        }}
"""
    result = _exec(code)
    return json.dumps(result, indent=2)


@mcp.tool()
def list_materials() -> str:
    """List all materials in the scene.

    Returns each material's name, base color, metallic, roughness,
    and number of users.
    """
    code = """
import bpy

materials = []
for mat in bpy.data.materials:
    info = {
        "name": mat.name,
        "users": mat.users,
        "use_nodes": mat.use_nodes,
    }

    # Try to read Principled BSDF properties
    if mat.use_nodes and mat.node_tree:
        bsdf = None
        for node in mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                bsdf = node
                break

        if bsdf:
            base_color = bsdf.inputs['Base Color'].default_value
            info["color"] = [round(base_color[0], 4), round(base_color[1], 4), round(base_color[2], 4)]
            info["metallic"] = round(bsdf.inputs['Metallic'].default_value, 4)
            info["roughness"] = round(bsdf.inputs['Roughness'].default_value, 4)

    materials.append(info)

result = materials
"""
    result = _exec(code)
    return json.dumps(result, indent=2)


@mcp.tool()
def add_texture(
    material_name: str,
    texture_path: str,
    texture_type: str = "BASE_COLOR",
) -> str:
    """Add an image texture node to a material.

    Loads an image file and connects it to the appropriate input of the
    Principled BSDF node. For NORMAL type, a Normal Map node is inserted
    between the texture and the BSDF. Non-color textures (ROUGHNESS,
    METALLIC, NORMAL, BUMP) have their color space set to Non-Color.

    Args:
        material_name: Name of the material to add the texture to.
        texture_path: File path of the image texture to load.
        texture_type: Which input to connect: BASE_COLOR, ROUGHNESS,
                      METALLIC, NORMAL, BUMP, or EMISSION.
    """
    code = f"""
import bpy

mat = bpy.data.materials.get({material_name!r})
if mat is None:
    result = {{"error": "Material '{material_name}' not found"}}
elif not mat.use_nodes or not mat.node_tree:
    result = {{"error": "Material '{material_name}' does not use nodes"}}
else:
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Find the Principled BSDF node
    bsdf = None
    for node in nodes:
        if node.type == 'BSDF_PRINCIPLED':
            bsdf = node
            break

    if bsdf is None:
        result = {{"error": "No Principled BSDF node found in material '{material_name}'"}}
    else:
        texture_type = {texture_type!r}.upper()

        # Create Image Texture node
        tex_node = nodes.new(type='ShaderNodeTexImage')
        tex_node.location = (bsdf.location.x - 400, bsdf.location.y)

        # Load image
        try:
            img = bpy.data.images.load({texture_path!r}, check_existing=True)
            tex_node.image = img
        except Exception as e:
            result = {{"error": f"Failed to load image: {{e}}"}}
            img = None

        if img is not None:
            # Set color space for non-color textures
            non_color_types = {{"ROUGHNESS", "METALLIC", "NORMAL", "BUMP"}}
            if texture_type in non_color_types:
                tex_node.image.colorspace_settings.name = 'Non-Color'

            # Map texture type to BSDF input
            input_map = {{
                "BASE_COLOR": "Base Color",
                "ROUGHNESS": "Roughness",
                "METALLIC": "Metallic",
                "EMISSION": "Emission Color",
            }}

            if texture_type == "NORMAL":
                # Insert a Normal Map node between texture and BSDF
                normal_map = nodes.new(type='ShaderNodeNormalMap')
                normal_map.location = (bsdf.location.x - 200, bsdf.location.y - 300)
                tex_node.location = (bsdf.location.x - 600, bsdf.location.y - 300)

                links.new(tex_node.outputs['Color'], normal_map.inputs['Color'])
                links.new(normal_map.outputs['Normal'], bsdf.inputs['Normal'])

            elif texture_type == "BUMP":
                # Insert a Bump node between texture and BSDF
                bump_node = nodes.new(type='ShaderNodeBump')
                bump_node.location = (bsdf.location.x - 200, bsdf.location.y - 400)
                tex_node.location = (bsdf.location.x - 600, bsdf.location.y - 400)

                links.new(tex_node.outputs['Color'], bump_node.inputs['Height'])
                links.new(bump_node.outputs['Normal'], bsdf.inputs['Normal'])

            elif texture_type in input_map:
                bsdf_input = input_map[texture_type]
                links.new(tex_node.outputs['Color'], bsdf.inputs[bsdf_input])
            else:
                result = {{"error": f"Unknown texture type: {{texture_type}}"}}
                img = None

        if img is not None:
            result = {{
                "material": mat.name,
                "texture_path": {texture_path!r},
                "texture_type": texture_type,
                "image_name": img.name,
                "image_size": list(img.size),
            }}
"""
    result = _exec(code)
    return json.dumps(result, indent=2)
