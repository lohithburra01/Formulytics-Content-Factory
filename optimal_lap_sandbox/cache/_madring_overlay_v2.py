"""Overlay Madring v2 trials on the MEASURED distance axis vs the practice envelope.

usage: _madring_overlay_v2.py OUT.png TRIAL [TRIAL ...]   (trial names in cache/madring_calib_v2/)
Panels: full-lap speed, cumulative time delta vs the top-10 median, and a zoom
per requested window (--zoom a:b in metres, repeatable). New file only.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cache"))
from _madring_calib_v2 import DEST, GPS, project_s  # noqa: E402


def trial_on_axis(name, mpts, grid, Lm):
    meta = json.loads((DEST / f"{name}.json").read_text(encoding="utf-8"))
    st = np.load(DEST / f"{name}_stations.npz")
    line = json.loads(Path(meta["line"]).read_text(encoding="utf-8"))
    s_st = project_s(mpts, np.asarray(line["raceline"], float))
    return meta, np.interp(grid, s_st, st["v_ms"] * 3.6, period=Lm)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("trials", nargs="+")
    ap.add_argument("--zoom", action="append", default=[])
    a = ap.parse_args()
    out = Path(a.out)
    if out.exists():
        raise FileExistsError(out)
    meas = json.loads((GPS / "madring_gps_raceline.json").read_text(encoding="utf-8"))
    mpts, Lm = np.asarray(meas["raceline"], float), float(meas["track_length_m"])
    tr = np.load(GPS / "speed_traces.npz")
    grid, top10, p90 = tr["grid_s"], tr["top10"], tr["p90"]
    t_ref = np.cumsum(1.0 / np.maximum(top10 / 3.6, 1.0))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    zooms = [tuple(float(x) for x in z.split(":")) for z in a.zoom]
    fig, axes = plt.subplots(2 + len(zooms), 1, figsize=(16, 4.2 * (2 + len(zooms))))
    axes[0].plot(grid, p90, color="0.65", lw=1, label="push-lap p90")
    axes[0].plot(grid, top10, color="k", lw=1.2, label="top-10 laps median")
    for zi, (z0, z1) in enumerate(zooms):
        m = (grid >= z0) & (grid <= z1)
        axes[2 + zi].plot(grid[m], p90[m], color="0.65", lw=1)
        axes[2 + zi].plot(grid[m], top10[m], color="k", lw=1.2)
    for name in a.trials:
        meta, sv = trial_on_axis(name, mpts, grid, Lm)
        lab = f"{name} ({meta['lap_s']:.2f} s)"
        axes[0].plot(grid, sv, lw=0.9, label=lab)
        axes[1].plot(grid, np.cumsum(1.0 / np.maximum(sv / 3.6, 1.0)) - t_ref, lw=1, label=lab)
        for zi, (z0, z1) in enumerate(zooms):
            m = (grid >= z0) & (grid <= z1)
            axes[2 + zi].plot(grid[m], sv[m], lw=1)
    axes[0].set_ylabel("km/h")
    axes[0].legend(fontsize=8)
    axes[1].set_ylabel("cum. time vs top-10 (s)")
    axes[1].axhline(0, color="k", lw=0.6)
    axes[1].legend(fontsize=8)
    for ax in axes:
        ax.grid(alpha=.3)
    for zi, (z0, z1) in enumerate(zooms):
        axes[2 + zi].set_title(f"zoom {z0:.0f}-{z1:.0f} m", fontsize=9)
    axes[-1].set_xlabel("metres from the timing line (measured axis)")
    fig.tight_layout()
    fig.savefig(out, dpi=72)
    print("wrote", out)


if __name__ == "__main__":
    main()
