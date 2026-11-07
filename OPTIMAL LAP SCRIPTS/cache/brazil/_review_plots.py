"""Sao Paulo 2026 review pictures (before any render):
  1. line.svg / line.png  - racing line on the SVG road, edges, 100 m ticks, corner numbers, off-track points in red
  2. speed.png            - sim 2026 speed vs 2025 Q pole (NOR 1:09.511) + predicted 2026 corner targets

  python cache/brazil/_review_plots.py <sim.csv> <raceline.json> <tag>
"""
import json, os, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "cache", "brazil")
sim_csv, rl_json, tag = sys.argv[1], sys.argv[2], sys.argv[3]

O = json.load(open(os.path.join(ROOT, "F1_Pipeline_Assets/tracks/sao_paulo_grand_prix_mirror_outline.json")))
outer, inner = np.asarray(O["outer"], float), np.asarray(O["inner"], float)
R = np.asarray(json.load(open(rl_json))["raceline"], float)[:, :2]
# sim runs on the x-mirrored outline (anticlockwise track); flip everything back for display
MX = np.array([-1.0, 1.0]); outer, inner, R = outer * MX, inner * MX, R * MX
sim = pd.read_csv(sim_csv)
ref = pd.read_csv(os.path.join(ROOT, "F1_Pipeline_Assets/exports/reference_2025_brazil_q.csv"))
pred = json.load(open(os.path.join(ROOT, "cache/predicted_brazil.json")))

# ---- off-track check: line point must lie inside outer and outside inner
po, pi = Path(outer), Path(inner)
inside = po.contains_points(R) & ~pi.contains_points(R)
if inside.mean() < 0.5:          # inner/outer naming flipped
    inside = pi.contains_points(R) & ~po.contains_points(R)
off = ~inside
s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(R, axis=0), axis=1))]

# ---- 1. line picture
fig, ax = plt.subplots(figsize=(24, 17))
road = np.vstack([outer, outer[:1]]); hole = np.vstack([inner, inner[:1]])
ax.fill(road[:, 0], road[:, 1], color="#d9d9d9", zorder=0)
ax.fill(hole[:, 0], hole[:, 1], color="white", zorder=1)
for E in (road, hole):
    ax.plot(E[:, 0], E[:, 1], color="#333", lw=0.8, zorder=2)
ax.plot(np.r_[R[:, 0], R[0, 0]], np.r_[R[:, 1], R[0, 1]], color="#d62728", lw=1.2, zorder=3,
        label="2026 optimal line (sim physics on your SVG)")
if off.any():
    ax.plot(R[off, 0], R[off, 1], "o", color="black", ms=3, zorder=4, label=f"OFF TRACK ({off.sum()} pts)")
for mm in range(100, int(s[-1]), 100):
    i = int(np.argmin(np.abs(s - mm)))
    big = mm % 500 == 0
    ax.plot(*R[i], ".", color="#1f77b4", ms=6 if big else 3, zorder=5)
    if big:
        ax.annotate(f"{mm} m", R[i], textcoords="offset points", xytext=(8, -12), fontsize=9, color="#1f77b4")
ax.plot(*R[0], "o", color="#2ca02c", ms=12, zorder=6, label="start/finish (lap distance 0)")
# corner speed labels at the predicted corner positions (sim min speed nearby)
L = float(sim.distance.iloc[-1])
for c in pred["corners"]:
    d = c["s_frac"] * L
    w = (sim.distance > d - 60) & (sim.distance < d + 60)
    j = sim.speed[w].idxmin(); dd = sim.distance[j]
    i = int(np.argmin(np.abs(s / s[-1] - dd / L)))
    ax.annotate(f"{sim.speed[j]:.0f} km/h", R[i], textcoords="offset points", xytext=(10, 10), fontsize=10,
                color="#7f0000", weight="bold", zorder=7)
ax.set_aspect("equal"); ax.axis("off"); ax.legend(loc="lower left", fontsize=11)
ax.set_title(f"Sao Paulo 2026 - racing line review ({tag})   lap {sim.time_s.iloc[-1]:.3f} s   "
             f"off-track {off.sum()}/{len(R)}", fontsize=14)
fig.savefig(os.path.join(OUT, f"line_{tag}.svg"), format="svg", bbox_inches="tight")
fig.savefig(os.path.join(OUT, f"line_{tag}.png"), dpi=200, bbox_inches="tight")
plt.close(fig)

# ---- 2. speed overlay, both on lap fraction (2025 integrated distance is GPS-free car data)
f_ref = ref.distance / ref.distance.iloc[-1]
f_sim = sim.distance / sim.distance.iloc[-1]
fig, (a1, a2) = plt.subplots(2, 1, figsize=(22, 10), sharex=True, gridspec_kw=dict(height_ratios=[3, 1]))
a1.plot(f_ref * 4309, ref.speed, color="#ff8000", lw=1.6, label=f"2025 Q pole NOR (real) {ref.time_s.iloc[-1]:.3f} s")
a1.plot(f_sim * 4309, sim.speed, color="#1f77b4", lw=1.6, label=f"2026 sim (this run) {sim.time_s.iloc[-1]:.3f} s")
for c in pred["corners"]:
    x = c.get("s_frac", 0) * 4309
    a1.plot(x, c["v26_target_kmh"], "v", color="black", ms=8)
a1.plot([], [], "v", color="black", label="predicted 2026 corner min (2025 x transfer)")
if "mode" in sim:
    sc = sim["mode"] == "SUPERCLIP"
    a1.fill_between(f_sim * 4309, 0, 400, where=sc, color="#9467bd", alpha=0.18, label="sim SUPERCLIP")
a1.set_ylim(50, 370); a1.set_ylabel("speed km/h"); a1.grid(alpha=0.3); a1.legend(loc="lower right", fontsize=10)
a1.set_title("Sao Paulo (Interlagos): 2026 sim vs 2025 qualifying pole (x = lap distance scaled to 4309 m)")
g = np.linspace(0, 1, 3000, endpoint=False)
dv = np.interp(g, f_sim, sim.speed) - np.interp(g, f_ref, ref.speed)
a2.plot(g * 4309, dv, color="#444", lw=1); a2.axhline(0, color="k", lw=0.6)
a2.set_ylabel("sim - 2025 km/h"); a2.set_xlabel("lap distance m"); a2.grid(alpha=0.3)
fig.savefig(os.path.join(OUT, f"speed_{tag}.png"), dpi=130, bbox_inches="tight")
print(f"[review] {tag}: lap {sim.time_s.iloc[-1]:.3f}  off-track {off.sum()}/{len(R)}  "
      f"vmax sim {sim.speed.max():.0f} / 2025 {ref.speed.max():.0f}  superclip pts {(sim.get('mode') == 'SUPERCLIP').sum()}")
