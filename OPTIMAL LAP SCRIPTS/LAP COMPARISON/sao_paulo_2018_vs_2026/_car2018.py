"""2018 Mercedes car for Interlagos (HAM pole 1:07.281, 2018 Q lap 16, F1IH backend car_data) - same method as
the Austin/Singapore 2025 cars: era-2017 car model (fitted to real 2018 Q telemetry), mass 734 (2018 minimum),
rho at 2240 m, DRS zones from RIC's real DRS channel, cda fitted to his top speed, cl to his lap time on the line.
python _car2018.py LINE_RL(sim frame) OUT_JSON"""
import json, os, sys, contextlib, io
from datetime import datetime
import numpy as np
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(H))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "cache", "era2017"))
import sim_2017_car as C
POLE = 67.281
def drs_zones():
    c = json.load(open(os.path.join(H, "ham2018_car_data.json")))[str(json.load(open(os.path.join(H, "ham2018_pick.json")))["lap"])]
    d = np.array([x["distance"] for x in c], float); f = d / d[-1]
    on = np.array([int(x["drs"] or 0) >= 10 for x in c])
    z, i = [], 0
    while i < len(on):
        if on[i]:
            j = i
            while j + 1 < len(on) and on[j + 1]: j += 1
            z.append([round(float(f[i]), 4), round(float(f[j]), 4)]); i = j + 1
        else: i += 1
    return z, float(max(x["speed"] for x in c))
def sim(rl, car, drs):
    with contextlib.redirect_stdout(io.StringIO()): return C.simulate(rl, car, drs, smooth=True)
if __name__ == "__main__":
    rl = np.asarray(json.load(open(sys.argv[1]))["raceline"])[:, :2]
    car = dict(json.load(open(os.path.join(ROOT, "cache", "era2017", "sepang_2017_report.json")))["car_untrimmed"])
    car.update(mass=734.0, rho=1.1353)            # 2018 minimum mass; rho ISA at 785 m (Interlagos)
    drs, VTOP = drs_zones(); print("[2018] DRS zones (lap frac):", drs, "top", VTOP)
    for it in range(4):
        lo, hi = 0.4, 2.4
        for _ in range(30):
            m = 0.5 * (lo + hi); v = sim(rl, dict(car, cda=m), drs)["v"].max() * 3.6
            lo, hi = (m, hi) if v > VTOP else (lo, m)
        car["cda"] = m
        lo, hi = 1.0, 9.0
        for _ in range(30):
            m = 0.5 * (lo + hi); t = sim(rl, dict(car, cl=m), drs)["lap"]
            lo, hi = (m, hi) if t > POLE else (lo, m)
        car["cl"] = m; r = sim(rl, car, drs)
        print(f"[2018] it{it}: cda {car['cda']:.4f} cl {car['cl']:.4f} -> lap {r['lap']:.3f} top {r['v'].max()*3.6:.1f} min {r['v'].min()*3.6:.1f}", flush=True)
    json.dump(dict(car=car, drs=drs, line=sys.argv[1], lap=r["lap"]), open(sys.argv[2], "w"), indent=1)
    q = np.genfromtxt(os.path.join(H, "ham2018_q.csv"), delimiter=",", names=True, dtype=None, encoding="utf-8")
    fq = q["distance"] / q["distance"][-1]; fs = np.linspace(0, 1, len(r["v"]), endpoint=False)
    sv = np.interp(fq, fs, r["v"] * 3.6)
    print(f"[2018] speed-trace corr vs HAM real {np.corrcoef(sv, q['speed'])[0,1]:.3f}, RMSE {np.sqrt(np.mean((sv-q['speed'])**2)):.1f} km/h")
