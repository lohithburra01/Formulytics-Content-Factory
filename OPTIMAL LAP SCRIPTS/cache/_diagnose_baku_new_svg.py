"""Measure non-adjacent road spacing in the replacement Baku SVG."""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
outline = json.loads((ROOT / "cache/baku_new_svg_outline_probe.json").read_text())
outer = np.asarray(outline["outer"])
inner = np.asarray(outline["inner"])
center = (outer + inner) / 2
n = len(center)
tree = cKDTree(center)
near = []
for i, p in enumerate(center):
    for j in tree.query_ball_point(p, 100):
        arc_delta = min((j - i) % n, (i - j) % n) * 3.0
        if j > i and arc_delta > 100:
            near.append((float(np.linalg.norm(p-center[j])), i, j))
near.sort()
print("closest distinct centerline passes (m, station i, station j):")
for row in near[:20]:
    print(row)
print("counts within 8 / 10 / 12 / 15 m:",
      [sum(d < limit for d, _, _ in near) for limit in (8, 10, 12, 15)])
fig, ax = plt.subplots(figsize=(15, 6))
ax.plot(center[:, 0], center[:, 1], c="#202020", lw=2)
ax.plot(outer[:, 0], outer[:, 1], c="#909090", lw=.5)
ax.plot(inner[:, 0], inner[:, 1], c="#909090", lw=.5)
for d, i, j in near[:1]:
    ax.plot([center[i,0],center[j,0]], [center[i,1],center[j,1]], c="red", lw=2)
    ax.annotate(f"{d:.1f}m / {i},{j}", center[i], color="red")
ax.axis("equal")
ax.set_title("New Baku SVG centerline and 10m probe road")
fig.tight_layout()
fig.savefig(ROOT / "cache/baku_new_svg_geometry.png", dpi=150)
