---
name: import-asset
description: Rechercher et importer des assets 3D depuis SketchFab ou Polyhaven
user-invocable: true
---

# Import Asset - Importer des assets 3D

## Sources disponibles

### SketchFab (modèles 3D)
Nécessite une clé API. Des millions de modèles 3D.

1. **Rechercher** : `sketchfab_search(query, downloadable=True, count=10)`
2. **Voir les détails** : `sketchfab_get_model(uid)` -- license, polycount, formats
3. **Importer** : `sketchfab_download_import(uid, name="MonObjet")` -- télécharge en glTF et importe
4. **Configurer** : `sketchfab_configure(api_token="xxx")` si pas encore fait

### Polyhaven (HDRIs, textures, modèles CC0)
Gratuit, pas de clé API. Tous les assets sont CC0.

1. **HDRIs** (environnement/éclairage) :
   - `polyhaven_search("forest", "hdris")`
   - `polyhaven_download_hdri(asset_id, "1k")` -- applique directement au World
2. **Textures PBR** (matériaux) :
   - `polyhaven_search("brick", "textures")`
   - `polyhaven_download_texture(asset_id, "1k", "MonMaterial")` -- télécharge diffuse+normal+rough et connecte tout
3. **Modèles 3D** :
   - `polyhaven_search("furniture", "models")`
   - `polyhaven_get_asset(asset_id)` pour les détails

### Fichiers locaux
- `import_model(path)` supporte : glTF, GLB, FBX, OBJ, STL, PLY
- Auto-détecte le format par l'extension

## Après import

1. **Vérifier** : `list_objects` pour voir ce qui a été importé
2. **Renommer** : `rename_object` pour des noms clairs
3. **Vérifier les matériaux** : `list_materials()` pour voir ce qui a été importé
4. **Positionner** : `set_transform` pour placer au bon endroit
5. **Redimensionner** : `set_transform(name, scale=[...])` + `apply_transform`
6. **Organiser** : `move_to_collection` dans la bonne collection
7. **Snapshot** : `get_scene_snapshot` pour vérifier

## Règles
- Vérifier la license avant d'utiliser un asset SketchFab
- Polyhaven est CC0 = libre d'utilisation partout
- Toujours appliquer les transforms après import
- Renommer les objets importés (les noms par défaut sont souvent moches)

## En cas d'erreur
- `undo()` pour annuler la dernière action
