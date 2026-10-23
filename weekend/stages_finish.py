"""Stages after the racing line: time knob (grill D6), final lap, checks report (D7), video."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

import numpy as np

from weekend import simdoor
from weekend.pipeline import ROOT, SIM, stage
from weekend.stages import _check_cfg, _line_prm, _rules, lap_summary, write_raceline

LINE_CODE = ["weekend/line.py", "cache/era2017/_opt_line_2017.py", "cache/bahrain/_apex_gaps.py"]


def _lap_time(vals, rl):
    sim = simdoor.configure(vals)
    v, t, arc, L, mode = simdoor.final_lap(sim, rl, vals, check=False)
    return float(t[-1] + (arc[0] + L - arc[-1]) / max(v[-1], 1.0))


def _pattern(vals, rl, ref):
    """Speed-pattern match of this car + line to the real reference lap (grill D24)."""
    from weekend import features as F
    sim = simdoor.configure(vals)
    v, t, arc, L, mode = simdoor.final_lap(sim, rl, vals, check=False)
    return F.pattern_score(dict(v=np.asarray(v), s=np.asarray(arc) - arc[0]), ref)


def _solve_knob(vals, rl, name, target, span, iters):
    """Value of `name` that puts the final lap on `target` s: bisection in start*(1 -+ span)."""
    x0 = float(vals[name])
    f = lambda x: _lap_time(dict(vals, **{name: x}), rl) - target  # noqa: E731
    lo, hi = x0 * (1 - span), x0 * (1 + span)
    flo, fhi = f(lo), f(hi)
    if flo * fhi > 0:
        return None
    for _ in range(iters):
        m = 0.5 * (lo + hi); fm = f(m)
        if flo * fm <= 0:
            hi, fhi = m, fm
        else:
            lo, flo = m, fm
    return 0.5 * (lo + hi)


@stage("time_knob", reads=[SIM, "knob.", "line.", "fit.range."],
       needs=["track", "base_line", "refs", "car_and_line"], code=LINE_CODE)
def time_knob(p, out, up, weekend):
    """Pattern first, lap time second (grill D24). A lap already inside the target band keeps the
    tuned car. Otherwise the gap goes into ONE knob, chosen by a test (least line change), but only
    among candidates that keep the speed pattern at least as close to the real lap; if none does,
    no knob is applied and the gap is reported as a conflict for the user."""
    from weekend import features as F
    from weekend import line as LN
    with open(os.path.join(up["refs"], "done.json"), encoding="utf-8") as fh:
        R = json.load(fh)
    target, (lo, hi) = R["target_s"], R["target_band_s"]
    ref = F.load(os.path.join(up["refs"], R["shape_ref_csv"]))
    vals = p.sim_vals()
    with open(os.path.join(up["car_and_line"], "car.json"), encoding="utf-8") as fh:
        vals.update(json.load(fh))
    base_file = os.path.join(up["base_line"], "raceline.json")
    outline = os.path.join(up["track"], "sim_outline.json")
    prm = _line_prm(p); rules = _rules(p)
    LN.setup(base_file, outline, prm)
    k0 = np.load(os.path.join(up["car_and_line"], "knots.npy"))
    rl0, _ = LN.O.line_of(k0)
    lap0 = _lap_time(vals, rl0)
    score0 = _pattern(vals, rl0, ref)
    tests = []
    names = [] if lo <= lap0 <= hi else p["knob.candidates"].split(",")
    for name in names:
        x = _solve_knob(vals, rl0, name, target, p["knob.span"], p["knob.iters"])
        if x is None:
            tests.append(dict(name=name, reachable=False)); continue
        v2 = dict(vals, **{name: x})
        prm2 = dict(prm, max_sweeps=p["knob.reopt_sweeps"], rule_retries=0)
        k, rl, rep = LN.optimise(v2, base_file, outline, prm2, rules, init_knots=k0,
                                 steps=p["knob.reopt_steps"], log=lambda m: None)
        change = LN.line_change_m(k0, k)
        x2 = _solve_knob(v2, rl, name, target, p["knob.span"], p["knob.iters"])
        xv = float(x2 if x2 is not None else x)
        score = _pattern(dict(v2, **{name: xv}), rl, ref)
        tests.append(dict(name=name, reachable=True, start=float(vals[name]), value=xv, scale=xv / float(vals[name]),
                          line_change_m=round(change, 3), pattern=round(score, 4),
                          keeps_pattern=score >= score0 - p["knob.max_pattern_drop"],
                          knots=k.tolist(), rules=rep["rules"]))
    ok = [t for t in tests if t["reachable"] and t["keeps_pattern"]]
    chosen = min(ok, key=lambda t: t["line_change_m"]) if ok else None
    conflict = None
    if names and not chosen:
        conflict = dict(lap_s=round(lap0, 3), target_band_s=[lo, hi], pattern=round(score0, 4),
                        note="no time knob reaches the band without worsening the speed pattern; user decides")
    k = np.array(chosen["knots"]) if chosen else k0
    if chosen:
        vals[chosen["name"]] = chosen["value"]
    np.save(os.path.join(out, "knots.npy"), k)
    names = list(p.prefixed("fit.range.")) + ([chosen["name"]] if chosen else [])
    with open(os.path.join(out, "car.json"), "w") as fh:
        json.dump({n: vals[n] for n in names}, fh, indent=1)
    for t in tests:
        t.pop("knots", None)
    return dict(target_s=target, lap_before_s=round(lap0, 3), pattern_before=round(score0, 4), tests=tests,
                conflict=conflict, rules=chosen["rules"] if chosen else None,
                knob=None if not chosen else dict(name=chosen["name"], value=chosen["value"], scale=chosen["scale"],
                                                  origin="FITTED", note="time knob: tuned to the lap-time target, not physics"))


@stage("final", reads=[SIM, "line.", "fit.range."], needs=["track", "base_line", "time_knob"], code=LINE_CODE)
def final(p, out, up, weekend):
    from weekend import line as LN
    vals = p.sim_vals()
    with open(os.path.join(up["time_knob"], "car.json"), encoding="utf-8") as fh:
        vals.update(json.load(fh))
    LN.setup(os.path.join(up["base_line"], "raceline.json"), os.path.join(up["track"], "sim_outline.json"), _line_prm(p))
    rl, _ = LN.O.line_of(np.load(os.path.join(up["time_knob"], "knots.npy")))
    sim = simdoor.configure(vals)
    arc, kappa, L = sim._arc_kappa_closed(rl)
    write_raceline(os.path.join(out, "sim_raceline.json"), rl, arc, kappa, L)
    with open(os.path.join(up["track"], "done.json"), encoding="utf-8") as fh:
        mirrored = json.load(fh)["mirror_x"]
    m = np.array([-1.0, 1.0]) if mirrored else np.array([1.0, 1.0])
    write_raceline(os.path.join(out, "raceline.json"), rl * m, arc, (-kappa if mirrored else kappa), L)
    simdoor.final_lap(sim, rl, vals, csv_out=os.path.join(out, "lap.csv"), check=True)
    with open(os.path.join(out, "car.json"), "w") as fh:
        json.dump(vals, fh, indent=1, sort_keys=True)
    return lap_summary(os.path.join(out, "lap.csv"))


@stage("checks", reads=["check.", "fit.", "ref.", "gate."], needs=["refs", "final", "car_and_line", "time_knob"],
       code=["weekend/features.py", "cache/_gate_2026.py", "cache/_track_registry.py"])
def checks(p, out, up, weekend):
    from weekend import features as F
    lap_csv = os.path.join(up["final"], "lap.csv")
    sim, ref = F.load(lap_csv), F.load(os.path.join(up["refs"], "shape_ref.csv"))
    with open(os.path.join(up["refs"], "done.json"), encoding="utf-8") as fh:
        R = json.load(fh)
    feats = F.features(sim, ref, _check_cfg(p))
    sig = F.signature(lap_csv)
    lap = float(sim["t"][-1])
    lo, hi = R["target_band_s"]
    res = dict(lap_s=lap, target_band_s=R["target_band_s"], lap_in_band=lo <= lap <= hi,
               pattern=round(F.pattern_score(sim, ref), 4))
    if "ref.fp1_sectors_s" in p:
        fp1 = p["ref.fp1_sectors_s"]; scale = R["target_s"] / sum(fp1)
        _, simsec = F.sectors(sim, fp1, ref)
        res["sectors"] = [dict(n=i + 1, sim_s=s, fp1_s=f, target_s=round(f * scale, 3), gap_s=round(s - f * scale, 3))
                          for i, (s, f) in enumerate(zip(simsec, fp1))]
    g = p.prefixed("gate.")

    def band(name, v, lo_, hi_):
        return dict(name=name, value=round(v, 2), band=[lo_, hi_],
                    ok=(lo_ is None or v >= lo_) and (hi_ is None or v <= hi_))
    res["gate"] = [band("GAIN median km/h/s", sig["gain_med"], *g["gain_med_kmh_s"]),
                   band("GAIN peak km/h/s", sig["gain_peak"], None, g["gain_peak_max_kmh_s"]),
                   band("DROP median km/h/s", sig["drop_med"], *g["drop_med_kmh_s"]),
                   band("DROP peak km/h/s", sig["drop_peak"], g["drop_peak_min_kmh_s"], None),
                   band("SUPERCLIP fraction", sig["superclip_frac"], None, g["superclip_frac_max"]),
                   band("SUPERCLIP peak km/h/s", sig["superclip_peak"], g["superclip_peak_min_kmh_s"], None)]
    with open(os.path.join(up["car_and_line"], "done.json"), encoding="utf-8") as fh:
        cl = json.load(fh)
    with open(os.path.join(up["time_knob"], "done.json"), encoding="utf-8") as fh:
        tk = json.load(fh)
    rules = tk["rules"] or cl["rules"]
    flagged = [c for c in feats["corners"] if abs(c["err"]) > p["check.flag_kmh"]]
    shape_csv = os.path.join(up["refs"], "shape_ref.csv")
    segs = F.segment_shapes(lap_csv, shape_csv, p["check.segment_prominence_kmh"], p["check.segment_rmse_kmh"])
    clips = F.clip_match(lap_csv, shape_csv, p["check.clip_match_m"])
    res.update(features=feats, line_rules=rules, tuning_conflicts=cl["conflicts"], fixed_point=cl["fixed_point"],
               knob=tk["knob"], knob_conflict=tk.get("conflict"), corners_flagged=flagged, segments=segs, clips=clips)
    # user rule 2026-10-23: corner by corner, never the whole-lap correlation alone (spec D28)
    res["all_ok"] = bool(res["lap_in_band"] and all(x["ok"] for x in res["gate"]) and all(r["satisfied"] for r in rules)
                         and not flagged and all(x["ok"] for x in segs) and clips["ok"])
    with open(os.path.join(out, "report.json"), "w") as fh:
        json.dump(res, fh, indent=1, default=float)
    return dict(all_ok=res["all_ok"], lap_s=lap, lap_in_band=res["lap_in_band"],
                gate_ok=all(x["ok"] for x in res["gate"]), rules_ok=all(r["satisfied"] for r in rules),
                sectors=res.get("sectors"), corners_flagged=len(flagged), knob=tk["knob"],
                pattern=res["pattern"], knob_conflict=tk.get("conflict"),
                segments_bad=[x for x in segs if not x["ok"]], clips_ok=clips["ok"])


@stage("video", reads=["video."], needs=["track", "final", "refs"], code=["raceline_video.py"])
def video(p, out, up, weekend):
    """D25: the LAP TIME text is the decided time (refs target), not the sim's own lap; motion is unchanged."""
    with open(os.path.join(up["refs"], "done.json"), encoding="utf-8") as fh:
        decided_s = json.load(fh)["target_s"]
    for k in ("video.font_bold_file", "video.font_regular_file"):
        path = os.path.normpath(os.path.join(ROOT, p[k]))
        with open(path, "rb") as fh:
            if hashlib.sha256(fh.read()).hexdigest() != p[k.replace("_file", "_sha256")]:
                raise SystemExit(f"[video] font changed: {path}")
    cmd = [sys.executable, os.path.join(ROOT, "raceline_video.py"),
           "--outline", os.path.join(up["track"], "outline.json"),
           "--raceline", os.path.join(up["final"], "raceline.json"),
           "--telemetry-csv", os.path.join(up["final"], "lap.csv"),
           "--track-name", p["video.track_name"], "--zoom", repr(float(p["video.zoom"])),
           "--fps", str(int(p["video.fps"])), "--trail-frames", str(int(p["video.trail_frames"])),
           "--display-laptime", repr(float(decided_s)),
           "--out", os.path.join(out, "video.mp4")]
    if p["video.max_seconds"]:
        cmd += ["--max-seconds", repr(float(p["video.max_seconds"]))]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    with open(os.path.join(out, "render.log"), "w", encoding="utf-8") as fh:
        fh.write(r.stdout + r.stderr)
    if r.returncode != 0:
        raise SystemExit(f"[video] render failed rc={r.returncode}")
    with open(os.path.join(out, "video.mp4"), "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()
    return dict(video="video.mp4", zoom=p["video.zoom"], lap_text_s=decided_s, sha256=sha)
