"""Animation tools for keyframing, frame control, and timeline management."""

from blender_mcp.server import mcp, _exec_json, _error_json


@mcp.tool()
def insert_keyframe(
    name: str,
    data_path: str = "location",
    frame: int | None = None,
    value: list[float] | None = None,
) -> str:
    """Insert a keyframe on an object's property.

    If frame is None, the current frame is used. If value is provided,
    the property is set to that value before inserting the keyframe.

    Args:
        name: Name of the object to keyframe.
        data_path: Property to keyframe ("location", "rotation_euler", "scale",
                   or any valid bpy data path).
        frame: Frame number to insert the keyframe at. Uses current frame if None.
        value: Optional value to set on the property before keyframing.
    """
    code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
else:
    frame = {frame!r}
    if frame is None:
        frame = bpy.context.scene.frame_current
    bpy.context.scene.frame_set(frame)

    value = {value!r}
    data_path = {data_path!r}
    if value is not None:
        setattr(obj, data_path, value)

    obj.keyframe_insert(data_path=data_path)

    result = {{
        "name": obj.name,
        "data_path": data_path,
        "frame": frame,
        "value": list(getattr(obj, data_path)),
    }}
"""
    return _exec_json(code)


@mcp.tool()
def delete_keyframe(
    name: str,
    data_path: str = "location",
    frame: int | None = None,
) -> str:
    """Delete a keyframe from an object's property at a given frame.

    If frame is None, the current frame is used.

    Args:
        name: Name of the object.
        data_path: Property data path to remove the keyframe from.
        frame: Frame number of the keyframe to delete. Uses current frame if None.
    """
    code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
else:
    frame = {frame!r}
    if frame is None:
        frame = bpy.context.scene.frame_current
    data_path = {data_path!r}

    obj.keyframe_delete(data_path=data_path, frame=frame)

    result = {{
        "name": obj.name,
        "data_path": data_path,
        "frame": frame,
    }}
"""
    return _exec_json(code)


@mcp.tool()
def set_frame(frame: int) -> str:
    """Set the current frame of the scene.

    Args:
        frame: The frame number to jump to.
    """
    code = f"""
import bpy

bpy.context.scene.frame_set({frame!r})
scene = bpy.context.scene

result = {{
    "frame_current": scene.frame_current,
    "frame_start": scene.frame_start,
    "frame_end": scene.frame_end,
}}
"""
    return _exec_json(code)


@mcp.tool()
def set_frame_range(start: int, end: int, fps: int | None = None) -> str:
    """Set the playback frame range and optionally the frame rate.

    Args:
        start: First frame of the range.
        end: Last frame of the range.
        fps: Frames per second. If None, the current fps is kept.
    """
    code = f"""
import bpy

scene = bpy.context.scene
scene.frame_start = {start!r}
scene.frame_end = {end!r}

fps = {fps!r}
if fps is not None:
    scene.render.fps = fps

result = {{
    "frame_start": scene.frame_start,
    "frame_end": scene.frame_end,
    "fps": scene.render.fps,
}}
"""
    return _exec_json(code)


@mcp.tool()
def get_keyframes(name: str) -> str:
    """Get all keyframes for an object.

    Reads every f-curve from the object's animation data and returns
    the data path, array index, and list of (frame, value) pairs.

    Args:
        name: Name of the object.
    """
    code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
elif obj.animation_data is None or obj.animation_data.action is None:
    result = {{
        "name": obj.name,
        "keyframes": [],
        "message": "Object has no animation data",
    }}
else:
    curves = []
    for fc in obj.animation_data.action.fcurves:
        points = [
            {{"frame": int(kp.co[0]), "value": kp.co[1]}}
            for kp in fc.keyframe_points
        ]
        curves.append({{
            "data_path": fc.data_path,
            "array_index": fc.array_index,
            "keyframe_points": points,
        }})

    result = {{
        "name": obj.name,
        "keyframes": curves,
    }}
"""
    return _exec_json(code)
