---
name: psx-asset
description: Créer un asset complet style PlayStation 1 (low poly, flat shading)
user-invocable: true
---

# PSX Asset - Créer un asset style PS1

## Esthétique PSX
- **Low poly** : 50-500 polygones max par objet
- **Flat shading** : pas de smooth, arêtes visibles
- **Couleurs simples** : pas de textures complexes, roughness haute (0.8-0.95)
- **Formes angulaires** : que des cubes, cylindres bas (8-12 segments), cônes
- **Pas de bevel** : arêtes vives, pas d'arrondis
- **Vertex colors** ou textures 64x64 / 128x128

## Workflow

1. **Nettoyer** : `clear_scene(keep_camera=True, keep_light=True)`

2. **Modéliser** :
   - `create_primitive` avec peu de segments (cylindre: 8, sphère: 8x6)
   - `set_transform` pour positionner/dimensionner
   - PAS de subdivision surface
   - PAS de bevel
   - Empiler des cubes/cylindres pour les formes complexes

3. **Matériaux PSX** :
   - `create_material(name, color=[R,G,B], roughness=0.9, metallic=0.0)`
   - Couleurs légèrement désaturées pour le style rétro
   - Pas d'émission sauf pour des écrans/lumières

4. **Flat shading** : `set_smooth_shading(name, smooth=False)` sur CHAQUE objet

5. **Assembler** :
   - `join_objects` pour fusionner en un seul mesh
   - `rename_object` avec un nom propre
   - `set_origin(name, "ORIGIN_GEOMETRY")`
   - `apply_transform`

6. **UVs** :
   - `auto_mark_seams(name, 30)` -- toutes les arêtes vives
   - `unwrap_uv(name, "unwrap")`
   - `pack_uv_islands(name, 0.005)`
   - Scaling UV par visibilité (devant > côtés > dessous)

7. **Vérifier** :
   - `get_mesh_stats` -- viser < 500 faces
   - `focus_viewport_on` + `get_scene_snapshot`
   - `get_uv_snapshot` pour les UVs

8. **Exporter** :
   - `export_model(path, "fbx")` pour Unity
   - `export_model(path, "glb")` pour Godot

## Palette de couleurs PSX typique
| Usage | Couleur RGB (0-1) |
|-------|-------------------|
| Bois sombre | [0.25, 0.15, 0.07] |
| Bois clair | [0.35, 0.22, 0.10] |
| Métal | [0.4, 0.38, 0.35] |
| Pierre | [0.45, 0.42, 0.38] |
| Tissu rouge | [0.5, 0.1, 0.08] |
| Tissu vert | [0.1, 0.3, 0.1] |
| Peau | [0.6, 0.4, 0.3] |
| Béton | [0.5, 0.48, 0.45] |

## Règles
- Maximum 500 faces par objet
- Toujours flat shading
- Pas de subdivision, bevel, ou smooth
- Cylindres = 8 segments max
- Sphères = ico_sphere avec 2 subdivisions max
- Apply transforms avant export
- Noms sans espaces ni accents
