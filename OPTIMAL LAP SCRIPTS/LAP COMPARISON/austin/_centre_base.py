"""Optimiser base = smoothed ROAD CENTRELINE (well-conditioned normals, on-road by construction) + init knots that
reproduce a given line on it (signed offset of that line along the base normals, sampled at the knot stations).
  python _centre_base.py OUTLINE.json LINE_rl.json OUT_base.json OUT_knots.npy --sigma-m 14 --n 2704 --every 12"""
import argparse, json
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.spatial import cKDTree
from shapely.geometry import Polygon
import shapely
ap = argparse.ArgumentParser()
for x in ("outline", "line", "out_base", "out_knots"): ap.add_argument(x)
ap.add_argument("--sigma-m", type=float, default=14.0); ap.add_argument("--n", type=int, default=2704)
ap.add_argument("--every", type=int, default=12); a = ap.parse_args()
o = json.load(open(a.outline)); C = (np.array(o["inner"]) + np.array(o["outer"])) / 2
R = np.array(json.load(open(a.line))["raceline"], float)[:, :2]
seg = np.linalg.norm(np.diff(np.vstack([C, C[:1]]), axis=0), axis=1); s = np.r_[0, np.cumsum(seg)]; L = s[-1]
t = np.linspace(0, L, a.n, endpoint=False)
C = np.column_stack([np.interp(t, s, np.r_[C[:, i], C[0, i]]) for i in (0, 1)])
C = np.column_stack([gaussian_filter1d(C[:, i], a.sigma_m / (L / a.n), mode="wrap") for i in (0, 1)])
j = int(np.argmin(np.linalg.norm(C - R[0], axis=1))); C = np.roll(C, -j, 0)      # start at the line's S/F
if np.dot(C[5] - C[0], R[5] - R[0]) < 0: C = np.roll(C[::-1], 1, 0)             # same direction as the line
tg = np.roll(C, -1, 0) - np.roll(C, 1, 0); tg /= np.linalg.norm(tg, axis=1, keepdims=True)
N = np.column_stack([-tg[:, 1], tg[:, 0]])
_, nn = cKDTree(C).query(R)                       # line point -> nearest base station
off = np.full(len(C), np.nan)
for i in range(len(C)):
    m = np.where(nn == i)[0]
    if len(m): off[i] = np.median(np.einsum("ij,j->i", R[m] - C[i], N[i]))
ok = ~np.isnan(off); idx = np.arange(len(C))
off = np.interp(idx, idx[ok], off[ok], period=len(C))
k = off[np.arange(0, len(C), a.every)]
A, B = Polygon(o["outer"]), Polygon(o["inner"]); big, small = (A, B) if A.area > B.area else (B, A)
onroad = shapely.contains_xy(big.difference(small), C[:, 0], C[:, 1])
def rmin(X):
    a_, b_, c_ = np.roll(X, 3, 0), X, np.roll(X, -3, 0); ab, bc, ac = b_ - a_, c_ - b_, c_ - a_
    kk = 2 * np.abs(ab[:, 0] * bc[:, 1] - ab[:, 1] * bc[:, 0]) / (np.linalg.norm(ab, axis=1) * np.linalg.norm(bc, axis=1) * np.linalg.norm(ac, axis=1) + 1e-12)
    return 1 / kk.max()
print(f"base: L {L:.0f} m, {a.n} pts, Rmin {rmin(C):.1f} m, off-road pts {(~onroad).sum()}; init knots |off| max {np.abs(k).max():.2f} m")
json.dump({"raceline": C.tolist(), "note": f"road centreline, gaussian {a.sigma_m} m"}, open(a.out_base, "w")); np.save(a.out_knots, k)
