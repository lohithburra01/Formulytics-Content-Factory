"""Zoomed per-corner crops of a raceline on the outline, with lateral-position (0=inner,1=outer) annotation.
  python cache/bahrain/_corner_crops.py <outline> <raceline> <out.png>"""
import json, sys, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
o = json.load(open(sys.argv[1])); r = json.load(open(sys.argv[2]))
out, inn, rl = np.array(o["outer"]), np.array(o["inner"]), np.array(r["raceline"])
n = len(rl); st = 8; kap = np.zeros(n)
for i in range(n):
    p0, p1, p2 = rl[i - st], rl[i], rl[(i + st) % n]; u, v = p1 - p0, p2 - p1
    kap[i] = 2*(u[0]*v[1]-u[1]*v[0])/(np.linalg.norm(u)*np.linalg.norm(v)*np.linalg.norm(p2-p0))
arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(rl, axis=0), axis=1))]
order = np.argsort(-np.abs(kap)); peaks = []
for i in order:
    if abs(kap[i]) < 1/250: break
    if all(min(abs(arc[i]-arc[j]), arc[-1]-abs(arc[i]-arc[j])) > 120 for j in peaks): peaks.append(i)
peaks.sort(key=lambda i: arc[i])
c = int(np.ceil(len(peaks)/4)); fig, axs = plt.subplots(c, 4, figsize=(20, 5*c))
for ax, i in zip(axs.flat, peaks):
    p = rl[i]; W = 110
    for e, col in ((out, "tab:blue"), (inn, "tab:red")): ax.plot(e[:, 0], e[:, 1], col, lw=1)
    ax.plot(rl[:, 0], rl[:, 1], "g", lw=1.5)
    ax.set_xlim(p[0]-W, p[0]+W); ax.set_ylim(p[1]-W, p[1]+W); ax.set_aspect("equal")
    ax.set_title(f"arc {arc[i]:.0f} m  R {1/abs(kap[i]):.0f} m")
for ax in axs.flat[len(peaks):]: ax.axis("off")
plt.tight_layout(); plt.savefig(sys.argv[3], dpi=60); print(len(peaks), "corners")
