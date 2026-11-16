"""Poll FastF1 for the 2026 Spanish GP FP1 fastest lap until the live-timing
archive publishes it, then write the reference CSV. Uses a FRESH cache dir each
attempt so a cached "no data yet" response can't block later retries."""
import os, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = sys.executable
FETCH = os.path.join(ROOT, "fetch_fastest_lap.py")
OUT = os.path.join(ROOT, "F1_Pipeline_Assets", "exports", "reference_2026_spain_q.csv")
POLL_CACHE = os.path.join(HERE, "_fp1_poll_cache")

INTERVAL_S = 600          # 10 min between attempts
MAX_ATTEMPTS = 18         # ~3 hours total

for attempt in range(1, MAX_ATTEMPTS + 1):
    if os.path.isdir(POLL_CACHE):
        shutil.rmtree(POLL_CACHE, ignore_errors=True)
    print(f"\n===== attempt {attempt}/{MAX_ATTEMPTS} =====", flush=True)
    r = subprocess.run(
        [PY, FETCH, "--year", "2026", "--track", "Spain", "--session", "FP1",
         "--out", OUT, "--cache", POLL_CACHE],
        capture_output=True, text=True)
    tail = (r.stdout + r.stderr).strip().splitlines()[-4:]
    print("\n".join(tail), flush=True)
    # success = exit 0 AND the CSV has real rows
    ok = r.returncode == 0 and os.path.exists(OUT) and sum(1 for _ in open(OUT)) > 10
    if ok:
        n = sum(1 for _ in open(OUT)) - 1
        print(f"\n*** FP1 DATA AVAILABLE — wrote {n} rows to {OUT} ***", flush=True)
        sys.exit(0)
    if attempt < MAX_ATTEMPTS:
        print(f"...not published yet; retrying in {INTERVAL_S//60} min", flush=True)
        time.sleep(INTERVAL_S)

print("\n*** gave up — FP1 data still not published after all attempts ***", flush=True)
sys.exit(1)
