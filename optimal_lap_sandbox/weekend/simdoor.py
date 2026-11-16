"""The single door into sim_2026_lap: every process that imports the sim (a stage, an
optimiser worker, a tuning sim) configures it here, from pack values only.

Pack names:
  UPPERCASE           a sim module constant, set verbatim (all of them, both ways checked)
  env.<NAME>          a setting the sim reads from os.environ inside a function
  track.street_grip_k mechanical-grip factor (scales mu*g only), via cache/singapore/_sg_grip.py
  sim.gain_cap_kmh_s  upper GAIN-median sanity band for this track (sim default 32)
  sim.brake_preserve  keep the solved braking profile through the jerk-limit smoothing
Numbers written inside sim functions are pinned by the code version, not by the pack.
"""
from __future__ import annotations

import contextlib
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIM_RUNTIME = ("BANKING_RAD",)   # set by the sim itself from the outline


def sim_constant_names(sim) -> set[str]:
    return {k for k, v in vars(sim).items()
            if k.isupper() and not k.startswith("_") and k not in SIM_RUNTIME
            and isinstance(v, (int, float, str, bool))}


def configure(vals: dict):
    """Import the sim and set it up from `vals` (pack name -> value). Returns the module."""
    for k, v in vals.items():
        if k.startswith("env."):
            os.environ[k[4:]] = str(v)
    for p in (ROOT, os.path.join(ROOT, "cache", "singapore")):
        if p not in sys.path:
            sys.path.insert(0, p)
    with contextlib.redirect_stdout(io.StringIO()):
        import sim_2026_lap as sim
    import _sg_grip

    consts = sim_constant_names(sim)
    given = {k for k in vals if k.isupper()}
    if consts - given:
        raise SystemExit(f"[simdoor] sim constants missing from the pack: {sorted(consts - given)}")
    if given - consts:
        raise SystemExit(f"[simdoor] pack values the sim does not have: {sorted(given - consts)}")
    for k in consts:
        setattr(sim, k, vals[k])
    sim.BANKING_RAD = None
    _sg_grip.apply(sim, float(vals["track.street_grip_k"]))
    _install_gain_cap(sim, float(vals["sim.gain_cap_kmh_s"]))
    return sim


def _install_gain_cap(sim, cap: float):
    """The sim's sanity check hard-codes GAIN median <= 32 km/h/s; allow up to `cap` for this
    track, every other sanity check unchanged (same rule as cache/_sim_singapore.py)."""
    orig = getattr(sim, "_assert_sanity_orig", sim.assert_sanity)
    sim._assert_sanity_orig = orig

    def assert_sanity(*a, **k):
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                orig(*a, **k)
        except SystemExit:
            lines = [l for l in err.getvalue().splitlines() if "[sanity] FAIL" in l]
            other = [l for l in lines if "GAIN rate median" not in l]
            g = [float(m.group(1)) for l in lines
                 for m in [re.search(r"GAIN rate median ([\d.]+)", l)] if m]
            sys.stderr.write(err.getvalue())
            if other or not g or g[0] > cap:
                raise
            print(f"[sanity] GAIN median {g[0]:.1f} <= track cap {cap} -> PASS")
        else:
            sys.stderr.write(err.getvalue())
    sim.assert_sanity = assert_sanity


def raw_lap(sim, raceline) -> float:
    """Bang-bang lap time of a line (the optimiser's and tuner's cost)."""
    arc, kappa, L = sim._arc_kappa_closed(raceline)
    with contextlib.redirect_stdout(io.StringIO()):
        return float(sim.simulate_lap(raceline, arc, kappa, L)[4][-1])


def final_lap(sim, raceline, vals: dict, csv_out: str | None = None, check: bool = True):
    """The shipped lap: bang-bang solve -> jerk-limited shape -> CSV (+ sanity), same order as
    sim_2026_lap.main(). Returns (v_ms, t_s, arc, track_length, mode)."""
    import numpy as np
    raceline = np.asarray(raceline, float)[:, :2]
    arc, kappa, L = sim._arc_kappa_closed(raceline)
    with contextlib.redirect_stdout(io.StringIO()):
        v, soc, mode, p_kw, t = sim.simulate_lap(raceline, arc, kappa, L)
        # the 2026 sim labels braking zones REGEN; off = shipped behaviour (no mask)
        bm = np.array([m == "REGEN" for m in mode]) if vals.get("sim.brake_preserve") else None
        v, t = sim.smooth_longitudinal(v, arc, L, win_s=0.45, brake_mask=bm)
        v, t = sim.suppress_microhumps(v, arc, L, t)
        if csv_out:
            sim.write_csv(csv_out, v, soc, mode, p_kw, t, arc, L, fps=30)
    if check:
        sim.assert_sanity(v, soc, mode, p_kw, t)
    return v, t, arc, L, mode
