---
name: model
description: Modéliser un objet 3D dans Blender à partir d'une description
user-invocable: true
---

# Model - Créer un modèle 3D dans Blender

## Workflow

1. **Analyser la demande** : comprendre ce que l'utilisateur veut modéliser
2. **Nettoyer la scène** si demandé : `clear_scene(keep_camera=True, keep_light=True)`
3. **Construire la géométrie** :
   - Utiliser `create_primitive` pour les formes de base (cube, sphere, cylinder...)
   - Utiliser `create_mesh` pour des formes custom (vertices/faces)
   - Utiliser `create_curve` pour des courbes/paths
   - Utiliser `create_text` pour du texte 3D
4. **Positionner et dimensionner** : `set_transform` pour location/rotation/scale
5. **Modifier la géométrie** :
   - `edit_mesh` pour extrude, bevel, inset, subdivide
   - `add_modifier` pour subdivision surface, mirror, boolean, array
   - `boolean_operation` pour combiner/soustraire des formes
6. **Appliquer les transforms** : `apply_transform` avant de continuer
7. **Matériaux** :
   - `create_material` avec les bonnes couleurs/propriétés
   - `assign_material` à chaque partie
   - `create_procedural_material` pour des presets (wood, marble, metal, brick, fabric)
8. **Organiser** :
   - `rename_object` pour des noms clairs
   - `join_objects` si nécessaire
   - `set_parent` pour la hiérarchie
   - `create_collection` + `move_to_collection` pour grouper
9. **Vérifier** :
   - `focus_viewport_on` pour centrer la vue
   - `get_scene_snapshot` pour voir le résultat
   - `get_mesh_stats` pour vérifier la topologie

## Style PSX (si demandé)
- Low poly : pas de subdivision surface
- Flat shading : `set_smooth_shading(name, smooth=False)`
- Couleurs simples, roughness haute (~0.8-0.9)
- Pas de bevel, pas d'arêtes arrondies

## Règles
- Toujours vérifier visuellement avec `get_scene_snapshot` après chaque étape majeure
- Nommer proprement chaque objet
- Appliquer les transforms avant UV/export
- Demander clarification si la description est ambiguë
