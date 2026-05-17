"""
Export the current F1 scene as a USDZ file for iPhone AR Quick Look.

HOW TO USE
==========
1. Generate the scene normally with the Hot Lap addon (cars + track + animation).
2. Open Blender's Text Editor, click "Open" -> pick this file.
3. (Optional) edit OUT_PATH below to choose where the .usdz lands.
4. Run Script (Alt+P).
5. Watch the system console for timing + final file size.
6. AirDrop / copy the .usdz to an iPhone -> tap it -> AR Quick Look opens it.

WHAT IT DOES (and why)
======================
The exporter strips the Launch Control rig from the export copy:
  - For each car, samples the BODY object's world matrix per frame.
  - Clones the body mesh, keyframes location/rotation/scale per frame.
  - Clones wheels/brakes/wheelcovers, parents them rigidly to the body clone.
  - The original scene is untouched.
The exported USDZ contains only plain animated meshes (no armatures, no
constraints, no skinning), which is what AR Quick Look plays reliably.

LIMITATIONS
-----------
- Wheels do not spin around their own axis (rigid-follow body). For
  table-top AR this is invisible and avoids quaternion wraparound issues
  in AR Quick Look's playback. If you really need spin, raise FRAME_STEP
  to 1 and add a separate per-wheel sampling pass.
- The Track mesh is included as-is (no decimation here — do that upstream).
- Suspension squash / armature deformation on the body is dropped.
"""

import bpy
import os
import time


# ── CONFIG ────────────────────────────────────────────────────────────────
# Output path. If empty string, writes next to the .blend file.
OUT_PATH = r"C:\Users\91910\Downloads\f1_ar_scene.usdz"
FRAME_STEP = 1          # 1 = every frame; 2 = every other frame (half the keys)
INCLUDE_TRACK = True    # include "Track" mesh and "track_cosmetic" collection
EXPORT_COLL_NAME = "F1_AR_Export"
# ──────────────────────────────────────────────────────────────────────────


def _collect_cars(scene):
    """Discover cars by scanning the scene.

    Strategy A: use scene.lc.cars if the addon's PropertyGroup is populated.
    Strategy B (fallback): find armatures whose name starts with car_rig_ /
    CarRig_, and gather their bone-parented mesh children. Bone names from
    the Launch Control rig (see addon globals.py):
        bone_body_deform               -> body
        bone_wheel_deform.{RL,RR,FL,FR} -> wheels
        bone_wheel_caliperDeform.*     -> brakes / wheel covers
    Strategy C (last resort): any armature whose data contains
    'bone_body_deform' counts as a car.
    """
    cars = []

    # ── Strategy A — addon registry ──
    lc = getattr(scene, "lc", None)
    if lc and getattr(lc, "cars", None):
        for car in lc.cars:
            body = car.body.body if car.body else None
            if not body:
                continue
            prefix = car.collection.name if car.collection else "car"
            wheels = [w for w in (car.wheels.to_list() if car.wheels else []) if w]
            brakes = [b for b in (car.brakes.to_list() if car.brakes else []) if b]
            covers = [wc for wc in (car.wheelcovers.to_list() if car.wheelcovers else []) if wc]
            cars.append({
                'prefix': prefix, 'body': body,
                'wheels': wheels, 'brakes': brakes, 'covers': covers,
            })
        if cars:
            print(f"[F1 AR] Discovered {len(cars)} car(s) via scene.lc.cars")
            return cars

    # ── Strategies B + C — scan scene armatures ──
    armatures = []
    for obj in scene.objects:
        if obj.type != 'ARMATURE':
            continue
        nm = obj.name.lower()
        if nm.startswith('car_rig') or nm.startswith('carrig'):
            armatures.append(obj)
        elif obj.data and 'bone_body_deform' in {b.name for b in obj.data.bones}:
            armatures.append(obj)

    print(f"[F1 AR] Scene scan found {len(armatures)} car armature(s): "
          f"{[a.name for a in armatures]}")

    for arm in armatures:
        prefix = arm.name.replace('car_rig_', '').replace('CarRig_', '') or arm.name
        body = None
        wheels, brakes, covers, others = [], [], [], []

        for child in arm.children:
            if child.type != 'MESH':
                continue
            pbone = child.parent_bone or ''
            if pbone == 'bone_body_deform':
                if body is None:
                    body = child
                else:
                    others.append(child)
            elif pbone.startswith('bone_wheel_deform'):
                wheels.append(child)
            elif pbone.startswith('bone_wheel_caliperDeform'):
                brakes.append(child)
            else:
                others.append(child)

        # Fallback body pick: mesh-child with the most vertices
        if body is None and others:
            others.sort(key=lambda o: len(o.data.vertices) if o.data else 0,
                        reverse=True)
            body = others.pop(0)

        if body is None:
            print(f"[F1 AR]   Skipping '{arm.name}' — no mesh children")
            continue

        # Anything still in `others` becomes a rigid follower of the body
        covers.extend(others)

        cars.append({
            'prefix': prefix, 'body': body,
            'wheels': wheels, 'brakes': brakes, 'covers': covers,
        })
        print(f"[F1 AR]   {prefix}: body='{body.name}', "
              f"{len(wheels)} wheels, {len(brakes)} brakes, "
              f"{len(covers)} other follower(s)")

    return cars


def _sample_body_matrices(scene, cars, frames):
    """One depsgraph evaluation per frame; read matrix_world of every body
    via evaluated_get(depsgraph) so Follow Path / armature constraints are
    actually resolved.

    The cars are animated by a Follow Path constraint on the armature, not
    by keyframes. The body is bone-parented to that armature. Raw
    `obj.matrix_world` returns the LAST cached transform, which is not
    refreshed by `scene.frame_set` alone for constraint-driven chains —
    you have to ask the evaluated copy. Without this the script would
    write the same matrix for every frame and the USDZ would look static.
    """
    out = {id(c['body']): [None] * len(frames) for c in cars}
    bodies = [c['body'] for c in cars]
    for i, f in enumerate(frames):
        scene.frame_set(f)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        for c, body in zip(cars, bodies):
            eval_obj = body.evaluated_get(depsgraph)
            out[id(body)][i] = eval_obj.matrix_world.copy()
        # Diagnostic: print first and last sampled position for car 0
        if cars and (i == 0 or i == len(frames) - 1):
            p = out[id(cars[0]['body'])][i].to_translation()
            print(f"[F1 AR]   sample[{i}] frame={f} "
                  f"{cars[0]['prefix']}.body pos=({p.x:.2f}, {p.y:.2f}, {p.z:.2f})")
    return out


def _reset_export_collection(scene):
    coll = bpy.data.collections.get(EXPORT_COLL_NAME)
    if coll:
        for obj in list(coll.objects):
            try:
                bpy.data.objects.remove(obj, do_unlink=True)
            except Exception:
                pass
        try:
            bpy.data.collections.remove(coll)
        except Exception:
            pass
    coll = bpy.data.collections.new(EXPORT_COLL_NAME)
    scene.collection.children.link(coll)
    return coll


def _bake_object_animation(obj, matrices, frames):
    """Bulk-set keyframes via foreach_set. Linear interp, every sample.

    100x faster than keyframe_insert per frame because we write entire
    fcurve arrays in one C-side call.
    """
    obj.animation_data_create()
    action = bpy.data.actions.new(obj.name + "_action")
    obj.animation_data.action = action

    n = len(matrices)
    loc_flat = [[0.0] * (2 * n) for _ in range(3)]
    rot_flat = [[0.0] * (2 * n) for _ in range(4)]
    sca_flat = [[0.0] * (2 * n) for _ in range(3)]

    for i, m in enumerate(matrices):
        f = float(frames[i])
        loc = m.to_translation()
        q = m.to_quaternion()
        s = m.to_scale()
        for axis, v in enumerate((loc.x, loc.y, loc.z)):
            loc_flat[axis][2 * i] = f
            loc_flat[axis][2 * i + 1] = v
        for axis, v in enumerate((q.w, q.x, q.y, q.z)):
            rot_flat[axis][2 * i] = f
            rot_flat[axis][2 * i + 1] = v
        for axis, v in enumerate((s.x, s.y, s.z)):
            sca_flat[axis][2 * i] = f
            sca_flat[axis][2 * i + 1] = v

    def add_curve(path, idx, flat):
        fc = action.fcurves.new(data_path=path, index=idx)
        fc.keyframe_points.add(count=n)
        fc.keyframe_points.foreach_set('co', flat)
        # LINEAR = 1 in Blender's keyframe interpolation enum
        fc.keyframe_points.foreach_set('interpolation', [1] * n)
        fc.update()

    for i in range(3):
        add_curve('location', i, loc_flat[i])
    for i in range(4):
        add_curve('rotation_quaternion', i, rot_flat[i])
    for i in range(3):
        add_curve('scale', i, sca_flat[i])

    # Push the action to an NLA strip too. Blender's USD exporter samples
    # the evaluated scene either way, but having an NLA strip ensures the
    # action stays bound across frame evaluations and is picked up by
    # exporters that consult NLA tracks (some Blender builds do).
    try:
        track = obj.animation_data.nla_tracks.new()
        track.name = obj.name + "_track"
        strip = track.strips.new(action.name, int(frames[0]), action)
        strip.action_frame_start = frames[0]
        strip.action_frame_end = frames[-1]
    except Exception as e:
        print(f"[F1 AR] (note) NLA push failed for {obj.name}: {e}")


def _clone_car(c, body_mats, export_coll, frames):
    """Body clone gets the keyframed animation. Wheels/brakes/covers are
    cloned at frame_start world position and parented to the body clone.
    """
    prefix = c['prefix']

    body_clone = c['body'].copy()
    body_clone.name = f"{prefix}_body_AR"
    body_clone.parent = None
    body_clone.matrix_parent_inverse.identity()
    body_clone.constraints.clear()
    body_clone.modifiers.clear()
    body_clone.animation_data_clear()
    body_clone.rotation_mode = 'QUATERNION'
    body_clone.matrix_world = body_mats[0]
    export_coll.objects.link(body_clone)

    _bake_object_animation(body_clone, body_mats, frames)

    for sub in c['wheels'] + c['brakes'] + c['covers']:
        clone = sub.copy()
        clone.name = f"{prefix}_{sub.name}_AR"
        clone.parent = None
        clone.constraints.clear()
        clone.modifiers.clear()
        clone.animation_data_clear()
        world_mat = sub.matrix_world.copy()
        export_coll.objects.link(clone)
        clone.matrix_world = world_mat
        # Re-parent to body_clone, preserving world position
        clone.parent = body_clone
        clone.matrix_parent_inverse = body_clone.matrix_world.inverted() @ world_mat


def _link_track(export_coll):
    track = bpy.data.objects.get("Track")
    if track and track.name not in [o.name for o in export_coll.objects]:
        try:
            export_coll.objects.link(track)
        except RuntimeError:
            pass
    cosmetic = bpy.data.collections.get("track_cosmetic")
    if cosmetic:
        already = {o.name for o in export_coll.objects}
        for obj in cosmetic.all_objects:
            if obj.type == 'MESH' and obj.name not in already:
                try:
                    export_coll.objects.link(obj)
                except RuntimeError:
                    pass


def _export_usdz(scene, export_coll, out_path):
    try:
        bpy.ops.object.mode_set(mode='OBJECT')
    except Exception:
        pass
    bpy.ops.object.select_all(action='DESELECT')
    for obj in export_coll.objects:
        try:
            obj.select_set(True)
        except Exception:
            pass

    # Snap the scene frame to the start before export. Some Blender USD
    # builds use the *current* frame as a starting point and only sample
    # forward from there if frame_start/end aren't honored.
    scene.frame_set(scene.frame_start)

    # Build the call as a kwargs dict and try the richest set first,
    # progressively dropping params that don't exist in older builds.
    full_kwargs = dict(
        filepath=out_path,
        selected_objects_only=True,
        visible_objects_only=False,
        export_animation=True,
        export_armatures=False,
        export_materials=True,
        generate_preview_surface=True,
        export_textures=True,
        overwrite_textures=True,
        root_prim_path='/F1Scene',
        # Per-component xform animation (TRS) plays back reliably in
        # AR Quick Look. The default 'MAT' (single 4x4 matrix per sample)
        # is treated by some viewers as a static bind and ignored.
        xform_op_mode='TRS',
        # Force per-frame sampling instead of "only at keyframe times".
        evaluation_mode='RENDER',
        frame_start=scene.frame_start,
        frame_end=scene.frame_end,
    )

    # Try progressively smaller param sets until one works
    fallbacks = [
        full_kwargs,
        {k: v for k, v in full_kwargs.items() if k not in ('xform_op_mode',)},
        {k: v for k, v in full_kwargs.items()
         if k not in ('xform_op_mode', 'evaluation_mode',
                      'export_textures', 'overwrite_textures',
                      'generate_preview_surface', 'root_prim_path',
                      'export_armatures')},
        dict(filepath=out_path,
             selected_objects_only=True,
             export_animation=True,
             export_materials=True),
    ]
    last_err = None
    for kwargs in fallbacks:
        try:
            bpy.ops.wm.usd_export(**kwargs)
            print(f"[F1 AR] USD export called with {len(kwargs)} kwargs: "
                  f"{sorted(kwargs.keys())}")
            return
        except TypeError as e:
            last_err = e
            continue
    raise RuntimeError(f"USD export failed across all param fallbacks: {last_err}")


def main():
    t0 = time.time()
    scene = bpy.context.scene

    cars = _collect_cars(scene)
    if not cars:
        print("[F1 AR] No LC cars found. Generate the scene with the addon first.")
        return

    frames = list(range(scene.frame_start, scene.frame_end + 1, max(1, int(FRAME_STEP))))
    print(f"[F1 AR] {len(cars)} car(s), {len(frames)} samples "
          f"(step={FRAME_STEP}, range={scene.frame_start}..{scene.frame_end})")

    restore_frame = scene.frame_current

    # 1. Sample body world matrices per frame
    t = time.time()
    body_mats = _sample_body_matrices(scene, cars, frames)
    print(f"[F1 AR] Sampled body matrices in {time.time() - t:.1f}s")

    # 2. Build the export collection
    scene.frame_set(scene.frame_start)
    export_coll = _reset_export_collection(scene)

    # 3. Clone bodies + wheels/brakes/covers
    t = time.time()
    for c in cars:
        _clone_car(c, body_mats[id(c['body'])], export_coll, frames)
    print(f"[F1 AR] Cloned + keyframed in {time.time() - t:.1f}s")

    # 3b. Sanity check — confirm the body clones actually got keyframes.
    # If this prints zero keyframes, the bug is in _bake_object_animation;
    # if it prints the right counts but the USDZ still has no motion,
    # the bug is in the USD exporter call.
    for obj in export_coll.objects:
        if obj.name.endswith("_body_AR"):
            ad = obj.animation_data
            action = ad.action if ad else None
            if not action:
                print(f"[F1 AR] !! {obj.name}: NO action assigned")
                continue
            n_fc = len(action.fcurves)
            if n_fc == 0:
                print(f"[F1 AR] !! {obj.name}: action has 0 fcurves")
                continue
            fc0 = action.fcurves[0]
            n_kf = len(fc0.keyframe_points)
            first = tuple(fc0.keyframe_points[0].co) if n_kf else None
            last = tuple(fc0.keyframe_points[-1].co) if n_kf else None
            print(f"[F1 AR] OK {obj.name}: action='{action.name}', "
                  f"{n_fc} fcurves, {n_kf} keys on '{fc0.data_path}[{fc0.array_index}]', "
                  f"first={first}, last={last}")

    # 4. Include track
    if INCLUDE_TRACK:
        _link_track(export_coll)

    scene.frame_set(restore_frame)

    # 5. Resolve output path
    if OUT_PATH:
        out_path = OUT_PATH
    else:
        blend_dir = bpy.path.abspath("//") if bpy.data.is_saved else os.getcwd()
        out_path = os.path.join(blend_dir, "f1_ar_scene.usdz")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # 6. Export
    t = time.time()
    _export_usdz(scene, export_coll, out_path)
    print(f"[F1 AR] USDZ export took {time.time() - t:.1f}s")

    if os.path.exists(out_path):
        size_mb = os.path.getsize(out_path) / (1024 * 1024)
        print(f"[F1 AR] DONE  ->  {out_path}  ({size_mb:.1f} MB, total {time.time() - t0:.1f}s)")
    else:
        print(f"[F1 AR] ERROR: file was not written to {out_path}")


if __name__ == "__main__":
    main()
