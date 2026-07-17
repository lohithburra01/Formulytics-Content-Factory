"""
elevation_3d_toy.py  —  standalone Blender bpy toy (STEP 1 of the 3D elevation idea)

Builds an ELEVATED 3D model of Spa from the data we already have and drops a
marker on the racing line that is time-synced to the 2D sim lap. You can orbit
it, scrub the timeline to watch the marker climb/drop, and tune the look with the
KNOBS below. This is a LOOK-AND-FEEL toy — NOT yet wired into the vertical video.

WHAT IT READS (all existing pipeline files):
  - belgian_grand_prix_outline.json   (outer/inner track edges, 2D)  -> road surface
  - belgian_grand_prix_raceline.json  (2D optimal line from the sim)  -> line + marker path
  - belgian_grand_prix_elevation.json (curated APPROX profile by lap fraction) -> the z field
  - spa_2026_synthetic.csv            (sim distance vs time)          -> marker pacing

HOW TO RUN in Blender:
  Option A (Text Editor): open this file, press "Run Script".
  Option B (Python console):  exec(open(r"D:\\f1_hot_lap\\OPTIMAL LAP SCRIPTS\\elevation_3d_toy.py").read())
  Re-running is safe — it deletes what it made last time first.

NOTE ON PHASE: the elevation profile is keyed by lap fraction, but the raw
raceline's point 0 is an arbitrary spot, so the climbs may sit on the wrong
corners until you nudge PHASE_OFFSET (0..1) so Eau Rouge lines up. That's the
main knob to fiddle. (The video build will align this automatically later.)
"""

import bpy
import csv
import json
import numpy as np

# ============================ KNOBS ============================
BASE      = r"D:\f1_hot_lap\OPTIMAL LAP SCRIPTS"
OUTLINE   = BASE + r"\F1_Pipeline_Assets\tracks\belgian_grand_prix_outline.json"
RACELINE  = BASE + r"\F1_Pipeline_Assets\tracks\belgian_grand_prix_raceline.json"
ELEV      = BASE + r"\F1_Pipeline_Assets\tracks\belgian_grand_prix_elevation.json"
SIMCSV    = BASE + r"\F1_Pipeline_Assets\exports\spa_2026_synthetic.csv"

TARGET_SIZE  = 40.0    # horizontal size of the model in Blender units
Z_EXAG       = 6.0     # vertical exaggeration (1 = true scale, looks flat; 4-8 = dramatic)
WIDTH_EXAG   = 6.0     # road-width exaggeration (Spa is 500:1 long:wide -> true width
                       #   renders as a thread; 5-8 makes the elevated ribbon read)
PHASE_OFFSET = 0.0     # rotate the elevation field around the loop (0..1) to align Eau Rouge
ROAD_N       = 800     # cross-sections around the road ribbon
LINE_BEVEL   = 0.12    # racing-line tube radius (Blender units)
LINE_LIFT    = 0.25    # lift the line/marker this far above the road surface
MARKER_R     = 0.7     # marker sphere radius
FPS          = 30      # marker keyframe rate
TURNTABLE    = True    # auto-rotating camera over the lap
COLL_NAME    = "F1_Elevation_Toy"
# ==============================================================


# ---------------------------------------------------------------- data helpers
def _resample_loop(xy, n):
    """Uniform arc-length resample of a closed 2D loop to n points."""
    xy = np.asarray(xy, float)
    if not np.allclose(xy[0], xy[-1]):
        xy = np.vstack([xy, xy[0]])
    seg = np.linalg.norm(np.diff(xy, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    u = np.linspace(0.0, cum[-1], n, endpoint=False)
    return np.column_stack([np.interp(u, cum, xy[:, 0]),
                            np.interp(u, cum, xy[:, 1])])


def _signed_area(poly):
    x, y = poly[:, 0], poly[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def _arc(xy):
    """Cumulative arc length (len == len(xy)), starting at 0."""
    seg = np.linalg.norm(np.diff(xy, axis=0, append=xy[:1]), axis=1)
    return np.concatenate([[0.0], np.cumsum(seg)[:-1]]), float(seg.sum())


# ---------------------------------------------------------------- scene helpers
def _clean():
    """Remove everything this script made last time (idempotent re-runs)."""
    coll = bpy.data.collections.get(COLL_NAME)
    if coll:
        for obj in list(coll.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(coll)
    for name in ("F1ELEV_road", "F1ELEV_line", "F1ELEV_marker",
                 "F1ELEV_peak", "F1ELEV_cam", "F1ELEV_pivot", "F1ELEV_sun"):
        for db in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras, bpy.data.lights):
            d = db.get(name)
            if d:
                db.remove(d)


def _mat(name, rgba, emit=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = rgba
    if "Roughness" in bsdf.inputs:
        bsdf.inputs["Roughness"].default_value = 0.6
    if emit > 0.0:
        # emission strength differs across Blender versions; set both if present
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = rgba
        if "Emission" in bsdf.inputs:
            bsdf.inputs["Emission"].default_value = rgba
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = emit
    return m


# ---------------------------------------------------------------- build
def build():
    _clean()
    coll = bpy.data.collections.new(COLL_NAME)
    bpy.context.scene.collection.children.link(coll)

    def link(obj):
        coll.objects.link(obj)
        return obj

    # ---- load data
    od = json.load(open(OUTLINE, encoding="utf-8"))
    outer = _resample_loop(od["outer"], ROAD_N)
    inner = _resample_loop(od["inner"], ROAD_N)
    rl = np.asarray(json.load(open(RACELINE, encoding="utf-8"))["raceline"], float)
    ed = json.load(open(ELEV, encoding="utf-8"))
    ef = np.asarray(ed["dist_frac"], float)
    ev = np.asarray(ed["elev_m"], float)
    ev = ev - ev.min()                                    # relative metres, min at 0

    # ---- one elevation FIELD, defined along the racing line (the master lap)
    rl_arc, rl_total = _arc(rl)
    rl_frac = rl_arc / rl_total
    rl_elev = np.interp((rl_frac + PHASE_OFFSET) % 1.0, ef, ev)   # metres, per rl point

    # ---- align outer/inner (same winding, matched start) then sample the field
    if _signed_area(outer) < 0:
        outer = outer[::-1]
    if _signed_area(inner) < 0:
        inner = inner[::-1]
    roll = int(np.argmin(np.sum((inner - outer[0]) ** 2, axis=1)))
    inner = np.roll(inner, -roll, axis=0)
    mid = 0.5 * (outer + inner)
    # fatten the ribbon about its own centreline (keeps Spa's true shape)
    outer = mid + (outer - mid) * WIDTH_EXAG
    inner = mid + (inner - mid) * WIDTH_EXAG
    d2 = ((mid[:, None, :] - rl[None, :, :]) ** 2).sum(-1)        # (ROAD_N, Nrl)
    road_elev = rl_elev[np.argmin(d2, axis=1)]                    # metres, per section

    # ---- common horizontal transform (centre + scale to TARGET_SIZE)
    allxy = np.vstack([outer, inner, rl])
    cx, cy = allxy[:, 0].mean(), allxy[:, 1].mean()
    S = TARGET_SIZE / max(np.ptp(allxy[:, 0]), np.ptp(allxy[:, 1]))
    zk = S * Z_EXAG
    def X(a): return (a - cx) * S
    def Y(a): return (a - cy) * S

    # ---- road ribbon mesh
    verts, faces = [], []
    for i in range(ROAD_N):
        z = road_elev[i] * zk
        verts.append((X(outer[i, 0]), Y(outer[i, 1]), z))
        verts.append((X(inner[i, 0]), Y(inner[i, 1]), z))
    for i in range(ROAD_N):
        a = 2 * i; b = 2 * ((i + 1) % ROAD_N)
        faces.append((a, a + 1, b + 1, b))
    me = bpy.data.meshes.new("F1ELEV_road")
    me.from_pydata(verts, [], faces)
    me.update()
    road = link(bpy.data.objects.new("F1ELEV_road", me))
    road.data.materials.append(_mat("F1ELEV_road_mat", (0.16, 0.16, 0.18, 1)))
    road.data.shade_smooth()

    # ---- racing line as a beveled poly curve (sits just above the road)
    cu = bpy.data.curves.new("F1ELEV_line", "CURVE")
    cu.dimensions = "3D"
    sp = cu.splines.new("POLY")
    sp.points.add(len(rl) - 1)
    for j, (px, py) in enumerate(rl):
        sp.points[j].co = (X(px), Y(py), rl_elev[j] * zk + LINE_LIFT, 1.0)
    sp.use_cyclic_u = True
    cu.bevel_depth = LINE_BEVEL
    line = link(bpy.data.objects.new("F1ELEV_line", cu))
    line.data.materials.append(_mat("F1ELEV_line_mat", (1.0, 0.35, 0.05, 1), emit=3.0))

    # ---- marker synced to the sim lap (distance vs time)
    rows = list(csv.DictReader(open(SIMCSV, encoding="utf-8")))
    dist = np.array([float(r["distance"]) for r in rows])
    tgt_arc = (dist / dist[-1]) * rl_total
    mx = np.interp(tgt_arc, rl_arc, rl[:, 0])
    my = np.interp(tgt_arc, rl_arc, rl[:, 1])
    mz = np.interp(tgt_arc, rl_arc, rl_elev)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=MARKER_R, segments=24, ring_count=16)
    marker = bpy.context.active_object
    marker.name = "F1ELEV_marker"
    for c in list(marker.users_collection):
        c.objects.unlink(marker)
    link(marker)
    marker.data.materials.append(_mat("F1ELEV_marker_mat", (1, 1, 1, 1), emit=6.0))
    scn = bpy.context.scene
    scn.render.fps = FPS
    scn.frame_start = 1
    scn.frame_end = len(rows)
    for f in range(len(rows)):
        marker.location = (X(mx[f]), Y(my[f]), mz[f] * zk + LINE_LIFT + MARKER_R)
        marker.keyframe_insert("location", frame=f + 1)
    for fc in marker.animation_data.action.fcurves:      # constant lap speed feel off? keep linear
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"

    # ---- peak-elevation flag (well-defined regardless of phase)
    pk = int(np.argmax(rl_elev))
    bpy.ops.object.empty_add(type="PLAIN_AXES", radius=1.5,
                             location=(X(rl[pk, 0]), Y(rl[pk, 1]), rl_elev[pk] * zk + 2.0))
    peak = bpy.context.active_object
    peak.name = "F1ELEV_peak"
    for c in list(peak.users_collection):
        c.objects.unlink(peak)
    link(peak)

    # ---- turntable camera
    if TURNTABLE:
        zmid = float(rl_elev.mean()) * zk
        bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, zmid))
        pivot = bpy.context.active_object
        pivot.name = "F1ELEV_pivot"
        for c in list(pivot.users_collection):
            c.objects.unlink(pivot)
        link(pivot)
        cam_data = bpy.data.cameras.new("F1ELEV_cam")
        cam = link(bpy.data.objects.new("F1ELEV_cam", cam_data))
        # low, oblique angle so the climbs/drops actually read as 3D
        cam.location = (0, -TARGET_SIZE * 1.35, TARGET_SIZE * 0.32)
        cam.parent = pivot
        con = cam.constraints.new("TRACK_TO")
        con.target = pivot
        con.track_axis = "TRACK_NEGATIVE_Z"
        con.up_axis = "UP_Y"
        pivot.rotation_euler = (0, 0, 0)
        pivot.keyframe_insert("rotation_euler", frame=scn.frame_start)
        pivot.rotation_euler = (0, 0, np.radians(360))
        pivot.keyframe_insert("rotation_euler", frame=scn.frame_end)
        if pivot.animation_data:
            for fc in pivot.animation_data.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"
        scn.camera = cam

    # ---- our own raking sun (slope shading), always added so the look is
    # consistent regardless of what's already in the scene
    sun_data = bpy.data.lights.new("F1ELEV_sun", "SUN")
    sun_data.energy = 3.5
    sun = link(bpy.data.objects.new("F1ELEV_sun", sun_data))
    sun.rotation_euler = (np.radians(52), 0, np.radians(35))

    print(f"[toy] road verts={len(verts)} faces={len(faces)}  line pts={len(rl)}  "
          f"marker frames={len(rows)}")
    print(f"[toy] elevation range (m, exaggerated x{Z_EXAG}): "
          f"{rl_elev.min():.1f}..{rl_elev.max():.1f}   z units: "
          f"{rl_elev.min()*zk:.2f}..{rl_elev.max()*zk:.2f}")
    print(f"[toy] KNOBS -> Z_EXAG={Z_EXAG}  PHASE_OFFSET={PHASE_OFFSET}  "
          f"(nudge PHASE_OFFSET to line up Eau Rouge)")


build()
