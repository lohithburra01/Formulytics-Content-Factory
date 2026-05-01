"""
fetch_fastest_lap.py

Pulls the fastest lap of an F1 Qualifying session (= the pole lap, which is
the fastest lap of the weekend at virtually every event) and writes it to
a CSV in the format raceline_video.py consumes.

Single session only — no brute-force scanning across FP/Sprint/etc.
If Q is unavailable (very rare) you can pass --session R as an override.

Usage:
  python fetch_fastest_lap.py --year 2024 --track "Miami" --out fastest_miami.csv

CSV columns: frame,time_s,distance,speed,throttle,brake,gear,rpm,ers_deploy
"""

import argparse
import csv
import os
import sys
import warnings

warnings.simplefilter("ignore")


def fetch_fastest(year, track, session_code, cache_dir):
    """Load the requested session and return its fastest lap (any driver)."""
    import fastf1
    import pandas as pd

    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        try:
            fastf1.Cache.enable_cache(cache_dir)
        except Exception as e:
            print(f"[cache] could not enable {cache_dir}: {e}", flush=True)

    print(f"[fetch] loading {year} {track} session {session_code} ...", flush=True)
    sess = fastf1.get_session(year, track, session_code)
    sess.load(telemetry=True, laps=True, weather=False, messages=False)

    if sess.laps is None or sess.laps.empty:
        raise RuntimeError(f"No laps in {year} {track} {session_code}")

    fast = sess.laps.pick_fastest()
    if fast is None or pd.isna(fast.get("LapTime")):
        raise RuntimeError(f"No valid fastest lap in {year} {track} {session_code}")

    lap_time = fast["LapTime"].total_seconds()
    driver   = fast["Driver"]
    return lap_time, fast, driver, session_code


def lap_to_rows(lap):
    """Convert a fastf1 Lap to the script's CSV row format."""
    tel = lap.get_telemetry().dropna(subset=["Distance", "Speed"])
    tel = tel.drop_duplicates(subset=["Time"]).reset_index(drop=True)

    # Reference time: SessionTime of first sample
    if "SessionTime" in tel.columns:
        t0 = tel["SessionTime"].iloc[0]
        time_col = tel["SessionTime"]
    else:
        t0 = tel["Time"].iloc[0]
        time_col = tel["Time"]

    rows = []
    for i in range(len(tel)):
        r = tel.iloc[i]
        t_td = time_col.iloc[i] - t0
        try:
            t_s = t_td.total_seconds()
        except AttributeError:
            t_s = float(t_td) / 1e9 if hasattr(t_td, "value") else float(t_td)

        brake_raw = r.get("Brake", 0)
        if isinstance(brake_raw, bool) or str(type(brake_raw)).find("bool") != -1:
            brake_pct = 100.0 if bool(brake_raw) else 0.0
        else:
            try:
                brake_pct = float(brake_raw)
            except Exception:
                brake_pct = 0.0

        rows.append({
            "frame":      i,
            "time_s":     round(float(t_s), 4),
            "distance":   round(float(r["Distance"]), 3),
            "speed":      round(float(r["Speed"]), 3),
            "throttle":   round(float(r.get("Throttle", 0) or 0), 2),
            "brake":      round(brake_pct, 2),
            "gear":       int(r.get("nGear", 0) or 0),
            "rpm":        int(r.get("RPM", 0) or 0),
            "ers_deploy": 0,
        })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year",  type=int, required=True)
    ap.add_argument("--track", required=True,
                    help='Track name as FastF1 expects, e.g. "Miami" or "Miami Grand Prix"')
    ap.add_argument("--out",   required=True, help="Output CSV path")
    ap.add_argument("--session", default="Q",
                    help='Session code: Q (default — pole lap), R, SQ, S, FP1, FP2, FP3')
    ap.add_argument("--cache", default=None,
                    help="FastF1 cache directory (default: F1_Pipeline_Assets/temp_data/f1_cache "
                         "next to this script if it exists, else ./cache)")
    args = ap.parse_args()

    if args.cache is None:
        here = os.path.dirname(os.path.abspath(__file__))
        candidate = os.path.join(here, "F1_Pipeline_Assets", "temp_data", "f1_cache")
        args.cache = candidate if os.path.isdir(os.path.dirname(candidate)) else os.path.join(here, "cache")

    print(f"[fetch] year={args.year} track={args.track} session={args.session} cache={args.cache}", flush=True)

    lap_time_s, lap, driver, session_code = fetch_fastest(
        args.year, args.track, args.session, args.cache)
    print(f"[fetch] fastest: {driver} {session_code} {lap_time_s:.3f}s", flush=True)

    rows = lap_to_rows(lap)
    if not rows:
        raise RuntimeError("Telemetry empty after extraction")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "frame", "time_s", "distance", "speed",
            "throttle", "brake", "gear", "rpm", "ers_deploy"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    final_t = rows[-1]["time_s"]
    final_d = rows[-1]["distance"]
    print(f"[fetch] wrote {len(rows)} rows to {args.out}", flush=True)
    print(f"[fetch] lap_time={final_t:.3f}s  distance={final_d:.0f}m  driver={driver}  session={session_code}",
          flush=True)


if __name__ == "__main__":
    sys.exit(main() or 0)
