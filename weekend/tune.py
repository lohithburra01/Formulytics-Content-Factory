"""Fixed tuning of the car numbers against the real lap's speed graph (grill D5, D21).

Each number is tuned ONLY against the feature group it controls (RULES below); the agent never
chooses what to change. One number at a time is solved to zero error (bracketed secant inside
its plausible range), sweeping over all rules until every group is inside tolerance. A number
whose error cannot reach zero inside its range is reported as a CONFLICT (never clamped silently).
"""
from __future__ import annotations

import os
import tempfile

import numpy as np

from weekend import features as F
from weekend import simdoor

# (pack name, feature group, selector on the reference feature, error key, kind)
# kind "kmh": error in km/h (median over the group); "pct": median % error.
# Sign: +1 means raising the number raises the sim's value (so error falls by lowering it).
RULES = [
    ("CDA_STRAIGHT_M2",     "straights",   lambda x: x["ref"] >= 290,                 "err",     "kmh", -1),
    ("CL_CORNER_M2",        "corners",     lambda x: x["ref"] >= 130,                 "err",     "kmh", +1),
    ("track.street_grip_k", "corners",     lambda x: x["ref"] < 130,                  "err",     "kmh", +1),
    ("MU_LONG",             "brake_bands", lambda x: x["band"][0] >= 200,             "err_pct", "pct", +1),
    ("TRAIL_FRAC_MIN",      "brake_bands", lambda x: x["band"][0] < 150,              "err_pct", "pct", +1),
    ("MU_DRIVE",            "accel_bands", lambda x: x["band"][1] <= 150,             "err_pct", "pct", +1),
]


def group_error(feats, group, sel, key):
    xs = [x[key] for x in feats[group] if sel(x) and x.get(key) is not None]
    return (float(np.median(xs)), len(xs)) if xs else (None, 0)


class Lap:
    """Evaluates a set of values on a fixed line: configure the sim, run the final lap, extract features."""

    def __init__(self, vals, raceline, ref, cfg):
        self.vals, self.rl, self.ref, self.cfg = dict(vals), np.asarray(raceline, float), ref, cfg
        self.n = 0
        self.tmp = tempfile.mkdtemp(prefix="tune_")

    def feats(self, vals):
        sim = simdoor.configure(vals)
        csv = os.path.join(self.tmp, "lap.csv")
        simdoor.final_lap(sim, self.rl, vals, csv_out=csv, check=False)
        self.n += 1
        return F.features(F.load(csv), self.ref, self.cfg), csv


def _solve(lap, vals, name, group, sel, key, sign, lo, hi, tol, max_eval):
    """1-D: find value in [lo, hi] with group error ~ 0. Returns (value, error, status)."""
    def err_at(x):
        v = dict(vals); v[name] = float(x)
        e, n = group_error(lap.feats(v)[0], group, sel, key)
        return e
    x0 = float(vals[name]); e0 = err_at(x0)
    if e0 is None:
        return x0, None, "no-features"
    if abs(e0) <= tol:
        return x0, e0, "ok"
    # step toward reducing the error; error falls when sign*dx*e0 < 0
    direction = -np.sign(e0) * sign
    a, ea = x0, e0
    span = hi - lo
    step = 0.1 * span
    b = float(np.clip(a + direction * step, lo, hi)); eb = err_at(b); n = 2
    while eb is not None and np.sign(eb) == np.sign(ea) and n < max_eval:
        if b in (lo, hi):
            return b, eb, "conflict"          # error keeps its sign at the range end
        a, ea = b, eb
        step *= 2
        b = float(np.clip(a + direction * step, lo, hi)); eb = err_at(b); n += 1
    if eb is None:
        return a, ea, "no-features"
    if np.sign(eb) == np.sign(ea):
        return (b, eb, "conflict") if b in (lo, hi) else (b, eb, "max-eval")
    # bracket [a, b]: secant / bisection
    while n < max_eval:
        x = b - eb * (b - a) / (eb - ea) if eb != ea else 0.5 * (a + b)
        if not (min(a, b) < x < max(a, b)):
            x = 0.5 * (a + b)
        ex = err_at(x); n += 1
        if ex is None:
            break
        if abs(ex) <= tol:
            return x, ex, "ok"
        if np.sign(ex) == np.sign(ea):
            a, ea = x, ex
        else:
            b, eb = x, ex
    x, ex = (a, ea) if abs(ea) < abs(eb) else (b, eb)
    return x, ex, "ok" if abs(ex) <= tol else "max-eval"


def tune(vals, ranges, raceline, ref, cfg, tol_kmh, tol_pct, max_sweeps, max_eval):
    """vals: sim values (start). ranges: name -> (lo, hi). Returns (tuned vals, report)."""
    vals = dict(vals)
    start = dict(vals)
    lap = Lap(vals, raceline, ref, cfg)
    history = []
    for sweep in range(1, max_sweeps + 1):
        rows = []
        for name, group, sel, key, kind, sign in RULES:
            lo, hi = ranges[name]
            tol = tol_kmh if kind == "kmh" else tol_pct
            x, e, status = _solve(lap, vals, name, group, sel, key, sign, lo, hi, tol, max_eval)
            if status == "conflict":          # D6: never leave a number pinned at its range end
                x = start[name]
            vals[name] = float(x)
            rows.append(dict(name=name, value=round(float(x), 6), error=None if e is None else round(e, 2),
                             unit="km/h" if kind == "kmh" else "%", status=status))
        feats, _ = lap.feats(vals)
        final = []
        for name, group, sel, key, kind, sign in RULES:
            e, n = group_error(feats, group, sel, key)
            tol = tol_kmh if kind == "kmh" else tol_pct
            final.append(dict(name=name, error=None if e is None else round(e, 2), n=n,
                              ok=e is not None and abs(e) <= tol))
        history.append(dict(sweep=sweep, solves=rows, after=final))
        if all(r["ok"] for r in final):
            break
    conflicts = [r for r in history[-1]["solves"] if r["status"] == "conflict"]
    return vals, dict(sweeps=len(history), sims=lap.n, history=history,
                      converged=all(r["ok"] for r in history[-1]["after"]), conflicts=conflicts)
