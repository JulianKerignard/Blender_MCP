"""Camera management tools."""

from blender_mcp.server import mcp, _exec_json, _error_json


@mcp.tool()
def create_camera(
    name: str = "",
    location: list[float] | None = None,
    rotation: list[float] | None = None,
    lens: float = 50.0,
    dof_enabled: bool = False,
    dof_distance: float = 10.0,
    fstop: float = 2.8,
    set_active: bool = True,
) -> str:
    """Create a new camera in the scene.

    Rotation is specified in degrees and converted to radians internally.
    Optionally sets the new camera as the active scene camera.

    Args:
        name: Optional name for the camera. If empty, Blender assigns one.
        location: Position as [X, Y, Z]. Defaults to [0, 0, 0].
        rotation: Rotation in degrees as [X, Y, Z]. Defaults to [0, 0, 0].
        lens: Focal length in millimeters.
        dof_enabled: Enable depth of field.
        dof_distance: Focus distance in meters (when DOF is enabled).
        fstop: F-stop aperture value (lower = more blur when DOF is enabled).
        set_active: If True, set this camera as the active scene camera.
    """
    code = f"""
import bpy
import math

loc = {location!r}
if loc is None:
    loc = [0, 0, 0]

rot_deg = {rotation!r}
if rot_deg is None:
    rot_deg = [0, 0, 0]
rot_rad = [math.radians(a) for a in rot_deg]

bpy.ops.object.camera_add(location=loc, rotation=rot_rad)
cam = bpy.context.active_object

requested_name = {name!r}
if requested_name:
    cam.name = requested_name

# Lens settings
cam.data.lens = {lens!r}

# Depth of field
cam.data.dof.use_dof = {dof_enabled!r}
cam.data.dof.focus_distance = {dof_distance!r}
cam.data.dof.aperture_fstop = {fstop!r}

# Set as active camera
is_active = False
if {set_active!r}:
    bpy.context.scene.camera = cam
    is_active = True

result = {{
    "name": cam.name,
    "lens": cam.data.lens,
    "dof_enabled": cam.data.dof.use_dof,
    "dof_distance": cam.data.dof.focus_distance,
    "fstop": cam.data.dof.aperture_fstop,
    "location": loc,
    "active_camera": is_active,
}}
"""
    return _exec_json(code)


@mcp.tool()
def set_camera_properties(
    name: str,
    lens: float | None = None,
    dof_enabled: bool | None = None,
    dof_distance: float | None = None,
    fstop: float | None = None,
    clip_start: float | None = None,
    clip_end: float | None = None,
) -> str:
    """Update properties of an existing camera.

    Only the provided (non-None) values are modified.

    Args:
        name: Name of the camera object to modify.
        lens: New focal length in millimeters.
        dof_enabled: Enable or disable depth of field.
        dof_distance: New focus distance in meters.
        fstop: New F-stop aperture value.
        clip_start: Near clipping distance.
        clip_end: Far clipping distance.
    """
    code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
elif obj.type != 'CAMERA':
    result = {{"error": "Object " + {name!r} + " is not a CAMERA (type: " + obj.type + ")"}}
else:
    updated = []

    lens = {lens!r}
    if lens is not None:
        obj.data.lens = lens
        updated.append("lens")

    dof_enabled = {dof_enabled!r}
    if dof_enabled is not None:
        obj.data.dof.use_dof = dof_enabled
        updated.append("dof_enabled")

    dof_distance = {dof_distance!r}
    if dof_distance is not None:
        obj.data.dof.focus_distance = dof_distance
        updated.append("dof_distance")

    fstop = {fstop!r}
    if fstop is not None:
        obj.data.dof.aperture_fstop = fstop
        updated.append("fstop")

    clip_start = {clip_start!r}
    if clip_start is not None:
        obj.data.clip_start = clip_start
        updated.append("clip_start")

    clip_end = {clip_end!r}
    if clip_end is not None:
        obj.data.clip_end = clip_end
        updated.append("clip_end")

    result = {{
        "name": obj.name,
        "lens": obj.data.lens,
        "dof_enabled": obj.data.dof.use_dof,
        "dof_distance": obj.data.dof.focus_distance,
        "fstop": obj.data.dof.aperture_fstop,
        "clip_start": obj.data.clip_start,
        "clip_end": obj.data.clip_end,
        "updated_properties": updated,
    }}
"""
    return _exec_json(code)


@mcp.tool()
def point_camera_at(
    camera_name: str,
    target: str = "",
    target_location: list[float] | None = None,
) -> str:
    """Point a camera at a target object or location.

    If a target object name is provided, a TRACK_TO constraint is added so
    the camera follows the object. If target_location is provided instead,
    the camera rotation is set to look at those coordinates.

    Args:
        camera_name: Name of the camera object.
        target: Name of the target object to track. Takes priority over target_location.
        target_location: World coordinates [X, Y, Z] to look at.
    """
    code = f"""
import bpy
from mathutils import Vector

cam = bpy.data.objects.get({camera_name!r})
if cam is None:
    result = {{"error": "Camera " + {camera_name!r} + " not found"}}
elif cam.type != 'CAMERA':
    result = {{"error": "Object " + {camera_name!r} + " is not a CAMERA (type: " + cam.type + ")"}}
else:
    target_name = {target!r}.strip()
    target_location = {target_location!r}

    if target_name:
        target_obj = bpy.data.objects.get(target_name)
        if target_obj is None:
            result = {{"error": "Target object " + target_name + " not found"}}
        else:
            # Remove any existing TRACK_TO constraints
            for con in list(cam.constraints):
                if con.type == 'TRACK_TO':
                    cam.constraints.remove(con)

            # Add TRACK_TO constraint
            track = cam.constraints.new(type='TRACK_TO')
            track.target = target_obj
            track.track_axis = 'TRACK_NEGATIVE_Z'
            track.up_axis = 'UP_Y'

            result = {{
                "camera": cam.name,
                "tracking_object": target_obj.name,
                "method": "TRACK_TO constraint",
            }}

    elif target_location is not None:
        target_loc = Vector(target_location)
        cam_loc = cam.location
        direction = target_loc - cam_loc
        cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

        result = {{
            "camera": cam.name,
            "looking_at": list(target_location),
            "method": "rotation",
        }}
    else:
        result = {{"error": "Provide either 'target' (object name) or 'target_location' [X, Y, Z]."}}
"""
    return _exec_json(code)


@mcp.tool()
def set_active_camera(name: str) -> str:
    """Set the active scene camera.

    Args:
        name: Name of the camera object to make active.
    """
    code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
elif obj.type != 'CAMERA':
    result = {{"error": "Object " + {name!r} + " is not a CAMERA (type: " + obj.type + ")"}}
else:
    bpy.context.scene.camera = obj
    result = {{
        "active_camera": obj.name,
        "lens": obj.data.lens,
    }}
"""
    return _exec_json(code)
