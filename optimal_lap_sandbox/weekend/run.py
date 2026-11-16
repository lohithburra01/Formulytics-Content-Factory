"""Run the Singapore final sim step from a Weekend Pack, and nothing else.

  python -m weekend.run weekend/packs/singapore_2026.json <out_dir>

The sim runs in a fresh child process whose environment holds no pipeline
settings, so env-vars, a leftover module state or the calibration JSON cannot
leak in. The child sets EVERY sim constant from the pack and refuses to run if
the sim has a constant the pack does not know (or the reverse).

Interim (expand step): the sim still keeps its values as module globals; this
module is the single door that writes them. Removing the globals is a later step.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Pack values that are not sim module constants.
FILES = ("outline_file", "reference_csv_file", "raceline_in_file")
ENV_SETTINGS = ("KGRIP_STENCIL", "LINE_WOBBLE_SIG", "LINE_WOBBLE_ADAPTIVE")
PIPELINE = FILES + ENV_SETTINGS + ("inset_m", "street_grip_k", "gain_cap_kmh_s",
                                   "mu_lat_scale")
# Set by the sim itself at run time (from the outline), not configuration.
SIM_RUNTIME = ("BANKING_RAD",)
# Only these env-vars reach the child (Windows needs them to start Python).
ENV_KEEP = ("SYSTEMROOT", "PATH", "TEMP", "TMP", "USERPROFILE", "LOCALAPPDATA",
            "APPDATA", "PROCESSOR_ARCHITECTURE", "NUMBER_OF_PROCESSORS", "OS")


def _sha256(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _sim_constants(sim) -> set[str]:
    return {k for k, v in vars(sim).items()
            if k.isupper() and not k.startswith("_") and k not in SIM_RUNTIME
            and isinstance(v, (int, float, str, bool))}


def _child(pack_file: str, out_dir: str) -> None:
    with open(pack_file, encoding="utf-8") as fh:
        vals = {k: v for k, v in json.load(fh)["values"].items()}
    get = lambda name: vals[name]["value"]  # noqa: E731

    for name in FILES:
        path = os.path.join(ROOT, get(name))
        if _sha256(path) != vals[name]["sha256"]:
            raise SystemExit(f"[run] {name} changed since the pack was resolved: {path}")
    for name in ENV_SETTINGS:
        os.environ[name] = str(get(name))

    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.join(ROOT, "cache"))
    import _sim_singapore as wrapper   # GAIN-guard wrapper; env is clean so it applies nothing else
    import _sg_grip
    sim = wrapper.sim

    consts = _sim_constants(sim)
    sim_in_pack = {k for k in vals if k not in PIPELINE}
    if consts - sim_in_pack:
        raise SystemExit(f"[run] sim constants missing from the pack: {sorted(consts - sim_in_pack)}")
    if sim_in_pack - consts:
        raise SystemExit(f"[run] pack values the sim does not have: {sorted(sim_in_pack - consts)}")
    for name in consts:
        setattr(sim, name, get(name))

    sim.MU_LAT = sim.MU_LAT * get("mu_lat_scale")
    _sg_grip.apply(sim, float(get("street_grip_k")))
    wrapper.GAIN_CAP = float(get("gain_cap_kmh_s"))

    sys.argv = ["sim_2026_lap.py",
                "--outline", os.path.join(ROOT, get("outline_file")),
                "--raceline-in", os.path.join(ROOT, get("raceline_in_file")),
                "--reference-csv", os.path.join(ROOT, get("reference_csv_file")),
                "--inset", repr(float(get("inset_m"))),
                # the sim copies these CLI knobs back onto its constants
                "--cda", repr(float(get("CDA_STRAIGHT_M2"))),
                "--cl", repr(float(get("CL_CORNER_M2"))),
                "--rho", repr(float(get("RHO"))),
                "--csv-out", os.path.join(out_dir, "lap.csv"),
                "--raceline-out", os.path.join(out_dir, "raceline.json")]
    if get("WARM_RHO") != get("RHO"):
        raise SystemExit("[run] the sim forces WARM_RHO = RHO; the pack disagrees")
    sim.main()


def run(pack_file: str, out_dir: str) -> dict:
    """Run the sim from the pack in a clean child process; return the result summary."""
    os.makedirs(out_dir, exist_ok=True)
    env = {k: os.environ[k] for k in ENV_KEEP if k in os.environ}
    log = os.path.join(out_dir, "sim.log")
    with open(log, "w", encoding="utf-8") as fh:
        r = subprocess.run([sys.executable, "-m", "weekend.run", "--child",
                            os.path.abspath(pack_file), os.path.abspath(out_dir)],
                           cwd=ROOT, env=env, stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode != 0:
        raise RuntimeError(f"sim failed (rc={r.returncode}), see {log}")
    lap_csv, rl = os.path.join(out_dir, "lap.csv"), os.path.join(out_dir, "raceline.json")
    with open(lap_csv, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return dict(lap_csv=lap_csv, raceline=rl,
                lap_csv_sha256=_sha256(lap_csv), raceline_sha256=_sha256(rl),
                lap_s=float(rows[-1]["time_s"]))


if __name__ == "__main__":
    if sys.argv[1] == "--child":
        _child(sys.argv[2], sys.argv[3])
    else:
        res = run(sys.argv[1], sys.argv[2])
        print(json.dumps(res, indent=1))
