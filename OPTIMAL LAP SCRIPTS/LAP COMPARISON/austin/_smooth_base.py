"""Smoothed optimiser base: the knot offsets are applied along the BASE normals, so a base that is tight
(R~8 m) at the hairpins pinches into a needle when the optimiser offsets it toward the apex. Gaussian-smooth
the line (wrap) so the normals are well conditioned; report Rmin and the on-road check.
  python _smooth_base.py IN_rl.json OUTLINE.json OUT_rl.json --sigma-m 12"""
import argparse, json
import numpy as np
from scipy.ndimage import gaussian_filter1d
from shapely.geometry import Polygon
import shapely
ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("outline"); ap.add_argument("out")
ap.add_argument("--sigma-m", type=float, default=12.0); a = ap.parse_args()
P = np.array(json.load(open(a.src))["raceline"], float)[:, :2]
ds = np.linalg.norm(np.diff(np.vstack([P, P[:1]]), axis=0), axis=1).mean()
Q = np.column_stack([gaussian_filter1d(P[:, i], a.sigma_m / ds, mode="wrap") for i in (0, 1)])
o = json.load(open(a.outline)); A, B = Polygon(o["outer"]), Polygon(o["inner"])
big, small = (A, B) if A.area > B.area else (B, A); road = big.difference(small)
def rmin(X):
    a_, b_, c_ = np.roll(X, 3, 0), X, np.roll(X, -3, 0); ab, bc, ac = b_ - a_, c_ - b_, c_ - a_
    k = 2 * np.abs(ab[:, 0] * bc[:, 1] - ab[:, 1] * bc[:, 0]) / (np.linalg.norm(ab, axis=1) * np.linalg.norm(bc, axis=1) * np.linalg.norm(ac, axis=1) + 1e-12)
    return 1 / k.max()
off = (~shapely.contains_xy(road, Q[:, 0], Q[:, 1])).sum()
print(f"sigma {a.sigma_m} m: Rmin {rmin(P):.1f} -> {rmin(Q):.1f} m, max move {np.linalg.norm(Q-P,axis=1).max():.2f} m, off-road pts {off}")
json.dump({"raceline": Q.tolist(), "note": f"gaussian sigma {a.sigma_m} m of {a.src}"}, open(a.out, "w"))
