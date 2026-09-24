"""Audit raceline use of the real SVG corridor at centerline corner peaks."""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import find_peaks
from scipy.spatial import cKDTree

root = Path(__file__).resolve().parents[1]
outline = json.loads((root / sys.argv[1]).read_text())
line_data = json.loads((root / sys.argv[2]).read_text())
outer = np.asarray(outline["outer"], float)
inner = np.asarray(outline["inner"], float)
center = (outer + inner) / 2
width = np.linalg.norm(outer - inner, axis=1)
line = np.asarray(line_data["raceline"], float)
n = len(center)
step_m = 6003 / n
ab = center - np.roll(center, 1, axis=0)
bc = np.roll(center, -1, axis=0) - center
ca = np.roll(center, -1, axis=0) - np.roll(center, 1, axis=0)
curvature = 2 * (ab[:, 0]*bc[:, 1] - ab[:, 1]*bc[:, 0]) / np.maximum(
    np.linalg.norm(ab,axis=1)*np.linalg.norm(bc,axis=1)*np.linalg.norm(ca,axis=1), 1e-9)
peaks, _ = find_peaks(np.abs(curvature), distance=20, prominence=.004)
peaks = sorted(peaks, key=lambda i: -abs(curvature[i]))[:25]
nearest = cKDTree(line)
print("station  curvature    road-width   apex-offset  usable-edge  utilization")
for i in peaks:
    # Search line points local to the apex station, then choose the one whose
    # closest centerline point is nearest the apex index.
    ids = nearest.query_ball_point(center[i], 20)
    if not ids:
        continue
    arr = line[ids]
    tang = center[(i+3)%n] - center[(i-3)%n]
    normal = np.array([-tang[1], tang[0]]) / np.linalg.norm(tang)
    along = (arr-center[i]) @ (tang/np.linalg.norm(tang))
    j = int(np.argmin(np.abs(along)))
    offset = float((arr[j]-center[i]) @ normal)
    usable = width[i]/2 - .95
    print(f"{i:7d} {curvature[i]:10.4f} {width[i]:11.2f} {offset:12.2f} {usable:12.2f} {abs(offset)/usable:11.2f}")
