"""Collection management tools for organizing Blender scene objects."""

from blender_mcp.server import mcp, _exec_json, _error_json


@mcp.tool()
def create_collection(name: str, parent: str = "") -> str:
    """Create a new collection in the scene.

    If a parent collection name is given, the new collection is linked under
    it. Otherwise it is linked directly to the scene's root collection.

    Args:
        name: Name for the new collection.
        parent: Optional parent collection name. Leave empty for the scene root.
    """
    code = f"""
import bpy

new_col = bpy.data.collections.new({name!r})

parent_name = {parent!r}.strip()
if parent_name:
    parent_col = bpy.data.collections.get(parent_name)
    if parent_col is None:
        result = {{"error": "Parent collection '" + parent_name + "' not found"}}
    else:
        parent_col.children.link(new_col)
        result = {{
            "name": new_col.name,
            "parent": parent_col.name,
        }}
else:
    bpy.context.scene.collection.children.link(new_col)
    result = {{
        "name": new_col.name,
        "parent": "Scene Collection",
    }}
"""
    return _exec_json(code)


@mcp.tool()
def move_to_collection(object_names: list[str], collection_name: str) -> str:
    """Move objects into a target collection.

    Each object is unlinked from all of its current collections and then
    linked to the specified target collection.

    Args:
        object_names: List of object names to move.
        collection_name: Name of the destination collection.
    """
    code = f"""
import bpy

target_col = bpy.data.collections.get({collection_name!r})
if target_col is None:
    # Also check the scene root collection
    if bpy.context.scene.collection.name == {collection_name!r}:
        target_col = bpy.context.scene.collection
    else:
        target_col = None

if target_col is None:
    result = {{"error": "Collection '{collection_name}' not found"}}
else:
    moved = []
    not_found = []
    names = {object_names!r}

    for obj_name in names:
        obj = bpy.data.objects.get(obj_name)
        if obj is None:
            not_found.append(obj_name)
            continue

        # Unlink from all current collections
        for col in list(obj.users_collection):
            col.objects.unlink(obj)

        # Link to the target collection
        target_col.objects.link(obj)
        moved.append(obj_name)

    result = {{
        "moved": moved,
        "not_found": not_found,
        "target_collection": target_col.name,
    }}
"""
    return _exec_json(code)


@mcp.tool()
def list_collections() -> str:
    """List all collections in the scene as a recursive tree.

    Returns each collection's name, object count, child collections,
    and visibility state.
    """
    code = """
import bpy

def build_tree(collection, layer_collection=None):
    info = {
        "name": collection.name,
        "object_count": len(collection.objects),
        "objects": [obj.name for obj in collection.objects],
        "hide_render": collection.hide_render,
    }

    # Viewport visibility from the view layer
    if layer_collection is not None:
        info["excluded"] = layer_collection.exclude
        info["hide_viewport"] = layer_collection.hide_viewport
    else:
        info["excluded"] = False
        info["hide_viewport"] = False

    children = []
    for child_col in collection.children:
        child_lc = None
        if layer_collection is not None:
            for lc_child in layer_collection.children:
                if lc_child.collection == child_col:
                    child_lc = lc_child
                    break
        children.append(build_tree(child_col, child_lc))

    info["children"] = children
    return info

scene = bpy.context.scene
root_lc = bpy.context.view_layer.layer_collection
result = build_tree(scene.collection, root_lc)
"""
    return _exec_json(code)


@mcp.tool()
def set_collection_visibility(
    name: str,
    visible: bool | None = None,
    render_visible: bool | None = None,
) -> str:
    """Set the viewport and/or render visibility of a collection.

    Only the provided (non-None) values are modified. Viewport visibility
    is controlled via the view layer's ``exclude`` flag; render visibility
    is controlled via the collection's ``hide_render`` property.

    Args:
        name: Name of the collection.
        visible: If provided, set viewport visibility (True = visible, False = excluded).
        render_visible: If provided, set render visibility (True = visible, False = hidden).
    """
    code = f"""
import bpy

col = bpy.data.collections.get({name!r})
if col is None:
    result = {{"error": "Collection '{name}' not found"}}
else:
    # Find the matching layer_collection (recursive search)
    def find_layer_collection(lc, target_name):
        if lc.collection.name == target_name:
            return lc
        for child in lc.children:
            found = find_layer_collection(child, target_name)
            if found is not None:
                return found
        return None

    root_lc = bpy.context.view_layer.layer_collection
    layer_col = find_layer_collection(root_lc, {name!r})

    if layer_col is None:
        result = {{"error": "Collection '{name}' not found in the active view layer"}}
    else:
        set_visible = {visible!r}
        set_render_visible = {render_visible!r}

        if set_visible is not None:
            # exclude=True means hidden; visible=True means exclude=False
            layer_col.exclude = not set_visible

        if set_render_visible is not None:
            col.hide_render = not set_render_visible

        result = {{
            "name": col.name,
            "excluded": layer_col.exclude,
            "hide_viewport": layer_col.hide_viewport,
            "hide_render": col.hide_render,
        }}
"""
    return _exec_json(code)
