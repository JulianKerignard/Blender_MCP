"""Constraint and parenting tools for Blender objects."""

from blender_mcp.server import mcp, _exec_json, _error_json


@mcp.tool()
def set_parent(
    child_name: str,
    parent_name: str,
    keep_transform: bool = True,
) -> str:
    """Set a parent-child relationship between two objects.

    Args:
        child_name: Name of the object to become the child.
        parent_name: Name of the object to become the parent.
        keep_transform: If True, the child's world-space transform is preserved
            by setting the parent inverse matrix. Default True.

    Returns:
        JSON with the child and parent names.
    """
    code = f"""
import bpy

child = bpy.data.objects.get({child_name!r})
parent = bpy.data.objects.get({parent_name!r})

if child is None:
    result = {{"error": "Child object " + {child_name!r} + " not found"}}
elif parent is None:
    result = {{"error": "Parent object " + {parent_name!r} + " not found"}}
else:
    child.parent = parent
    if {keep_transform!r}:
        child.matrix_parent_inverse = parent.matrix_world.inverted()

    result = {{
        "child": child.name,
        "parent": parent.name,
        "keep_transform": {keep_transform!r},
    }}
"""
    return _exec_json(code)


@mcp.tool()
def clear_parent(name: str, keep_transform: bool = True) -> str:
    """Remove the parent of an object.

    Args:
        name: Name of the child object whose parent should be cleared.
        keep_transform: If True, the object's world-space transform is preserved
            after un-parenting. Default True.

    Returns:
        JSON with the object name and previous parent info.
    """
    code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
elif obj.parent is None:
    result = {{"error": "Object " + {name!r} + " has no parent"}}
else:
    old_parent = obj.parent.name

    if {keep_transform!r}:
        world_matrix = obj.matrix_world.copy()
        obj.parent = None
        obj.matrix_world = world_matrix
    else:
        obj.parent = None

    result = {{
        "name": obj.name,
        "old_parent": old_parent,
        "keep_transform": {keep_transform!r},
    }}
"""
    return _exec_json(code)


@mcp.tool()
def add_constraint(
    name: str,
    constraint_type: str,
    target_name: str = "",
    properties: dict | None = None,
) -> str:
    """Add a constraint to an object.

    Common constraint types: TRACK_TO, COPY_LOCATION, COPY_ROTATION,
    COPY_SCALE, LIMIT_LOCATION, LIMIT_ROTATION, LIMIT_SCALE, DAMPED_TRACK,
    LOCKED_TRACK, FOLLOW_PATH, CHILD_OF, FLOOR.

    Args:
        name: Name of the object to add the constraint to.
        constraint_type: Blender constraint type string (e.g. "TRACK_TO").
        target_name: Optional name of the target object for the constraint.
        properties: Optional dict of additional constraint properties to set
            via attribute name, e.g. {"influence": 0.5, "track_axis": "TRACK_NEGATIVE_Z"}.

    Returns:
        JSON with the constraint info.
    """
    code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
else:
    constraint = obj.constraints.new(type={constraint_type!r})
    _error = None

    target_name = {target_name!r}
    if target_name:
        target = bpy.data.objects.get(target_name)
        if target is None:
            obj.constraints.remove(constraint)
            _error = "Target object " + target_name + " not found"
        else:
            constraint.target = target

    if _error:
        result = {{"error": _error}}
    else:
        props = {properties!r}
        if props:
            for attr, value in props.items():
                if hasattr(constraint, attr):
                    setattr(constraint, attr, value)

        info = {{
            "object": obj.name,
            "constraint_name": constraint.name,
            "constraint_type": constraint.type,
            "enabled": constraint.enabled,
        }}
        if hasattr(constraint, 'target') and constraint.target is not None:
            info["target"] = constraint.target.name
        result = info
"""
    return _exec_json(code)


@mcp.tool()
def remove_constraint(name: str, constraint_name: str) -> str:
    """Remove a constraint from an object.

    Args:
        name: Name of the object.
        constraint_name: Name of the constraint to remove.

    Returns:
        JSON confirming the removal.
    """
    code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
else:
    constraint = obj.constraints.get({constraint_name!r})
    if constraint is None:
        result = {{"error": "Constraint " + {constraint_name!r} + " not found on object " + {name!r}}}
    else:
        obj.constraints.remove(constraint)
        result = {{
            "object": obj.name,
            "removed_constraint": {constraint_name!r},
            "remaining_constraints": [c.name for c in obj.constraints],
        }}
"""
    return _exec_json(code)


@mcp.tool()
def list_constraints(name: str) -> str:
    """List all constraints on an object.

    Args:
        name: Name of the object.

    Returns:
        JSON with a list of constraints including name, type, enabled state, and target.
    """
    code = f"""
import bpy

obj = bpy.data.objects.get({name!r})
if obj is None:
    result = {{"error": "Object " + {name!r} + " not found"}}
else:
    constraints = []
    for c in obj.constraints:
        info = {{
            "name": c.name,
            "type": c.type,
            "enabled": c.enabled,
        }}
        if hasattr(c, 'target') and c.target is not None:
            info["target"] = c.target.name
        else:
            info["target"] = None
        constraints.append(info)

    result = {{
        "object": obj.name,
        "constraint_count": len(constraints),
        "constraints": constraints,
    }}
"""
    return _exec_json(code)
