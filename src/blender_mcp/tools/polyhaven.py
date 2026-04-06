"""Poly Haven integration tools for downloading HDRIs, textures, and models."""

import json
import logging
from pathlib import Path

import httpx

from blender_mcp.server import mcp, _exec, _exec_json, _error_json
from blender_mcp.config import get_download_dir, load_config

logger = logging.getLogger(__name__)

POLYHAVEN_API = "https://api.polyhaven.com"
POLYHAVEN_HEADERS = {"User-Agent": "BlenderMCP/0.1.0"}

# Module-level cached HTTP client (reused across calls)
_http_client: httpx.Client | None = None


def _get_http_client(timeout: int = 30) -> httpx.Client:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.Client(
            timeout=timeout, follow_redirects=True, headers=POLYHAVEN_HEADERS
        )
    return _http_client


@mcp.tool()
def polyhaven_search(
    query: str = "",
    asset_type: str = "all",
    categories: str = "",
) -> str:
    """Search for assets on Poly Haven (HDRIs, textures, models).

    Args:
        query: Search terms to filter results by name or tags (case-insensitive).
        asset_type: Type of asset: "hdris", "textures", "models", or "all".
        categories: Optional category filter (e.g. "outdoor", "brick", "furniture").
    """
    try:
        params: dict[str, str] = {}
        if asset_type.strip().lower() != "all":
            params["t"] = asset_type.strip().lower()

        if categories.strip():
            params["c"] = categories.strip()

        client = _get_http_client()
        resp = client.get(f"{POLYHAVEN_API}/assets", params=params)
        resp.raise_for_status()
        data = resp.json()

        # data is a dict where keys are asset IDs
        results = []
        query_lower = query.strip().lower()
        for asset_id, info in data.items():
            if query_lower:
                name = info.get("name", "").lower()
                tags = [t.lower() for t in info.get("tags", [])]
                if query_lower not in name and not any(
                    query_lower in tag for tag in tags
                ):
                    continue

            results.append({
                "id": asset_id,
                "name": info.get("name", ""),
                "type": info.get("type", ""),
                "categories": info.get("categories", []),
                "tags": info.get("tags", []),
                "download_count": info.get("download_count", 0),
            })

            if len(results) >= 20:
                break

        return json.dumps({
            "query": query,
            "asset_type": asset_type,
            "returned": len(results),
            "results": results,
        }, indent=2)

    except httpx.HTTPStatusError as e:
        return _error_json(f"HTTP {e.response.status_code}: {e.response.text}")
    except Exception as e:
        return _error_json(str(e))


@mcp.tool()
def polyhaven_get_asset(asset_id: str) -> str:
    """Get detailed information about a specific Poly Haven asset.

    Args:
        asset_id: The asset identifier (e.g. "kloofendal_48d_partly_cloudy").
    """
    try:
        client = _get_http_client()
        resp = client.get(f"{POLYHAVEN_API}/asset/{asset_id}")
        resp.raise_for_status()
        data = resp.json()

        # Also fetch available files to determine resolutions/formats
        files_resp = client.get(f"{POLYHAVEN_API}/files/{asset_id}")
        files_resp.raise_for_status()
        files_data = files_resp.json()

        # Extract available resolutions and formats from the files data
        available = {}
        for category_key, resolutions in files_data.items():
            if not isinstance(resolutions, dict):
                continue
            available[category_key] = {}
            for res_key, formats in resolutions.items():
                if not isinstance(formats, dict):
                    continue
                available[category_key][res_key] = list(formats.keys())

        # Build authors dict
        authors = {}
        for author_id, author_info in data.get("authors", {}).items():
            if isinstance(author_info, dict):
                authors[author_id] = author_info.get("name", author_id)
            else:
                authors[author_id] = str(author_info)

        result = {
            "id": asset_id,
            "name": data.get("name", ""),
            "type": data.get("type", ""),
            "tags": data.get("tags", []),
            "categories": data.get("categories", []),
            "authors": authors,
            "available_resolutions_and_formats": available,
        }
        return json.dumps(result, indent=2)

    except httpx.HTTPStatusError as e:
        return _error_json(f"HTTP {e.response.status_code}: {e.response.text}")
    except Exception as e:
        return _error_json(str(e))


@mcp.tool()
def polyhaven_download_hdri(
    asset_id: str,
    resolution: str = "1k",
) -> str:
    """Download an HDRI from Poly Haven and set it as the world environment in Blender.

    Downloads the EXR file, then sets up the world node tree with an
    Environment Texture connected through a Background shader to the World Output.

    Args:
        asset_id: The HDRI asset identifier (e.g. "kloofendal_48d_partly_cloudy").
        resolution: Resolution to download (e.g. "1k", "2k", "4k"). Defaults to "1k".
    """
    try:
        config = load_config()
        client = _get_http_client()

        # Fetch file URLs
        resp = client.get(f"{POLYHAVEN_API}/files/{asset_id}")
        resp.raise_for_status()
        files_data = resp.json()

        # Navigate: hdri -> resolution -> exr -> url
        hdri_data = files_data.get("hdri", {})
        if not hdri_data:
            return _error_json(
                f"No HDRI data found for asset '{asset_id}'. "
                f"Available keys: {list(files_data.keys())}"
            )

        res_data = hdri_data.get(resolution, {})
        if not res_data:
            return _error_json(
                f"Resolution '{resolution}' not available. "
                f"Available: {list(hdri_data.keys())}"
            )

        exr_data = res_data.get("exr", {})
        if not exr_data or "url" not in exr_data:
            return _error_json(
                f"No EXR format found for resolution '{resolution}'. "
                f"Available formats: {list(res_data.keys())}"
            )

        download_url = exr_data["url"]

        # Download the EXR file
        download_dir = get_download_dir(config)
        hdri_dir = download_dir / "polyhaven" / "hdris"
        hdri_dir.mkdir(parents=True, exist_ok=True)
        file_path = hdri_dir / f"{asset_id}_{resolution}.exr"

        with httpx.Client(
            timeout=120, follow_redirects=True, headers=POLYHAVEN_HEADERS
        ) as stream_client:
            with stream_client.stream("GET", download_url) as stream:
                stream.raise_for_status()
                with open(file_path, "wb") as f:
                    for chunk in stream.iter_bytes(chunk_size=8192):
                        f.write(chunk)

        # Set up the HDRI in Blender's world node tree
        import_path = str(file_path).replace("\\", "/")
        code = f"""
import bpy

scene = bpy.context.scene

# Ensure world exists
if scene.world is None:
    scene.world = bpy.data.worlds.new("World")

world = scene.world
world.use_nodes = True
tree = world.node_tree

# Clear existing nodes
tree.nodes.clear()

# Create nodes
bg_node = tree.nodes.new(type='ShaderNodeBackground')
bg_node.location = (0, 0)

env_tex_node = tree.nodes.new(type='ShaderNodeTexEnvironment')
env_tex_node.location = (-300, 0)

output_node = tree.nodes.new(type='ShaderNodeOutputWorld')
output_node.location = (300, 0)

# Load the EXR image
img = bpy.data.images.load({import_path!r}, check_existing=True)
env_tex_node.image = img

# Connect nodes: Env Texture -> Background -> World Output
tree.links.new(env_tex_node.outputs['Color'], bg_node.inputs['Color'])
tree.links.new(bg_node.outputs['Background'], output_node.inputs['Surface'])

result = {{
    "success": True,
    "asset_id": {asset_id!r},
    "resolution": {resolution!r},
    "file_path": {import_path!r},
    "image_name": img.name,
}}
"""
        return _exec_json(code)

    except httpx.HTTPStatusError as e:
        return _error_json(f"HTTP {e.response.status_code}: {e.response.text}")
    except Exception as e:
        return _error_json(str(e))


@mcp.tool()
def polyhaven_download_texture(
    asset_id: str,
    resolution: str = "1k",
    material_name: str = "",
) -> str:
    """Download a PBR texture set from Poly Haven and optionally apply it to a material.

    Downloads available maps (diffuse, normal, roughness, displacement) and
    optionally wires them into an existing material's Principled BSDF node tree.

    Args:
        asset_id: The texture asset identifier (e.g. "rock_wall_08").
        resolution: Resolution to download (e.g. "1k", "2k", "4k"). Defaults to "1k".
        material_name: If provided, apply the textures to this existing material in Blender.
    """
    try:
        config = load_config()
        client = _get_http_client()

        # Fetch file URLs
        resp = client.get(f"{POLYHAVEN_API}/files/{asset_id}")
        resp.raise_for_status()
        files_data = resp.json()

        # Map of Poly Haven keys to our local names and BSDF roles
        map_keys = {
            "Diffuse": {"role": "diffuse", "ext": "png"},
            "diff": {"role": "diffuse", "ext": "png"},
            "nor_gl": {"role": "normal", "ext": "png"},
            "rough": {"role": "roughness", "ext": "png"},
            "disp": {"role": "displacement", "ext": "png"},
            "arm": {"role": "arm", "ext": "png"},
        }

        download_dir = get_download_dir(config)
        tex_dir = download_dir / "polyhaven" / "textures" / asset_id
        tex_dir.mkdir(parents=True, exist_ok=True)

        downloaded_files = {}

        for map_key, map_info in map_keys.items():
            map_data = files_data.get(map_key, {})
            if not map_data:
                continue

            res_data = map_data.get(resolution, {})
            if not res_data:
                continue

            # Try preferred extension, then fall back to whatever is available
            ext = map_info["ext"]
            format_data = res_data.get(ext, {})
            if not format_data:
                # Try first available format
                for available_ext, available_data in res_data.items():
                    if isinstance(available_data, dict) and "url" in available_data:
                        format_data = available_data
                        ext = available_ext
                        break

            if not format_data or "url" not in format_data:
                continue

            download_url = format_data["url"]
            role = map_info["role"]
            file_path = tex_dir / f"{asset_id}_{role}_{resolution}.{ext}"

            with httpx.Client(
                timeout=120, follow_redirects=True, headers=POLYHAVEN_HEADERS
            ) as stream_client:
                with stream_client.stream("GET", download_url) as stream:
                    stream.raise_for_status()
                    with open(file_path, "wb") as f:
                        for chunk in stream.iter_bytes(chunk_size=8192):
                            f.write(chunk)

            downloaded_files[role] = str(file_path).replace("\\", "/")

        if not downloaded_files:
            return _error_json(
                f"No texture maps found for asset '{asset_id}' at resolution "
                f"'{resolution}'. Available keys: {list(files_data.keys())}"
            )

        # If material_name is provided, apply textures in Blender
        applied_maps = []
        if material_name.strip():
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
        # Find the Material Output node
        mat_output = None
        for node in nodes:
            if node.type == 'OUTPUT_MATERIAL':
                mat_output = node
                break

        downloaded = {downloaded_files!r}
        applied = []
        y_offset = 0

        # --- Diffuse / Base Color ---
        if "diffuse" in downloaded:
            tex = nodes.new(type='ShaderNodeTexImage')
            tex.location = (bsdf.location.x - 400, bsdf.location.y - y_offset)
            img = bpy.data.images.load(downloaded["diffuse"], check_existing=True)
            tex.image = img
            links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
            applied.append("diffuse")
            y_offset += 300

        # --- Roughness ---
        if "roughness" in downloaded:
            tex = nodes.new(type='ShaderNodeTexImage')
            tex.location = (bsdf.location.x - 400, bsdf.location.y - y_offset)
            img = bpy.data.images.load(downloaded["roughness"], check_existing=True)
            img.colorspace_settings.name = 'Non-Color'
            tex.image = img
            links.new(tex.outputs['Color'], bsdf.inputs['Roughness'])
            applied.append("roughness")
            y_offset += 300

        # --- Normal ---
        if "normal" in downloaded:
            tex = nodes.new(type='ShaderNodeTexImage')
            tex.location = (bsdf.location.x - 600, bsdf.location.y - y_offset)
            img = bpy.data.images.load(downloaded["normal"], check_existing=True)
            img.colorspace_settings.name = 'Non-Color'
            tex.image = img

            normal_map = nodes.new(type='ShaderNodeNormalMap')
            normal_map.location = (bsdf.location.x - 200, bsdf.location.y - y_offset)

            links.new(tex.outputs['Color'], normal_map.inputs['Color'])
            links.new(normal_map.outputs['Normal'], bsdf.inputs['Normal'])
            applied.append("normal")
            y_offset += 300

        # --- Displacement ---
        if "displacement" in downloaded and mat_output is not None:
            tex = nodes.new(type='ShaderNodeTexImage')
            tex.location = (bsdf.location.x - 600, bsdf.location.y - y_offset)
            img = bpy.data.images.load(downloaded["displacement"], check_existing=True)
            img.colorspace_settings.name = 'Non-Color'
            tex.image = img

            disp_node = nodes.new(type='ShaderNodeDisplacement')
            disp_node.location = (bsdf.location.x - 200, bsdf.location.y - y_offset)

            links.new(tex.outputs['Color'], disp_node.inputs['Height'])
            links.new(disp_node.outputs['Displacement'], mat_output.inputs['Displacement'])
            applied.append("displacement")
            y_offset += 300

        result = {{
            "success": True,
            "material": mat.name,
            "applied_maps": applied,
        }}
"""
            exec_result = _exec(code)

            if isinstance(exec_result, dict) and "error" in exec_result:
                return json.dumps(exec_result, indent=2)

            if isinstance(exec_result, dict):
                applied_maps = exec_result.get("result", {}).get("applied_maps", [])
                if not applied_maps and isinstance(exec_result.get("result"), dict):
                    applied_maps = exec_result["result"].get("applied_maps", [])

        result = {
            "success": True,
            "asset_id": asset_id,
            "resolution": resolution,
            "downloaded_files": downloaded_files,
            "material_name": material_name if material_name.strip() else None,
            "applied_maps": applied_maps,
        }
        return json.dumps(result, indent=2)

    except httpx.HTTPStatusError as e:
        return _error_json(f"HTTP {e.response.status_code}: {e.response.text}")
    except Exception as e:
        return _error_json(str(e))
