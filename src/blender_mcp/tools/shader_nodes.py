"""Shader node tools for building and editing node-based materials."""

from blender_mcp.server import mcp, _exec_json, _error_json


@mcp.tool()
def add_shader_node(
    material_name: str,
    node_type: str,
    location: list[float] | None = None,
    properties: dict | None = None,
) -> str:
    """Add a shader node to a material's node tree.

    The node_type can be a short name (e.g. "TEX_NOISE", "MATH", "BUMP")
    or a full Blender type (e.g. "ShaderNodeTexNoise"). Short names are
    automatically mapped to the correct ShaderNode class.

    Args:
        material_name: Name of the material to add the node to.
        node_type: Node type identifier. Short names: TEX_NOISE, TEX_VORONOI,
            TEX_WAVE, TEX_CHECKER, TEX_GRADIENT, TEX_MUSGRAVE, MIX_RGB,
            MATH, VALTORGB, MAPPING, TEX_COORD, BUMP, NORMAL_MAP,
            SEPARATE_XYZ, COMBINE_XYZ, or any full ShaderNode* type name.
        location: [x, y] position in the node editor. Defaults to [-300, 0].
        properties: Optional dict of property values to set on the node.
            Keys matching input socket names set default_value on that socket;
            other keys are set as node attributes.
    """
    props = properties or {}
    code = f"""
import bpy

mat = bpy.data.materials.get({material_name!r})
if mat is None:
    result = {{"error": "Material '{material_name}' not found"}}
elif not mat.use_nodes or not mat.node_tree:
    result = {{"error": "Material '{material_name}' does not use nodes"}}
else:
    nodes = mat.node_tree.nodes
    node_type_raw = {node_type!r}

    # Mapping from short names to full Blender shader node types
    _type_map = {{
        "TEX_NOISE": "ShaderNodeTexNoise",
        "TEX_VORONOI": "ShaderNodeTexVoronoi",
        "TEX_WAVE": "ShaderNodeTexWave",
        "TEX_CHECKER": "ShaderNodeTexChecker",
        "TEX_GRADIENT": "ShaderNodeTexGradient",
        "TEX_MUSGRAVE": "ShaderNodeTexMusgrave",
        "MIX_RGB": "ShaderNodeMix" if bpy.app.version >= (3, 4, 0) else "ShaderNodeMixRGB",
        "MATH": "ShaderNodeMath",
        "VALTORGB": "ShaderNodeValToRGB",
        "MAPPING": "ShaderNodeMapping",
        "TEX_COORD": "ShaderNodeTexCoord",
        "BUMP": "ShaderNodeBump",
        "NORMAL_MAP": "ShaderNodeNormalMap",
        "SEPARATE_XYZ": "ShaderNodeSeparateXYZ",
        "COMBINE_XYZ": "ShaderNodeCombineXYZ",
    }}

    # Resolve the node type
    if node_type_raw.startswith("ShaderNode"):
        resolved_type = node_type_raw
    elif node_type_raw.upper() in _type_map:
        resolved_type = _type_map[node_type_raw.upper()]
    else:
        # Try prepending ShaderNode as a fallback
        resolved_type = "ShaderNode" + node_type_raw

    try:
        node = nodes.new(type=resolved_type)
    except RuntimeError as e:
        result = {{"error": f"Failed to create node type '{{resolved_type}}': {{e}}"}}
        node = None

    if node is not None:
        loc = {location!r}
        if loc is None:
            loc = [-300, 0]
        node.location = (loc[0], loc[1])

        # Set properties
        props = {props!r}
        set_errors = []
        for key, value in props.items():
            try:
                node.inputs[key].default_value = value
            except (KeyError, TypeError, AttributeError):
                try:
                    setattr(node, key, value)
                except Exception as e2:
                    set_errors.append(f"{{key}}: {{e2}}")

        inputs_info = []
        for inp in node.inputs:
            inputs_info.append({{"name": inp.name, "type": inp.type}})

        outputs_info = []
        for out in node.outputs:
            outputs_info.append({{"name": out.name, "type": out.type}})

        result = {{
            "name": node.name,
            "type": node.type,
            "label": node.label,
            "location": list(node.location),
            "inputs": inputs_info,
            "outputs": outputs_info,
        }}
        if set_errors:
            result["property_errors"] = set_errors
"""
    return _exec_json(code)


@mcp.tool()
def connect_nodes(
    material_name: str,
    from_node: str,
    from_output: str | int,
    to_node: str,
    to_input: str | int,
) -> str:
    """Connect two shader nodes by linking an output to an input.

    Args:
        material_name: Name of the material containing the nodes.
        from_node: Name of the source node.
        from_output: Name or index of the output socket on the source node.
        to_node: Name of the destination node.
        to_input: Name or index of the input socket on the destination node.
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

    node1 = nodes.get({from_node!r})
    node2 = nodes.get({to_node!r})

    if node1 is None:
        result = {{"error": "Source node '{from_node}' not found"}}
    elif node2 is None:
        result = {{"error": "Destination node '{to_node}' not found"}}
    else:
        from_output = {from_output!r}
        to_input = {to_input!r}

        try:
            output_socket = node1.outputs[from_output]
        except (KeyError, IndexError) as e:
            output_socket = None
            result = {{"error": f"Output '{{from_output}}' not found on node '{from_node}': {{e}}"}}

        if output_socket is not None:
            try:
                input_socket = node2.inputs[to_input]
            except (KeyError, IndexError) as e:
                input_socket = None
                result = {{"error": f"Input '{{to_input}}' not found on node '{to_node}': {{e}}"}}

            if input_socket is not None:
                link = links.new(output_socket, input_socket)
                result = {{
                    "from_node": node1.name,
                    "from_output": output_socket.name,
                    "to_node": node2.name,
                    "to_input": input_socket.name,
                    "linked": True,
                }}
"""
    return _exec_json(code)


@mcp.tool()
def disconnect_node(
    material_name: str,
    node_name: str,
    input_name: str = "",
    output_name: str = "",
) -> str:
    """Disconnect links from a shader node's sockets.

    If input_name is given, only links to that input are removed.
    If output_name is given, only links from that output are removed.
    If neither is given, all links connected to the node are removed.

    Args:
        material_name: Name of the material containing the node.
        node_name: Name of the node to disconnect.
        input_name: Specific input socket name to disconnect. Empty = skip.
        output_name: Specific output socket name to disconnect. Empty = skip.
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

    node = nodes.get({node_name!r})
    if node is None:
        result = {{"error": "Node '{node_name}' not found"}}
    else:
        input_name = {input_name!r}
        output_name = {output_name!r}
        removed_count = 0

        # Collect links to remove (iterate over a copy since we modify the collection)
        to_remove = []

        if input_name:
            inp = node.inputs.get(input_name)
            if inp is None:
                result = {{"error": f"Input '{{input_name}}' not found on node '{node_name}'"}}
            else:
                for link in links:
                    if link.to_socket == inp:
                        to_remove.append(link)
        elif output_name:
            out = node.outputs.get(output_name)
            if out is None:
                result = {{"error": f"Output '{{output_name}}' not found on node '{node_name}'"}}
            else:
                for link in links:
                    if link.from_socket == out:
                        to_remove.append(link)
        else:
            # Remove all links connected to this node
            for link in links:
                if link.from_node == node or link.to_node == node:
                    to_remove.append(link)

        for link in to_remove:
            links.remove(link)
            removed_count += 1

        if 'result' not in dir() or not isinstance(result, dict) or 'error' not in result:
            result = {{
                "node": node.name,
                "input_name": input_name,
                "output_name": output_name,
                "links_removed": removed_count,
            }}
"""
    return _exec_json(code)


@mcp.tool()
def set_node_property(
    material_name: str,
    node_name: str,
    properties: dict,
) -> str:
    """Set properties on an existing shader node.

    For each key/value pair, the tool first tries to set the value on
    a matching input socket (e.g. "Scale", "Detail"). If no matching
    socket is found, it tries to set it as a node attribute (e.g.
    blend_type, operation).

    Args:
        material_name: Name of the material containing the node.
        node_name: Name of the node to modify.
        properties: Dict of property names to values.
    """
    code = f"""
import bpy

mat = bpy.data.materials.get({material_name!r})
if mat is None:
    result = {{"error": "Material '{material_name}' not found"}}
elif not mat.use_nodes or not mat.node_tree:
    result = {{"error": "Material '{material_name}' does not use nodes"}}
else:
    node = mat.node_tree.nodes.get({node_name!r})
    if node is None:
        result = {{"error": "Node '{node_name}' not found"}}
    else:
        props = {properties!r}
        updated = []
        errors = []

        for key, value in props.items():
            try:
                node.inputs[key].default_value = value
                updated.append(key)
            except (KeyError, TypeError, AttributeError):
                try:
                    setattr(node, key, value)
                    updated.append(key)
                except Exception as e:
                    errors.append(f"{{key}}: {{e}}")

        result = {{
            "node": node.name,
            "updated": updated,
        }}
        if errors:
            result["errors"] = errors
"""
    return _exec_json(code)


@mcp.tool()
def list_material_nodes(material_name: str) -> str:
    """List all nodes in a material's shader node tree.

    Returns each node's name, type, label, location, inputs (with
    default values where available), and outputs.

    Args:
        material_name: Name of the material to inspect.
    """
    code = f"""
import bpy

mat = bpy.data.materials.get({material_name!r})
if mat is None:
    result = {{"error": "Material '{material_name}' not found"}}
elif not mat.use_nodes or not mat.node_tree:
    result = {{"error": "Material '{material_name}' does not use nodes"}}
else:
    nodes_list = []
    for node in mat.node_tree.nodes:
        inputs_info = []
        for inp in node.inputs:
            inp_data = {{"name": inp.name, "type": inp.type}}
            try:
                val = inp.default_value
                if hasattr(val, '__iter__') and not isinstance(val, str):
                    inp_data["default_value"] = list(val)
                else:
                    inp_data["default_value"] = val
            except (AttributeError, TypeError):
                pass
            inputs_info.append(inp_data)

        outputs_info = []
        for out in node.outputs:
            outputs_info.append({{"name": out.name, "type": out.type}})

        nodes_list.append({{
            "name": node.name,
            "type": node.type,
            "label": node.label,
            "location": [node.location.x, node.location.y],
            "inputs": inputs_info,
            "outputs": outputs_info,
        }})

    result = {{"material": mat.name, "node_count": len(nodes_list), "nodes": nodes_list}}
"""
    return _exec_json(code)


@mcp.tool()
def create_procedural_material(
    name: str,
    preset: str,
) -> str:
    """Create a full procedural material from a named preset.

    Sets up a complete node tree with textures, color ramps, and
    proper connections for realistic-looking materials.

    Args:
        name: Name for the new material.
        preset: Preset name. One of: wood, marble, metal_scratched, brick, fabric.
    """
    preset_lower = preset.strip().lower()
    valid_presets = ("wood", "marble", "metal_scratched", "brick", "fabric")
    if preset_lower not in valid_presets:
        return _error_json(
            f"Unknown preset: {preset!r}. Must be one of: {', '.join(valid_presets)}"
        )

    code = f"""
import bpy

# Create material with nodes
mat = bpy.data.materials.new(name={name!r})
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links
nodes.clear()

preset = {preset_lower!r}
created_nodes = []

# Helper to track created nodes
def track(node):
    created_nodes.append(node.name)
    return node

# Create common base nodes: Principled BSDF + Material Output
bsdf = track(nodes.new(type='ShaderNodeBsdfPrincipled'))
bsdf.location = (400, 0)

output = track(nodes.new(type='ShaderNodeOutputMaterial'))
output.location = (700, 0)
links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

if preset == "wood":
    # Texture Coordinate
    tex_coord = track(nodes.new(type='ShaderNodeTexCoord'))
    tex_coord.location = (-1200, 0)

    # Mapping
    mapping = track(nodes.new(type='ShaderNodeMapping'))
    mapping.location = (-1000, 0)
    mapping.inputs['Scale'].default_value = (1.0, 5.0, 1.0)
    links.new(tex_coord.outputs['Generated'], mapping.inputs['Vector'])

    # Noise Texture
    noise = track(nodes.new(type='ShaderNodeTexNoise'))
    noise.location = (-700, 0)
    noise.inputs['Scale'].default_value = 15.0
    noise.inputs['Detail'].default_value = 5.0
    noise.inputs['Distortion'].default_value = 0.5
    links.new(mapping.outputs['Vector'], noise.inputs['Vector'])

    # Color Ramp
    color_ramp = track(nodes.new(type='ShaderNodeValToRGB'))
    color_ramp.location = (-400, 0)
    cr = color_ramp.color_ramp
    cr.elements[0].position = 0.15
    cr.elements[0].color = (0.15, 0.07, 0.02, 1.0)  # dark brown
    cr.elements[1].position = 0.85
    cr.elements[1].color = (0.45, 0.25, 0.10, 1.0)  # light brown
    links.new(noise.outputs['Fac'], color_ramp.inputs['Fac'])
    links.new(color_ramp.outputs['Color'], bsdf.inputs['Base Color'])

    # Math node for roughness variation
    math_node = track(nodes.new(type='ShaderNodeMath'))
    math_node.location = (-200, -200)
    math_node.operation = 'MULTIPLY'
    math_node.inputs[1].default_value = 0.3
    links.new(noise.outputs['Fac'], math_node.inputs[0])
    links.new(math_node.outputs['Value'], bsdf.inputs['Roughness'])

    bsdf.inputs['Roughness'].default_value = 0.5
    bsdf.inputs['Metallic'].default_value = 0.0

elif preset == "marble":
    # Texture Coordinate
    tex_coord = track(nodes.new(type='ShaderNodeTexCoord'))
    tex_coord.location = (-1400, 0)

    # Mapping
    mapping = track(nodes.new(type='ShaderNodeMapping'))
    mapping.location = (-1200, 0)
    links.new(tex_coord.outputs['Generated'], mapping.inputs['Vector'])

    # Noise Texture (main pattern)
    noise = track(nodes.new(type='ShaderNodeTexNoise'))
    noise.location = (-900, 0)
    noise.inputs['Scale'].default_value = 3.0
    noise.inputs['Detail'].default_value = 8.0
    links.new(mapping.outputs['Vector'], noise.inputs['Vector'])

    # Voronoi Texture (veining)
    voronoi = track(nodes.new(type='ShaderNodeTexVoronoi'))
    voronoi.location = (-900, -300)
    voronoi.inputs['Scale'].default_value = 5.0
    links.new(mapping.outputs['Vector'], voronoi.inputs['Vector'])

    # Mix node for combining noise and voronoi
    use_shader_mix = bpy.app.version >= (3, 4, 0)
    if use_shader_mix:
        mix = track(nodes.new(type='ShaderNodeMix'))
        mix.data_type = 'RGBA'
        mix.location = (-600, -100)
        mix.inputs['Factor'].default_value = 0.3
        links.new(noise.outputs['Fac'], mix.inputs['A'])
        links.new(voronoi.outputs['Distance'], mix.inputs['B'])
    else:
        mix = track(nodes.new(type='ShaderNodeMixRGB'))
        mix.location = (-600, -100)
        mix.inputs['Fac'].default_value = 0.3
        links.new(noise.outputs['Fac'], mix.inputs['Color1'])
        links.new(voronoi.outputs['Distance'], mix.inputs['Color2'])

    # Color Ramp
    color_ramp = track(nodes.new(type='ShaderNodeValToRGB'))
    color_ramp.location = (-300, 0)
    cr = color_ramp.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (0.95, 0.95, 0.95, 1.0)  # white
    cr.elements[1].position = 0.5
    cr.elements[1].color = (0.7, 0.7, 0.7, 1.0)  # grey
    el = cr.elements.new(0.85)
    el.color = (0.3, 0.3, 0.3, 1.0)  # dark grey

    if use_shader_mix:
        links.new(mix.outputs['Result'], color_ramp.inputs['Fac'])
    else:
        links.new(mix.outputs['Color'], color_ramp.inputs['Fac'])
    links.new(color_ramp.outputs['Color'], bsdf.inputs['Base Color'])

    bsdf.inputs['Roughness'].default_value = 0.2
    bsdf.inputs['Metallic'].default_value = 0.0

elif preset == "metal_scratched":
    bsdf.inputs['Metallic'].default_value = 1.0
    bsdf.inputs['Base Color'].default_value = (0.8, 0.8, 0.8, 1.0)

    # Texture Coordinate
    tex_coord = track(nodes.new(type='ShaderNodeTexCoord'))
    tex_coord.location = (-1000, 0)

    # Noise Texture (scratches)
    noise = track(nodes.new(type='ShaderNodeTexNoise'))
    noise.location = (-700, 0)
    noise.inputs['Scale'].default_value = 50.0
    noise.inputs['Detail'].default_value = 3.0
    links.new(tex_coord.outputs['Object'], noise.inputs['Vector'])

    # Invert (Math node: 1 - Fac)
    invert = track(nodes.new(type='ShaderNodeMath'))
    invert.location = (-400, 0)
    invert.operation = 'SUBTRACT'
    invert.inputs[0].default_value = 1.0
    invert.use_clamp = True
    links.new(noise.outputs['Fac'], invert.inputs[1])

    links.new(invert.outputs['Value'], bsdf.inputs['Roughness'])

elif preset == "brick":
    # Texture Coordinate
    tex_coord = track(nodes.new(type='ShaderNodeTexCoord'))
    tex_coord.location = (-1200, 0)

    # Voronoi Texture (brick pattern)
    voronoi = track(nodes.new(type='ShaderNodeTexVoronoi'))
    voronoi.location = (-900, 0)
    voronoi.inputs['Scale'].default_value = 5.0
    links.new(tex_coord.outputs['Generated'], voronoi.inputs['Vector'])

    # Noise Texture (variation)
    noise = track(nodes.new(type='ShaderNodeTexNoise'))
    noise.location = (-900, -300)
    noise.inputs['Scale'].default_value = 10.0
    noise.inputs['Detail'].default_value = 4.0
    links.new(tex_coord.outputs['Generated'], noise.inputs['Vector'])

    # Mix noise with voronoi for color variation
    use_shader_mix = bpy.app.version >= (3, 4, 0)
    if use_shader_mix:
        mix = track(nodes.new(type='ShaderNodeMix'))
        mix.data_type = 'RGBA'
        mix.location = (-600, 0)
        mix.inputs['Factor'].default_value = 0.3
        links.new(voronoi.outputs['Distance'], mix.inputs['A'])
        links.new(noise.outputs['Fac'], mix.inputs['B'])
    else:
        mix = track(nodes.new(type='ShaderNodeMixRGB'))
        mix.location = (-600, 0)
        mix.inputs['Fac'].default_value = 0.3
        links.new(voronoi.outputs['Distance'], mix.inputs['Color1'])
        links.new(noise.outputs['Fac'], mix.inputs['Color2'])

    # Color Ramp (brick colors)
    color_ramp = track(nodes.new(type='ShaderNodeValToRGB'))
    color_ramp.location = (-300, 0)
    cr = color_ramp.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (0.35, 0.12, 0.06, 1.0)  # dark brick red
    cr.elements[1].position = 1.0
    cr.elements[1].color = (0.6, 0.25, 0.12, 1.0)  # lighter brick

    if use_shader_mix:
        links.new(mix.outputs['Result'], color_ramp.inputs['Fac'])
    else:
        links.new(mix.outputs['Color'], color_ramp.inputs['Fac'])
    links.new(color_ramp.outputs['Color'], bsdf.inputs['Base Color'])

    # Bump from Voronoi distance
    bump = track(nodes.new(type='ShaderNodeBump'))
    bump.location = (100, -300)
    bump.inputs['Strength'].default_value = 0.5
    links.new(voronoi.outputs['Distance'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])

    bsdf.inputs['Roughness'].default_value = 0.7
    bsdf.inputs['Metallic'].default_value = 0.0

elif preset == "fabric":
    # Texture Coordinate
    tex_coord = track(nodes.new(type='ShaderNodeTexCoord'))
    tex_coord.location = (-1200, 0)

    # Wave Texture (fabric weave)
    wave = track(nodes.new(type='ShaderNodeTexWave'))
    wave.location = (-900, 0)
    wave.bands_direction = 'DIAGONAL'
    wave.inputs['Scale'].default_value = 20.0
    links.new(tex_coord.outputs['Generated'], wave.inputs['Vector'])

    # Noise Texture (fabric variation)
    noise = track(nodes.new(type='ShaderNodeTexNoise'))
    noise.location = (-900, -300)
    noise.inputs['Scale'].default_value = 30.0
    noise.inputs['Detail'].default_value = 5.0
    links.new(tex_coord.outputs['Generated'], noise.inputs['Vector'])

    # Mix wave and noise for color
    use_shader_mix = bpy.app.version >= (3, 4, 0)
    if use_shader_mix:
        mix = track(nodes.new(type='ShaderNodeMix'))
        mix.data_type = 'RGBA'
        mix.location = (-600, 0)
        mix.inputs['Factor'].default_value = 0.2
        links.new(wave.outputs['Fac'], mix.inputs['A'])
        links.new(noise.outputs['Fac'], mix.inputs['B'])
    else:
        mix = track(nodes.new(type='ShaderNodeMixRGB'))
        mix.location = (-600, 0)
        mix.inputs['Fac'].default_value = 0.2
        links.new(wave.outputs['Fac'], mix.inputs['Color1'])
        links.new(noise.outputs['Fac'], mix.inputs['Color2'])

    if use_shader_mix:
        links.new(mix.outputs['Result'], bsdf.inputs['Base Color'])
    else:
        links.new(mix.outputs['Color'], bsdf.inputs['Base Color'])

    # Wave Fac to roughness
    links.new(wave.outputs['Fac'], bsdf.inputs['Roughness'])

    bsdf.inputs['Roughness'].default_value = 0.8
    bsdf.inputs['Metallic'].default_value = 0.0

result = {{
    "material": mat.name,
    "preset": preset,
    "nodes_created": created_nodes,
    "node_count": len(created_nodes),
}}
"""
    return _exec_json(code)


@mcp.tool()
def remove_shader_node(
    material_name: str,
    node_name: str,
) -> str:
    """Remove a shader node from a material's node tree.

    Args:
        material_name: Name of the material containing the node.
        node_name: Name of the node to remove.
    """
    code = f"""
import bpy

mat = bpy.data.materials.get({material_name!r})
if mat is None:
    result = {{"error": "Material '{material_name}' not found"}}
elif not mat.use_nodes or not mat.node_tree:
    result = {{"error": "Material '{material_name}' does not use nodes"}}
else:
    node = mat.node_tree.nodes.get({node_name!r})
    if node is None:
        result = {{"error": "Node '{node_name}' not found in material '{material_name}'"}}
    else:
        node_type = node.type
        mat.node_tree.nodes.remove(node)
        result = {{
            "material": mat.name,
            "removed_node": {node_name!r},
            "removed_type": node_type,
        }}
"""
    return _exec_json(code)
