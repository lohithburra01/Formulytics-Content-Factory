"""Lift the Baku simulated raceline with the official 2025 Q position z trace."""
import json
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--raceline", default="F1_Pipeline_Assets/tracks/azerbaijan_grand_prix_raceline.json")
parser.add_argument("--out", default="F1_Pipeline_Assets/tracks/azerbaijan_grand_prix_elevation.json")
args = parser.parse_args()
pos = pd.read_csv(ROOT / "cache/baku_2025_q_position.csv")
ref = pd.read_csv(ROOT / "F1_Pipeline_Assets/exports/reference_2025_baku_q.csv")
rl_path = ROOT / args.raceline
out = ROOT / args.out

time = pd.to_timedelta(pos["Time"]).dt.total_seconds().to_numpy()
z = pos["Z"].to_numpy(dtype=float) / 10.0  # timing archive uses decimetres
distance = np.interp(time, ref.time_s, ref.distance)
distance -= distance[0]
closure = float(z[-1] - z[0])
z -= closure * distance / distance[-1]
z = gaussian_filter1d(z, 2.0, mode="nearest")
frac = np.linspace(0, 1, 2000, endpoint=False)
elev = np.interp(frac, distance / distance[-1], z)
span = float(elev.max() - elev.min())
if not (2 <= span <= 150 and abs(closure) < 8):
    raise ValueError(f"elevation sanity failed: span={span:.1f}, closure={closure:.1f}")
with rl_path.open(encoding="utf-8") as f:
    rl = json.load(f)
points = np.asarray(rl["raceline"], dtype=float)
arc = np.asarray(rl["arc_length"], dtype=float)
height = np.interp(arc / float(rl["track_length_m"]), frac, elev, period=1.0)
stations = np.column_stack((points, height)).round(2).tolist()
payload = dict(track="baku", source="F1 official timing archive via FastF1, "
               "2025 Azerbaijan Q VER lap 22 position.z",
               alt_min_m=round(float(elev.min()), 1),
               alt_max_m=round(float(elev.max()), 1),
               span_m=round(span, 1),
               dist_frac=frac.round(5).tolist(),
               elev_m=elev.round(2).tolist(), stations=stations)
out.write_text(json.dumps(payload), encoding="utf-8")
print(f"elevation: {payload['alt_min_m']}..{payload['alt_max_m']} m ASL, "
      f"span {span:.1f} m, closure {closure:+.1f} m; {len(stations)} stations")
print(f"wrote {out}")
