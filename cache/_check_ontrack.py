"""On-track check: every raceline point must lie inside the corridor
(offset from centerline <= local half-width). Reports worst excursions and
plots the line on the corridor."""
import json, sys, os
import numpy as np
from scipy.spatial import cKDTree
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

outline = json.load(open(sys.argv[1]))
rl = json.load(open(sys.argv[2]))
name = sys.argv[3] if len(sys.argv) > 3 else "track"
outer = np.asarray(outline["outer"]); inner = np.asarray(outline["inner"])
center = 0.5 * (outer + inner)
halfw = 0.5 * np.linalg.norm(outer - inner, axis=1)
line = np.asarray(rl["raceline"])

tree = cKDTree(center)
dist, idx = tree.query(line, k=1)          # nearest centerline station to each line pt
# signed offset isn't needed; dist is the perpendicular-ish distance to centerline
local_half = halfw[idx]
over = dist - local_half                    # >0 => off track
TOL = 0.30                                   # 30 cm tolerance (resample/normal jitter)
n_off = int((over > TOL).sum())
print(f"{name}: {len(line)} raceline pts vs corridor")
print(f"  max offset from centerline = {dist.max():.2f} m  (local half-width {local_half.min():.2f}-{local_half.max():.2f} m)")
print(f"  worst excursion beyond edge = {over.max():.2f} m")
print(f"  points off-track (> {TOL} m beyond edge) = {n_off} / {len(line)}")
print(f"  --> {'ON-TRACK OK' if n_off == 0 else 'OFF-TRACK — investigate'}")

fig, ax = plt.subplots(figsize=(16, 7))
ax.plot(outer[:, 0], outer[:, 1], "-", lw=0.8, color="#1f77b4")
ax.plot(inner[:, 0], inner[:, 1], "-", lw=0.8, color="#d62728")
ax.plot(line[:, 0], line[:, 1], "-", lw=1.4, color="#2ca02c", label="racing line")
off_mask = over > TOL
if off_mask.any():
    ax.scatter(line[off_mask, 0], line[off_mask, 1], c="magenta", s=30,
               zorder=6, label=f"off-track ({n_off})")
ax.scatter([line[0, 0]], [line[0, 1]], c="lime", s=140, marker="o",
           edgecolors="k", zorder=7, label="S/F")
ax.set_aspect("equal"); ax.legend(loc="upper right")
ax.set_title(f"{name} racing line — worst excursion {over.max():.2f} m, off={n_off}")
out = os.path.abspath(os.path.join(os.path.dirname(__file__), f"_ontrack_{name}.png"))
fig.savefig(out, dpi=90, bbox_inches="tight")
print(f"  wrote {out}")
