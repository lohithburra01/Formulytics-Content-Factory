"""Overlay sim speed trace vs a real reference lap (speed-vs-distance).

The sim S/F is a geometric proxy and the track may be reversed vs the real
driven direction, so we ALIGN first: resample both to a common lap-fraction
grid, then pick the orientation (forward/reversed) + circular shift that
maximises speed-profile cross-correlation. Only then do the corners line up."""
import csv, os, sys
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

def load(path):
    d, v = [], []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d.append(float(r["distance"])); v.append(float(r["speed"]))
    d = np.asarray(d); v = np.asarray(v)
    # ensure monotonic distance (real telem can have tiny non-monotonic blips)
    keep = np.concatenate([[True], np.diff(d) > 0])
    return d[keep], v[keep]

sim_path, real_path = sys.argv[1], sys.argv[2]
sim_lap = float(sys.argv[3]); real_lap = float(sys.argv[4]); real_drv = sys.argv[5]
ds, vs = load(sim_path)      # sim
dr, vr = load(real_path)     # real
Ls, Lr = ds[-1], dr[-1]

N = 1000
frac = np.linspace(0, 1, N, endpoint=False)
vs_g = np.interp(frac, ds / Ls, vs)          # sim on lap-fraction grid
vr_g = np.interp(frac, dr / Lr, vr)          # real on lap-fraction grid

def best_shift(a, b):
    """circular shift of b that best matches a; returns (shift, corr_peak)."""
    A = (a - a.mean()); B = (b - b.mean())
    cc = np.fft.irfft(np.fft.rfft(A) * np.conj(np.fft.rfft(B)), n=len(a))
    k = int(np.argmax(cc))
    return k, cc[k] / (np.linalg.norm(A) * np.linalg.norm(B) + 1e-9)

# try sim forward and reversed; align to the REAL trace
cands = {"forward": vs_g, "reversed": vs_g[::-1].copy()}
best = None
for name, cand in cands.items():
    k, peak = best_shift(vr_g, cand)
    if best is None or peak > best[2]:
        best = (name, k, peak, cand)
orient, shift, peak, cand = best
vs_al = np.roll(cand, shift)
print(f"alignment: sim orientation={orient}, circular shift={shift}/{N} "
      f"({shift/N*100:.1f}% of lap), corr peak={peak:.3f}")

x = frac * Lr   # show on real-lap distance scale (m)
fig, ax = plt.subplots(figsize=(16, 6.5))
ax.plot(x, vr_g, "-", lw=2.2, color="#d62728",
        label=f"REAL — {real_drv} {real_lap:.3f}s")
ax.plot(x, vs_al, "-", lw=2.2, color="#1f77b4",
        label=f"SIM 2026 optimal — {sim_lap:.3f}s")
ax.fill_between(x, vr_g, vs_al, where=vs_al >= vr_g, color="#1f77b4", alpha=0.12)
ax.fill_between(x, vr_g, vs_al, where=vs_al <  vr_g, color="#d62728", alpha=0.12)
ax.set_xlabel("lap distance (m)  [aligned by speed-trace cross-correlation]")
ax.set_ylabel("speed (km/h)")
ax.set_title(f"Circuit de Barcelona-Catalunya — sim 2026 optimal vs {real_drv}")
ax.grid(alpha=0.3); ax.legend(loc="lower center", fontsize=9)
ax.set_ylim(40, 360)

# stats box
def stats(v): return f"top {v.max():.0f}  min {v.min():.0f}  mean {v.mean():.0f} km/h"
txt = (f"REAL:  {stats(vr_g)}   lap {real_lap:.2f}s\n"
       f"SIM :  {stats(vs_al)}   lap {sim_lap:.2f}s\n"
       f"(optimal lap, calibrated to real-2026 patterns; grip <= real)")
ax.text(0.012, 0.97, txt, transform=ax.transAxes, va="top", fontsize=9,
        family="monospace", bbox=dict(boxstyle="round", fc="white", alpha=0.85))

out = os.path.abspath(os.path.join(os.path.dirname(__file__), "_overlay_catalunya_speed.png"))
fig.savefig(out, dpi=95, bbox_inches="tight")
print(f"wrote {out}")
print(f"REAL: top={vr_g.max():.0f} min={vr_g.min():.0f} mean={vr_g.mean():.0f}")
print(f"SIM : top={vs_al.max():.0f} min={vs_al.min():.0f} mean={vs_al.mean():.0f}")
