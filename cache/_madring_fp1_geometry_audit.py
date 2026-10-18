"""Read-only numeric registration of the supplied SVG line to Madring FP1.

Analysis script; prints evidence before selecting a lap origin or height datum.
All existing files are read only. Run from the project directory.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
raw = ROOT / "cache/madring_fp1_20260911"
ref = pd.read_csv(ROOT / "F1_Pipeline_Assets/exports/reference_2026_madring_fp1.csv")
pos = pd.read_csv(raw / "rus_fastest_position.csv")
rl = json.loads((ROOT / "cache/madring_geometry_verified_raceline.json").read_text())
points = np.asarray(rl["raceline"])
arc = np.asarray(rl["arc_length"])
length = float(rl["track_length_m"])
lap_distance = float(ref.distance.iloc[-1] - ref.distance.iloc[0])
pos_t = pd.to_timedelta(pos.Time).dt.total_seconds().to_numpy()
pos_frac = (np.interp(pos_t, ref.time_s, ref.distance) - ref.distance.iloc[0]) / lap_distance
xy = pos[["X", "Y"]].to_numpy(dtype=float) / 10.0
grid = np.linspace(0.0, 1.0, 2048, endpoint=False)
sample = np.column_stack([np.interp(grid, pos_frac, xy[:,j], period=1.0) for j in range(2)])
target = np.column_stack([np.interp(grid, arc / length, points[:,j], period=1.0) for j in range(2)])
source_mean = sample.mean(axis=0)
x = sample - source_mean
xnorm = float(np.sum(x*x))
best = {}
for determinant in (1, -1):
    result = None
    for lag in range(len(grid)):
        yraw = np.roll(target, -lag, axis=0)
        target_mean = yraw.mean(axis=0)
        y = yraw - target_mean
        u, singular, vt = np.linalg.svd(x.T @ y)
        diag = np.array([1.0, determinant * np.linalg.det(u @ vt)])
        rotation = (u * diag) @ vt
        scale = float(np.sum(singular * diag) / xnorm)
        translated = scale * x @ rotation + target_mean
        errors = np.linalg.norm(translated-yraw, axis=1)
        rms = float(np.sqrt(np.mean(errors**2)))
        if result is None or rms < result["rms_m"]:
            result = dict(lag=lag, shift_frac=lag/len(grid), shift_m=lag/len(grid)*length,
                          rms_m=rms, median_m=float(np.median(errors)),
                          p95_m=float(np.percentile(errors,95)), max_m=float(errors.max()),
                          scale=scale, rotation=rotation.tolist(),
                          translation=(target_mean-scale*source_mean@rotation).tolist())
    best["rotation" if determinant==1 else "reflection"] = result

z = pos.Z.to_numpy(dtype=float)/10.0
zs = gaussian_filter1d(z, 2.0, mode="wrap")
elev = np.interp(grid, pos_frac, zs, period=1.0)
report = dict(reference_distance_m=lap_distance, registration=best,
              raw_xy_length_m=float(np.linalg.norm(np.diff(np.vstack([xy,xy[0]]),axis=0),axis=1).sum()),
              raw_height_min_m=float(z.min()), raw_height_max_m=float(z.max()),
              closure_m=float(z[-1]-z[0]), smoothed_span_m=float(elev.max()-elev.min()),
              low_frac=float(grid[np.argmin(elev)]), high_frac=float(grid[np.argmax(elev)]))
print(json.dumps(report,indent=2))

if __name__ == "__main__":
    import sim_2026_lap as sim
    index=sim.locate_start_finish(points,np.asarray(rl["kappa"]),str(ROOT / "F1_Pipeline_Assets/exports/reference_2026_madring_fp1.csv"))
    print("Curvature-derived origin:",index,"at",round(float(arc[index]),2),"m")
