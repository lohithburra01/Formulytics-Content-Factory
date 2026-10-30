"""Braking / acceleration per corner: sim vs a reference speed trace (speed only).

  python cache/mexico/_brake_compare.py <sim.csv> [ref.csv] [max_frac]

Each ref corner (local min after a >= 40 km/h drop) is paired with the sim min within +-4% lap fraction.
Per corner: entry speed, brake length (m from entry peak to min), mean decel km/h/s over the drop,
min speed, exit gain km/h/s over the first 2 s after the min.
"""
import os, sys
import numpy as np
import pandas as pd
from scipy.signal import find_peaks

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sim = pd.read_csv(sys.argv[1])
ref = pd.read_csv(sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "-" else
                  os.path.join(ROOT, "F1_Pipeline_Assets/exports/reference_2025_mexico_q.csv"))
max_frac = float(sys.argv[3]) if len(sys.argv) > 3 else 0.8


def corners(df):
    v, d, t = df.speed.to_numpy(float), df.distance.to_numpy(float), df.time_s.to_numpy(float)
    f = d / d[-1]
    mins, _ = find_peaks(-v, prominence=25)
    out = []
    for m in mins:
        j = m
        b = df.brake.to_numpy(float)
        while j > 0 and v[j - 1] >= v[j]:         # walk back to the entry peak
            j -= 1
        on = np.where(b[j:m + 1] > 0)[0]           # then forward to brake-on
        j = j + int(on[0]) if len(on) else j
        if v[j] - v[m] < 40:
            continue
        k = m
        while k + 1 < len(v) and t[k + 1] - t[m] <= 2.0:
            k += 1
        out.append(dict(frac=f[m], v_entry=v[j], v_min=v[m], brake_m=d[m] - d[j],
                        decel=(v[j] - v[m]) / max(t[m] - t[j], 1e-3),
                        exit_gain=(v[k] - v[m]) / max(t[k] - t[m], 1e-3)))
    return out


R, S = corners(ref), corners(sim)
rows = []
for r in R:
    if r["frac"] >= max_frac:
        continue
    c = [s for s in S if abs(s["frac"] - r["frac"]) < 0.04]
    if not c:
        continue
    s = min(c, key=lambda s: abs(s["frac"] - r["frac"]))
    rows.append(dict(at_m=round(r["frac"] * 4304), ref_entry=r["v_entry"], sim_entry=s["v_entry"],
                     ref_min=r["v_min"], sim_min=s["v_min"],
                     ref_brake_m=round(r["brake_m"]), sim_brake_m=round(s["brake_m"]),
                     ref_decel=round(r["decel"], 1), sim_decel=round(s["decel"], 1),
                     ref_exit=round(r["exit_gain"], 1), sim_exit=round(s["exit_gain"], 1)))
df = pd.DataFrame(rows).round(1)
pd.set_option("display.width", 220)
print(df.to_string(index=False))
if len(df):
    print(f"\nmedian decel ratio sim/ref {np.median(df.sim_decel / df.ref_decel):.2f}   "
          f"median exit-gain ratio {np.median(df.sim_exit / df.ref_exit):.2f}   "
          f"median min-speed diff {np.median(df.sim_min - df.ref_min):+.1f} km/h")
