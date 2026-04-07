"""SketchFab integration tools for searching, downloading, and importing 3D models."""

import json
import logging
import os
import zipfile
from pathlib import Path

import httpx

from blender_mcp.server import mcp, _exec, _error_json
from blender_mcp.config import (
    get_sketchfab_token,
    get_download_dir,
    get_http_client,
    load_config,
    save_config,
)

logger = logging.getLogger(__name__)

SKETCHFAB_API = "https://api.sketchfab.com/v3"


def _auth_headers() -> dict[str, str]:
    """Return authorization headers if a token is available."""
    token = get_sketchfab_token()
    if token:
        return {"Authorization": f"Token {token}"}
    return {}


@mcp.tool()
def sketchfab_search(
    query: str,
    downloadable: bool = True,
    count: int = 10,
    categories: str = "",
) -> str:
    """Search for 3D models on SketchFab.

    Args:
        query: Search terms (e.g. "medieval castle", "sci-fi weapon").
        downloadable: If True, only return models that can be downloaded.
        count: Number of results to return (max 24).
        categories: Optional category filter (e.g. "architecture", "characters").
    """
    try:
        params: dict[str, str | int | bool] = {
            "type": "models",
            "q": query,
            "downloadable": str(downloadable).lower(),
            "count": min(count, 24),
        }
        if categories.strip():
            params["categories"] = categories.strip()

        client = get_http_client()
        resp = client.get(
            f"{SKETCHFAB_API}/search",
            params=params,
            headers=_auth_headers(),
        )
        resp.raise_for_status()
        data = resp.json()

        models = []
        for item in data.get("results", []):
            thumbnail_url = ""
            thumbnails = item.get("thumbnails", {}).get("images", [])
            if thumbnails:
                # Pick a medium-sized thumbnail
                for thumb in thumbnails:
                    if thumb.get("width", 0) >= 200:
                        thumbnail_url = thumb.get("url", "")
                        break
                if not thumbnail_url:
                    thumbnail_url = thumbnails[0].get("url", "")

            license_info = item.get("license", {})
            models.append({
                "uid": item.get("uid", ""),
                "name": item.get("name", ""),
                "description": (item.get("description", "") or "")[:200],
                "thumbnail_url": thumbnail_url,
                "viewCount": item.get("viewCount", 0),
                "likeCount": item.get("likeCount", 0),
                "isDownloadable": item.get("isDownloadable", False),
                "license": {
                    "label": license_info.get("label", "") if license_info else "",
                    "url": license_info.get("url", "") if license_info else "",
                },
            })

        result = {
            "query": query,
            "total_results": data.get("totalCount", len(models)),
            "returned": len(models),
            "models": models,
        }
        return json.dumps(result, indent=2)

    except httpx.HTTPStatusError as e:
        return _error_json(f"HTTP {e.response.status_code}: {e.response.text}")
    except Exception as e:
        return _error_json(str(e))


@mcp.tool()
def sketchfab_get_model(uid: str) -> str:
    """Get detailed information about a specific SketchFab model.

    Args:
        uid: The unique identifier of the SketchFab model.
    """
    try:
        client = get_http_client()
        resp = client.get(
            f"{SKETCHFAB_API}/models/{uid}",
            headers=_auth_headers(),
        )
        resp.raise_for_status()
        data = resp.json()

        # Extract available formats
        formats = {}
        archives = data.get("archives", {})
        if archives:
            for fmt_name, fmt_data in archives.items():
                if isinstance(fmt_data, dict):
                    formats[fmt_name] = {
                        "size": fmt_data.get("size", 0),
                        "textureCount": fmt_data.get("textureCount", 0),
                    }

        user_info = data.get("user", {})
        license_info = data.get("license", {})

        result = {
            "uid": data.get("uid", ""),
            "name": data.get("name", ""),
            "description": data.get("description", ""),
            "tags": [t.get("name", "") for t in data.get("tags", [])],
            "categories": [c.get("name", "") for c in data.get("categories", [])],
            "license": {
                "label": license_info.get("label", "") if license_info else "",
                "url": license_info.get("url", "") if license_info else "",
            },
            "formats": formats,
            "polyCount": data.get("faceCount", 0),
            "vertexCount": data.get("vertexCount", 0),
            "textureCount": data.get("textureCount", 0),
            "animationCount": data.get("animationCount", 0),
            "isDownloadable": data.get("isDownloadable", False),
            "user": {
                "username": user_info.get("username", "") if user_info else "",
                "displayName": user_info.get("displayName", "") if user_info else "",
                "profileUrl": user_info.get("profileUrl", "") if user_info else "",
            },
            "viewCount": data.get("viewCount", 0),
            "likeCount": data.get("likeCount", 0),
        }
        return json.dumps(result, indent=2)

    except httpx.HTTPStatusError as e:
        return _error_json(f"HTTP {e.response.status_code}: {e.response.text}")
    except Exception as e:
        return _error_json(str(e))


@mcp.tool()
def sketchfab_download_import(uid: str, name: str = "") -> str:
    """Download a 3D model from SketchFab and import it into Blender.

    Requires a SketchFab API token to be configured. The model must be
    downloadable. Downloads as glTF and imports into the current scene.

    Args:
        uid: The unique identifier of the SketchFab model to download.
        name: Optional name to give the imported objects in Blender.
    """
    try:
        config = load_config()
        token = get_sketchfab_token(config)
        if not token:
            return _error_json(
                "No SketchFab API token configured. "
                "Use sketchfab_configure to set your token, or set "
                "the SKETCHFAB_API_TOKEN environment variable."
            )

        headers = {"Authorization": f"Token {token}"}

        # Step 1: Request download URL
        client = get_http_client()
        resp = client.get(
            f"{SKETCHFAB_API}/models/{uid}/download",
            headers=headers,
        )
        if resp.status_code == 401:
            return _error_json("Authentication failed. Check your API token.")
        if resp.status_code == 403:
            return _error_json("Download not permitted for this model. It may not be downloadable.")
        resp.raise_for_status()
        download_data = resp.json()

        # Get the glTF download URL (prefer gltf over other formats)
        download_url = None
        for fmt_key in ("gltf", "glb", "source"):
            fmt_info = download_data.get(fmt_key)
            if fmt_info and isinstance(fmt_info, dict):
                download_url = fmt_info.get("url")
                if download_url:
                    break

        if not download_url:
            return json.dumps({
                "error": "No downloadable format found.",
                "available_keys": list(download_data.keys()),
            }, indent=2)

        # Step 2: Download the ZIP archive
        download_dir = get_download_dir(config)
        model_dir = download_dir / uid
        model_dir.mkdir(parents=True, exist_ok=True)

        zip_path = model_dir / "model.zip"
        with httpx.Client(timeout=120, follow_redirects=True) as stream_client:
            with stream_client.stream("GET", download_url) as stream:
                stream.raise_for_status()
                with open(zip_path, "wb") as f:
                    for chunk in stream.iter_bytes(chunk_size=8192):
                        f.write(chunk)

        # Step 3: Extract ZIP
        extract_dir = model_dir / "extracted"
        if extract_dir.exists():
            import shutil
            shutil.rmtree(extract_dir)
        extract_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.namelist():
                member_path = os.path.normpath(os.path.join(extract_dir, member))
                if not member_path.startswith(os.path.normpath(str(extract_dir))):
                    return _error_json(f"Unsafe path in ZIP archive: {member}")
            zf.extractall(extract_dir)

        # Clean up ZIP after successful extraction
        zip_path.unlink(missing_ok=True)

        # Step 4: Find the glTF/GLB file
        gltf_file = None
        for ext in ("*.gltf", "*.glb"):
            found = list(extract_dir.rglob(ext))
            if found:
                gltf_file = found[0]
                break

        if gltf_file is None:
            extracted_files = [str(p.relative_to(extract_dir)) for p in extract_dir.rglob("*") if p.is_file()]
            return json.dumps({
                "error": "No .gltf or .glb file found in the downloaded archive.",
                "extracted_files": extracted_files[:20],
            }, indent=2)

        # Step 5: Import into Blender via _exec
        # Use forward slashes in the path for Blender/Python compatibility
        import_path = str(gltf_file).replace("\\", "/")
        rename_to = name.strip()

        code = f"""
import bpy

# Record existing objects
before = set(obj.name for obj in bpy.data.objects)

# Import glTF
bpy.ops.import_scene.gltf(filepath={import_path!r})

# Find newly imported objects
after = set(obj.name for obj in bpy.data.objects)
new_objects = list(after - before)

# Optionally rename imported objects
rename_to = {rename_to!r}
if rename_to and new_objects:
    # Rename root-level imported objects (those without a parent among new objects)
    new_obj_set = set(new_objects)
    roots = [n for n in new_objects if bpy.data.objects[n].parent is None
             or bpy.data.objects[n].parent.name not in new_obj_set]
    if len(roots) == 1:
        bpy.data.objects[roots[0]].name = rename_to
        # Update new_objects list with the renamed object
        new_objects = [rename_to if n == roots[0] else n for n in new_objects]
    else:
        for i, root_name in enumerate(roots):
            suffix = f".{{i:03d}}" if len(roots) > 1 else ""
            bpy.data.objects[root_name].name = rename_to + suffix
        new_objects = [obj.name for obj in bpy.data.objects if obj.name not in before]

result = {{
    "imported_objects": sorted(new_objects),
    "count": len(new_objects),
}}
"""
        exec_result = _exec(code)

        if isinstance(exec_result, dict) and "error" in exec_result:
            return json.dumps(exec_result, indent=2)

        result = {
            "success": True,
            "uid": uid,
            "import_path": import_path,
        }
        if isinstance(exec_result, dict):
            result.update(exec_result)
        return json.dumps(result, indent=2)

    except httpx.HTTPStatusError as e:
        return _error_json(f"HTTP {e.response.status_code}: {e.response.text}")
    except zipfile.BadZipFile:
        return _error_json("Downloaded file is not a valid ZIP archive.")
    except Exception as e:
        return _error_json(str(e))


@mcp.tool()
def sketchfab_configure(api_token: str = "", download_dir: str = "") -> str:
    """Configure SketchFab integration settings.

    Set the API token for authenticated access (required for downloading)
    and/or the directory where models are saved.

    Args:
        api_token: Your SketchFab API token. Find it at https://sketchfab.com/settings/password
        download_dir: Directory to save downloaded models. Defaults to ~/.blender_mcp/downloads
    """
    try:
        config = load_config()

        if api_token.strip():
            config["sketchfab_api_token"] = api_token.strip()
        if download_dir.strip():
            config["download_dir"] = download_dir.strip()

        if api_token.strip() or download_dir.strip():
            save_config(config)

        # Report current status
        current_token = os.environ.get("SKETCHFAB_API_TOKEN", "") or config.get("sketchfab_api_token", "")
        current_dir = get_download_dir(config)

        result = {
            "token_set": bool(current_token),
            "token_source": (
                "environment variable" if os.environ.get("SKETCHFAB_API_TOKEN")
                else "config file" if current_token
                else "not set"
            ),
            "download_dir": str(current_dir),
        }
        return json.dumps(result, indent=2)

    except Exception as e:
        return _error_json(str(e))
