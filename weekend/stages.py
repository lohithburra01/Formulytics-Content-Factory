"""All pipeline stages, registered with weekend.pipeline. Each reads only what it declares."""
from __future__ import annotations

import json
import os

import numpy as np

from weekend.pipeline import SIM, stage
from weekend import simdoor


def write_raceline(path, raceline, arc, kappa, L):
    """Same JSON shape the sim writes (raceline, arc_length, kappa, track_length_m, banking_deg)."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"raceline": np.asarray(raceline).tolist(), "arc_length": np.asarray(arc).tolist(),
                   "kappa": np.asarray(kappa).tolist(), "track_length_m": float(L),
                   "banking_deg": []}, f)


def lap_summary(csv_path):
    import csv
    with open(csv_path, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return dict(lap_s=float(rows[-1]["time_s"]), vmax_kmh=max(float(r["speed"]) for r in rows),
                vmin_kmh=min(float(r["speed"]) for r in rows))


@stage("final_fixed", reads=[SIM, "line.fixed_raceline_file"])
def final_fixed(p, out, up, weekend):
    """Final lap on a fixed, already S/F-aligned line (the shipped v4b step)."""
    sim = simdoor.configure(p.sim_vals())
    with open(p.file("line.fixed_raceline_file"), encoding="utf-8") as fh:
        rl = np.asarray(json.load(fh)["raceline"], float)[:, :2]
    arc, kappa, L = sim._arc_kappa_closed(rl)
    write_raceline(os.path.join(out, "raceline.json"), rl, arc, kappa, L)
    simdoor.final_lap(sim, rl, p.sim_vals(), csv_out=os.path.join(out, "lap.csv"))
    return lap_summary(os.path.join(out, "lap.csv"))


# ---- track geometry (official map-matched path; the SVG only fixes the frame) -----------------

def _official_path(samples, ref_drv, svg_centre, dedup_m, sigma, step_m, n_frac, shift_max):
    """cache/singapore/_official_path.py as a function (same maths, same order)."""
    from scipy.ndimage import gaussian_filter1d
    ref = np.array([[r["x"], r["y"]] for r in samples if r["drv"] == ref_drv], float) / 10.0
    allp = np.array([[r["x"], r["y"]] for r in samples], float) / 10.0
    seg = np.diff(ref, axis=0); sl = np.linalg.norm(seg, axis=1); cum = np.r_[0, np.cumsum(sl)]

    def proj(p):
        a = ref[:-1]; u = np.clip(np.einsum("ij,ij->i", p - a, seg) / np.maximum(sl ** 2, 1e-9), 0, 1)
        q = a + u[:, None] * seg; k = np.argmin(np.linalg.norm(q - p, axis=1))
        return cum[k] + u[k] * sl[k], np.linalg.norm(q[k] - p)
    pr = np.array([proj(p) for p in allp]); P = allp[np.argsort(pr[:, 0])]
    P = P[np.r_[True, np.linalg.norm(np.diff(P, axis=0), axis=1) > dedup_m]]
    Ps = np.column_stack([gaussian_filter1d(P[:, 0], sigma, mode="wrap"),
                          gaussian_filter1d(P[:, 1], sigma, mode="wrap")])
    c = np.r_[0, np.cumsum(np.linalg.norm(np.diff(np.vstack([Ps, Ps[:1]]), axis=0), axis=1))]; Lp = c[-1]
    u = np.arange(0, Lp, step_m)
    Q = np.column_stack([np.interp(u, c, np.r_[Ps[:, 0], Ps[0, 0]]), np.interp(u, c, np.r_[Ps[:, 1], Ps[0, 1]])])
    Cc = svg_centre
    cc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(np.vstack([Cc, Cc[:1]]), axis=0), axis=1))]; Lc = cc[-1]
    f = np.linspace(0, 1, n_frac, endpoint=False)
    A = np.column_stack([np.interp(f * Lp, u, Q[:, 0]), np.interp(f * Lp, u, Q[:, 1])])
    B = np.column_stack([np.interp(f * Lc, cc, np.r_[Cc[:, 0], Cc[0, 0]]), np.interp(f * Lc, cc, np.r_[Cc[:, 1], Cc[0, 1]])])
    best = None
    for sh in range(-shift_max, shift_max + 1):
        Ar = np.roll(A, sh, axis=0); ma, mb = Ar.mean(0), B.mean(0); X, Y = Ar - ma, B - mb
        U, Sg, Vt = np.linalg.svd(X.T @ Y); R = (U @ Vt).T
        if np.linalg.det(R) < 0:
            continue
        s = Sg.sum() / (X ** 2).sum(); err = np.sqrt(((s * X @ R.T - Y) ** 2).sum(1).mean())
        if best is None or err < best[0]:
            best = (err, sh, R, s, ma, mb)
    err, sh, R, s, ma, mb = best
    return s * (Q - ma) @ R.T + mb, dict(length_m=float(Lp), scale=float(s), rms_m=float(err),
                                         sf_shift_m=float(sh * Lp / n_frac))


@stage("track", reads=["track."], code=["svg_to_outline.py"])
def track(p, out, up, weekend):
    """SVG frame -> roll -> official path aligned onto it -> FIA length, min radius, edges, mirror."""
    import svg_to_outline as SO
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        o, i = SO.build_outline_from_svg(p.file("track.svg_file"), p["track.svg_frame_length_m"],
                                         p["track.svg_road_width_m"], p["track.svg_min_radius_m"])
    c = (o + i) / 2                                   # roll so index 0 ~ the real S/F (frame only)
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(c, axis=0), axis=1))]
    k = int(np.argmin(np.abs(s - p["track.svg_sf_arc_m"])))
    o, i = np.roll(o, -k, axis=0), np.roll(i, -k, axis=0)
    # the shipped chain round-trips the frame outline through JSON; keep that exact
    o, i = np.array(json.loads(json.dumps(o.tolist()))), np.array(json.loads(json.dumps(i.tolist())))
    with open(p.file("track.path_samples_file"), encoding="utf-8") as fh:
        samples = json.load(fh)
    Q, info = _official_path(samples, p["track.path_ref_driver"], (o + i) / 2, p["track.path_dedup_m"],
                             p["track.path_sigma"], p["track.path_step_m"], p["track.path_align_samples"],
                             p["track.path_sf_shift_max"])
    Q = np.array(json.loads(json.dumps(Q.tolist())))
    mb = Q.mean(0); Q = mb + (p["track.length_m"] / info["length_m"] / info["scale"]) * (Q - mb)
    cq = np.r_[0, np.cumsum(np.linalg.norm(np.diff(np.vstack([Q, Q[:1]]), axis=0), axis=1))]
    u = np.linspace(0, cq[-1], p["track.stations"], endpoint=False)
    C = np.column_stack([np.interp(u, cq, np.r_[Q[:, k], Q[0, k]]) for k in (0, 1)])
    C = SO.limit_min_radius(C, p["track.min_radius_m"])
    a, b = SO.generate_edges_constant_width(C, p["track.asbuilt_width_m"]); C = (a + b) / 2
    O, I = SO.generate_edges_constant_width(C, p["track.width_m"])
    with open(os.path.join(out, "outline.json"), "w") as fh:
        json.dump(dict(outer=O.tolist(), inner=I.tolist()), fh)
    m = np.array([-1.0, 1.0]) if p["track.mirror_x"] else np.array([1.0, 1.0])
    with open(os.path.join(out, "sim_outline.json"), "w") as fh:
        json.dump(dict(outer=(O * m).tolist(), inner=(I * m).tolist()), fh)
    return dict(official_path=info, mirror_x=bool(p["track.mirror_x"]))


# ---- base line: the sim's own min-curvature line, the corridor reference for the optimiser ----

@stage("base_line", reads=[SIM, "line.base_inset_m", "ref.q2025_csv_file"], needs=["track"])
def base_line(p, out, up, weekend):
    sim = simdoor.configure(p.sim_vals())
    with open(os.path.join(up["track"], "sim_outline.json"), encoding="utf-8") as fh:
        o = json.load(fh)
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        rl, arc, kappa, L = sim.build_raceline(np.array(o["outer"], float), np.array(o["inner"], float),
                                               inset_m=p["line.base_inset_m"])
        sf = sim.locate_start_finish(rl, kappa, p.file("ref.q2025_csv_file"))
    if sf:
        rl = np.roll(rl, -sf, axis=0); kappa = np.roll(kappa, -sf)
        seg = np.linalg.norm(np.diff(np.vstack([rl, rl[0]]), axis=0), axis=1)
        arc = np.concatenate([[0.0], np.cumsum(seg)])[:-1]
    write_raceline(os.path.join(out, "raceline.json"), rl, arc, kappa, L)
    return dict(stations=len(rl), length_m=float(L), sf_index=int(sf or 0))


# ---- references and the lap-time target (grill D3, D21) ------------------------------------

@stage("refs", reads=["ref."], needs=["track"], code=["cache/_track_registry.py"])
def refs(p, out, up, weekend):
    """Shape reference = 2026 FP1 trace when it exists (D21), else none (pre-FP1: predicted targets).
    Lap-time target band = FP1 - [hi, lo] s when FP1 exists, else 2025 Q + [lo, hi] s (D3)."""
    has_fp1 = "ref.fp1_csv_file" in p
    if has_fp1:
        base, (a, b) = p["ref.fp1_lap_s"], p["ref.target_fp1_minus_s"]
        band, branch = [round(base - b, 3), round(base - a, 3)], "fp1"
        shape = p.file("ref.fp1_csv_file")
    else:
        base, (a, b) = p["ref.q2025_lap_s"], p["ref.target_q2025_plus_s"]
        band, branch = [round(base + a, 3), round(base + b, 3)], "q2025"
        shape = None
    res = dict(target_band_s=band, target_s=round(sum(band) / 2, 3), branch=branch,
               shape_ref_csv="shape_ref.csv" if shape else None)
    if shape:
        import shutil
        shutil.copyfile(shape, os.path.join(out, "shape_ref.csv"))
    return res


# ---- tuning + racing line, repeated until the line stops moving (grill D5, D6) ----------------

def _check_cfg(p):
    c = p.prefixed("check.")
    return dict(window_frac=c["window_frac"], corner_prominence_kmh=c["corner_prominence_kmh"],
                corner_sep_m=c["corner_sep_m"], onset_drop_kmh=c["onset_drop_kmh"],
                exit_gain_kmh=c["exit_gain_kmh"], brake_bands=_bands(c["brake_bands_kmh"]),
                accel_bands=_bands(c["accel_bands_kmh"]))


def _bands(edges):
    e = sorted(edges)
    return [[e[i], e[i + 1]] for i in range(len(e) - 1)]


def _rules(p):
    out = []
    for k, v in sorted(p.prefixed("line.rule.").items()):
        label, apex_m, phase, side = v.split("|")
        out.append(dict(label=label, apex_m=float(apex_m), phase=phase, side=side))
    return out


def _line_prm(p):
    x = p.prefixed("line.")
    return dict(margin_m=x["margin_m"], every=x["every"], smooth_w=x["smooth_w"], apex_w=x["apex_w"],
                apex_tol_m=x["apex_tol_m"], apex_win=x["apex_win"], steps_first=x["steps_first"],
                steps_next=x["steps_next"], max_sweeps=x["max_sweeps"], accept_s=x["accept_s"],
                workers=x["workers"], rule_w=x["rule_w"], rule_window_frac=x["rule_window_frac"],
                rule_seed_frac=x["rule_seed_frac"], rule_retries=x["rule_retries"])


@stage("car_and_line", reads=[SIM, "fit.", "check.", "line."], needs=["track", "base_line", "refs"],
       code=["weekend/tune.py", "weekend/line.py", "weekend/features.py", "cache/_gate_2026.py",
             "cache/_track_registry.py", "cache/era2017/_opt_line_2017.py", "cache/bahrain/_apex_gaps.py"])
def car_and_line(p, out, up, weekend):
    from weekend import tune as T, line as LN, features as F
    log = open(os.path.join(out, "progress.txt"), "a", buffering=1)
    say = lambda m: (print(m, flush=True), log.write(m + "\n"))  # noqa: E731
    vals = p.sim_vals()
    ranges = {k: tuple(v) for k, v in p.prefixed("fit.range.").items()}
    ref = F.load(os.path.join(up["refs"], "shape_ref.csv"))
    cfg = _check_cfg(p); prm = _line_prm(p); rules = _rules(p)
    base_file = os.path.join(up["base_line"], "raceline.json")
    outline = os.path.join(up["track"], "sim_outline.json")
    with open(base_file, encoding="utf-8") as fh:
        rl = np.asarray(json.load(fh)["raceline"], float)[:, :2]
    tun = lambda v, line: T.tune(v, ranges, line, ref, cfg, p["fit.tol_kmh"], p["fit.tol_pct"],  # noqa: E731
                                 p["fit.max_sweeps"], p["fit.max_eval"])
    vals, rep = tun(vals, rl); rounds = [dict(round=0, line="base", tune=rep)]
    say(f"[car_and_line] round 0 tuned on the base line: converged={rep['converged']} sims={rep['sims']}")
    knots = None
    for rnd in range(1, p["line.max_rounds"] + 1):
        k, rl, lrep = LN.optimise(vals, base_file, outline, prm, rules, init_knots=knots,
                                  steps=prm["steps_first"] if knots is None else prm["steps_next"], log=say)
        change = None if knots is None else LN.line_change_m(knots, k)
        vals, rep = tun(vals, rl)
        rounds.append(dict(round=rnd, line=lrep, tune=rep, line_change_m=change))
        np.save(os.path.join(out, f"knots_{rnd}.npy"), k)
        say(f"[car_and_line] round {rnd}: pure lap {lrep['pure_lap_s']:.3f}s, line change "
            f"{change if change is None else round(change, 2)} m, tune converged={rep['converged']}")
        knots = k
        if change is not None and change < p["line.fixed_point_tol_m"]:
            break
    np.save(os.path.join(out, "knots.npy"), knots)
    with open(os.path.join(out, "raceline.json"), "w") as fh:
        json.dump({"raceline": rl.tolist()}, fh)
    with open(os.path.join(out, "car.json"), "w") as fh:
        json.dump({k: vals[k] for k in ranges}, fh, indent=1)
    with open(os.path.join(out, "rounds.json"), "w") as fh:
        json.dump(rounds, fh, indent=1, default=float)
    fixed = rounds[-1].get("line_change_m") is not None and rounds[-1]["line_change_m"] < p["line.fixed_point_tol_m"]
    return dict(rounds=len(rounds) - 1, fixed_point=bool(fixed), car={k: round(vals[k], 6) for k in ranges},
                conflicts=rounds[-1]["tune"]["conflicts"], rules=rounds[-1]["line"]["rules"],
                pure_lap_s=rounds[-1]["line"]["pure_lap_s"])


import weekend.stages_finish  # noqa: E402,F401  (registers time_knob, final, checks, video)
