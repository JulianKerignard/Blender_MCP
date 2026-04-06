"""Lighting management tools."""

from blender_mcp.server import mcp, _exec_json, _error_json


@mcp.tool()
def create_light(
    light_type: str = "POINT",
    name: str = "",
    location: list[float] | None = None,
    rotation: list[float] | None = None,
    energy: float = 1000.0,
    color: list[float] | None = None,
    size: float = 0.25,
    spot_size: float | None = None,
    spot_blend: float | None = None,
) -> str:
    """Create a new light in the scene.

    Supports POINT, SUN, SPOT, and AREA light types. Rotation is specified
    in degrees and converted to radians internally.

    Args:
        light_type: Type of light: POINT, SUN, SPOT, or AREA.
        name: Optional name for the light. If empty, Blender assigns one.
        location: Position as [X, Y, Z]. Defaults to [0, 0, 0].
        rotation: Rotation in degrees as [X, Y, Z]. Defaults to [0, 0, 0].
        energy: Light power/energy value.
        color: Light color as [R, G, B] with values 0-1. Defaults to [1, 1, 1].
        size: Light size. For POINT/SPOT/SUN this is shadow_soft_size,
              for AREA this is the shape size.
        spot_size: Cone angle in degrees for SPOT lights. Defaults to 45.
        spot_blend: Softness of the SPOT cone edge, 0-1. Defaults to 0.15.
    """
    code = f"""
import bpy
import math

light_type = {light_type!r}.strip().upper()
loc = {location!r}
if loc is None:
    loc = [0, 0, 0]

rot_deg = {rotation!r}
if rot_deg is None:
    rot_deg = [0, 0, 0]
rot_rad = [math.radians(a) for a in rot_deg]

color = {color!r}
if color is None:
    color = [1.0, 1.0, 1.0]

bpy.ops.object.light_add(type=light_type, location=loc, rotation=rot_rad)
light = bpy.context.active_object

requested_name = {name!r}
if requested_name:
    light.name = requested_name

# Set energy and color
light.data.energy = {energy!r}
light.data.color = color

# Type-specific settings
if light_type in ('POINT', 'SPOT', 'SUN'):
    light.data.shadow_soft_size = {size!r}

if light_type == 'SPOT':
    spot_size_deg = {spot_size!r}
    if spot_size_deg is None:
        spot_size_deg = 45.0
    light.data.spot_size = math.radians(spot_size_deg)

    spot_blend = {spot_blend!r}
    if spot_blend is None:
        spot_blend = 0.15
    light.data.spot_blend = spot_blend

if light_type == 'AREA':
    light.data.shape = 'RECTANGLE'
    light.data.size = {size!r}

result = {{
    "name": light.name,
    "type": light_type,
    "energy": {energy!r},
    "color": color,
    "location": loc,
}}
"""
    return _exec_json(code)


@mcp.tool()
def set_light_properties(
    name: str,
    energy: float | None = None,
    color: list[float] | None = None,
    size: float | None = None,
    spot_size: float | None = None,
    spot_blend: float | None = None,
) -> str:
    """Update properties of an existing light.

    Only the provided (non-None) values are modified.

    Args:
        name: Name of the light object to modify.
        energy: New energy/power value.
        color: New color as [R, G, B] with values 0-1.
        size: New shadow_soft_size (POINT/SPOT/SUN) or shape size (AREA).
        spot_size: New cone angle in degrees (SPOT only).
        spot_blend: New spot blend value 0-1 (SPOT only).
    """
    code = f"""
import bpy
import math

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
elif obj.type != 'LIGHT':
    result = {{"error": "Object " + {name!r} + " is not a LIGHT (type: " + obj.type + ")"}}
else:
    updated = []

    energy = {energy!r}
    if energy is not None:
        obj.data.energy = energy
        updated.append("energy")

    color = {color!r}
    if color is not None:
        obj.data.color = color
        updated.append("color")

    size = {size!r}
    if size is not None:
        if obj.data.type in ('POINT', 'SPOT', 'SUN'):
            obj.data.shadow_soft_size = size
        elif obj.data.type == 'AREA':
            obj.data.size = size
        updated.append("size")

    spot_size_deg = {spot_size!r}
    if spot_size_deg is not None and obj.data.type == 'SPOT':
        obj.data.spot_size = math.radians(spot_size_deg)
        updated.append("spot_size")

    spot_blend = {spot_blend!r}
    if spot_blend is not None and obj.data.type == 'SPOT':
        obj.data.spot_blend = spot_blend
        updated.append("spot_blend")

    result = {{
        "name": obj.name,
        "type": obj.data.type,
        "energy": obj.data.energy,
        "color": list(obj.data.color),
        "updated_properties": updated,
    }}
"""
    return _exec_json(code)


@mcp.tool()
def list_lights() -> str:
    """List all lights in the scene.

    Returns each light's name, type, energy, color, location, and visibility.
    """
    code = """
import bpy

lights = []
for obj in bpy.context.scene.objects:
    if obj.type == 'LIGHT':
        lights.append({
            "name": obj.name,
            "type": obj.data.type,
            "energy": obj.data.energy,
            "color": list(obj.data.color),
            "location": list(obj.location),
            "visible": obj.visible_get(),
        })

result = lights
"""
    return _exec_json(code)


@mcp.tool()
def setup_studio_lighting(
    style: str = "three_point",
    clear_existing: bool = True,
) -> str:
    """Set up a predefined studio lighting configuration.

    Creates a complete lighting setup matching the chosen style.
    Optionally removes all existing lights first.

    Args:
        style: Lighting style preset. One of:
               - "three_point": Classic key/fill/rim three-point setup.
               - "outdoor_sun": Sunlight with sky-blue world background.
               - "dramatic": Single strong spotlight from above-side.
               - "soft": Two large soft area lights from opposite sides.
        clear_existing: If True, delete all existing lights before creating the setup.
    """
    code = f"""
import bpy
import math

style = {style!r}.strip().lower()
clear_existing = {clear_existing!r}

# Delete existing lights if requested
deleted = []
if clear_existing:
    for obj in list(bpy.context.scene.objects):
        if obj.type == 'LIGHT':
            deleted.append(obj.name)
            bpy.data.objects.remove(obj, do_unlink=True)

created = []

if style == "three_point":
    # Key light: AREA, 45 degrees front-right, elevated
    bpy.ops.object.light_add(type='AREA', location=(4, -4, 5),
                             rotation=(math.radians(45), 0, math.radians(45)))
    key = bpy.context.active_object
    key.name = "Key_Light"
    key.data.energy = 1000
    key.data.shape = 'RECTANGLE'
    key.data.size = 2.0
    key.data.color = (1.0, 0.95, 0.9)
    created.append(key.name)

    # Fill light: AREA, front-left, lower energy
    bpy.ops.object.light_add(type='AREA', location=(-3, -4, 3),
                             rotation=(math.radians(35), 0, math.radians(-30)))
    fill = bpy.context.active_object
    fill.name = "Fill_Light"
    fill.data.energy = 300
    fill.data.shape = 'RECTANGLE'
    fill.data.size = 3.0
    fill.data.color = (0.9, 0.93, 1.0)
    created.append(fill.name)

    # Rim/back light: SPOT, behind and above
    bpy.ops.object.light_add(type='SPOT', location=(0, 5, 5),
                             rotation=(math.radians(-135), 0, 0))
    rim = bpy.context.active_object
    rim.name = "Rim_Light"
    rim.data.energy = 500
    rim.data.spot_size = math.radians(60)
    rim.data.spot_blend = 0.3
    rim.data.shadow_soft_size = 0.5
    rim.data.color = (1.0, 1.0, 1.0)
    created.append(rim.name)

elif style == "outdoor_sun":
    # Sun light with slight angle
    bpy.ops.object.light_add(type='SUN', location=(0, 0, 10),
                             rotation=(math.radians(30), 0, math.radians(15)))
    sun = bpy.context.active_object
    sun.name = "Sun_Light"
    sun.data.energy = 5
    sun.data.color = (1.0, 0.98, 0.95)
    sun.data.shadow_soft_size = 0.01
    created.append(sun.name)

    # Set sky-blue world background
    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.33, 0.55, 0.85, 1.0)
        bg.inputs["Strength"].default_value = 1.0

elif style == "dramatic":
    # Single strong spotlight from above-side, warm color
    bpy.ops.object.light_add(type='SPOT', location=(3, -2, 6),
                             rotation=(math.radians(35), 0, math.radians(25)))
    spot = bpy.context.active_object
    spot.name = "Dramatic_Spot"
    spot.data.energy = 2000
    spot.data.spot_size = math.radians(40)
    spot.data.spot_blend = 0.2
    spot.data.shadow_soft_size = 0.3
    spot.data.color = (1.0, 0.85, 0.6)
    created.append(spot.name)

elif style == "soft":
    # Left area light
    bpy.ops.object.light_add(type='AREA', location=(-5, 0, 4),
                             rotation=(math.radians(20), math.radians(-60), 0))
    left = bpy.context.active_object
    left.name = "Soft_Left"
    left.data.energy = 400
    left.data.shape = 'RECTANGLE'
    left.data.size = 5.0
    left.data.color = (1.0, 0.98, 0.95)
    created.append(left.name)

    # Right area light
    bpy.ops.object.light_add(type='AREA', location=(5, 0, 4),
                             rotation=(math.radians(20), math.radians(60), 0))
    right = bpy.context.active_object
    right.name = "Soft_Right"
    right.data.energy = 400
    right.data.shape = 'RECTANGLE'
    right.data.size = 5.0
    right.data.color = (0.95, 0.97, 1.0)
    created.append(right.name)

else:
    result = {{"error": "Unknown style: " + style + ". Use three_point, outdoor_sun, dramatic, or soft."}}
    created = None

if created is not None:
    result = {{
        "style": style,
        "deleted_lights": deleted,
        "created_lights": created,
    }}
"""
    return _exec_json(code)
