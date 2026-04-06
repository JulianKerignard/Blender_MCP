---
name: psx-asset
description: Creer un asset complet style PlayStation 1 (low poly, flat shading)
user-invocable: true
---

# PSX Asset - Creer un asset style PS1

## Esthetique PSX
- **Low poly** : 50-500 polygones max par objet
- **Flat shading** : pas de smooth, aretes visibles
- **Couleurs simples** : pas de textures complexes, roughness haute (0.8-0.95)
- **Formes angulaires** : cubes, cylindres bas (8 segments), cones
- **Pas de bevel** : aretes vives
- **Courbes pour les cables/fils** : utiliser `create_curve` avec `bevel_depth`

## Precision du placement

**REGLE : Toujours mesurer avant de placer les details.**

Workflow de placement precis :
1. Creer la piece principale, noter ses dimensions via `get_object_info`
2. Pour chaque sous-element, CALCULER sa position :
   - Position X = (largeur_parent / 2) - offset
   - Position Z = hauteur_base + epaisseur/2
3. Verifier avec `get_scene_snapshot` apres chaque groupe de pieces

## Workflow

1. **Nettoyer** : `clear_scene(keep_camera=True, keep_light=True)`

2. **Forme principale** :
   - `create_primitive` avec peu de segments (cylindre: 8, sphere: 8x6)
   - `set_transform` pour dimensionner
   - `apply_transform` immediatement
   - `get_object_info` pour noter les dimensions exactes

3. **Sous-elements (precis)** :
   - CALCULER les positions depuis les dimensions mesurees
   - Cables/fils : `create_curve("bezier", points=[...])` + `set_curve_properties(bevel_depth=0.005)`
   - PAS de subdivision surface, PAS de bevel
   - Empiler des primitives pour les formes complexes

4. **Materiaux PSX** :
   - `create_material(name, color=[R,G,B], roughness=0.9, metallic=0.0)`
   - Couleurs legerement desaturees pour le style retro

5. **Flat shading** : `set_smooth_shading(name, smooth=False)` sur CHAQUE objet

6. **Assembler** :
   - `join_objects` pour fusionner
   - `rename_object` avec un nom propre
   - `set_origin(name, "ORIGIN_GEOMETRY")`
   - `apply_transform`

7. **UVs** :
   - `auto_mark_seams(name, 30)`
   - `unwrap_uv(name, "unwrap")`
   - `pack_uv_islands(name, 0.005)`
   - `get_uv_snapshot("NomObjet")` pour verifier

8. **Noise PSX** :
   - `add_vertex_noise(name, strength=0.002)` -- vertex jitter
   - `add_uv_noise(name, strength=0.006)` -- UV wobble
   - `add_roughness_noise(name, scale=30, strength=0.12)` -- surface usee

9. **Verifier** :
   - `get_mesh_stats` -- viser < 500 faces
   - `focus_viewport_on` + `get_scene_snapshot`
   - `get_uv_snapshot` pour les UVs

10. **Exporter** :
    - `export_model(path, "fbx")` pour Unity
    - `export_model(path, "glb")` pour Godot

## Palette de couleurs PSX typique
| Usage | Couleur RGB (0-1) |
|-------|-------------------|
| Bois sombre | [0.25, 0.15, 0.07] |
| Bois clair | [0.35, 0.22, 0.10] |
| Metal | [0.4, 0.38, 0.35] |
| Pierre | [0.45, 0.42, 0.38] |
| Tissu rouge | [0.5, 0.1, 0.08] |
| Tissu vert | [0.1, 0.3, 0.1] |
| Peau | [0.6, 0.4, 0.3] |
| Beton | [0.5, 0.48, 0.45] |
| Plastique noir | [0.08, 0.08, 0.08] |
| Bakelite | [0.05, 0.04, 0.03] |

## En cas d'erreur
- `undo()` pour annuler
- `get_vertices(name)` pour voir ou sont les vertices exactement
- `reset_uv(name)` pour recommencer les UVs
- Si le placement est mauvais : `get_object_info` pour remesurer et recalculer
