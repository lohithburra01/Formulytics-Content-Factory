"""Check HAM-2018 line vs the 2026 line on the REAL (un-mirrored) track: gaps, Rmin, off-track; plot."""
import json, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.path import Path
from scipy.spatial import cKDTree
T = "../../F1_Pipeline_Assets/tracks/"
o = json.load(open(T + "sao_paulo_grand_prix_outline.json")); out, inn = np.array(o["outer"]), np.array(o["inner"])
A = np.array(json.load(open("h18_real_rl.json"))["raceline"])[:, :2]
B = np.array(json.load(open(T + "sao_paulo_grand_prix_raceline.json"))["raceline"])[:, :2]
def rad(X, h=3):
    a, b, c = np.roll(X, h, 0), X, np.roll(X, -h, 0); ab, bc, ac = b - a, c - b, c - a
    k = 2 * np.abs(ab[:, 0] * bc[:, 1] - ab[:, 1] * bc[:, 0]) / (np.linalg.norm(ab, axis=1) * np.linalg.norm(bc, axis=1) * np.linalg.norm(ac, axis=1) + 1e-12)
    return 1 / np.maximum(k, 1e-9)
po, pi = Path(out), Path(inn); ins = po.contains_points(A) & ~pi.contains_points(A)
if ins.mean() < .5: ins = pi.contains_points(A) & ~po.contains_points(A)
g, _ = cKDTree(B).query(A); L = np.sum(np.linalg.norm(np.diff(A, axis=0), axis=1))
print(f"2018 line: len {L:.0f} m, Rmin {rad(A).min():.1f} m (2026 line {rad(B).min():.1f}), off-track {(~ins).sum()}, gap to 2026 line mean {g.mean():.2f} max {g.max():.2f} m")
fig, ax = plt.subplots(figsize=(24, 17))
ax.fill(*np.vstack([out, out[:1]]).T, color="#d9d9d9"); ax.fill(*np.vstack([inn, inn[:1]]).T, color="white")
ax.plot(*np.vstack([B, B[:1]]).T, color="#1f77b4", lw=1.0, label="2026 optimal line")
ax.plot(*np.vstack([A, A[:1]]).T, color="#d62728", lw=1.0, label="HAM 2018 car line (own optimiser line)")
if (~ins).any(): ax.plot(A[~ins, 0], A[~ins, 1], "ko", ms=3, label="off-track")
ax.set_aspect("equal"); ax.axis("off"); ax.legend(fontsize=13, loc="lower left")
ax.set_title(f"Interlagos: 2018 vs 2026 lines   gap mean {g.mean():.2f} m, max {g.max():.2f} m", fontsize=15)
fig.savefig("check_lines.png", dpi=170, bbox_inches="tight")
