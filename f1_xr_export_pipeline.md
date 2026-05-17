# F1 XR Export Pipeline — Problem Statement & Plan

## What We Have

- A Blender addon that generates a scene: appends track + car assets, animates cars along a path using FastF1/OpenF1 telemetry data via a Follow Path constraint
- Decimated car blend files (body ~14k verts, wheels ~11k verts)
- Decimated track blend file (~550k visible verts)
- Animation: 2 cars, ~2000 frames, movement driven by Follow Path constraint on the armature

## What We Want

A GLB file that:
- Contains only the visible, decimated meshes (no gfx_ helpers, no sim_ objects, no Porsche, no dummy objects)
- Has the car animation baked as real keyframes (location + rotation per frame)
- Is small enough to open on an iPhone (~30-50mb target)
- Can be viewed in Khronos glTF Viewer or equivalent

---

## Problems Encountered

### 1. Wrong objects being exported
The addon appends everything from the source blend files including hundreds of helper objects (gfx_, sim_, dummy_, col_, skidmark_, etc). These bloat the vert count from ~700k visible to 2.7M total in the blend file.

### 2. Animation not translating to GLB
The car movement is driven by a Follow Path constraint on the armature, not by keyframes. GLB/glTF does not support constraints. The constraint must be baked into actual location/rotation keyframes before export.

The bake worked (car_rig_RUS and CarRig_mercedes_antonelli both baked) but the exported GLB showed no movement. Likely because the mesh body objects are not directly animated — the armature moves, but the mesh is skinned to the armature, and the armature's baked object-level movement may not be driving the mesh correctly in the export.

### 3. File size too large
289mb GLB. Caused by baking every frame of every bone in the full car rig. The internal rig bones (suspension, wheels, steering) all get baked individually, creating thousands of keyframe channels.

### 4. Track still has heavy objects
china-gp.110 at 157k verts survived the decimation passes and needs removal.

---

## Root Cause

The addon uses a complex car rig (Launch Control Auto Car Rig) with many bones and constraints. Baking the full rig for glTF export produces massive keyframe data. The mesh visibility and animation chain is:

```
Follow Path constraint on Armature → Armature moves → Mesh skinned to Armature → Mesh appears to move
```

GLB needs:
```
Keyframed location/rotation on Armature → Mesh skinned to Armature → Mesh moves
```

The bake converts constraint to keyframes correctly, but the export pipeline is also re-baking internal bone constraints causing bloat and possibly incorrect results.

---

## Proposed Clean Pipeline

### Step 1: Generate scene with addon
Use the addon normally to generate track + cars + animation.

### Step 2: Clean the scene with a script
Delete all non-visual objects before export:
- All objects with prefix: gfx_, GFX_, sim_, dummy_, col_, skidmark_, shrinkwrap_, ground_detect_, speedometer_, speed_calc, internal_wheel
- Porsche objects (in hidden collection, excluded from export anyway)
- Heavy track objects like china-gp.110

### Step 3: Bake only the armature object movement
Bake only OBJECT level (location/rotation of the armature root), not POSE level (individual bones). This captures the car moving along the track without baking every suspension bone.

```python
bpy.ops.nla.bake(
    frame_start=frame_start,
    frame_end=frame_end,
    step=2,               # every 2nd frame to halve file size
    only_selected=True,
    visual_keying=True,
    clear_constraints=True,
    clear_parents=False,
    use_current_action=False,
    bake_types={'OBJECT'} # object level only, not pose
)
```

### Step 4: Strip pose animation from rig
After baking object movement, remove or mute all pose-level bone actions to prevent the exporter from baking them again. This is the key missing step.

### Step 5: Export with correct settings
```python
bpy.ops.export_scene.gltf(
    filepath="...",
    export_format='GLB',
    export_apply=True,
    export_image_format='JPEG',
    export_jpeg_quality=75,
    export_cameras=False,
    export_lights=False,
    export_animations=True,
    export_frame_range=True,
    export_force_sampling=False,  # do not re-bake, use existing keyframes
)
```

### Step 6: Verify in Khronos glTF Viewer
Open on iPhone, confirm cars move along track.

---

## Target Metrics

| Metric | Current | Target |
|--------|---------|--------|
| GLB file size | 289mb | 30-50mb |
| Visible verts | 707k | 500k |
| Animation | Not working | Cars moving on track |
| Phone viewable | No | Yes |

---

## Next Immediate Step

The critical fix is Step 4: after baking object movement, clear the pose-level action from the armature so the glTF exporter does not try to bake all the internal rig bones again. This alone should fix both the file size and the animation.
