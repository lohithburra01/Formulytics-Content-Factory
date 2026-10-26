"""SPIKE v5: v4 physics, drawn in the SAME style as spikes/pterasoftware/pterasoftware_f1_wings.png
(white background, wake vortex points as viridis dots, red wing panels, top view + side view)."""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import hairpin_v4 as v4

v4.OUT = Path(__file__).parent / "out_v5"
ZOOM = 6.0
_first = [None]


def draw(f, P, c0, h, V, nodes, birth, tf, log):
    if _first[0] is None: _first[0] = f
    fig, (a, b) = plt.subplots(2, 1, figsize=(10, 12.5), gridspec_kw={"height_ratios": [3.2, 1]})
    c, s_ = np.cos(h), np.sin(h)
    a.plot(P[:, 0] - c0[0], P[:, 1] - c0[1], color="#e6e6e6", lw=12 * (0.8 * 10 * 100 / (2 * ZOOM)) * 72 / 100, solid_capstyle="round", zorder=0)
    a.plot(P[:, 0] - c0[0], P[:, 1] - c0[1], color="#bbbbbb", lw=0.8, ls="--", zorder=1)
    for wi, rows in enumerate(nodes):
        if not rows.size: continue
        xy = rows[..., :2] - np.array(c0)
        along = -((xy[..., 0]) * c + (xy[..., 1]) * s_)            # distance behind the car (for colour, as in the original)
        a.scatter(xy[..., 0].ravel(), xy[..., 1].ravel(), s=4, c=along.ravel(), cmap="viridis", vmin=-3, vmax=10, linewidths=0, zorder=3)
        b.scatter(along.ravel(), rows[..., 2].ravel(), s=4, c=along.ravel(), cmap="viridis", vmin=-3, vmax=10, linewidths=0, zorder=3)
    car = v4.CAR
    a.plot(np.r_[car[:, 0], car[:1, 0]] * c - np.r_[car[:, 1], car[:1, 1]] * s_,
           np.r_[car[:, 0], car[:1, 0]] * s_ + np.r_[car[:, 1], car[:1, 1]] * c, color="k", lw=0.8, zorder=4)
    for name, x, half, chord, z, pitch in v4.WINGS:             # wing panels as red dots, like the original
        xs, ys = np.meshgrid(np.linspace(x - chord, x, 6), np.linspace(-half, half, 13))
        a.scatter(xs * c - ys * s_, xs * s_ + ys * c, s=6, c="red", zorder=5, label="wing panels" if name == "front" else None)
        b.scatter(-np.linspace(x - chord, x, 6), np.full(6, z), s=6, c="red", zorder=5)
    a.scatter([], [], s=4, c="#3b528b", label="wake vortex points")
    a.set_xlim(-ZOOM, ZOOM); a.set_ylim(-ZOOM, ZOOM); a.set_aspect("equal")
    a.set_title(f"TOP VIEW (north up)  {V * 3.6:.0f} km/h   front wing {log[-1][2]:.0f} N   rear wing {log[-1][3]:.0f} N")
    a.legend(loc="upper right", fontsize=8)
    b.axhline(0, color="k", lw=2); b.text(-3.8, 0.04, "ground", fontsize=8)
    b.set_xlim(-4, 12); b.set_ylim(-0.1, 2.2); b.set_aspect("equal")
    b.set_title("SIDE VIEW (distance behind the car, height above ground)"); b.set_xlabel("m behind car centre")
    fig.tight_layout()
    fig.savefig(v4.OUT / f"f_{f - _first[0]:04d}.png", dpi=100); plt.close(fig)


v4.draw = draw
if __name__ == "__main__":
    v4.main()
