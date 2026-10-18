"""Madring trial v2: frozen 2026 physics on a given line, scored on the MEASURED distance axis.

Knobs are the three CLI ones (CDA, CL, rho) plus an optional EFFECTIVE banking
bump in metres from the timing line (track geometry, e.g. La Monumental). Sim
stations are projected onto the measured practice line, so the sim speed and
the practice speed traces share one distance axis whatever line the sim drove.
New files only (exclusive create) in cache/madring_calib_v2/.
"""
import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from scipy.signal import find_peaks
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")
import sim_2026_lap as sim
from _track_registry import rho_isa
from _gate_2026 import load as gate_load, rate_kmh_s

GPS = ROOT / "cache/madring_gps_line"
DEST = ROOT / "cache/madring_calib_v2"


def project_s(path, pts):
    """Arc position of each point on a closed polyline (nearest segment)."""
    seg = np.roll(path, -1, axis=0) - path
    seglen = np.linalg.norm(seg, axis=1)
    cum = np.r_[0.0, np.cumsum(seglen)[:-1]]
    _, near = cKDTree(path).query(pts)
    best, s_out = np.full(len(pts), np.inf), np.zeros(len(pts))
    for off in (-1, 0):
        j = (near + off) % len(path)
        w = pts - path[j]
        tt = np.clip(np.einsum("ij,ij->i", w, seg[j]) / np.maximum(seglen[j] ** 2, 1e-12), 0.0, 1.0)
        dist = np.linalg.norm(w - tt[:, None] * seg[j], axis=1)
        take = dist < best
        best[take], s_out[take] = dist[take], (cum[j] + tt * seglen[j])[take]
    return s_out % seglen.sum()


def trace_time(v_kmh, ds=1.0):
    return float(np.sum(ds / np.maximum(v_kmh / 3.6, 1.0)))


def run(a):
    DEST.mkdir(exist_ok=True)
    assert a.name.replace("_", "").isalnum(), "simple trial name required"
    out = dict(csv=DEST / f"{a.name}.csv", json=DEST / f"{a.name}.json", npz=DEST / f"{a.name}_stations.npz")
    for p in out.values():
        if p.exists():
            raise FileExistsError(p)
    line = json.loads(Path(a.line).read_text(encoding="utf-8"))
    pts = np.asarray(line["raceline"], float)
    arc = np.asarray(line["arc_length"], float)
    kap = np.asarray(line["kappa"], float)
    L = float(line["track_length_m"])
    rho = a.rho if a.rho else rho_isa(a.altitude)
    sim._apply_car_overrides(SimpleNamespace(cda=a.cda, cl=a.cl, rho=rho))
    bank = np.zeros(len(pts))
    if a.bank_peak:
        w = np.clip(np.minimum((arc - a.bank_start) / a.bank_ramp, (a.bank_end - arc) / a.bank_ramp), 0.0, 1.0)
        bank = a.bank_peak * 0.5 * (1.0 - np.cos(np.pi * w))
    sim.BANKING_RAD = np.radians(bank) if bank.any() else None
    v, soc, mode, pw, t = sim.simulate_lap(pts, arc, kap, L)
    raw = float(t[-1])
    v, t = sim.smooth_longitudinal(v, arc, L, win_s=0.45)
    v, t = sim.suppress_microhumps(v, arc, L, t)
    sim.write_csv(str(out["csv"]), v, soc, mode, pw, t, arc, L, fps=30)
    try:
        sim.assert_sanity(v, soc, mode, pw, t)
        sanity = True
    except SystemExit:
        sanity = False
    np.savez_compressed(out["npz"], v_ms=v, soc=soc, mode=np.asarray(mode), power_kw=pw, time_s=t,
                        arc_length=arc, kappa=kap, banking_deg=bank)

    meas = json.loads((GPS / "madring_gps_raceline.json").read_text(encoding="utf-8"))
    Lm = float(meas["track_length_m"])
    tr = np.load(GPS / "speed_traces.npz")
    grid, top10, p90 = tr["grid_s"], tr["top10"], tr["p90"]
    s_st = project_s(np.asarray(meas["raceline"], float), pts)
    sv = np.interp(grid, s_st, v * 3.6, period=Lm)

    def win(s0, half=40.0):
        return np.abs(((grid - s0 + Lm / 2) % Lm) - Lm / 2) <= half

    corners = []
    for i in find_peaks(-top10, prominence=12, distance=60)[0]:
        m = win(grid[i])
        corners.append(dict(s_m=int(grid[i]), top10=round(float(top10[i]), 1), p90=round(float(p90[m].min()), 1),
                            sim=round(float(sv[m].min()), 1), err_top10=round(float(sv[m].min() - top10[i]), 1),
                            err_p90=round(float(sv[m].min() - p90[m].min()), 1)))
    straights = []
    for i in find_peaks(top10, prominence=15, distance=60)[0]:
        m = win(grid[i], 60.0)
        straights.append(dict(s_m=int(grid[i]), top10=round(float(top10[i]), 1),
                              p90=round(float(p90[m].max()), 1), sim=round(float(sv[m].max()), 1)))
    t_sim_cum = np.cumsum(1.0 / np.maximum(sv / 3.6, 1.0))
    t_ref_cum = np.cumsum(1.0 / np.maximum(top10 / 3.6, 1.0))
    deltas = {f"{int(q * 100)}%": round(float(t_sim_cum[int(q * len(grid)) - 1] - t_ref_cum[int(q * len(grid)) - 1]), 3)
              for q in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)}
    tt, vv, th, br, _ = gate_load(out["csv"])
    rates = rate_kmh_s(tt, vv)
    gain = rates[(th > 80) & (br < 5) & (vv < 0.88 * vv.max()) & (rates > 2)]
    drop = -rates[(br > 15) & (rates < -2)]
    near = (th > 90) & (br < 5) & (vv > 0.85 * vv.max())
    clip = -rates[near & (rates < -1)]
    errs = np.array([c["err_top10"] for c in corners])
    result = dict(name=a.name, line=str(Path(a.line).resolve()), cda=a.cda, cl=a.cl, rho=rho,
                  altitude_m=None if a.rho else a.altitude,
                  bank=dict(peak_deg=a.bank_peak, start_m=a.bank_start, end_m=a.bank_end, ramp_m=a.bank_ramp),
                  raw_lap_s=raw, lap_s=float(t[-1]), top10_trace_time_s=trace_time(top10),
                  p90_trace_time_s=trace_time(p90), min_kmh=float(v.min() * 3.6), top_kmh=float(v.max() * 3.6),
                  corr_top10=float(np.corrcoef(sv, top10)[0, 1]), mae_top10=float(np.mean(np.abs(sv - top10))),
                  corner_median_err_top10=float(np.median(errs)), corner_mad_err=float(np.median(np.abs(errs - np.median(errs)))),
                  corners=corners, straights=straights, cum_delta_vs_top10_s=deltas,
                  physics=dict(gain_median=float(np.median(gain)), gain_peak=float(gain.max()),
                               drop_median=float(np.median(drop)), drop_peak=float(drop.max()),
                               superclip_fraction=float(len(clip) / max(1, near.sum()))),
                  sanity_pass=sanity)
    with out["json"].open("x", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    print(f"\n== {a.name}: lap {result['lap_s']:.3f} s (top10 trace {result['top10_trace_time_s']:.3f}, "
          f"p90 {result['p90_trace_time_s']:.3f}) | v {result['min_kmh']:.0f}-{result['top_kmh']:.0f} | "
          f"corr {result['corr_top10']:.4f} MAE {result['mae_top10']:.1f} | corner err median "
          f"{result['corner_median_err_top10']:+.1f} (MAD {result['corner_mad_err']:.1f}) | sanity {sanity}")
    print("corners  s:top10/p90/sim(err): " + "  ".join(
        f"{c['s_m']}:{c['top10']:.0f}/{c['p90']:.0f}/{c['sim']:.0f}({c['err_top10']:+.0f})" for c in corners))
    print("straights s:top10/p90/sim: " + "  ".join(
        f"{s['s_m']}:{s['top10']:.0f}/{s['p90']:.0f}/{s['sim']:.0f}" for s in straights))
    print("cum delta vs top10 (s): " + " ".join(f"{k}={v:+.2f}" for k, v in deltas.items()))
    print("physics: " + ", ".join(f"{k} {v:.1f}" if "fraction" not in k else f"{k} {v:.3f}"
                                  for k, v in result["physics"].items()), flush=True)
    return 0 if sanity else 10


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--line", default=str(GPS / "madring_gps_raceline.json"))
    ap.add_argument("--cda", type=float, default=0.8)
    ap.add_argument("--cl", type=float, default=4.2)
    ap.add_argument("--altitude", type=float, default=684.0)
    ap.add_argument("--rho", type=float, default=None)
    ap.add_argument("--bank-peak", type=float, default=0.0, help="EFFECTIVE bank angle, degrees")
    ap.add_argument("--bank-start", type=float, default=0.0, help="metres from the timing line")
    ap.add_argument("--bank-end", type=float, default=0.0)
    ap.add_argument("--bank-ramp", type=float, default=40.0)
    raise SystemExit(run(ap.parse_args()))
