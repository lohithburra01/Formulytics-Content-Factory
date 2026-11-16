"""Simulate the 2025 car (car2025c.json) on its own line opt2025c -> sim2025_own_line.csv (for the telemetry
warp) and the real-frame (un-mirrored) line F1_Pipeline_Assets/tracks/singapore_2025_rus_raceline.json."""
import sys, json, os, numpy as np
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(H))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "cache", "era2017")); sys.path.insert(0, H)
import _car2025 as K, sim_2026_lap as S
c = json.load(open(os.path.join(H, "car2025c.json"))); rl = np.array(json.load(open(os.path.join(H, "opt2025c_rl.json")))["raceline"])
r = K.sim(rl, c["car"], c["drs"])
S.write_csv(os.path.join(H, "sim2025_own_line.csv"), r["v"], np.ones(len(r["v"])), r["mode"], r["pkw"], r["t"], r["arc"], r["L"], fps=30)
json.dump({"raceline": (rl * [-1, 1]).tolist(), "arc_length": r["arc"].tolist(), "track_length_m": r["L"]},
          open(os.path.join(ROOT, "F1_Pipeline_Assets", "tracks", "singapore_2025_rus_raceline.json"), "w"))
print(f"[2025] own-line lap {r['lap']:.3f} s")
