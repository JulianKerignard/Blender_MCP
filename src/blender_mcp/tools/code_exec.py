"""Code execution and utility tools."""

from blender_mcp.server import mcp, _exec_json


@mcp.tool()
def execute_blender_code(code: str) -> str:
    """Execute arbitrary Python code in Blender.

    Use this for advanced operations not covered by other tools.
    The code runs in Blender's Python environment with access to bpy.

    Args:
        code: Python code to execute in Blender. Has access to bpy and all Blender modules.

    Returns:
        The result of the execution, including any value from the 'result' variable if set.
    """
    return _exec_json(code)


@mcp.tool()
def get_blender_info() -> str:
    """Get information about the running Blender instance.

    Returns Blender version, active scene, renderer, and available addons.
    """
    code = """
import bpy
import sys

result = {
    "blender_version": bpy.app.version_string,
    "python_version": sys.version,
    "active_scene": bpy.context.scene.name,
    "render_engine": bpy.context.scene.render.engine,
    "file_path": bpy.data.filepath or "(unsaved)",
    "object_count": len(bpy.data.objects),
    "mesh_count": len(bpy.data.meshes),
    "material_count": len(bpy.data.materials),
}
"""
    return _exec_json(code)


@mcp.tool()
def undo() -> str:
    """Undo the last operation in Blender."""
    return _exec_json("import bpy; bpy.ops.ed.undo()")


@mcp.tool()
def save_file(filepath: str = "") -> str:
    """Save the current Blender file.

    If no filepath is provided, saves to the current file path.
    If the file has never been saved, a filepath is required.

    Args:
        filepath: Path to save the .blend file. If empty, saves in place.
    """
    code = f"""
import bpy

filepath = {filepath!r}.strip()

if filepath:
    # Normalize path
    filepath = filepath.replace('\\\\', '/')
    bpy.ops.wm.save_as_mainfile(filepath=filepath)
    result = {{"saved_to": filepath}}
elif bpy.data.filepath:
    bpy.ops.wm.save_mainfile()
    result = {{"saved_to": bpy.data.filepath}}
else:
    result = {{"error": "File has never been saved. Provide a filepath."}}
"""
    return _exec_json(code)


@mcp.tool()
def open_file(filepath: str) -> str:
    """Open a Blender file.

    WARNING: This will discard unsaved changes in the current file.

    Args:
        filepath: Path to the .blend file to open.
    """
    code = f"""
import bpy

filepath = {filepath!r}.strip().replace('\\\\', '/')
bpy.ops.wm.open_mainfile(filepath=filepath)

result = {{
    "opened": bpy.data.filepath,
    "object_count": len(bpy.data.objects),
    "scene": bpy.context.scene.name,
}}
"""
    return _exec_json(code)
