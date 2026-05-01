"""
extract_track_outline.py

Paste this whole file into Blender's Scripting tab and click Run.
The mesh object MUST be named exactly: Track

Output: <blendfile_dir>/<blendfile_name>_outline.json
        { "outer": [[x,y], ...], "inner": [[x,y], ...] }

Strategy:
  1. Weld duplicate verts (handles unwelded meshes that produce spurious loops).
  2. Walk boundary edges into closed loops.
  3. Print *every* loop with perimeter + bbox area.
  4. Pick the two loops with the largest bounding-box AREA — that's the
     true outer and inner edge of the track ribbon, even when there are
     many small spurious loops.
"""

import bpy
import bmesh
import json
import os
from mathutils import Vector


TRACK_OBJ_NAME = "Track"
WELD_DISTANCE = 0.001
MIN_LOOP_VERTS = 8


def extract_outline():
    obj = bpy.data.objects.get(TRACK_OBJ_NAME)
    if obj is None:
        raise RuntimeError(f"No object named '{TRACK_OBJ_NAME}' in scene.")
    if obj.type != 'MESH':
        raise RuntimeError(f"'{TRACK_OBJ_NAME}' is not a mesh (type={obj.type}).")

    mw = obj.matrix_world

    bm = bmesh.new()
    bm.from_mesh(obj.data)

    n_verts_pre = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=WELD_DISTANCE)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    n_verts_post = len(bm.verts)
    print(f"[outline] welded: {n_verts_pre} → {n_verts_post} verts")

    boundary_edges = [e for e in bm.edges if len(e.link_faces) == 1]
    if not boundary_edges:
        bm.free()
        raise RuntimeError("No boundary edges found.")

    print(f"[outline] {len(boundary_edges)} boundary edges")

    vert_to_edges = {}
    for e in boundary_edges:
        for v in e.verts:
            vert_to_edges.setdefault(v.index, []).append(e)

    visited_edges = set()
    loops = []

    for start_edge in boundary_edges:
        if start_edge.index in visited_edges:
            continue

        loop_verts = []
        current_edge = start_edge
        current_vert = current_edge.verts[0]
        loop_verts.append(current_vert)

        while True:
            visited_edges.add(current_edge.index)
            next_vert = current_edge.other_vert(current_vert)
            if next_vert is None:
                break

            if next_vert == loop_verts[0] and len(loop_verts) > 2:
                break

            loop_verts.append(next_vert)

            candidates = [
                e for e in vert_to_edges.get(next_vert.index, [])
                if e.index != current_edge.index and e.index not in visited_edges
            ]
            if not candidates:
                break
            current_edge = candidates[0]
            current_vert = next_vert

        if len(loop_verts) >= MIN_LOOP_VERTS:
            loops.append(loop_verts)

    if len(loops) < 2:
        bm.free()
        raise RuntimeError(
            f"Found only {len(loops)} closed boundary loop(s). "
            "Need at least 2 (outer + inner of the track ribbon)."
        )

    def loop_xy(loop):
        return [(float((mw @ v.co).x), float((mw @ v.co).y)) for v in loop]

    def perim_xy(xy):
        total = 0.0
        for i in range(len(xy)):
            ax, ay = xy[i]
            bx, by = xy[(i + 1) % len(xy)]
            total += ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
        return total

    def bbox_area_xy(xy):
        xs = [p[0] for p in xy]
        ys = [p[1] for p in xy]
        return (max(xs) - min(xs)) * (max(ys) - min(ys)), (min(xs), max(xs), min(ys), max(ys))

    loop_xys = [loop_xy(L) for L in loops]
    loop_data = []
    for k, xy in enumerate(loop_xys):
        p = perim_xy(xy)
        a, bb = bbox_area_xy(xy)
        loop_data.append({"idx": k, "verts": len(xy), "perim": p, "bbox_area": a, "bbox": bb, "xy": xy})

    loop_data.sort(key=lambda d: d["bbox_area"], reverse=True)

    print("[outline] all loops by bbox area:")
    for k, d in enumerate(loop_data[:20]):
        bb = d["bbox"]
        print(f"  rank {k:2d}: verts={d['verts']:5d}  perim={d['perim']:8.1f}  "
              f"bbox_area={d['bbox_area']:10.0f}  "
              f"x=[{bb[0]:.0f},{bb[1]:.0f}] y=[{bb[2]:.0f},{bb[3]:.0f}]")

    outer = loop_data[0]
    inner = loop_data[1]

    bm.free()

    return outer["xy"], inner["xy"], outer["perim"], inner["perim"]


def main():
    outer, inner, p_outer, p_inner = extract_outline()

    blend_path = bpy.data.filepath
    if blend_path:
        blend_dir = os.path.dirname(blend_path)
        blend_stem = os.path.splitext(os.path.basename(blend_path))[0]
    else:
        blend_dir = os.path.expanduser("~")
        blend_stem = "untitled"
        print("[outline] Warning: .blend not saved; writing to home dir.")

    out_path = os.path.join(blend_dir, f"{blend_stem}_outline.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"outer": [list(p) for p in outer], "inner": [list(p) for p in inner]}, f)

    print("=" * 60)
    print(f"  outer: {len(outer)} pts, perimeter {p_outer:.1f}")
    print(f"  inner: {len(inner)} pts, perimeter {p_inner:.1f}")
    print(f"  → {out_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
