"""Top-down barbed-wire (concertina) security fence along both sides of the track, for raceline_video.py --fence.
Fence lines = the visual road edges offset AWAY from the road by `offset_m` (shapely buffer: no self-intersections
at tight corners). Drawn as razor-wire coil loops + a straight strand + posts, culled to the camera view."""
import cv2
import numpy as np

WIRE_COLOR = (165, 165, 165)   # BGR
STRAND_COLOR = (120, 120, 120)
POST_COLOR = (95, 95, 95)
LOOP_R_M, LOOP_STEP_M, POST_STEP_M, POST_R_M = 0.45, 0.32, 3.0, 0.18


def _resample(ring, step):
    p = np.asarray(ring, float); seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)]); n = max(int(s[-1] / step), 8); t = np.linspace(0, s[-1], n, endpoint=False)
    return np.column_stack([np.interp(t, s, p[:, 0]), np.interp(t, s, p[:, 1])])


def build(outer_visual, inner_visual, offset_m):
    from shapely.geometry import Polygon
    rings = []
    g_out = Polygon(outer_visual).buffer(offset_m, join_style="round")
    g_in = Polygon(inner_visual).buffer(-offset_m, join_style="round")
    for g in (g_out, g_in):
        for poly in getattr(g, "geoms", [g]):
            if not poly.is_empty and poly.exterior.length > 50: rings.append(np.asarray(poly.exterior.coords))
    return [dict(loops=_resample(r, LOOP_STEP_M), posts=_resample(r, POST_STEP_M)) for r in rings]


def draw(frame, fences, cam_x, cam_y, cam_scale, cam_y_frac):
    H, W = frame.shape[:2]; m = 40
    rl = max(1, int(round(LOOP_R_M * cam_scale))); rp = max(1, int(round(POST_R_M * cam_scale)))
    for f in fences:
        for key in ("loops", "posts"):
            P = f[key]
            sx = W / 2 + (P[:, 0] - cam_x) * cam_scale; sy = H * cam_y_frac - (P[:, 1] - cam_y) * cam_scale
            vis = (sx > -m) & (sx < W + m) & (sy > -m) & (sy < H + m)
            if not vis.any(): continue
            pts = np.column_stack([sx, sy])
            if key == "loops":
                # straight strand through the coil: draw contiguous visible runs as polylines
                idx = np.flatnonzero(vis); runs = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)
                for r in runs:
                    if len(r) > 1:
                        cv2.polylines(frame, [np.round(pts[r] * 4).astype(np.int32)], False, STRAND_COLOR, 1, cv2.LINE_AA, shift=2)
                for x, y in pts[vis]:
                    cv2.circle(frame, (int(round(x * 4)), int(round(y * 4))), rl * 4, WIRE_COLOR, 1, cv2.LINE_AA, shift=2)
            else:
                for x, y in pts[vis]:
                    cv2.circle(frame, (int(round(x * 4)), int(round(y * 4))), rp * 4, POST_COLOR, -1, cv2.LINE_AA, shift=2)
