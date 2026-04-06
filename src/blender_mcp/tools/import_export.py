"""Import and export tools for 3D model files."""

import json
import os
from pathlib import Path

from blender_mcp.server import mcp, _exec, _error_json


# Mapping of file extensions to Blender import operators.
# Use {path} (unquoted) -- callers pass repr(normalized_path) so the
# resulting code contains a safely-quoted string literal.
IMPORT_OPERATORS = {
    ".gltf": "bpy.ops.import_scene.gltf(filepath={path})",
    ".glb": "bpy.ops.import_scene.gltf(filepath={path})",
    ".fbx": "bpy.ops.import_scene.fbx(filepath={path})",
    ".obj": "bpy.ops.wm.obj_import(filepath={path})",
    ".stl": "bpy.ops.wm.stl_import(filepath={path})",
    ".ply": "bpy.ops.wm.ply_import(filepath={path})",
}

# Mapping of file extensions to Blender export operators.
EXPORT_OPERATORS = {
    ".gltf": "bpy.ops.export_scene.gltf(filepath={path}, export_format='GLTF_SEPARATE'{selected})",
    ".glb": "bpy.ops.export_scene.gltf(filepath={path}, export_format='GLB'{selected})",
    ".fbx": "bpy.ops.export_scene.fbx(filepath={path}{selected})",
    ".obj": "bpy.ops.wm.obj_export(filepath={path}{selected})",
    ".stl": "bpy.ops.wm.stl_export(filepath={path}{selected})",
}

SUPPORTED_IMPORT_TYPES = list(IMPORT_OPERATORS.keys())
SUPPORTED_EXPORT_TYPES = list(EXPORT_OPERATORS.keys())


def _detect_file_type(file_path: str, file_type: str) -> str:
    """Detect or validate the file type from extension or explicit type."""
    if file_type.strip():
        ft = file_type.strip().lower()
        if not ft.startswith("."):
            ft = "." + ft
        return ft
    return Path(file_path).suffix.lower()


@mcp.tool()
def import_model(file_path: str, file_type: str = "") -> str:
    """Import a 3D model file into Blender.

    Supports glTF (.gltf/.glb), FBX (.fbx), OBJ (.obj), STL (.stl),
    and PLY (.ply) formats. The file type is auto-detected from the
    extension unless explicitly specified.

    Args:
        file_path: Absolute path to the model file to import.
        file_type: Override file type (e.g. "gltf", "fbx", ".obj"). Auto-detected if empty.
    """
    try:
        ext = _detect_file_type(file_path, file_type)

        if ext not in IMPORT_OPERATORS:
            return json.dumps({
                "error": f"Unsupported file type '{ext}'.",
                "supported_types": SUPPORTED_IMPORT_TYPES,
            }, indent=2)

        # Normalize path: use forward slashes for Blender/Python compatibility
        normalized_path = file_path.replace("\\", "/")

        import_call = IMPORT_OPERATORS[ext].format(path=repr(normalized_path))

        code = f"""
import bpy

# Record existing object names
before = set(obj.name for obj in bpy.data.objects)

# Run the import
{import_call}

# Find newly imported objects
after = set(obj.name for obj in bpy.data.objects)
new_objects = sorted(after - before)

result = {{
    "imported_objects": new_objects,
    "count": len(new_objects),
}}
"""
        result = _exec(code)

        if isinstance(result, dict) and "error" in result:
            return json.dumps(result, indent=2)

        output = {
            "success": True,
            "file_path": file_path,
            "file_type": ext,
        }
        if isinstance(result, dict):
            output.update(result)
        return json.dumps(output, indent=2)

    except Exception as e:
        return _error_json(str(e))


@mcp.tool()
def export_model(
    file_path: str,
    file_type: str = "",
    selected_only: bool = False,
) -> str:
    """Export the scene or selected objects to a 3D model file.

    Supports glTF (.gltf), GLB (.glb), FBX (.fbx), OBJ (.obj), and
    STL (.stl) formats. The file type is auto-detected from the extension
    unless explicitly specified.

    Args:
        file_path: Absolute path for the output file.
        file_type: Override file type (e.g. "glb", "fbx", ".stl"). Auto-detected if empty.
        selected_only: If True, export only the currently selected objects.
    """
    try:
        ext = _detect_file_type(file_path, file_type)

        if ext not in EXPORT_OPERATORS:
            return json.dumps({
                "error": f"Unsupported export type '{ext}'.",
                "supported_types": SUPPORTED_EXPORT_TYPES,
            }, indent=2)

        # Normalize path
        normalized_path = file_path.replace("\\", "/")

        # Build the selected-only parameter string for the operator call
        if selected_only:
            if ext in (".gltf", ".glb"):
                selected_param = ", use_selection=True"
            elif ext == ".fbx":
                selected_param = ", use_selection=True"
            elif ext == ".obj":
                selected_param = ", export_selected_objects=True"
            elif ext == ".stl":
                selected_param = ", export_selected_objects=True"
            else:
                selected_param = ""
        else:
            selected_param = ""

        export_call = EXPORT_OPERATORS[ext].format(
            path=repr(normalized_path),
            selected=selected_param,
        )

        # Ensure the output directory exists
        output_dir = repr(str(Path(file_path).parent).replace("\\", "/"))

        code = f"""
import bpy
import os

# Ensure output directory exists
os.makedirs({output_dir}, exist_ok=True)

# Run the export
{export_call}

result = {{
    "success": True,
}}
"""
        result = _exec(code)

        if isinstance(result, dict) and "error" in result:
            return json.dumps(result, indent=2)

        output = {
            "success": True,
            "file_path": file_path,
            "file_type": ext,
            "selected_only": selected_only,
        }
        return json.dumps(output, indent=2)

    except Exception as e:
        return _error_json(str(e))
