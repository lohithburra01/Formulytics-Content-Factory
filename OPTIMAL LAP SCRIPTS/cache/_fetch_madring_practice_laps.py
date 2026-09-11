"""Fetch every timed Madring FP1/FP2 lap's position + car samples (F1 archive, FastF1).

Purpose: a MEASURED racing line (multi-lap GPS average), corridor spread and a
speed envelope, replacing the SVG polyline geometry whose fast bends are ~25-30%
too tight (cache/madring_diagnosis). Same route as the FP1 fetch (backend
f1timing, cache disabled). Writes only new files under cache/madring_practice_laps/.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import fastf1
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
fastf1.Cache.set_disabled()
dest = ROOT / "cache/madring_practice_laps"
dest.mkdir()  # exclusive: refuses to reuse an existing folder

summary = dict(fetched_utc=datetime.now(timezone.utc).isoformat(), fastf1_version=fastf1.__version__)
for ident in ("Practice 1", "Practice 2"):
    tag = "fp1" if ident.endswith("1") else "fp2"
    session = fastf1.get_session(2026, "Spanish Grand Prix", ident, backend="f1timing")
    assert "2026-09-13_Spanish_Grand_Prix" in session.api_path, session.api_path
    session.load(laps=True, telemetry=True, weather=False, messages=False)
    laps = session.laps
    timed = laps[laps["LapTime"].notna() & laps["PitInTime"].isna() & laps["PitOutTime"].isna()]
    if "Deleted" in timed.columns:
        timed = timed[timed["Deleted"].fillna(False) == False]  # noqa: E712
    cols = [c for c in ("Driver", "DriverNumber", "LapNumber", "LapTime", "Sector1Time", "Sector2Time",
                        "Sector3Time", "Compound", "TyreLife", "IsAccurate", "LapStartDate") if c in timed.columns]
    meta = pd.DataFrame(timed[cols]).copy()
    for c in ("LapTime", "Sector1Time", "Sector2Time", "Sector3Time"):
        meta[c] = meta[c].dt.total_seconds()
    pos_parts, car_parts, skipped = [], [], 0
    for _, lap in timed.iterlaps():
        try:
            p = lap.get_pos_data()
            c = lap.get_car_data().add_distance()
        except Exception as exc:  # a lap without samples must not sink the session
            print("skip", lap["Driver"], lap["LapNumber"], type(exc).__name__, exc, flush=True)
            skipped += 1
            continue
        drv, num = str(lap["Driver"]), int(lap["LapNumber"])
        pos_parts.append(pd.DataFrame(dict(driver=drv, lap=num, t=p["Time"].dt.total_seconds(),
                                           x=p["X"] / 10.0, y=p["Y"] / 10.0, z=p["Z"] / 10.0,
                                           status=p["Status"])))
        car_parts.append(pd.DataFrame(dict(driver=drv, lap=num, t=c["Time"].dt.total_seconds(),
                                           speed=c["Speed"], throttle=c["Throttle"],
                                           brake=c["Brake"].astype(int), gear=c["nGear"],
                                           rpm=c["RPM"], dist=c["Distance"])))
    pd.concat(pos_parts).to_csv(dest / f"pos_{tag}.csv.gz", index=False)
    pd.concat(car_parts).to_csv(dest / f"car_{tag}.csv.gz", index=False)
    meta.to_csv(dest / f"laps_{tag}.csv", index=False)
    best = meta.sort_values("LapTime").iloc[0]
    ideal = float(meta["Sector1Time"].min() + meta["Sector2Time"].min() + meta["Sector3Time"].min())
    summary[tag] = dict(api_path=session.api_path, timed_laps=len(meta), skipped=skipped,
                        fastest=dict(driver=best["Driver"], lap=int(best["LapNumber"]), lap_s=float(best["LapTime"])),
                        ideal_lap_best_sectors_s=round(ideal, 3))
    print(tag, json.dumps(summary[tag]), flush=True)

with (dest / "summary.json").open("x", encoding="utf-8") as stream:
    json.dump(summary, stream, indent=2)
print(json.dumps(summary, indent=2))
