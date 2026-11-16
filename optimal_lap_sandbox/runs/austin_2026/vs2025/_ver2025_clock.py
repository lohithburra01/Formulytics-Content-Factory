"""VER 2025 Austin Q pole (OpenF1 car_data, reference_2025_austin_q.csv) cut to the official clock 92.510 s."""
import csv, sys
import numpy as np
src, out, lap = sys.argv[1], sys.argv[2], float(sys.argv[3])
rows = list(csv.DictReader(open(src, encoding="utf-8")))
t = np.array([float(r["time_s"]) for r in rows]); d = np.array([float(r["distance"]) for r in rows])
v = np.array([float(r["speed"]) for r in rows])
br = np.array([float(r["brake"]) for r in rows])
keep = t < lap
t, d, v, br = list(t[keep]), list(d[keep]), list(v[keep]), list(br[keep])
t.append(lap); d.append(float(np.interp(lap, [r for r in map(float, (x["time_s"] for x in rows))], [float(x["distance"]) for x in rows])))
v.append(float(np.interp(lap, [float(x["time_s"]) for x in rows], [float(x["speed"]) for x in rows])))
br.append(0.0)
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["frame", "time_s", "distance", "speed", "mode"])  # mode: BRAKING from brake channel only (no DRS channel)
    for i, (a, b, c, k) in enumerate(zip(t, d, v, br)):
        w.writerow([i, round(a, 4), round(b, 3), round(c, 2), "BRAKING" if k > 0 else ""])
print(f"[ver2025] {len(t)} rows, lap {lap}, distance {d[-1]:.1f} m")
