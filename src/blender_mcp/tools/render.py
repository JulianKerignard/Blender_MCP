"""Render and viewport tools."""

import os
import tempfile

from mcp.server.fastmcp import Image

from blender_mcp.server import mcp, _exec, _exec_json, _exec_and_read_image, _error_json

# Shared image format map for generated Blender code
_FORMAT_MAP_SNIPPET = """
format_map = {
    ".png": "PNG",
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".bmp": "BMP",
    ".tiff": "TIFF",
    ".tif": "TIFF",
    ".exr": "OPEN_EXR",
    ".hdr": "HDR",
}
"""


@mcp.tool()
def render_image(
    output_path: str = "",
    resolution_x: int = 1920,
    resolution_y: int = 1080,
    samples: int = 128,
    engine: str = "",
    return_image: bool = False,
) -> str | Image:
    """Render the current scene to an image file.

    If no output_path is provided, a temporary file is used. Returns the
    path to the rendered image, or the image itself when return_image is True.

    Args:
        output_path: Destination file path for the render. If empty, a temp file is used.
        resolution_x: Horizontal resolution in pixels.
        resolution_y: Vertical resolution in pixels.
        samples: Number of render samples.
        engine: Render engine (BLENDER_EEVEE, CYCLES, BLENDER_WORKBENCH).
                Leave empty to keep the current engine.
        return_image: If True, return the rendered image inline instead of the file path JSON.
    """
    code = f"""
import bpy
import tempfile
import os

scene = bpy.context.scene

# Set render engine if specified
engine = {engine!r}.strip().upper()
if engine:
    scene.render.engine = engine

# Set resolution
scene.render.resolution_x = {resolution_x!r}
scene.render.resolution_y = {resolution_y!r}

# Set samples based on engine
if scene.render.engine == 'CYCLES':
    scene.cycles.samples = {samples!r}
else:
    try:
        scene.eevee.taa_render_samples = {samples!r}
    except AttributeError:
        pass

# Determine output path
output_path = {output_path!r}.strip()
if not output_path:
    output_path = os.path.join(tempfile.gettempdir(), "blender_render.png")

# Ensure the directory exists
out_dir = os.path.dirname(output_path)
if out_dir:
    os.makedirs(out_dir, exist_ok=True)

scene.render.filepath = output_path

# Set image format based on extension
ext = os.path.splitext(output_path)[1].lower()
{_FORMAT_MAP_SNIPPET}
scene.render.image_settings.file_format = format_map.get(ext, "PNG")

# Render
bpy.ops.render.render(write_still=True)

result = {{
    "output_path": output_path,
    "resolution": [{resolution_x!r}, {resolution_y!r}],
    "engine": scene.render.engine,
    "samples": {samples!r},
}}
"""
    if return_image:
        image_bytes = _exec_and_read_image(code)
        if image_bytes is not None:
            return Image(data=image_bytes, format="png")
        return _error_json("Failed to render image or read the output file.")
    return _exec_json(code)


@mcp.tool()
def set_render_settings(
    engine: str = "",
    resolution_x: int = None,
    resolution_y: int = None,
    samples: int = None,
    use_denoising: bool = None,
    film_transparent: bool = None,
) -> str:
    """Configure render settings without rendering.

    Only non-None values are applied.

    Args:
        engine: Render engine: BLENDER_EEVEE, CYCLES, or BLENDER_WORKBENCH.
                Leave empty to keep the current engine.
        resolution_x: Horizontal resolution in pixels.
        resolution_y: Vertical resolution in pixels.
        samples: Number of render samples.
        use_denoising: Enable or disable denoising.
        film_transparent: Make the background transparent.
    """
    code = f"""
import bpy

scene = bpy.context.scene
updated = []

# Engine
engine = {engine!r}.strip().upper()
if engine:
    scene.render.engine = engine
    updated.append("engine")

# Resolution
resolution_x = {resolution_x!r}
if resolution_x is not None:
    scene.render.resolution_x = resolution_x
    updated.append("resolution_x")

resolution_y = {resolution_y!r}
if resolution_y is not None:
    scene.render.resolution_y = resolution_y
    updated.append("resolution_y")

# Samples
samples = {samples!r}
if samples is not None:
    if scene.render.engine == 'CYCLES':
        scene.cycles.samples = samples
    elif scene.render.engine == 'BLENDER_EEVEE':
        scene.eevee.taa_render_samples = samples
    updated.append("samples")

# Denoising
use_denoising = {use_denoising!r}
if use_denoising is not None:
    if scene.render.engine == 'CYCLES':
        scene.cycles.use_denoising = use_denoising
    elif scene.render.engine == 'BLENDER_EEVEE':
        scene.eevee.use_gtao = use_denoising  # closest EEVEE equivalent
    updated.append("use_denoising")

# Film transparent
film_transparent = {film_transparent!r}
if film_transparent is not None:
    scene.render.film_transparent = film_transparent
    updated.append("film_transparent")

result = {{
    "engine": scene.render.engine,
    "resolution_x": scene.render.resolution_x,
    "resolution_y": scene.render.resolution_y,
    "film_transparent": scene.render.film_transparent,
    "updated_settings": updated,
}}
"""
    return _exec_json(code)


@mcp.tool()
def get_viewport_screenshot(
    output_path: str = "",
    width: int = 1920,
    height: int = 1080,
) -> str:
    """Capture a viewport screenshot using OpenGL render.

    If no output_path is provided, a temporary file is used.

    Args:
        output_path: Destination file path. If empty, a temp file is used.
        width: Image width in pixels.
        height: Image height in pixels.
    """
    code = f"""
import bpy
import tempfile
import os

scene = bpy.context.scene

# Save original resolution to restore later
orig_x = scene.render.resolution_x
orig_y = scene.render.resolution_y
orig_pct = scene.render.resolution_percentage

# Set viewport render resolution
scene.render.resolution_x = {width!r}
scene.render.resolution_y = {height!r}
scene.render.resolution_percentage = 100

# Determine output path
output_path = {output_path!r}.strip()
if not output_path:
    output_path = os.path.join(tempfile.gettempdir(), "blender_viewport.png")

# Ensure the directory exists
out_dir = os.path.dirname(output_path)
if out_dir:
    os.makedirs(out_dir, exist_ok=True)

scene.render.filepath = output_path

# Set image format based on extension
ext = os.path.splitext(output_path)[1].lower()
{_FORMAT_MAP_SNIPPET}
scene.render.image_settings.file_format = format_map.get(ext, "PNG")

# Use OpenGL render for viewport capture
bpy.ops.render.opengl(write_still=True)

# Restore original resolution
scene.render.resolution_x = orig_x
scene.render.resolution_y = orig_y
scene.render.resolution_percentage = orig_pct

result = {{
    "output_path": output_path,
    "width": {width!r},
    "height": {height!r},
}}
"""
    return _exec_json(code)


@mcp.tool()
def get_scene_snapshot(width: int = 960, height: int = 540) -> Image:
    """Capture the 3D viewport and return the image for Claude to see.

    This is the primary way for Claude to see what the scene looks like.
    Uses a fast OpenGL viewport render.

    Args:
        width: Image width in pixels. Default 960 for fast capture.
        height: Image height in pixels. Default 540 for fast capture.
    """
    tmp_path = os.path.join(tempfile.gettempdir(), "blender_mcp_snapshot.png")
    code = f"""
import bpy
import tempfile
import os

scene = bpy.context.scene

# Save original resolution to restore later
orig_x = scene.render.resolution_x
orig_y = scene.render.resolution_y
orig_pct = scene.render.resolution_percentage

# Set viewport render resolution
scene.render.resolution_x = {width!r}
scene.render.resolution_y = {height!r}
scene.render.resolution_percentage = 100

output_path = {tmp_path!r}

# Ensure the directory exists
out_dir = os.path.dirname(output_path)
if out_dir:
    os.makedirs(out_dir, exist_ok=True)

scene.render.filepath = output_path
scene.render.image_settings.file_format = "PNG"

# Use OpenGL render for viewport capture
bpy.ops.render.opengl(write_still=True)

# Restore original resolution
scene.render.resolution_x = orig_x
scene.render.resolution_y = orig_y
scene.render.resolution_percentage = orig_pct

result = {{
    "output_path": output_path,
}}
"""
    image_bytes = _exec_and_read_image(code)
    if image_bytes is not None:
        return Image(data=image_bytes, format="png")
    return _error_json("Failed to capture viewport snapshot.")


@mcp.tool()
def render_preview(width: int = 480, height: int = 270, samples: int = 16) -> Image:
    """Render a quick low-resolution preview and return the image for Claude to see.

    Uses EEVEE for speed. Good for checking materials, lighting, and composition.

    Args:
        width: Image width in pixels. Default 480 for fast preview.
        height: Image height in pixels. Default 270 for fast preview.
        samples: Number of render samples. Default 16 for speed.
    """
    tmp_path = os.path.join(tempfile.gettempdir(), "blender_mcp_preview.png")
    code = f"""
import bpy
import os

scene = bpy.context.scene

# Save original render settings
orig_engine = scene.render.engine
orig_x = scene.render.resolution_x
orig_y = scene.render.resolution_y
orig_pct = scene.render.resolution_percentage

# Use current engine (EEVEE is default and fast enough)
scene.render.resolution_x = {width!r}
scene.render.resolution_y = {height!r}
scene.render.resolution_percentage = 100

output_path = {tmp_path!r}
out_dir = os.path.dirname(output_path)
if out_dir:
    os.makedirs(out_dir, exist_ok=True)

scene.render.filepath = output_path
scene.render.image_settings.file_format = "PNG"

bpy.ops.render.render(write_still=True)

# Restore original settings
scene.render.engine = orig_engine
scene.render.resolution_x = orig_x
scene.render.resolution_y = orig_y
scene.render.resolution_percentage = orig_pct

result = {{
    "output_path": output_path,
}}
"""
    image_bytes = _exec_and_read_image(code)
    if image_bytes is not None:
        return Image(data=image_bytes, format="png")
    return _error_json("Failed to render preview image.")
