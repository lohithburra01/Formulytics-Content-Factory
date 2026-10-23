"""Everything a new weekend needs from OpenF1, in one go, waiting out the live-session lockout.

  python -m weekend.fetch_weekend austin 2026 --country "United States" --circuit Austin

While any F1 session is live OpenF1 answers 401 to every endpoint, so this polls until it opens, then:
  1. last year's Q pole lap       -> F1_Pipeline_Assets/exports/reference_<prev>_<track>_q.csv
  2. last year's Q path (top-10)  -> cache/<track>/path_samples.json   (same recipe as Singapore)
  3. this year's FP1 fastest lap  -> F1_Pipeline_Assets/exports/reference_<year>_<track>_fp1.csv
Facts for the notes (session keys, drivers, lap times, sectors) -> cache/<track>/fetch_facts.json.
Files that already exist are skipped, so it is safe to re-run.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import fetch_openf1_lap as F  # noqa: E402

EXPORTS = os.path.join(ROOT, "F1_Pipeline_Assets", "exports")


def is_open() -> str | None:
    try:
        F.urllib.request.urlopen(F.BASE + "/sessions?year=2025&country_name=Italy", timeout=45).close()
        return None
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return type(e).__name__


def session(year, country, circuit, name):
    ss = [s for s in F.get("sessions", year=year, country_name=country, session_name=name)
          if not circuit or s.get("circuit_short_name") == circuit]
    if len(ss) != 1:
        raise SystemExit(f"[fetch] {year} {name}: expected 1 session, got {len(ss)}")
    return ss[0]["session_key"]


def fastest_laps(sk):
    laps = [l for l in F.get("laps", session_key=sk) if l.get("lap_duration") and not l.get("is_pit_out_lap")]
    best = {}
    for l in laps:
        if l["driver_number"] not in best or l["lap_duration"] < best[l["driver_number"]]["lap_duration"]:
            best[l["driver_number"]] = l
    return sorted(best.values(), key=lambda l: l["lap_duration"])


def lap_csv(year, country, circuit, name, out):
    if os.path.exists(out):
        print(f"[fetch] {os.path.basename(out)} exists, skipping", flush=True); return
    args = [sys.executable, os.path.join(ROOT, "fetch_openf1_lap.py"), "--year", str(year), "--country", country,
            "--session", name, "--out", out] + (["--circuit", circuit] if circuit else [])
    r = subprocess.run(args, capture_output=True, text=True)
    print(r.stdout[-800:], r.stderr[-800:], flush=True)
    if r.returncode or not os.path.exists(out):
        raise SystemExit(f"[fetch] {name} {year} lap csv FAILED rc={r.returncode}")


def path_samples(sk, out):
    if os.path.exists(out):
        print(f"[fetch] {out} exists, skipping", flush=True); return
    rows = []
    for l in fastest_laps(sk)[:10]:
        st = F.parse_dt(l["date_start"]); en = st + timedelta(seconds=l["lap_duration"])
        loc = F.get("location", session_key=sk, driver_number=l["driver_number"],
                    **{"date>": st.isoformat(), "date<": en.isoformat()})
        rows += [dict(drv=l["driver_number"], t=(F.parse_dt(r["date"]) - st).total_seconds(),
                      x=r["x"], y=r["y"], z=r["z"]) for r in loc]
        print(f"[path] drv {l['driver_number']} {l['lap_duration']} s, {len(loc)} samples", flush=True)
    with open(out, "w") as fh:
        json.dump(rows, fh)


def lap_fact(sk, lap):
    return dict(session_key=sk, driver=lap["driver_number"], lap_number=lap["lap_number"],
                lap_s=lap["lap_duration"], sectors_s=[lap.get(f"duration_sector_{i}") for i in (1, 2, 3)])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("track"); ap.add_argument("year", type=int)
    ap.add_argument("--country", required=True); ap.add_argument("--circuit", default=None)
    ap.add_argument("--every", type=float, default=120.0); ap.add_argument("--minutes", type=float, default=600.0)
    ap.add_argument("--no-fp1", action="store_true", help="only last year's data")
    a = ap.parse_args()
    prev, d = a.year - 1, os.path.join(ROOT, "cache", a.track)
    os.makedirs(d, exist_ok=True)
    facts_file = os.path.join(d, "fetch_facts.json")
    facts = json.load(open(facts_file)) if os.path.exists(facts_file) else {}
    deadline = time.time() + a.minutes * 60
    while (why := is_open()):
        if time.time() > deadline:
            print(f"[wait] gave up: {why}", flush=True); return 3
        print(f"[wait] {time.strftime('%H:%M:%S')} OpenF1 locked ({why})", flush=True); time.sleep(a.every)
    print(f"[wait] OpenF1 open at {time.strftime('%H:%M:%S')}", flush=True)

    sk = session(prev, a.country, a.circuit, "Qualifying")
    facts[f"q{prev}"] = lap_fact(sk, fastest_laps(sk)[0])
    lap_csv(prev, a.country, a.circuit, "Qualifying", os.path.join(EXPORTS, f"reference_{prev}_{a.track}_q.csv"))
    path_samples(sk, os.path.join(d, "path_samples.json"))
    json.dump(dict(facts, fetched=str(date.today())), open(facts_file, "w"), indent=1)

    if not a.no_fp1:
        while True:                                   # FP1 laps can take a while to publish after the flag
            try:
                sk = session(a.year, a.country, a.circuit, "Practice 1"); laps = fastest_laps(sk)
            except SystemExit as e:
                laps = []; print(e, flush=True)
            if laps:
                break
            if time.time() > deadline:
                print("[fp1] gave up waiting for laps", flush=True); return 4
            print(f"[fp1] {time.strftime('%H:%M:%S')} no FP1 laps yet", flush=True); time.sleep(a.every)
        facts[f"fp1_{a.year}"] = lap_fact(sk, laps[0])
        lap_csv(a.year, a.country, a.circuit, "Practice 1", os.path.join(EXPORTS, f"reference_{a.year}_{a.track}_fp1.csv"))
    json.dump(dict(facts, fetched=str(date.today())), open(facts_file, "w"), indent=1)
    print("[done]", json.dumps(facts), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
