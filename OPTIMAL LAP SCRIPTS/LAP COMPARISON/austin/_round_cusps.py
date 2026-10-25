"""Round a drawn kerb CUSP on one road edge with a fillet of radius R (FITTED geometry correction).

The Austin map SVG draws two corners (~3.69 km and ~4.20 km) so that the inside edge folds into a point
(edge radius ~4 m). The optimiser then bends the line hard to kiss that point = a visible 'forced push'.
Unlike cache/_outline_local_smooth.py this leaves the centreline, the other edge and the corner shape
alone: only the edge points within --half m of the corner move, onto the edge polygon rounded with
radius R (morphological opening/closing, whichever touches the cusp). Everything else is bit-identical.

  python _round_cusps.py IN.json OUT.json --edge inner --near X,Y --radius 14 --half 40 [--mirror-out M.json]
"""
import argparse, json
import numpy as np
from shapely.geometry import Polygon, Point

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("out")
ap.add_argument("--edge", default="inner", choices=["inner", "outer"])
ap.add_argument("--near", action="append", required=True, help="X,Y of a cusp (repeatable)")
ap.add_argument("--radius", type=float, default=14.0); ap.add_argument("--half", type=float, default=40.0)
ap.add_argument("--mirror-out", default=None, help="also write the x-mirrored outline (CCW tracks)")
a = ap.parse_args()

o = json.load(open(a.src))
E = np.asarray(o[a.edge], float)
poly = Polygon(E).buffer(0)
opened = poly.buffer(-a.radius, join_style=1).buffer(a.radius, join_style=1)
closed = poly.buffer(a.radius, join_style=1).buffer(-a.radius, join_style=1)
seg = np.linalg.norm(np.diff(np.vstack([E, E[0]]), axis=0), axis=1)
s = np.r_[0, np.cumsum(seg)][:-1]; L = seg.sum()
En = E.copy(); log = []
for nr in a.near:
    c = np.array([float(v) for v in nr.split(",")])
    j0 = int(np.argmin(np.linalg.norm(E - c, axis=1)))
    ds = (s - s[j0] + L / 2) % L - L / 2
    win = np.where(np.abs(ds) <= a.half)[0]
    # pick the rounded shape that actually moves the cusp
    mv = {nm: g.exterior.distance(Point(E[j0])) for nm, g in (("opening", opened), ("closing", closed))}
    nm = max(mv, key=mv.get); g = (opened if nm == "opening" else closed).exterior
    for i in win:
        En[i] = np.array(g.interpolate(g.project(Point(E[i]))).coords[0])
    log.append(f"cusp near {nr}: idx {j0}, {nm} R={a.radius} m, {len(win)} pts, max move "
               f"{np.linalg.norm(En[win] - E[win], axis=1).max():.2f} m")


def rmin(P, idx):
    a_, b_, c_ = np.roll(P, 2, 0), P, np.roll(P, -2, 0); ab, bc, ac = b_ - a_, c_ - b_, c_ - a_
    k = 2 * np.abs(ab[:, 0] * bc[:, 1] - ab[:, 1] * bc[:, 0]) / (
        np.linalg.norm(ab, axis=1) * np.linalg.norm(bc, axis=1) * np.linalg.norm(ac, axis=1) + 1e-12)
    return 1 / k[idx].max()


moved = np.where(np.linalg.norm(En - E, axis=1) > 1e-9)[0]
for line in log:
    print(line)
if len(moved):
    print(f"edge Rmin over moved points {rmin(E, moved):.1f} -> {rmin(En, moved):.1f} m")
o2 = dict(o); o2[a.edge] = En.tolist()
o2["round_cusps"] = dict(src=a.src, edge=a.edge, near=a.near, radius_m=a.radius, half_m=a.half)
json.dump(o2, open(a.out, "w"))
if a.mirror_out:
    m = dict(o2); m["inner"] = (np.asarray(o2["inner"]) * [-1.0, 1.0]).tolist()
    m["outer"] = (np.asarray(o2["outer"]) * [-1.0, 1.0]).tolist()
    json.dump(m, open(a.mirror_out, "w"))
