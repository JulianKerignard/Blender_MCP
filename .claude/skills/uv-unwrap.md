---
name: uv-unwrap
description: Workflow complet de UV unwrapping pour un objet Blender
user-invocable: true
---

# UV Unwrap - Déplier les UVs d'un objet

## Workflow

1. **Préparer** :
   - `apply_transform(name, scale=True)` -- OBLIGATOIRE avant unwrap
   - `get_mesh_stats` pour connaître la complexité du mesh

2. **Choisir la méthode** selon le type d'objet :
   - **Cubes/formes angulaires** : `auto_mark_seams(name, 30)` + `unwrap_uv(name, "unwrap")`
   - **Formes organiques** : `auto_mark_seams(name, 45)` + `unwrap_uv(name, "unwrap")`
   - **Objets simples** : `unwrap_uv(name, "smart_project")` (tout automatique)
   - **Cylindres** : `unwrap_uv(name, "cylinder_project")`
   - **Sphères** : `unwrap_uv(name, "sphere_project")`

3. **Ranger les îlots** :
   - `pack_uv_islands(name, margin=0.005)` pour du game-ready
   - `pack_uv_islands(name, margin=0.01)` pour du bake avec margin

4. **Optimiser pour le game** (optionnel) :
   - Scaling par visibilité avec `scale_uv(name, [u_scale, v_scale], pivot="CENTER")` pour ajuster le tiling
   - Pour un scaling avancé par face, utiliser `execute_blender_code` avec du code BMesh

5. **Vérifier** :
   - `get_uv_info` pour voir les layers
   - `get_uv_bounds` pour les stats (coverage, taille)
   - `get_uv_snapshot` pour voir visuellement le layout

6. **Si le résultat n'est pas bon** :
   - `reset_uv` pour tout effacer
   - Recommencer avec une autre méthode ou des seams manuels
   - `mark_seams(name, edge_indices=[...])` pour des seams custom
   - `unwrap_selected_faces` pour déplier face par face

## Cas spéciaux

### Multi-objets (atlas commun)
1. `join_objects` pour fusionner en un seul mesh
2. Unwrap le mesh joint
3. Toutes les faces partagent le même espace UV 0-1

### Plusieurs UV layers
- `create_uv_layer(name, "Lightmap")` pour une 2e couche
- `set_active_uv_layer` pour switcher
- UV1 = diffuse, UV2 = lightmap (typique Unity/Unreal)

### PSX style
- Pas besoin de seams complexes
- `smart_project` suffit
- Petites textures (64x64), les imperfections UV sont le charme

## Règles
- TOUJOURS apply scale avant unwrap
- Vérifier avec `get_uv_snapshot` après chaque étape
- Pour du game : margin 0.005 minimum entre îlots
- Pour du bake : margin 0.01-0.02

## En cas d'erreur
- `undo()` pour annuler la dernière action
- `reset_uv(name)` pour effacer les UVs et recommencer le dépliage
