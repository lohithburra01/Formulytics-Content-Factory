"""Local relaxation of the SVG racing line where every map is too coarse (FITTED sites).

Diagnosis (cache/madring_diagnosis, _madring_gps_line, _madring_opt_line): at a
few kinks the SVG line, the raw timing path and optimised lines in 12/14 m GPS
corridors ALL give radii the frozen grip model cannot carry at the speeds the
practice cars actually hold (e.g. R ~ 60 m where the top-10 laps do 204-210
km/h). Each listed site is relaxed with tapered local smoothing, just enough
that its minimum grip radius reaches the radius the grip model needs for the
observed top-10 speed at the chosen CL/rho. These corners become FITTED (like
Zandvoort's banking), not predictions. The drawn road is moved with the line
(same tapered displacement), i.e. the SVG corner shape is corrected rather than
the car being drawn off the road; the corrected corridor is validity-checked
and must contain the whole line.
Site spec: S_MEAS:V_KMH:HALF (metres on the measured practice axis, km/h, metres).
New files only (exclusive create).
"""
import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from scipy.ndimage import gaussian_filter1d, median_filter
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "cache"))
sys.stdout.reconfigure(encoding="utf-8")
import sim_2026_lap as sim
from _track_registry import rho_isa
from _madring_calib_v2 import GPS, project_s

DEST = ROOT / "cache/madring_opt_lines"


def grip_kappa(p):
    a, c = np.roll(p, 4, axis=0), np.roll(p, -4, axis=0)
    ab, bc, ac = p - a, c - p, c - a
    den = np.linalg.norm(ab, axis=1) * np.linalg.norm(bc, axis=1) * np.linalg.norm(ac, axis=1)
    k = np.where(den < 1e-9, 0.0, 2 * (ab[:, 0] * bc[:, 1] - ab[:, 1] * bc[:, 0]) / np.maximum(den, 1e-12))
    return median_filter(k, 5, mode="wrap")


def main(a):
    DEST.mkdir(exist_ok=True)
    out = DEST / f"{a.name}_raceline.json"
    outline_out = ROOT / f"F1_Pipeline_Assets/tracks/madring_grand_prix_outline_{a.name}.json"
    for path_ in (out, outline_out):
        if path_.exists():
            raise FileExistsError(path_)
    src = json.loads(Path(a.src).read_text(encoding="utf-8"))
    p = np.asarray(src["raceline"], float)
    p_src = p.copy()
    n = len(p)
    arc = np.asarray(src["arc_length"], float)
    ds = float(src["track_length_m"]) / n
    sim._apply_car_overrides(SimpleNamespace(cda=0.8, cl=a.cl, rho=a.rho or rho_isa(a.altitude)))
    meas = json.loads((GPS / "madring_gps_raceline.json").read_text(encoding="utf-8"))
    Lm = float(meas["track_length_m"])
    s_meas = project_s(np.asarray(meas["raceline"], float), p)
    from shapely.geometry import LinearRing, LineString, Point, Polygon
    ol = json.loads(Path(a.outline).read_text(encoding="utf-8"))
    outer, inner = np.asarray(ol["outer"], float), np.asarray(ol["inner"], float)
    corridor = Polygon(outer, [inner])
    sites = []
    for spec in a.site:
        s0, v_kmh, half = (float(x) for x in spec.split(":"))
        near = np.where(np.abs(((s_meas - s0 + Lm / 2) % Lm) - Lm / 2) <= 60.0)[0]
        k0 = grip_kappa(p)
        c = int(near[np.argmax(np.abs(k0[near]))])
        v = v_kmh / 3.6
        r_target = v * v / sim.a_lat_max_banked(v, "CORNER", 0.0)
        d_st = np.abs(((np.arange(n) - c + n / 2) % n) - n / 2) * ds  # metres from the site centre
        core = half / 2
        w = np.where(d_st <= core, 1.0, np.where(d_st >= half, 0.0,
                     0.5 * (1 + np.cos(np.pi * (d_st - core) / (half - core)))))
        win = d_st <= half
        r_before = float(1 / np.abs(k0[win]).max())
        chosen, best = None, None
        for sig_m in np.arange(4.0, 121.0, 2.0):
            sm = np.column_stack([gaussian_filter1d(p[:, j], sig_m / ds, mode="wrap") for j in range(2)])
            cand = p + w[:, None] * (sm - p)
            r_min = float(1 / np.abs(grip_kappa(cand)[win]).max())
            if best is None or r_min > best[2]:
                best = (sig_m, cand, r_min)
            if r_min >= r_target:
                chosen = (sig_m, cand, r_min)
                break
        sig_m, cand, r_min = chosen or best  # unreached: best effort is reported, then refused below
        shift = float(np.linalg.norm(cand - p, axis=1).max())
        outside = [float(corridor.exterior.distance(Point(q)) if not corridor.contains(Point(q)) else 0.0)
                   for q in cand[win]]
        p = cand
        sites.append(dict(s_meas=s0, v_target_kmh=v_kmh, centre_station=c, centre_arc_m=float(arc[c]),
                          half_window_m=half, r_target_m=round(r_target, 1), r_before_m=round(r_before, 1),
                          r_after_m=round(r_min, 1), sigma_m=float(sig_m), reached=bool(r_min >= r_target),
                          max_lateral_shift_m=round(shift, 2), max_outside_svg_corridor_m=round(max(outside), 2)))
        print(json.dumps(sites[-1]), flush=True)
    assert LineString(np.vstack([p, p[:1]])).is_simple, "relaxed line self-intersects"

    # move the drawn road with the line: each outline station takes the
    # displacement of its nearest source-line station (tapered to 0 off-site)
    delta = p - p_src
    tree = cKDTree(p_src)
    outer_new = outer + delta[tree.query(outer)[1]]
    inner_new = inner + delta[tree.query(inner)[1]]
    corr_new = Polygon(outer_new, [inner_new])
    band = corr_new.buffer(0.30)
    road = dict(valid=corr_new.is_valid, outer_simple=LinearRing(outer_new).is_simple,
                inner_simple=LinearRing(inner_new).is_simple,
                line_outside_0p3m=int(sum(not band.contains(Point(q)) for q in p)),
                max_edge_shift_m=round(float(max(np.linalg.norm(outer_new - outer, axis=1).max(),
                                                 np.linalg.norm(inner_new - inner, axis=1).max())), 2))
    print("road", json.dumps(road), flush=True)
    assert road["valid"] and road["outer_simple"] and road["inner_simple"], road
    assert road["line_outside_0p3m"] == 0, road

    seg = np.linalg.norm(np.diff(np.vstack([p, p[:1]]), axis=0), axis=1)
    arc_new = np.r_[0.0, np.cumsum(seg)[:-1]]
    kap, _ = sim.kappa_ds_menger(p)
    info = dict(src=str(Path(a.src).resolve()), outline_src=str(Path(a.outline).resolve()),
                outline=str(outline_out), cl_for_targets=a.cl, rho=sim.RHO, sites=sites, road=road,
                length_m=float(seg.sum()), length_src_m=float(src["track_length_m"]))
    print("length", round(info["length_src_m"], 2), "->", round(info["length_m"], 2), flush=True)
    with outline_out.open("x", encoding="utf-8") as fh:
        json.dump(dict(outer=outer_new.tolist(), inner=inner_new.tolist(),
                       source=f"provisional SVG outline moved with the fitted line relaxations of {out.name}"), fh)
    with out.open("x", encoding="utf-8") as fh:
        json.dump(dict(raceline=p.tolist(), arc_length=arc_new.tolist(), kappa=kap.tolist(),
                       track_length_m=float(seg.sum()), banking_deg=[], info=info,
                       source="SVG racing line with FITTED local relaxations (see info.sites)"), fh)
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--src", default=str(ROOT / "cache/madring_fp1_elevation/madring_fp1_raceline.json"))
    ap.add_argument("--outline", default=str(ROOT / "F1_Pipeline_Assets/tracks/madring_grand_prix_outline_provisional.json"))
    ap.add_argument("--site", action="append", required=True)
    ap.add_argument("--cl", type=float, default=5.0)
    ap.add_argument("--altitude", type=float, default=684.0)
    ap.add_argument("--rho", type=float, default=None)
    raise SystemExit(main(ap.parse_args()))
