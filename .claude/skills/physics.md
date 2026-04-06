---
name: physics
description: Ajouter de la physique et des simulations dans Blender (rigid body, cloth, collision)
user-invocable: true
---

# Physics - Simulations physiques dans Blender

## Limitations

Les outils MCP n'ont PAS de tools dedies pour la physique. Tout passe par `execute_blender_code`.
Les simulations doivent etre bakees pour etre exportees.

## Rigid Body (corps rigides)

### Ajouter un rigid body actif (tombe, rebondit)
```
execute_blender_code("""
import bpy
obj = bpy.data.objects['MonObjet']
bpy.context.view_layer.objects.active = obj
bpy.ops.rigidbody.object_add(type='ACTIVE')
obj.rigid_body.mass = 1.0
obj.rigid_body.friction = 0.5
obj.rigid_body.restitution = 0.3  # rebond
obj.rigid_body.collision_shape = 'CONVEX_HULL'  # ou BOX, SPHERE, MESH
result = {"rigid_body": "active", "mass": 1.0}
""")
```

### Ajouter un rigid body passif (sol, mur -- ne bouge pas)
```
execute_blender_code("""
import bpy
obj = bpy.data.objects['Sol']
bpy.context.view_layer.objects.active = obj
bpy.ops.rigidbody.object_add(type='PASSIVE')
obj.rigid_body.collision_shape = 'BOX'
result = {"rigid_body": "passive"}
""")
```

### Lancer la simulation
```
set_frame_range(1, 250)
set_frame(1)
# La simulation se calcule quand on avance dans la timeline
set_frame(120)  # Aller au frame 120 pour voir le resultat
get_scene_snapshot()
```

### Baker la simulation
```
execute_blender_code("""
import bpy
bpy.ops.ptcache.bake_all(bake=True)
result = {"baked": True}
""")
```

## Cloth (tissu)

### Ajouter une simulation de tissu
```
execute_blender_code("""
import bpy
obj = bpy.data.objects['Tissu']
bpy.context.view_layer.objects.active = obj
bpy.ops.object.modifier_add(type='CLOTH')
cloth = obj.modifiers['Cloth'].settings
cloth.quality = 5
cloth.mass = 0.3
cloth.tension_stiffness = 15
cloth.compression_stiffness = 15
cloth.bending_stiffness = 0.5
result = {"cloth": "added"}
""")
```

### Ajouter un objet de collision (pour que le tissu tombe dessus)
```
execute_blender_code("""
import bpy
obj = bpy.data.objects['Table']
bpy.context.view_layer.objects.active = obj
bpy.ops.object.modifier_add(type='COLLISION')
result = {"collision": "added"}
""")
```

## Soft Body

### Ajouter un soft body (objet mou, gelatine)
```
execute_blender_code("""
import bpy
obj = bpy.data.objects['Gelatine']
bpy.context.view_layer.objects.active = obj
bpy.ops.object.modifier_add(type='SOFT_BODY')
sb = obj.modifiers['Softbody'].settings
sb.mass = 1.0
sb.friction = 0.5
sb.goal_spring = 0.5
sb.goal_friction = 0.5
result = {"soft_body": "added"}
""")
```

## Force Fields

### Ajouter du vent
```
execute_blender_code("""
import bpy
bpy.ops.object.effector_add(type='WIND', location=(0, -2, 0))
wind = bpy.context.active_object
wind.field.strength = 10
wind.field.flow = 0.5
result = {"wind": "added", "strength": 10}
""")
```

### Ajouter de la gravite modifiee
```
execute_blender_code("""
import bpy
bpy.context.scene.gravity = (0, 0, -9.81)  # Gravite par defaut
# Ou gravite lunaire :
# bpy.context.scene.gravity = (0, 0, -1.62)
result = {"gravity": list(bpy.context.scene.gravity)}
""")
```

## Workflow typique

1. **Creer la scene** : sol (passive), objets (active)
2. **Configurer la physique** : masse, friction, rebond
3. **Definir le frame range** : `set_frame_range(1, 250)`
4. **Tester** : `set_frame(120)` + `get_scene_snapshot()`
5. **Baker** : `execute_blender_code` avec `ptcache.bake_all`
6. **Exporter** : les keyframes bakees sont incluses dans le FBX/glTF

## En cas d'erreur
- `undo()` pour annuler
- Si la simulation explose : reduire la masse, augmenter la friction
- Si le tissu traverse les objets : augmenter la qualite du cloth et verifier la collision
- Pour resetter : `set_frame(1)` remet tout a la position initiale
