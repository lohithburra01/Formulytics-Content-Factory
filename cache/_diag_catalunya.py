"""Throwaway diagnostic: parse the Catalunya track path and visualise it so we
can tell centerline-vs-ribbon and check the geometry before running the pipeline."""
import re, sys, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from svg_to_outline import parse_svg_path_d, commands_to_polyline

SVG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "Formula1_Circuit_Catalunya_2021.svg")
text = open(SVG, encoding="utf-8").read()

# Grab EVERY d=, report each, and pick the longest polyline (the real track).
ds = re.findall(r'(?:^|\s)d\s*=\s*"([^"]+)"', text)
print(f"found {len(ds)} d= attributes")
best = None
for k, d in enumerate(ds):
    try:
        cmds = parse_svg_path_d(d)
        poly = np.asarray(commands_to_polyline(cmds), dtype=float)
    except Exception as e:
        print(f"  [{k}] parse FAILED: {e}  (head={d[:40]!r})")
        continue
    seg = np.linalg.norm(np.diff(poly, axis=0), axis=1).sum()
    print(f"  [{k}] npts={len(poly):5d}  raw_perimeter={seg:10.1f}  head={d[:30]!r}")
    # the real track has FAR more points than a clipPath rect/pattern; pick by npts
    if best is None or len(poly) > len(best[2]):
        best = (k, seg, poly)

idx, _, poly = best
print(f"\n--> using path index {idx}, {len(poly)} points")

# flip y to math-up
poly = poly.copy(); poly[:, 1] = -poly[:, 1]

fig, ax = plt.subplots(figsize=(16, 7))
# colour by traversal order: a ribbon goes out one edge then back the other
c = np.arange(len(poly))
sc = ax.scatter(poly[:, 0], poly[:, 1], c=c, cmap="turbo", s=4)
ax.plot(poly[:, 0], poly[:, 1], "-", lw=0.3, color="k", alpha=0.3)
ax.scatter([poly[0, 0]], [poly[0, 1]], c="lime", s=120, marker="o",
           edgecolors="k", zorder=5, label="start (path point 0)")
ax.scatter([poly[len(poly)//2, 0]], [poly[len(poly)//2, 1]], c="red", s=120,
           marker="s", edgecolors="k", zorder=5, label="midpoint of path")
ax.set_aspect("equal"); ax.legend(); ax.set_title(f"Catalunya path[{idx}] — colour = traversal order")
fig.colorbar(sc, label="point index")
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_diag_catalunya.png")
fig.savefig(out, dpi=90, bbox_inches="tight")
print(f"wrote {out}")

# ribbon test: for each point, distance to the nearest NON-adjacent point.
# A ribbon has a tight bimodal nearest-neighbour (~track width); a centerline does not.
from scipy.spatial import cKDTree
tree = cKDTree(poly)
dists, idxs = tree.query(poly, k=8)
# nearest neighbour that is far in index order (>5% of path away) = opposite edge
N = len(poly)
opp = []
for i in range(N):
    for j, di in zip(idxs[i][1:], dists[i][1:]):
        if min(abs(i-j), N-abs(i-j)) > 0.05*N:
            opp.append(di); break
opp = np.array(opp) if opp else np.array([np.nan])
print(f"\nopposite-edge nearest-distance: median={np.nanmedian(opp):.2f} "
      f"p10={np.nanpercentile(opp,10):.2f} p90={np.nanpercentile(opp,90):.2f} (SVG units)")
print("If this median is small & consistent relative to track size => RIBBON (two edges).")
print("If large/variable (points only near their own neighbours) => CENTERLINE.")
