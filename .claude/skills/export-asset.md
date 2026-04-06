---
name: export-asset
description: Exporter un asset 3D game-ready depuis Blender
user-invocable: true
---

# Export Asset - Préparer et exporter pour un moteur de jeu

## Workflow

1. **Vérifier la géométrie** :
   - `get_mesh_stats` pour vérifier tris/quads, non-manifold, loose verts
   - Corriger si nécessaire (join loose parts, remove doubles via execute_blender_code)

2. **Préparer le mesh** :
   - `apply_transform` sur tous les objets (location=True, rotation=True, scale=True)
   - `set_origin(name, "ORIGIN_GEOMETRY")` pour centrer l'origine
   - `join_objects` si plusieurs parties doivent être un seul asset
   - `rename_object` pour un nom propre

3. **Vérifier les UVs** :
   - `get_uv_info` pour vérifier qu'il y a des UVs
   - Si pas d'UVs : `auto_mark_seams` + `unwrap_uv` + `pack_uv_islands`
   - `get_uv_snapshot` pour vérifier visuellement

4. **Vérifier les matériaux** :
   - `list_materials` pour voir ce qui est assigné
   - S'assurer que les noms sont propres

5. **Exporter** :
   - **Pour Unity** : `export_model(path, "fbx")`
   - **Pour Godot** : `export_model(path, "gltf")` ou `export_model(path, "glb")`
   - **Pour Unreal** : `export_model(path, "fbx")`
   - **Universel** : `export_model(path, "glb")` (glTF binary, le plus compatible)
   - Option `selected_only=True` pour exporter uniquement la sélection

6. **Sauvegarder** : `save_file` pour garder le .blend source

## Conventions de nommage
- Props : `SM_NomDuProp` (Static Mesh)
- Characters : `SK_NomDuPerso` (Skeletal)
- Pas d'espaces, PascalCase

## Checklist export
- [ ] Scale appliqué (1,1,1)
- [ ] Rotation appliquée (0,0,0)
- [ ] Origine au bon endroit
- [ ] UVs présents et propres
- [ ] Matériaux nommés
- [ ] Pas de loose vertices
- [ ] Mesh watertight (si nécessaire)

## Règles
- Toujours apply transforms avant export
- Vérifier les stats avec `get_mesh_stats`
- Nommer les fichiers sans espaces ni caractères spéciaux
- FBX pour Unity/Unreal, glTF pour Godot/Web
