---
name: animate
description: Créer des animations simples dans Blender (keyframes, timeline)
user-invocable: true
---

# Animate - Créer des animations

## Workflow

1. **Configurer la timeline** :
   - `set_frame_range(start=1, end=120, fps=24)` -- 5 secondes à 24fps
   - `set_frame(1)` pour aller au début

2. **Poser les keyframes** :
   - `insert_keyframe(name, "location", frame=1, value=[0, 0, 0])` -- position au frame 1
   - `insert_keyframe(name, "location", frame=60, value=[5, 0, 0])` -- se déplace au frame 60
   - `insert_keyframe(name, "rotation_euler", frame=1, value=[0, 0, 0])` -- rotation
   - `insert_keyframe(name, "scale", frame=1, value=[1, 1, 1])` -- scale

3. **Vérifier** :
   - `get_keyframes(name)` pour voir toutes les keyframes
   - `set_frame(frame)` pour naviguer dans le temps
   - `get_scene_snapshot` à différents frames pour voir l'animation

4. **Modifier** :
   - `delete_keyframe(name, "location", frame=60)` pour supprimer une keyframe
   - `insert_keyframe` pour repositionner

5. **Caméra animée** (optionnel) :
   - Keyframer la position/rotation de la caméra
   - Ou utiliser `point_camera_at` + constraints pour un tracking automatique

## Types d'animation courants

### Translation simple (A → B)
```
Frame 1:   insert_keyframe(obj, "location", 1, [0, 0, 0])
Frame 60:  insert_keyframe(obj, "location", 60, [5, 0, 0])
```

### Rotation continue (360°)
```
Frame 1:   insert_keyframe(obj, "rotation_euler", 1, [0, 0, 0])
Frame 120: insert_keyframe(obj, "rotation_euler", 120, [0, 0, 360])
```

### Bounce (rebond)
```
Frame 1:   insert_keyframe(obj, "location", 1, [0, 0, 2])
Frame 30:  insert_keyframe(obj, "location", 30, [0, 0, 0])
Frame 50:  insert_keyframe(obj, "location", 50, [0, 0, 1])
Frame 70:  insert_keyframe(obj, "location", 70, [0, 0, 0])
```

### Apparition (scale 0 → 1)
```
Frame 1:   insert_keyframe(obj, "scale", 1, [0, 0, 0])
Frame 30:  insert_keyframe(obj, "scale", 30, [1, 1, 1])
```

## Règles
- Toujours définir le frame range avant de commencer
- Keyframer au premier ET dernier frame
- Vérifier visuellement avec `get_scene_snapshot` à plusieurs frames
- 24 fps pour du cinéma, 30 fps pour du jeu, 60 fps pour du smooth
