"""How superclipping really looks in 2026 (real Q/FP1 speed traces, speed + throttle + brake only).

For every full-throttle straight >= 400 m in each reference_2026_*.csv, aligned on the brake point:
  - peak speed and where it happens (s before braking)
  - CLIP = the full-throttle tail after the car stops gaining (accel < 2 km/h/s): duration, start speed,
    speed lost by the brake point, mean rate (km/h/s)
Writes cache/mexico/superclip_study.csv + superclip_study.png (all straights overlaid, x = time to brake).
"""
import glob, os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "cache", "mexico")
rows = []
fig, ax = plt.subplots(1, 2, figsize=(22, 8))
for f in sorted(glob.glob(os.path.join(ROOT, "F1_Pipeline_Assets/exports/reference_2026_*.csv"))):
    name = os.path.basename(f)[15:-4]
    r = pd.read_csv(f)
    t, v, thr, brk, d = (r[c].to_numpy(float) for c in ("time_s", "speed", "throttle", "brake", "distance"))
    full = (thr >= 95) & (brk <= 0)
    i = 0
    while i < len(v):
        if not full[i]:
            i += 1; continue
        j = i
        while j + 1 < len(v) and full[j + 1]:
            j += 1
        if d[j] - d[i] >= 400 and j + 1 < len(v):       # straight that ends in a brake/lift
            tt, vv = t[i:j + 1], v[i:j + 1]
            # smooth accel over ~0.6 s
            k = max(1, int(round(0.6 / np.median(np.diff(tt)))))
            a = np.gradient(np.convolve(vv, np.ones(k) / k, mode="same"), tt)
            ipk = int(np.argmax(vv))
            gaining = np.where(a[: ipk + 1] >= 2.0)[0]
            ic = int(gaining[-1]) + 1 if len(gaining) else 0
            ic = min(ic, len(vv) - 1)
            dur = tt[-1] - tt[ic]
            rows.append(dict(track=name, straight_m=round(d[j] - d[i]), v_peak=vv.max(),
                             peak_before_brake_s=round(tt[-1] - tt[ipk], 2),
                             clip_start_v=vv[ic], clip_s=round(dur, 2), v_at_brake=vv[-1],
                             clip_loss_kmh=round(vv[ic:].max() - vv[-1], 1),
                             clip_rate_kmhps=round((vv[-1] - vv[ic]) / dur, 2) if dur > 0.3 else 0.0))
            x = tt - tt[-1]
            ax[0].plot(x, vv, lw=1, alpha=0.7)
            ax[1].plot(x, vv - vv[-1], lw=1, alpha=0.7)
        i = j + 1
df = pd.DataFrame(rows)
df.to_csv(os.path.join(OUT, "superclip_study.csv"), index=False)
for a, yl in zip(ax, ("speed km/h", "speed - speed at brake point km/h")):
    a.set_xlim(-14, 0.3); a.grid(alpha=0.3); a.set_xlabel("time to brake point s"); a.set_ylabel(yl)
ax[0].set_title("Real 2026 full-throttle straights (all tracks), aligned on braking")
ax[1].set_title("Same, relative to the brake-point speed: clipping = flat/falling tail")
fig.savefig(os.path.join(OUT, "superclip_study.png"), dpi=110, bbox_inches="tight")
pd.set_option("display.width", 200)
print(df.to_string(index=False))
long = df[df.straight_m >= 700]
print("\nstraights >= 700 m:", len(long))
print(long[["clip_s", "clip_loss_kmh", "clip_rate_kmhps", "peak_before_brake_s"]].describe().round(2).to_string())
