"""Austin elevation the main-folder way (cache/_fetch_elevation.py): the OpenF1 location z (altitude) of one
clean 2025 Q lap (pole driver) vs lap distance -> closure detrend -> smooth -> lifted onto the final line.
Only the altitude is used; the line is the SVG physics line."""
import json, sys
import numpy as np
from scipy.ndimage import gaussian_filter1d

samples = json.load(open("cache/austin/path_samples.json"))
drv = json.load(open("cache/austin/fetch_facts.json"))["q2025"]["driver"]
p = sorted([s for s in samples if s["drv"] == drv], key=lambda s: s["t"])
xy = np.array([[s["x"], s["y"]] for s in p], float) / 10.0
z = np.array([s["z"] for s in p], float) / 10.0                 # dm -> m above sea level
dist = np.r_[0, np.cumsum(np.linalg.norm(np.diff(xy, axis=0), axis=1))]
total = dist[-1]
closure = float(z[-1] - z[0])
z_s = gaussian_filter1d(z - closure * dist / total, 2.0, mode="nearest")
frac = np.linspace(0.0, 1.0, 700, endpoint=False)
elev = np.interp(frac * total, dist, z_s)
span = float(elev.max() - elev.min())
print(f"[elev] {len(p)} samples, alt {elev.min():.1f}..{elev.max():.1f} m, span {span:.1f} m, closure {closure:+.1f} m, lap {total:.0f} m")
assert 2.0 <= span <= 150.0 and abs(closure) < 8.0, "validation failed"
rl = json.load(open(sys.argv[1]))
pts = np.asarray(rl["raceline"], float); arc = np.asarray(rl["arc_length"], float)
zi = np.interp((arc - arc[0]) / float(rl["track_length_m"]), frac, elev, period=1.0)
out = dict(track="austin", source=f"openf1 location.z, 2025 Q pole lap driver {drv} (altitude only)",
           alt_min_m=round(float(elev.min()), 1), alt_max_m=round(float(elev.max()), 1), span_m=round(span, 1),
           dist_frac=frac.round(5).tolist(), elev_m=elev.round(2).tolist(),
           stations=np.column_stack([pts[:, 0], pts[:, 1], zi]).round(2).tolist())
json.dump(out, open(sys.argv[2], "w"))
print("[elev] wrote", sys.argv[2], len(out["stations"]), "stations")
