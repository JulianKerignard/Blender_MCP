"""Code execution and utility tools."""

from blender_mcp.server import mcp, _exec


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
    import json
    result = _exec(code)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_blender_info() -> str:
    """Get information about the running Blender instance.

    Returns Blender version, active scene, renderer, and available addons.
    """
    import json
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
    result = _exec(code)
    return json.dumps(result, indent=2)


@mcp.tool()
def undo() -> str:
    """Undo the last operation in Blender."""
    import json
    result = _exec("import bpy; bpy.ops.ed.undo()")
    return json.dumps(result, indent=2)
