"""python -m weekend <track> <year> [--resume]  -> run the race-weekend pipeline (see weekend/runner.py)."""
import json
import sys

from weekend.runner import run

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    res = run(args[0], int(args[1]), resume="--resume" in sys.argv)
    print(json.dumps(res, indent=1, default=str))
    sys.exit(3 if res.get("paused") else 0)
