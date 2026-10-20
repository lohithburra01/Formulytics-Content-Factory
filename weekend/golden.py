"""Golden record of a finished run (small, committed) and its fast replay (pre-commit).

  python -m weekend.golden record <runs/track_year> <golden_dir>   # after a full run
  python -m weekend.golden replay <golden_dir> <out_dir>           # final lap from the record
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import shutil
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _sha(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _only(pattern):
    hits = [h for h in glob.glob(pattern) if not h.endswith(".partial") and ".partial." not in h]
    if len(hits) != 1:
        raise SystemExit(f"expected one match for {pattern}, got {hits}")
    return hits[0]


def record(run_root, gold, final_dir=None):
    os.makedirs(gold, exist_ok=True)
    fin = final_dir or os.path.dirname(_only(os.path.join(run_root, "final", "*", "done.json")))
    with open(os.path.join(fin, "inputs.json"), encoding="utf-8") as fh:
        inp = json.load(fh)
    up = inp["up"]
    shutil.copyfile(os.path.join(up["base_line"], "raceline.json"), os.path.join(gold, "base_raceline.json"))
    shutil.copyfile(os.path.join(up["track"], "sim_outline.json"), os.path.join(gold, "sim_outline.json"))
    shutil.copyfile(os.path.join(up["time_knob"], "knots.npy"), os.path.join(gold, "knots.npy"))
    shutil.copyfile(os.path.join(fin, "car.json"), os.path.join(gold, "car.json"))
    prm = {k[5:]: v["value"] for k, v in inp["values"].items() if k.startswith("line.")}
    with open(os.path.join(gold, "line_params.json"), "w") as fh:
        json.dump(prm, fh, indent=1, sort_keys=True)
    with open(os.path.join(gold, "expected.json"), "w") as fh:
        json.dump(dict(lap_csv_sha256=_sha(os.path.join(fin, "lap.csv")),
                       raceline_sha256=_sha(os.path.join(fin, "sim_raceline.json")),
                       source=os.path.relpath(fin, ROOT)), fh, indent=1)


def replay(gold, out):
    from weekend import line as LN, simdoor
    from weekend.stages import write_raceline
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(gold, "car.json")) as fh:
        vals = json.load(fh)
    with open(os.path.join(gold, "line_params.json")) as fh:
        prm = json.load(fh)
    LN.setup(os.path.join(gold, "base_raceline.json"), os.path.join(gold, "sim_outline.json"), prm)
    rl, _ = LN.O.line_of(np.load(os.path.join(gold, "knots.npy")))
    sim = simdoor.configure(vals)
    arc, kappa, L = sim._arc_kappa_closed(rl)
    write_raceline(os.path.join(out, "raceline.json"), rl, arc, kappa, L)
    simdoor.final_lap(sim, rl, vals, csv_out=os.path.join(out, "lap.csv"), check=True)


if __name__ == "__main__":
    {"record": lambda: record(sys.argv[2], sys.argv[3]), "replay": lambda: replay(sys.argv[2], sys.argv[3])}[sys.argv[1]]()
