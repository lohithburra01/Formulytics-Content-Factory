import json, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.getcwd())
from weekend import pipeline as PL, simdoor

d = sys.argv[1]
pack = json.load(open("weekend/packs/austin_2026.json", encoding="utf-8"))
vals = PL.P(pack["values"]).sim_vals()
sim = simdoor.configure(vals)
rl = np.array(json.load(open(os.path.join(d, "raceline.json")))["raceline"]) * np.array([-1.0, 1.0])   # sim frame
v, t, arc, L, mode = simdoor.final_lap(sim, rl, vals, check=False)
r = pd.read_csv("F1_Pipeline_Assets/exports/reference_2026_austin_fp1.csv")
g = np.linspace(0, 1, 2000, endpoint=False)
vs = np.interp(g, (np.asarray(arc) - arc[0]) / L, np.asarray(v) * 3.6)
vr = np.interp(g, r.distance / r.distance.iloc[-1], r.speed)
best = []
for name, x in (("as drawn", vs), ("reversed", vs[::-1])):
    cs = [np.corrcoef(np.roll(x, -k), vr)[0, 1] for k in range(len(g))]
    k = int(np.argmax(cs)); best.append((cs[k], name, k))
    print(f"{name}: best corr {cs[k]:.3f} at start shift {k / len(g) * L:.0f} m")
print("lap", round(float(t[-1]), 2))
