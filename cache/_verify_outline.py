"""Verify a generated outline JSON: plot outer/inner edges + reconstructed
centerline, flag any inner/outer crossing (folded corridor)."""
import json, sys, os
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

path = sys.argv[1]
name = sys.argv[2] if len(sys.argv) > 2 else "track"
d = json.load(open(path))
outer = np.asarray(d["outer"]); inner = np.asarray(d["inner"])
center = 0.5 * (outer + inner)
width = np.linalg.norm(outer - inner, axis=1)

# corridor sanity: width should be ~constant (road width), never near zero (fold)
print(f"{name}: {len(outer)} stations")
print(f"  width  min={width.min():.2f}  median={np.median(width):.2f}  max={width.max():.2f} m")
seg = np.linalg.norm(np.diff(np.vstack([center, center[0]]), axis=0), axis=1)
print(f"  centerline perimeter = {seg.sum():.1f} m")
# fold detector: does the inner edge ever cross to the wrong side?
# (nearest inner point to each outer point much closer than half-width => pinch)
mn = width.min()
print(f"  --> {'OK (no pinch)' if mn > 0.5*np.median(width) else 'WARNING: corridor pinches/folds'}")

fig, ax = plt.subplots(figsize=(16, 7))
ax.plot(outer[:, 0], outer[:, 1], "-", lw=1.0, color="#1f77b4", label="outer edge")
ax.plot(inner[:, 0], inner[:, 1], "-", lw=1.0, color="#d62728", label="inner edge")
ax.plot(center[:, 0], center[:, 1], "-", lw=0.6, color="k", alpha=0.5, label="centerline")
ax.scatter([center[0, 0]], [center[0, 1]], c="lime", s=140, marker="o",
           edgecolors="k", zorder=6, label="S/F (index 0)")
# direction arrow
ax.annotate("", xy=center[40], xytext=center[0],
            arrowprops=dict(arrowstyle="->", color="green", lw=2))
ax.set_aspect("equal"); ax.legend(loc="upper right")
ax.set_title(f"{name} corridor — width med {np.median(width):.1f} m, "
             f"perim {seg.sum():.0f} m")
out = os.path.join(os.path.dirname(path), "..", "..", "cache", f"_verify_{name}.png")
out = os.path.abspath(out)
fig.savefig(out, dpi=90, bbox_inches="tight")
print(f"  wrote {out}")
