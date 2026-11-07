"""HAM 2018 Brazil Q pole 1:07.281 (F1InsightsHub backend car_data, FastF1-derived; F1 archive is 401).
Writes ham2018_car_data.json (raw) and ham2018_q.csv (frame,time_s,distance,speed,mode) cut to the official clock.
mode: BRAKING from brake, DRS when the DRS flap is open (channel >= 10)."""
import csv, json, os
import requests
from datetime import datetime
import numpy as np
H = os.path.dirname(os.path.abspath(__file__)); POLE = 67.281
RAW = os.path.join(H, "ham2018_car_data.json")
def get(lap):
    return requests.get("https://backend.f1insightshub.com/fastf1/car_data", timeout=90, params=dict(
        driver_number=44, lap_number=lap, session_key="2018|Brazilian Grand Prix|Qualifying")).json()
if not os.path.exists(RAW):
    laps = {}
    for n in range(1, 30):
        try:
            c = get(n)
            if isinstance(c, list) and len(c) > 50: laps[n] = c
        except Exception as e: print('lap', n, e)
    json.dump(laps, open(RAW, "w"))
laps = json.load(open(RAW))
for n, c in laps.items():
    t = [datetime.fromisoformat(x["date"]) for x in c]
    print(f"lap {n}: {len(c)} rows, {(t[-1]-t[0]).total_seconds():.3f} s, {c[-1]['distance']:.0f} m, vmax {max(x['speed'] for x in c):.1f}")
best = min((n for n, c in laps.items() if c[-1]["distance"] > 4000 and c[0]["speed"] > 200),
           key=lambda n: (datetime.fromisoformat(laps[n][-1]["date"]) - datetime.fromisoformat(laps[n][0]["date"])).total_seconds())
c = laps[best]; t0 = datetime.fromisoformat(c[0]["date"])
t = np.array([(datetime.fromisoformat(x["date"]) - t0).total_seconds() for x in c])
d = np.array([x["distance"] for x in c], float); v = np.array([x["speed"] for x in c], float)
print(f"pole lap = {best}: raw {t[-1]:.3f} s -> clock {POLE}")
t = t * POLE / t[-1]   # sample timestamps -> official lap time
with open(os.path.join(H, "ham2018_q.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["frame", "time_s", "distance", "speed", "mode"])
    for i, x in enumerate(c):
        m = "BRAKING" if x["brake"] else ("DRS" if int(x["drs"] or 0) >= 10 else "")
        w.writerow([i, round(t[i], 4), round(d[i], 3), round(v[i], 2), m])
json.dump(dict(lap=int(best)), open(os.path.join(H, "ham2018_pick.json"), "w"))
