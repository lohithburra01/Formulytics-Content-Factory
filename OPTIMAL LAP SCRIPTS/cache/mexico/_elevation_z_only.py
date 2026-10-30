"""Mexico elevation from the OpenF1 altitude channel ONLY (z vs lap time; x/y never read).
Lap distance comes from the 2025 Q pole car data (time_s -> distance) of the same lap (NOR, drv 4).

  python cache/mexico/_elevation_z_only.py
"""
import json, os
import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
S = json.load(open(os.path.join(ROOT, "cache/mexico/path_samples.json")))
ref = pd.read_csv(os.path.join(ROOT, "F1_Pipeline_Assets/exports/reference_2025_mexico_q.csv"))
p = sorted([s for s in S if s["drv"] == 4], key=lambda s: s["t"])
t = np.array([s["t"] for s in p], float)
z = np.array([s["z"] for s in p], float) / 10.0                    # dm -> m above sea level
dist = np.interp(t, ref.time_s, ref.distance)
total = float(ref.distance.iloc[-1])
closure = float(z[-1] - z[0])
z_s = gaussian_filter1d(z - closure * dist / total, 2.0, mode="nearest")
frac = np.linspace(0.0, 1.0, 700, endpoint=False)
elev = np.interp(frac * total, dist, z_s)
span = float(elev.max() - elev.min())
print(f"[elev] {len(p)} z samples, alt {elev.min():.1f}..{elev.max():.1f} m, span {span:.1f} m, closure {closure:+.1f} m")
assert 1.0 <= span <= 150.0 and abs(closure) < 8.0, "validation failed"
rl = json.load(open(os.path.join(ROOT, "F1_Pipeline_Assets/tracks/mexico_city_grand_prix_raceline.json")))
pts = np.asarray(rl["raceline"], float)[:, :2]; arc = np.asarray(rl["arc_length"], float)
zi = np.interp((arc - arc[0]) / float(rl["track_length_m"]), frac, elev, period=1.0)
out = dict(track="mexico", source="openf1 location.z only (altitude), 2025 Q pole lap NOR; distance from car data",
           alt_min_m=round(float(elev.min()), 1), alt_max_m=round(float(elev.max()), 1), span_m=round(span, 1),
           dist_frac=frac.round(5).tolist(), elev_m=elev.round(2).tolist(),
           stations=np.column_stack([pts[:, 0], pts[:, 1], zi]).round(2).tolist())
dst = os.path.join(ROOT, "F1_Pipeline_Assets/tracks/mexico_city_grand_prix_elevation.json")
json.dump(out, open(dst, "w"))
print("[elev] wrote", dst)
