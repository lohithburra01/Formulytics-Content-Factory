"""THROWAWAY SKETCH (kinematics only, no aero solve): where wing-tip trails lie when the car corners.

Trails = positions the 4 wing tips passed through in the last TRAIL_S seconds (air at rest relative to the track,
so shed air stays where it was left). Compared with the WRONG idea: trails rigidly attached behind the car.
Speeds are a rough curvature-limited estimate, only to space the trail points realistically.
"""
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RL = sys.argv[1]
TRAIL_S = 1.2
TIPS = {"front L": (2.6, 0.9), "front R": (2.6, -0.9), "rear L": (-2.4, 0.5), "rear R": (-2.4, -0.5)}  # (ahead, left) m from car centre

P = np.asarray(json.load(open(RL))["raceline"], float)
seg = np.linalg.norm(np.diff(P, axis=0, append=P[:1]), axis=1)
s = np.concatenate([[0], np.cumsum(seg)])[:-1]
# resample every 0.5 m
L = s[-1] + seg[-1]
ss = np.arange(0, L, 0.5)
P = np.c_[np.interp(ss, s, P[:, 0], period=L), np.interp(ss, s, P[:, 1], period=L)]
d1 = (np.roll(P, -1, 0) - np.roll(P, 1, 0)) / 1.0
d2 = (np.roll(P, -1, 0) - 2 * P + np.roll(P, 1, 0)) / 0.25
k = (d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]) / np.maximum(np.linalg.norm(d1, axis=1) ** 3, 1e-9)
k = np.convolve(np.r_[k[-20:], k, k[:20]], np.ones(21) / 21, "same")[20:-20]
v = np.minimum(85.0, np.sqrt(4.0 * 9.81 / np.maximum(np.abs(k), 1e-6)))
for _ in range(2):                                     # accel 1 g / brake 5 g limits
    for i in range(1, len(v)): v[i] = min(v[i], np.sqrt(v[i - 1] ** 2 + 2 * 9.81 * 0.5))
    for i in range(len(v) - 2, -1, -1): v[i] = min(v[i], np.sqrt(v[i + 1] ** 2 + 2 * 5 * 9.81 * 0.5))
t = np.concatenate([[0], np.cumsum(0.5 / v[:-1])])
hdg = np.arctan2(d1[:, 1], d1[:, 0])

def tips_at(i):
    c, sn = np.cos(hdg[i]), np.sin(hdg[i])
    return {n: P[i] + a * np.array([c, sn]) + l * np.array([-sn, c]) for n, (a, l) in TIPS.items()}

ic = int(np.argmax(np.abs(k)))                          # tightest corner on the lap
moments = {}
for name, dt in [("entry", -1.2), ("apex", 0.0), ("exit", 1.4)]:
    moments[name] = int(np.argmin(np.abs(t - (t[ic] + dt))))

cols = {"front L": "#00d0ff", "front R": "#00d0ff", "rear L": "#ffb000", "rear R": "#ffb000"}
fig, ax = plt.subplots(2, 3, figsize=(16, 11), facecolor="#111")
R = 35
for col, (name, i) in enumerate(moments.items()):
    hist = np.where((t <= t[i]) & (t >= t[i] - TRAIL_S))[0]
    for row in range(2):
        a = ax[row, col]; a.set_facecolor("#2a2a2a")
        a.plot(P[:, 0] - P[i, 0], P[:, 1] - P[i, 1], color="#555", lw=60, solid_capstyle="round", zorder=1)   # track (approx width)
        a.plot(P[:, 0] - P[i, 0], P[:, 1] - P[i, 1], color="#888", lw=0.8, ls="--")                 # racing line
        if row == 0:   # physical: tips' past positions, fading with age
            for n in TIPS:
                pts = np.array([tips_at(j)[n] for j in hist]) - P[i]
                age = (t[i] - t[hist]) / TRAIL_S
                a.scatter(pts[:, 0], pts[:, 1], s=6, c=cols[n], alpha=np.clip(1 - age, 0.05, 1), zorder=4)
        else:          # wrong: rigid straight trails attached behind the car
            for n, (fa, fl) in TIPS.items():
                c, sn = np.cos(hdg[i]), np.sin(hdg[i])
                p0 = fa * np.array([c, sn]) + fl * np.array([-sn, c])
                back = -np.array([c, sn]) * v[i] * TRAIL_S
                a.plot([p0[0], p0[0] + back[0]], [p0[1], p0[1] + back[1]], color=cols[n], lw=1.5, zorder=4)
        c, sn = np.cos(hdg[i]), np.sin(hdg[i])
        body = np.array([[2.8, 0], [-2.6, 0.8], [-2.6, -0.8]])
        a.fill(body[:, 0] * c - body[:, 1] * sn, body[:, 0] * sn + body[:, 1] * c, color="red", zorder=5)
        a.set_xlim(-R, R); a.set_ylim(-R, R); a.set_aspect("equal"); a.set_xticks([]); a.set_yticks([])
        a.set_title(f"{name}: {v[i] * 3.6:.0f} km/h" + ("" if row == 0 else "  (WRONG)"), color="w")
ax[0, 0].set_ylabel("TRAILS STAY IN THE AIR\nwhere the tips passed", color="w", fontsize=12)
ax[1, 0].set_ylabel("WRONG: trails glued\nstraight behind the car", color="w", fontsize=12)
fig.suptitle(f"Austin, tightest corner - camera over the car, north up (car turns, track slides). Last {TRAIL_S} s of tip trails.\n"
             "Blue = front-wing tips, orange = rear-wing tips. Kinematic sketch: no aero solve yet (real trails also sink/spread slowly).",
             color="w")
fig.tight_layout()
fig.savefig("corner_sketch.png", dpi=100, facecolor="#111")
print("corner at s =", ss[ic], "m, R =", 1 / abs(k[ic]), "m; saved corner_sketch.png")
