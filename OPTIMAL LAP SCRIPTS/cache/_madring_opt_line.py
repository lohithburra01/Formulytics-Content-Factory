"""Racing line optimised inside a corridor centred on the measured timing path.

The F1 timing position feed is map-matched onto one reference path (73 push
laps within 3 cm). Its large-scale shape is accurate (S/F within 8 m of the FP1
registration; overlays the SVG), but its corners are centreline-tight: the sim
driven directly on it is 12 s slow with every corner -11..-63 km/h
(cache/madring_calib_v2/gps_direct_default.json). So it is used as the
CENTRELINE: a symmetric --width corridor, then the sim's own build_raceline
(IQP seed + jerk-limited min-curvature QP, default wall-safe inset) -- the line
builder every shipped track used -- rolled so index 0 is the measured timing
line. New files only (exclusive create).
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import median_filter
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")
import sim_2026_lap as sim

GPS = ROOT / "cache/madring_gps_line"
DEST = ROOT / "cache/madring_opt_lines"


def normals(path):
    tan = np.roll(path, -1, 0) - np.roll(path, 1, 0)
    tan /= np.linalg.norm(tan, axis=1, keepdims=True)
    return np.column_stack([-tan[:, 1], tan[:, 0]])


def area(p):
    return 0.5 * float(np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1]))


def grip_radius_min(p):
    a, c = np.roll(p, 4, axis=0), np.roll(p, -4, axis=0)
    ab, bc, ac = p - a, c - p, c - a
    k = 2 * (ab[:, 0] * bc[:, 1] - ab[:, 1] * bc[:, 0]) / (
        np.linalg.norm(ab, axis=1) * np.linalg.norm(bc, axis=1) * np.linalg.norm(ac, axis=1))
    return float(1 / np.abs(median_filter(k, 5, mode="wrap")).max())


def main(a):
    DEST.mkdir(exist_ok=True)
    assert a.name.replace("_", "").isalnum(), "simple name required"
    outline_path = ROOT / f"F1_Pipeline_Assets/tracks/madring_grand_prix_outline_{a.name}.json"
    line_path = DEST / f"{a.name}_raceline.json"
    for p in (outline_path, line_path):
        if p.exists():
            raise FileExistsError(p)
    meas = json.loads((GPS / "madring_gps_raceline.json").read_text(encoding="utf-8"))
    c = np.asarray(meas["raceline"], float)  # SVG frame, driving direction, index 0 = timing line
    Lc = float(meas["track_length_m"])
    print(f"timing path: {len(c)} pts, {Lc:.1f} m, winding {'CW' if area(c) < 0 else 'CCW'}", flush=True)
    seg = np.linalg.norm(np.diff(np.vstack([c, c[:1]]), axis=0), axis=1)
    arc = np.r_[0.0, np.cumsum(seg)[:-1]]
    u = np.arange(2000) / 2000 * Lc
    cc = np.column_stack([np.interp(u, arc, c[:, j], period=Lc) for j in range(2)])
    nrm = normals(cc)
    left, right = cc + a.width / 2 * nrm, cc - a.width / 2 * nrm
    outer, inner = (left, right) if abs(area(left)) > abs(area(right)) else (right, left)
    if area(outer) < 0:  # svg_to_outline convention: CCW loops, index 0 kept at the timing line
        outer, inner = np.roll(outer[::-1], 1, axis=0), np.roll(inner[::-1], 1, axis=0)
    from shapely.geometry import LinearRing, Point, Polygon
    corridor = Polygon(outer, [inner])
    checks = dict(outer_simple=LinearRing(outer).is_simple, inner_simple=LinearRing(inner).is_simple,
                  valid=corridor.is_valid)
    print("outline", checks, flush=True)
    assert all(checks.values()), checks
    with outline_path.open("x", encoding="utf-8") as fh:
        json.dump(dict(outer=outer.tolist(), inner=inner.tolist(),
                       source=f"measured timing path (FP1+FP2 GPS, map-matched) as centreline, "
                              f"symmetric {a.width:g} m corridor"), fh)

    rl, _, kap, _ = sim.build_raceline(outer, inner, inset_m=a.inset)
    sf = int(cKDTree(rl).query(c[0])[1])
    rl, kap = np.roll(rl, -sf, axis=0), np.roll(kap, -sf)
    seg = np.linalg.norm(np.diff(np.vstack([rl, rl[:1]]), axis=0), axis=1)
    arc_r = np.r_[0.0, np.cumsum(seg)[:-1]]
    total = float(seg.sum())
    ahead = int(cKDTree(c).query(rl[50])[1])
    assert 0 < ahead < len(c) // 2, f"direction mismatch: station 50 maps to timing index {ahead}"
    band = corridor.buffer(0.30)
    outside = [i for i, p in enumerate(rl) if not band.contains(Point(p))]
    gap_sf = float(np.linalg.norm(rl[0] - c[0]))
    info = dict(stations=len(rl), length_m=total, length_vs_timing_path=total / Lc, sf_shift_idx=sf,
                sf_gap_m=gap_sf, min_grip_radius_m=grip_radius_min(rl), outside_0p3m=len(outside),
                corridor_width_m=a.width, inset_m=a.inset)
    print("line", json.dumps(info), flush=True)
    with line_path.open("x", encoding="utf-8") as fh:
        json.dump(dict(raceline=rl.tolist(), arc_length=arc_r.tolist(), kappa=kap.tolist(),
                       track_length_m=total, banking_deg=[], outline=str(outline_path), info=info,
                       source="sim_2026_lap.build_raceline in a corridor centred on the measured timing path; "
                              "index 0 = measured timing line"), fh)
    return 0 if not outside else 3


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--width", type=float, default=12.0)
    ap.add_argument("--inset", type=float, default=None, help="None = sim default (wall-safe)")
    raise SystemExit(main(ap.parse_args()))
