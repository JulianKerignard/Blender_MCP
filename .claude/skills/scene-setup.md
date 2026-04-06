---
name: scene-setup
description: Configurer une scène complète Blender (éclairage, caméra, environnement)
user-invocable: true
---

# Scene Setup - Configurer la scène

## Workflow

1. **Éclairage** :
   - `setup_studio_lighting(style)` pour un preset rapide :
     - "three_point" : éclairage studio classique
     - "outdoor_sun" : lumière extérieure naturelle
     - "dramatic" : éclairage cinématique
     - "soft" : éclairage doux et uniforme
   - Ou créer manuellement : `create_light(light_type, energy, color, location, rotation)`
   - Ajuster : `set_light_properties` pour affiner

2. **Caméra** :
   - `create_camera` avec lens (35mm grand angle, 50mm standard, 85mm portrait)
   - `point_camera_at(camera_name, target)` pour viser un objet
   - `set_active_camera` pour définir la caméra de rendu
   - `set_camera_properties` pour DOF, clip range

3. **Environnement** :
   - `polyhaven_search("studio", "hdris")` pour trouver un HDRI
   - `polyhaven_download_hdri(asset_id, "1k")` pour l'appliquer
   - Ou `execute_blender_code` pour changer la couleur de fond directement via bpy

4. **Rendu** :
   - `set_render_settings` pour configurer moteur, résolution, samples
   - EEVEE : rapide, bon pour preview et stylisé
   - Cycles : réaliste, plus lent
   - `focus_viewport_on("NomObjet")` pour cadrer la vue avant les snapshots
   - `render_preview` pour un aperçu rapide
   - `render_image(return_image=True)` pour le rendu final

5. **Organisation** :
   - `create_collection("Lights")` + `move_to_collection` pour ranger les lumières
   - `create_collection("Cameras")` pour les caméras

## Presets de scène

### Studio photo
- Three-point lighting
- Caméra 85mm, f/2.8, focus sur le sujet
- HDRI studio ou fond gris

### Extérieur jour
- Sun light, energy=5, angle léger
- HDRI outdoor
- Caméra 35-50mm

### PSX Horror
- Un seul spot dramatique
- Pas de HDRI, fond noir
- Caméra 50mm, pas de DOF

## Règles
- Toujours vérifier avec `get_scene_snapshot` ou `render_preview`
- Nommer les lumières clairement (Key_Light, Fill_Light, Rim_Light)
- Pour du jeu : EEVEE suffit pour le preview

## En cas d'erreur
- `undo()` pour annuler la dernière opération
- Si l'éclairage est trop fort/faible : ajuster avec `set_light_properties` (energy, color)
- Si la caméra ne vise pas le bon objet : `point_camera_at(camera_name, target)`
- Si le HDRI ne s'applique pas : vérifier avec `execute_blender_code` que le World shader est correctement configuré
