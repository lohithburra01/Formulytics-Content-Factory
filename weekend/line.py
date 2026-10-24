"""Racing line from the pack: minimum-lap-time lateral offsets from the base line (knots every
`every` stations, periodic spline), parallel pattern search, cost = the tuned car's bang-bang lap
+ corridor violation + smoothness + inside-apex touch + the user's line rules.

A line rule is direction-only (grill D6): (corner apex position, phase entry|apex|exit, side
inside|outside). The window and the side are derived from the base line's corners; the optimiser
decides the amount. Rules are hard: if the result does not reach the side, the rule weight is
raised and the search continues (up to `rule_retries`), else the violation is reported.
Re-uses cache/era2017/_opt_line_2017.py (corridor, knots) and cache/bahrain/_apex_gaps.py (corners).
"""
from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (ROOT, os.path.join(ROOT, "cache", "era2017"), os.path.join(ROOT, "cache", "bahrain")):
    if p not in sys.path:
        sys.path.insert(0, p)
import _opt_line_2017 as O  # noqa: E402
import _apex_gaps as AG  # noqa: E402

_SIM = {}


def _init(state, vals):
    O.init(state)
    from weekend import simdoor
    _SIM["sim"] = simdoor.configure(vals)


def _lap(rl):
    from weekend import simdoor
    return simdoor.raw_lap(_SIM["sim"], rl)


def _offsets(rl):
    return np.einsum("ij,ij->i", rl - O.G["P"], O.G["N"])


def rule_gaps(off):
    """Per rule: min distance (m) from the line to the required bound inside its window."""
    out = []
    for rule in O.G.get("rules", []):
        idx, side = rule[0], rule[1]
        f = rule[2] if len(rule) > 2 else 1.0        # how far across toward that side (1 = the edge bound)
        lo, hi = O.G["lo"][idx], O.G["hi"][idx]
        g = np.maximum(lo + f * (hi - lo) - off[idx], 0.0) if side > 0 else np.maximum(off[idx] - (hi - f * (hi - lo)), 0.0)
        out.append(float(g.min()))
    return out


def cost(k):
    k = np.asarray(k)
    rl, viol = O.line_of(k)
    try:
        lap = _lap(rl)
    except Exception:
        return 1e6
    d2 = np.roll(k, -1) - 2 * k + np.roll(k, 1)
    c = lap + 2.0 * viol + O.G["smooth_w"] * float((d2 ** 2).sum())
    off = _offsets(rl)
    tol = O.G["apex_tol"]
    for g, w in zip(rule_gaps(off), O.G.get("rule_w", [])):
        c += w * max(g - tol, 0.0) ** 2
    if O.G["apex_w"] > 0:
        g = AG.apex_terms(off, O.G["apex_pk"], O.G["apex_kap"], O.G["apex_win"])
        c += O.G["apex_w"] * float((np.maximum(g - tol, 0) ** 2).sum())
    return c


def setup(base_rl_file, outline_file, prm):
    O.setup(base_rl_file, outline_file, None, None, prm["margin_m"], prm["every"])
    O.G.update(smooth_w=prm["smooth_w"], apex_w=prm["apex_w"], apex_tol=prm["apex_tol_m"],
               apex_win=prm["apex_win"])
    K = len(O.G["kidx"])
    pk, kap = AG.corners(O.line_of(np.zeros(K))[0], O.G["arc"], O.G["L"])   # one corner set: the base line's
    O.G.update(apex_pk=pk, apex_kap=kap)
    return K


def corner_table():
    arc = O.G["arc"]
    return [dict(n=n, apex_m=round(float(arc[i]), 1), turn="left" if O.G["apex_kap"][i] > 0 else "right")
            for n, i in enumerate(O.G["apex_pk"], 1)]


def resolve_rules(rules, prm):
    """rules: [{apex_m, phase, side, label}] -> station windows + required bound (+1 hi / -1 lo)."""
    arc = O.G["arc"][:len(O.G["P"])]; L = O.G["L"]; pk = O.G["apex_pk"]
    apexes = [float(arc[i]) for i in pk]
    out = []
    for r in rules:
        j = int(np.argmin([min(abs(a - r["apex_m"]), L - abs(a - r["apex_m"])) for a in apexes]))
        i_ap = pk[j]
        inside = 1 if O.G["apex_kap"][i_ap] > 0 else -1          # hi side is inside for a left (kappa>0)
        side = inside if r["side"] == "inside" else -inside
        a0, a1 = prm["rule_window_frac"]
        if r["phase"] == "entry":
            prev = apexes[j - 1] if j > 0 else apexes[-1] - L
            gap = apexes[j] - prev
            lo_m, hi_m = prev + a0 * gap, prev + a1 * gap
        elif r["phase"] == "exit":
            nxt = apexes[j + 1] if j + 1 < len(apexes) else apexes[0] + L
            gap = nxt - apexes[j]
            lo_m, hi_m = apexes[j] + (1 - a1) * gap, apexes[j] + (1 - a0) * gap
        elif r["phase"] == "at":          # a point on the lap (e.g. a second apex the base line merged away)
            lo_m, hi_m = r["apex_m"] - 10.0, r["apex_m"] + 10.0
        else:
            w = prm["apex_win"]
            idx = np.arange(i_ap - w, i_ap + w + 1) % len(arc)
            out.append(dict(rule=r, corner=j + 1, idx=idx, side=side, window_m=None)); continue
        lo_m, hi_m = lo_m % L, hi_m % L
        idx = np.where((arc >= lo_m) & (arc <= hi_m))[0] if lo_m <= hi_m else \
            np.where((arc >= lo_m) | (arc <= hi_m))[0]
        out.append(dict(rule=r, corner=j + 1, idx=idx, side=side, window_m=[round(lo_m, 1), round(hi_m, 1)]))
    return out


def seed_rules(k, resolved, frac):
    """Move the knots inside each rule window toward its required bound (direction only; the
    optimiser then settles the amount) - same blend as cache/singapore/_seed_wide.py."""
    k = k.copy(); ka = O.G["arc"][O.G["kidx"]]
    lo = O.G["lo"][O.G["kidx"]]; hi = O.G["hi"][O.G["kidx"]]
    for r in resolved:
        if r["window_m"] is None:
            continue
        a0, a1 = r["window_m"]
        if a1 < a0:
            continue
        tgt = hi if r["side"] > 0 else lo
        w = np.clip(np.sin(np.pi * (ka - a0) / (a1 - a0)), 0, None) ** 0.5 * ((ka > a0) & (ka < a1))
        k = k + frac * w * (tgt - k)
    return k


def optimise(vals, base_rl_file, outline_file, prm, rules, init_knots=None, steps=None, log=print, rule_w0=None,
             only_m=None):
    K = setup(base_rl_file, outline_file, prm)
    resolved = resolve_rules(rules, prm)
    O.G["rules"] = [(r["idx"], r["side"], r["rule"].get("frac", 1.0)) for r in resolved]
    # weights learned by an earlier call (previous tune<->line round) carry over: no re-climbing from 1.5
    O.G["rule_w"] = list(rule_w0) if rule_w0 is not None and len(rule_w0) == len(resolved) else [prm["rule_w"]] * len(resolved)
    k = np.zeros(K) if init_knots is None else np.asarray(init_knots, float)
    if resolved and init_knots is None:
        k = seed_rules(k, resolved, prm["rule_seed_frac"])
    steps = steps or prm["steps_first"]
    t0 = time.time(); retries = 0
    local = None          # on a retry: only the knots near the unmet rules move (the rest of the lap is done)
    if only_m is not None:   # fix one stretch of an existing line: only knots inside [lo_m, hi_m] move
        ka = O.G["arc"][O.G["kidx"]]
        local = [j for j, a_ in enumerate(ka) if only_m[0] <= a_ <= only_m[1]]
    while True:
        state = dict(O.G)
        with ProcessPoolExecutor(prm["workers"], initializer=_init, initargs=(state, vals)) as ex:
            best = list(ex.map(cost, [k]))[0]; base = best
            log(f"[line] start {best:.3f}  rules {len(resolved)}  w {O.G['rule_w']}")
            for step in steps:
                for sw in range(prm["max_sweeps"]):
                    cands = [(i, s) for i in (range(K) if local is None else local) for s in (step, -step)]
                    cs = []
                    for i, s in cands:
                        c = k.copy(); c[i] += s; cs.append(c)
                    res = list(ex.map(cost, cs, chunksize=4))
                    imp = sorted((r, i, s) for (i, s), r in zip(cands, res) if r < best - prm["accept_s"])
                    if not imp:
                        break
                    chosen, used = [], set()
                    for r, i, s in imp:
                        if all(abs(i - j) >= 3 and abs(i - j) <= K - 3 for j in used):
                            chosen.append((i, s)); used.add(i)
                    comb = k.copy()
                    for i, s in chosen:
                        comb[i] += s
                    rc = list(ex.map(cost, [comb]))[0]
                    if rc < imp[0][0]:
                        k, best = comb, rc
                    else:
                        k = k.copy(); k[imp[0][1]] += imp[0][2]; best = imp[0][0]
                    log(f"[line] step {step} sweep {sw}: {best:.3f} (-{base - best:.3f}) t {time.time() - t0:.0f}s")
        rl, viol = O.line_of(k)
        gaps = rule_gaps(_offsets(rl))
        bad = [i for i, g in enumerate(gaps) if g > prm["apex_tol_m"]]
        if not bad or retries >= prm["rule_retries"]:
            break
        retries += 1
        for i in bad:
            O.G["rule_w"][i] *= 4.0
        steps = steps[-2:]
        ka, near = O.G["arc"][O.G["kidx"]], set()
        for i in bad:
            ra = O.G["arc"][resolved[i]["idx"]]
            lo_m, hi_m = float(ra.min()) - prm["rule_local_m"], float(ra.max()) + prm["rule_local_m"]
            near |= {j for j, a_ in enumerate(ka) if lo_m <= a_ <= hi_m}
        local = sorted(near)
        log(f"[line] rule(s) {bad} not reached (gaps {[round(gaps[i], 2) for i in bad]} m) -> weight x4, retry {retries}")
    _init(dict(O.G), vals)
    off = _offsets(rl)
    apex = AG.apex_terms(off, O.G["apex_pk"], O.G["apex_kap"], O.G["apex_win"])
    report = dict(cost=best, pure_lap_s=_lap(rl), violation_m=viol, seconds=round(time.time() - t0),
                  rule_w=list(O.G["rule_w"]),
                  corners=[dict(c, apex_gap_m=round(float(g), 3)) for c, g in zip(corner_table(), apex)],
                  rules=[dict(label=r["rule"].get("label"), corner=r["corner"], phase=r["rule"]["phase"],
                              side=r["rule"]["side"], window_m=r["window_m"], gap_m=round(g, 3),
                              satisfied=g <= prm["apex_tol_m"]) for r, g in zip(resolved, gaps)])
    return k, rl, report


def line_change_m(k_a, k_b):
    """Max lateral difference between two knot vectors' lines (m)."""
    ra, _ = O.line_of(np.asarray(k_a)); rb, _ = O.line_of(np.asarray(k_b))
    return float(np.max(np.linalg.norm(ra - rb, axis=1)))
