"""Wait out OpenF1's live-session lockout, then pull the refs we need.

While ANY F1 session is running, OpenF1 answers every endpoint - historical
ones included - with 401 {"detail": "Live F1 session in progress..."}. That
blocks the whole pre-weekend pipeline on a race Friday, so this poller sits on
the API and fires the fetches the moment it opens up.

  python cache/_fetch_when_open.py [--minutes 240] [--every 180]

Fetches (skipped if the file already exists):
  1. 2025 Monza Q   -> reference_2025_monza_q.csv   (Monza's own 2025 anchor)
  2. 2026 Zandvoort Q -> reference_2026_zandvoort_q.csv (7th transfer pair)
Then prints each CSV's lap time + integrated distance for provenance checks.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTS = os.path.join(REPO_ROOT, "F1_Pipeline_Assets", "exports")
PROBE = "https://api.openf1.org/v1/sessions?year=2025&country_name=Italy"

JOBS = [
    dict(name="2025 Monza Q", out=os.path.join(EXPORTS, "reference_2025_monza_q.csv"),
         args=["--year", "2025", "--country", "Italy", "--circuit", "Monza",
               "--session", "Qualifying"], want_m=5793.0),
    dict(name="2026 Zandvoort Q", out=os.path.join(EXPORTS, "reference_2026_zandvoort_q.csv"),
         args=["--year", "2026", "--country", "Netherlands",
               "--session", "Qualifying"], want_m=4259.0),
]


def api_open() -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(PROBE, timeout=45) as r:
            return (r.status == 200), f"HTTP {r.status}"
    except urllib.error.HTTPError as e:
        body = e.read(160).decode("utf-8", "ignore")
        try:
            body = json.loads(body).get("detail", body)[:90]
        except Exception:                                   # noqa: BLE001
            pass
        return False, f"HTTP {e.code}: {body}"
    except Exception as e:                                  # noqa: BLE001
        return False, f"{type(e).__name__}: {str(e)[:90]}"


def summarise(path: str, want_m: float) -> str:
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return "EMPTY CSV"
    t = float(rows[-1]["time_s"])
    d = float(rows[-1]["distance"])
    err = 100.0 * (d - want_m) / want_m
    flag = "OK" if abs(err) <= 2.0 else "CHECK"
    return (f"lap {t:7.3f}s  dist {d:7.0f} m vs official {want_m:.0f} "
            f"({err:+.1f}%) [{flag}]  rows {len(rows)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=240.0)
    ap.add_argument("--every", type=float, default=180.0)
    args = ap.parse_args()

    deadline = time.time() + args.minutes * 60.0
    while True:
        ok, why = api_open()
        if ok:
            print(f"[wait] OpenF1 open at {time.strftime('%H:%M:%S')}", flush=True)
            break
        if time.time() >= deadline:
            print(f"[wait] gave up after {args.minutes:.0f} min - last: {why}",
                  file=sys.stderr, flush=True)
            return 3
        print(f"[wait] {time.strftime('%H:%M:%S')} locked - {why}", flush=True)
        time.sleep(args.every)

    rc = 0
    for job in JOBS:
        if os.path.exists(job["out"]):
            print(f"[fetch] {job['name']}: exists, skipping", flush=True)
        else:
            print(f"[fetch] {job['name']} ...", flush=True)
            p = subprocess.run(
                [sys.executable, os.path.join(REPO_ROOT, "fetch_openf1_lap.py"),
                 *job["args"], "--out", job["out"]],
                capture_output=True, text=True)
            sys.stdout.write(p.stdout[-1500:])
            sys.stderr.write(p.stderr[-1500:])
            if p.returncode != 0 or not os.path.exists(job["out"]):
                print(f"[fetch] {job['name']} FAILED rc={p.returncode}",
                      file=sys.stderr, flush=True)
                rc = 2
                continue
        print(f"[check] {job['name']:16s} {summarise(job['out'], job['want_m'])}",
              flush=True)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
