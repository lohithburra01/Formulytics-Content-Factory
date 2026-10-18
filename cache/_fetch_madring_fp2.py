"""Fetch the Madring FP2 fastest lap from the F1 official archive via FastF1.

Same route that worked for FP1 (backend f1timing, cache disabled). Writes only
new files: cache/madring_fp2_20260911/ (raw car/position + provenance) and
F1_Pipeline_Assets/exports/reference_2026_madring_fp2.csv (FP1 reference columns).
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import fastf1
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
fastf1.Cache.set_disabled()
dest = ROOT / "cache/madring_fp2_20260911"
ref_out = ROOT / "F1_Pipeline_Assets/exports/reference_2026_madring_fp2.csv"
for p in (dest, ref_out):
    if p.exists():
        raise FileExistsError(p)

session = fastf1.get_session(2026, "Spanish Grand Prix", "Practice 2", backend="f1timing")
print("SESSION", session.api_path, session.event["EventName"], session.event["EventDate"], flush=True)
assert "2026-09-13_Spanish_Grand_Prix" in session.api_path, session.api_path
session.load(laps=True, telemetry=True, weather=False, messages=False)

laps = session.laps
timed = laps[laps["LapTime"].notna()].sort_values("LapTime")
print(timed[["Driver", "LapNumber", "LapTime", "Compound"]].head(12).to_string(), flush=True)
lap = laps.pick_fastest()
drv = str(lap["Driver"])
lap_s = lap["LapTime"].total_seconds()
print("FASTEST", drv, lap["LapNumber"], lap["LapTime"], flush=True)

car = lap.get_car_data()
posd = lap.get_pos_data()
tel = lap.get_telemetry()
dest.mkdir()
car.to_csv(dest / f"{drv.lower()}_fastest_car.csv", index=False)
posd.to_csv(dest / f"{drv.lower()}_fastest_position.csv", index=False)
out = pd.DataFrame(dict(
    frame=np.arange(len(tel)),
    time_s=tel["Time"].dt.total_seconds().round(3),
    distance=tel["Distance"].round(3),
    speed=tel["Speed"].round(3),
    throttle=tel["Throttle"].round(1),
    brake=tel["Brake"].astype(float) * 100.0,
    gear=tel["nGear"].round().astype(int),
    rpm=tel["RPM"].round().astype(int),
    ers_deploy=0))
with ref_out.open("x", encoding="utf-8", newline="") as stream:
    out.to_csv(stream, index=False)
prov = dict(source="Formula 1 official timing archive via FastF1", api_path=session.api_path,
            session="Practice 2", driver=drv, driver_number=str(lap["DriverNumber"]),
            lap_number=int(lap["LapNumber"]), lap_duration_s=lap_s,
            lap_start_utc=str(lap["LapStartDate"]),
            fetched_utc=datetime.now(timezone.utc).isoformat(),
            car_samples=len(car), position_samples=len(posd), csv_samples=len(out),
            distance_m=float(out.distance.iloc[-1]), fastf1_version=fastf1.__version__)
with (dest / "provenance.json").open("x", encoding="utf-8") as stream:
    json.dump(prov, stream, indent=2)
print(json.dumps(prov, indent=2))
