"""Fit GRIP_MAP so sim corner minima in the flagged sections hit the 2026 target trace
(2025 Q speed x transfer r(v)). Fixed approved line (--raceline-in), fixed car.

  python cache/mexico/_fit_grip_map.py
"""
import json, os, subprocess, sys
import numpy as np
import pandas as pd
from scipy.signal import find_peaks

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
C = os.path.join(ROOT, "cache", "mexico")
SECTIONS = [(0, 99999)]                           # whole lap, both ways (approved shape-fit method)
RL = os.path.join(ROOT, "cache", "autofit_mexico_rl.json")   # the line the user approved
ENV = dict(os.environ, ICE_DERATE="0.035", SUPERCLIP_MEASURED="1", MU_LONG="2.1")
tr = json.load(open(os.path.join(ROOT, "cache", "transfer_2026.json")))
ref = pd.read_csv(os.path.join(ROOT, "F1_Pipeline_Assets/exports/reference_2025_mexico_q.csv"))


def run(gmap, tag):
    env = dict(ENV, GRIP_MAP=";".join(f"{a:.0f}:{b:.0f}:{f:.4f}" for a, b, f in gmap)) if gmap else ENV
    csv = os.path.join(C, f"gm_{tag}.csv")
    cmd = [sys.executable, os.path.join(ROOT, "sim_2026_lap.py"),
           "--outline", os.path.join(ROOT, "F1_Pipeline_Assets/tracks/mexico_city_grand_prix_outline.json"),
           "--raceline-in", RL, "--raceline-out", os.path.join(C, f"gm_{tag}.json"), "--csv-out", csv,
           "--rho", "0.9824", "--cda", "0.75", "--cl", "4.6"]
    subprocess.run(cmd, env=env, cwd=ROOT, capture_output=True, text=True)
    return pd.read_csv(csv)


def target_trace(L):
    v25 = ref.speed.to_numpy(float)
    r = np.interp(v25, tr["knots_v25"], tr["r_knots"])
    return ref.distance.to_numpy(float) / ref.distance.iloc[-1] * L, v25 * r


gmap = None
for it in range(5):
    sim = run(gmap, f"it{it}")
    L = sim.distance.iloc[-1]
    xt, vt = target_trace(L)
    v, d = sim.speed.to_numpy(float), sim.distance.to_numpy(float)
    mins, _ = find_peaks(-v, prominence=8)
    rows = []
    for m in mins:
        if not any(a <= d[m] <= b for a, b in SECTIONS):
            continue
        w = (xt > d[m] - 50) & (xt < d[m] + 50)
        rows.append((d[m], v[m], vt[w].min()))
    print(f"it{it}: lap {sim.time_s.iloc[-1]:.3f}  " +
          "  ".join(f"{x:.0f}m {s:.0f}->{t:.0f}" for x, s, t in rows), flush=True)
    if all(abs(s - t) <= 4 for _, s, t in rows):
        break
    old = {round(a + 50): f for a, b, f in (gmap or [])}
    new = []
    for x, s, t in rows:
        key = min(old, key=lambda k: abs(k - x)) if old else None
        f0 = old[key] if key is not None and abs(key - x) < 30 else 1.0
        new.append((x - 50, x + 50, float(np.clip(f0 * t / s, 0.7, 1.6))))
    gmap = new
json.dump(dict(grip_map=gmap, csv=f"gm_it{it}.csv"), open(os.path.join(C, "grip_map_fit.json"), "w"), indent=1)
print("final GRIP_MAP", ";".join(f"{a:.0f}:{b:.0f}:{f:.4f}" for a, b, f in (gmap or [])))
