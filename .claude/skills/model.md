---
name: model
description: Modeliser un objet 3D dans Blender a partir d'une description
user-invocable: true
---

# Model - Creer un modele 3D dans Blender

## Principes de precision

**REGLE FONDAMENTALE : Toujours mesurer avant de placer.**

1. Creer la forme principale
2. Lire ses dimensions exactes avec `get_object_info` ou `get_vertices`
3. CALCULER mathematiquement les positions des sous-elements
4. Verifier avec `get_scene_snapshot` apres chaque etape

**Ne jamais estimer une position "au feeling"** -- toujours deriver les coordonnees des dimensions reelles.

## Workflow

1. **Analyser la demande** : comprendre ce que l'utilisateur veut modeliser
2. **Nettoyer la scene** si demande : `clear_scene(keep_camera=True, keep_light=True)`
3. **Construire la forme principale** :
   - `create_primitive` pour les formes de base
   - `create_curve` pour les formes courbes (poignees, tubes, cables, arches)
   - `create_mesh` pour des formes custom (vertices/faces)
   - `create_text` pour du texte 3D
4. **MESURER la forme principale** :
   - `get_object_info(name)` pour dimensions et bounding box
   - `get_vertices(name)` pour les positions exactes de chaque vertex
   - Noter les dimensions pour calculer les positions des sous-elements
5. **Placer les sous-elements avec precision** :
   - CALCULER chaque position a partir des dimensions mesurees
   - Exemple : si le corps fait 0.5m de large, le bouton va a x = 0.5/2 - 0.02 = 0.23
   - `set_transform` avec les coordonnees calculees
6. **Utiliser les courbes** quand c'est pertinent :
   - Cables, fils : `create_curve("bezier", points=[...])` + `set_curve_properties(bevel_depth=0.005)`
   - Poignees, arches : courbe bezier + bevel
   - Formes organiques : courbe + extrusion
   - Tubes : courbe + `set_curve_properties(bevel_depth=radius)`
   - Convertir en mesh si besoin : `curve_to_mesh`
7. **Modifier la geometrie** :
   - `edit_mesh` pour extrude, bevel, inset, subdivide
   - `add_modifier` pour subdivision surface, mirror, boolean, array
   - `boolean_operation` pour combiner/soustraire des formes
   - `get_vertices` apres modification pour verifier le resultat
8. **Appliquer les transforms** : `apply_transform` avant de continuer
9. **Materiaux** :
   - `create_material` avec les bonnes couleurs/proprietes
   - `assign_material` a chaque partie
   - `create_procedural_material` pour des presets (wood, marble, metal, brick, fabric)
10. **Organiser** :
    - `rename_object` pour des noms clairs
    - `join_objects` si necessaire
    - `set_parent` pour la hierarchie
    - `create_collection` + `move_to_collection` pour grouper
11. **Verifier** :
    - `focus_viewport_on` pour centrer la vue
    - `get_scene_snapshot` pour voir le resultat
    - `get_mesh_stats` pour verifier la topologie
    - `list_materials()` pour verifier les materiaux

## Erreurs courantes a eviter

- **Placer des elements "au feeling"** -- toujours calculer depuis les dimensions mesurees
- **Oublier les courbes** -- un cable n'est pas un cylindre, c'est une courbe avec bevel
- **Ne pas verifier visuellement** -- prendre un snapshot apres chaque etape majeure
- **Ne pas apply scale** -- toujours apply avant UV ou export

## Style PSX (si demande)
- Low poly : pas de subdivision surface
- Flat shading : `set_smooth_shading(name, smooth=False)`
- Couleurs simples, roughness haute (~0.8-0.9)
- Pas de bevel, pas d'aretes arrondies

## En cas d'erreur
- `undo()` pour annuler la derniere operation
- `get_vertices(name)` pour comprendre ou sont les vertices
- `get_object_info(name)` pour verifier les dimensions
- Si un boolean echoue : verifier que les meshes se chevauchent
