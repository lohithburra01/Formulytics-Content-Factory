"""Smoothly pull any vehicle-body excursions inside the replacement SVG road."""
import json
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
outline = json.loads((ROOT / "F1_Pipeline_Assets/tracks/azerbaijan_grand_prix_outline_new_svg.json").read_text())
source = ROOT / "F1_Pipeline_Assets/tracks/azerbaijan_grand_prix_raceline_new_svg_fixed.json"
output = ROOT / "F1_Pipeline_Assets/tracks/azerbaijan_grand_prix_raceline_new_svg_final.json"
data = json.loads(source.read_text())
outer = np.asarray(outline["outer"], float)
inner = np.asarray(outline["inner"], float)
center = (outer + inner) / 2
halfwidth = np.linalg.norm(outer - inner, axis=1) / 2
tree = cKDTree(center)
line = np.asarray(data["raceline"], float)
original = line.copy()
clearance = 0.95  # half the 1.9 m simulated vehicle width

for iteration in range(120):
    distance, idx = tree.query(line)
    excess = np.maximum(distance - (halfwidth[idx] - clearance), 0)
    if excess.max() < 0.015:
        break
    direction = (line - center[idx]) / np.maximum(distance[:, None], 1e-9)
    correction = -direction * excess[:, None]
    line += gaussian_filter1d(correction, sigma=4.0, axis=0, mode="wrap")
else:
    raise RuntimeError(f"line still violates body clearance: {excess.max():.3f} m")

seg = np.linalg.norm(np.roll(line, -1, axis=0) - line, axis=1)
arc = np.r_[0, np.cumsum(seg[:-1])]
ab = line - np.roll(line, 1, axis=0)
bc = np.roll(line, -1, axis=0) - line
ca = np.roll(line, -1, axis=0) - np.roll(line, 1, axis=0)
kappa = 2 * (ab[:, 0] * bc[:, 1] - ab[:, 1] * bc[:, 0]) / np.maximum(
    np.linalg.norm(ab,axis=1)*np.linalg.norm(bc,axis=1)*np.linalg.norm(ca,axis=1), 1e-9)
data.update(raceline=line.tolist(), arc_length=arc.tolist(),
            kappa=kappa.tolist(), track_length_m=float(seg.sum()))
output.write_text(json.dumps(data))
distance, idx = tree.query(line)
print(f"corrected {np.count_nonzero(np.linalg.norm(line-original,axis=1)>.01)} points; "
      f"max shift {np.linalg.norm(line-original,axis=1).max():.2f} m; "
      f"minimum vehicle-body margin {(halfwidth[idx]-distance-clearance).min():.3f} m")
print(output)
