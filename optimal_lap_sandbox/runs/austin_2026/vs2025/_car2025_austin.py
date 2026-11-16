"""2025 car for Austin (VER pole 1:32.510, OpenF1 session 9884 lap 11) - same method as cache/singapore/_car2025.py:
era-2017 car model (fitted to real 2018 Q telemetry), mass 800, DRS zones from VER's real DRS channel,
cda fitted to his top speed, cl to his lap time on the given line.  python _car2025_austin.py LINE_RL(sim frame) OUT_JSON"""
import json, os, sys, contextlib, io, urllib.request
from datetime import datetime
import numpy as np
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(os.path.dirname(H)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "cache", "era2017"))
import sim_2017_car as C
POLE = 92.51
RAW = os.path.join(H, "ver2025_car_data.json")
def fetch():
    if not os.path.exists(RAW):
        g = lambda q: json.load(urllib.request.urlopen("https://api.openf1.org/v1/" + q, timeout=90))
        lap = g("laps?session_key=9884&driver_number=1&lap_number=11")[0]
        t1 = (datetime.fromisoformat(lap["date_start"]).timestamp() + lap["lap_duration"] + 2)
        end = datetime.fromtimestamp(t1, datetime.fromisoformat(lap["date_start"]).tzinfo).isoformat()
        cd = g(f"car_data?session_key=9884&driver_number=1&date>={lap['date_start']}&date<={end}".replace("+", "%2B"))
        json.dump(dict(lap=lap, car_data=cd), open(RAW, "w"))
    return json.load(open(RAW))
def drs_zones(raw):
    lap = raw["lap"]; P_ = datetime.fromisoformat
    cd = sorted([c for c in raw["car_data"] if c.get("speed") is not None], key=lambda c: c["date"])
    t = np.array([(P_(c["date"]) - P_(lap["date_start"])).total_seconds() for c in cd]); v = np.array([c["speed"] for c in cd], float)
    d = np.r_[0, np.cumsum(0.5 * (v[1:] + v[:-1]) / 3.6 * np.diff(t))] + v[0] / 3.6 * t[0]; D = float(np.interp(POLE, t, d))
    f = d / D; on = np.array([int(c.get("drs") or 0) >= 10 for c in cd]) & (t >= 0) & (t <= POLE)
    z, i = [], 0
    while i < len(on):
        if on[i]:
            j = i
            while j + 1 < len(on) and on[j + 1]: j += 1
            z.append([round(float(max(f[i], 0)), 4), round(float(min(f[j], 1)), 4)]); i = j + 1
        else: i += 1
    return z, float(v[(t >= 0) & (t <= POLE)].max())
def sim(rl, car, drs):
    with contextlib.redirect_stdout(io.StringIO()): return C.simulate(rl, car, drs, smooth=True)
if __name__ == "__main__":
    rl = np.asarray(json.load(open(sys.argv[1]))["raceline"])[:, :2]
    car = dict(json.load(open(os.path.join(ROOT, "cache", "era2017", "sepang_2017_report.json")))["car_untrimmed"])
    car.update(mass=800.0, rho=1.205)            # rho = Austin pack value (171 m)
    drs, VTOP = drs_zones(fetch()); print("[2025] DRS zones (lap frac):", drs, "top", VTOP)
    for it in range(4):
        lo, hi = 0.6, 2.4
        for _ in range(30):
            m = 0.5 * (lo + hi); v = sim(rl, dict(car, cda=m), drs)["v"].max() * 3.6
            lo, hi = (m, hi) if v > VTOP else (lo, m)
        car["cda"] = m
        lo, hi = 2.0, 7.0
        for _ in range(30):
            m = 0.5 * (lo + hi); t = sim(rl, dict(car, cl=m), drs)["lap"]
            lo, hi = (m, hi) if t > POLE else (lo, m)
        car["cl"] = m; r = sim(rl, car, drs)
        print(f"[2025] it{it}: cda {car['cda']:.4f} cl {car['cl']:.4f} -> lap {r['lap']:.3f} top {r['v'].max()*3.6:.1f} min {r['v'].min()*3.6:.1f}", flush=True)
    json.dump(dict(car=car, drs=drs, line=sys.argv[1], lap=r["lap"]), open(sys.argv[2], "w"), indent=1)
    # direction/shape check vs VER's real trace (by lap fraction)
    q = np.genfromtxt(os.path.join(H, "ver2025_q.csv"), delimiter=",", names=True, dtype=None, encoding="utf-8")
    fq = q["distance"] / q["distance"][-1]; arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(rl, axis=0), axis=1))]
    fs = np.linspace(0, 1, len(r["v"]), endpoint=False)
    print(f"[2025] speed-trace corr vs VER real {np.corrcoef(np.interp(fq, fs, r['v']*3.6), q['speed'])[0,1]:.3f}")
