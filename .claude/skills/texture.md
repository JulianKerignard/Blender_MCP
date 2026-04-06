---
name: texture
description: Texturer et appliquer des matériaux sur des objets Blender
user-invocable: true
---

# Texture - Appliquer textures et matériaux

## Workflow

1. **Identifier la cible** : `list_objects` pour voir les objets disponibles
2. **Préparer les UVs** :
   - `apply_transform` (scale surtout) sur l'objet
   - `auto_mark_seams` avec un angle adapté (30° pour cubes, 45° pour formes organiques)
   - `unwrap_uv` avec la bonne méthode (unwrap pour formes simples, smart_project pour complexes)
   - `pack_uv_islands` pour optimiser l'espace UV
   - `get_uv_snapshot` pour vérifier visuellement le layout UV
3. **Créer les matériaux** :
   - `create_material` avec couleur, metallic, roughness adaptés
   - Ou `create_procedural_material` pour un preset (wood, marble, metal_scratched, brick, fabric)
4. **Assigner** : `assign_material` sur les objets
5. **Textures image** (si l'utilisateur fournit des fichiers) :
   - `add_texture(material, path, "BASE_COLOR")` pour la diffuse
   - `add_texture(material, path, "NORMAL")` pour la normal map
   - `add_texture(material, path, "ROUGHNESS")` pour la roughness
6. **Assets Polyhaven** (textures PBR gratuites) :
   - `polyhaven_search(query, "textures")` pour trouver
   - `polyhaven_download_texture(asset_id, "1k", material_name)` pour télécharger et appliquer
7. **HDRIs** (environnement) :
   - `polyhaven_search(query, "hdris")` pour trouver
   - `polyhaven_download_hdri(asset_id, "1k")` pour appliquer au World
8. **Shader nodes avancés** (si besoin) :
   - `add_shader_node` pour ajouter des nodes
   - `connect_nodes` pour les connecter
   - `set_node_property` pour ajuster les valeurs
   - `list_material_nodes` pour inspecter le graph
9. **Vérifier** : `get_scene_snapshot` en Material Preview

## Résolutions recommandées
- PSX/Low-res : textures 64x64 ou 128x128
- Jeu indie : 512x512 ou 1024x1024
- Qualité : 2k ou 4k

## Règles
- Toujours faire les UVs AVANT d'appliquer les textures
- Apply scale avant unwrap
- Vérifier les UVs avec `get_uv_snapshot`
- Pour du PSX : pas de normal map, juste diffuse avec haute roughness
