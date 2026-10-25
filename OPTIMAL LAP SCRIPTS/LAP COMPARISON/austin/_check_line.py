"""Check the new Austin lapcomp line vs the old sandbox line: curvature spikes + zoomed plots at the two kerb cusps.
  python _check_line.py NEW_rl.json(mirror frame) OUT.png"""
import json, sys
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

ROOT = "D:/f1_hot_lap/OPTIMAL LAP SCRIPTS/"
OLD = "D:/f1_hot_lap/OPTIMAL LAP SCRIPTS_sandbox/runs/austin_2026/svg_line/raceline_sf.json"
OLD_OUT = "D:/f1_hot_lap/OPTIMAL LAP SCRIPTS_sandbox/runs/austin_2026/svg_line/outline.json"
NEW_OUT = ROOT + "F1_Pipeline_Assets/tracks/united_states_grand_prix_lapcomp_outline.json"
SPOTS = [614, 3692, 4196, 5218]


def curv(P, ds=2.0):
    d = np.diff(np.vstack([P, P[:1]]), axis=0); s = np.r_[0, np.cumsum(np.hypot(*d.T))]; L = s[-1]
    t = np.arange(0, L, ds)
    Q = np.c_[np.interp(t, s, np.r_[P[:, 0], P[0, 0]]), np.interp(t, s, np.r_[P[:, 1], P[0, 1]])]
    a = np.roll(Q, -1, 0) - Q; b = Q - np.roll(Q, 1, 0)
    ang = (np.arctan2(a[:, 1], a[:, 0]) - np.arctan2(b[:, 1], b[:, 0]) + np.pi) % (2 * np.pi) - np.pi
    k = np.abs(ang / ds)
    w = 21; ks = np.convolve(np.r_[k[-w:], k, k[:w]], np.ones(w) / w, "same")[w:-w]
    return t, k, ks, Q


old = np.array(json.load(open(OLD))["raceline"], float)
new = np.array(json.load(open(sys.argv[1]))["raceline"], float) * [-1.0, 1.0]
res = {}
for nm, P in (("old", old), ("new", new)):
    t, k, ks, Q = curv(P); res[nm] = (t, k, ks, Q)
    print(f"{nm}: L {t[-1]:.0f} m, |k|max {k.max():.4f} (R {1/k.max():.1f} m), spike (k - 40m avg) max {np.max(k-ks):.4f}")
    for s in SPOTS:
        m = np.abs(t - s) < 40
        print(f"   {s} m: Rmin {1/k[m].max():5.1f} m, spike {np.max((k-ks)[m]):.4f}")

oo, no = json.load(open(OLD_OUT)), json.load(open(NEW_OUT))
fig = plt.figure(figsize=(16, 9))
for j, s in enumerate(SPOTS):
    ax = fig.add_subplot(2, 4, j + 1)
    c = res["old"][3][int(s / 2)]
    for o, st in ((oo, "k:"), (no, "k-")):
        ax.plot(*np.array(o["inner"]).T, st, lw=1); ax.plot(*np.array(o["outer"]).T, st, lw=1)
    ax.plot(*old.T, "r", lw=1.4, label="old (sandbox)"); ax.plot(*new.T, "b", lw=1.4, label="new")
    ax.set_xlim(c[0] - 75, c[0] + 75); ax.set_ylim(c[1] - 75, c[1] + 75); ax.set_aspect("equal")
    ax.set_title(f"{s} m"); ax.set_xticks([]); ax.set_yticks([])
    if j == 0: ax.legend(fontsize=8)
ax = fig.add_subplot(2, 1, 2)
for nm, col in (("old", "r"), ("new", "b")):
    t, k, ks, Q = res[nm]; ax.plot(t, 1000 * k, col, lw=0.9, label=f"{nm} line")
for s in SPOTS: ax.axvline(s, color="grey", lw=0.5, ls="--")
ax.set_xlabel("lap distance [m]"); ax.set_ylabel("curvature [1/km]  (100 = 10 m radius)"); ax.legend()
plt.tight_layout(); plt.savefig(sys.argv[2], dpi=75)
