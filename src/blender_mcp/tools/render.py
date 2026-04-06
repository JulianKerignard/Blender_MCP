"""Render and viewport tools."""

import json

from blender_mcp.server import mcp, _exec


@mcp.tool()
def render_image(
    output_path: str = "",
    resolution_x: int = 1920,
    resolution_y: int = 1080,
    samples: int = 128,
    engine: str = "",
) -> str:
    """Render the current scene to an image file.

    If no output_path is provided, a temporary file is used. Returns the
    path to the rendered image.

    Args:
        output_path: Destination file path for the render. If empty, a temp file is used.
        resolution_x: Horizontal resolution in pixels.
        resolution_y: Vertical resolution in pixels.
        samples: Number of render samples.
        engine: Render engine (BLENDER_EEVEE_NEXT, CYCLES, BLENDER_WORKBENCH).
                Leave empty to keep the current engine.
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

# Set samples
if scene.render.engine == 'CYCLES':
    scene.cycles.samples = {samples!r}
elif scene.render.engine == 'BLENDER_EEVEE_NEXT':
    scene.eevee.taa_render_samples = {samples!r}

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
format_map = {{
    ".png": "PNG",
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".bmp": "BMP",
    ".tiff": "TIFF",
    ".tif": "TIFF",
    ".exr": "OPEN_EXR",
    ".hdr": "HDR",
}}
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
    result = _exec(code)
    return json.dumps(result, indent=2)


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
        engine: Render engine: BLENDER_EEVEE_NEXT, CYCLES, or BLENDER_WORKBENCH.
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
    elif scene.render.engine == 'BLENDER_EEVEE_NEXT':
        scene.eevee.taa_render_samples = samples
    updated.append("samples")

# Denoising
use_denoising = {use_denoising!r}
if use_denoising is not None:
    if scene.render.engine == 'CYCLES':
        scene.cycles.use_denoising = use_denoising
    elif scene.render.engine == 'BLENDER_EEVEE_NEXT':
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
    result = _exec(code)
    return json.dumps(result, indent=2)


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
format_map = {{
    ".png": "PNG",
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".bmp": "BMP",
}}
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
    result = _exec(code)
    return json.dumps(result, indent=2)
