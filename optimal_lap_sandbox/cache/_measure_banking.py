"""MEASURE a circuit's banking from OpenF1 location data. Real data, not assumed.

The previous display profile was a constant baseline plus three hand-placed
bumps — 87.5% of the lap was a literal invented 2.0 deg. This measures it.

METHOD
  The `location` channel gives x, y, z per car in decimetres of real track
  space. Over many drivers and many laps, cars run DIFFERENT LINES ACROSS THE
  ROAD at the same longitudinal station. So:
    1. build a spine (centre path) from one clean lap -> defines station + S/F
    2. project every sample from every driver/lap onto the spine
       -> (station, signed lateral offset, z)
    3. per station, least-squares fit z = a*lateral + b
       -> banking = atan(a), and the sign says which edge is high
    4. smooth along stations; keep per-station n / spread / R^2 as confidence

WHY THE PRECISION IS ENOUGH
  On a ~14 m road, 19 deg of bank is a 4.8 m edge-to-edge height difference;
  even 2 deg is 0.49 m. The z channel resolves 0.1 m, so both sit well above
  the noise floor given enough samples.

VALIDATION (the whole point — this is falsifiable)
  Zandvoort's Hugenholtz (~19 deg) and Arie Luyendyk (~18 deg) are documented.
  If the fit does not recover them, the measurement is wrong and must not ship.

  python cache/_measure_banking.py --track zandvoort --year 2025 --session Race
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _track_registry import REPO_ROOT, TRACKS  # noqa: E402

BASE = "https://api.openf1.org/v1"
N_STATIONS = 2000
MIN_SAMPLES = 25          # per station, to attempt a fit
MIN_SPREAD_M = 3.0        # lateral spread needed for the slope to mean anything
MAX_LAT_M = 11.0          # reject pit lane / off-track excursions


def get(endpoint, tries=5, **params):
    url = f"{BASE}/{endpoint}?" + urllib.parse.urlencode(params)
    for a in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if a == tries - 1:
                raise
            wait = 5 * (a + 1)
            print(f"[bank] {type(e).__name__} on {endpoint}, retry in {wait}s",
                  file=sys.stderr)
            time.sleep(wait)
    return []


def resample_closed(xy, n):
    """Uniform arc-length resample of a closed path."""
    d = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(xy, axis=0), axis=1))]
    t = np.linspace(0.0, d[-1], n, endpoint=False)
    return np.column_stack([np.interp(t, d, xy[:, 0]),
                            np.interp(t, d, xy[:, 1])]), d[-1]


def main() -> int:
    global N_STATIONS, MIN_SPREAD_M, MIN_SAMPLES
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", required=True, choices=sorted(TRACKS))
    ap.add_argument("--year", type=int, default=2025)
    ap.add_argument("--session", default="Race")
    ap.add_argument("--minutes", type=float, default=25.0,
                    help="window of session running to sample")
    ap.add_argument("--start-offset-min", type=float, default=8.0,
                    help="skip the opening laps (safety car / bunching)")
    ap.add_argument("--stations", type=int, default=N_STATIONS,
                    help="longitudinal bins; fewer = more samples and more "
                         "lateral spread per bin")
    ap.add_argument("--min-spread", type=float, default=MIN_SPREAD_M)
    ap.add_argument("--min-samples", type=int, default=MIN_SAMPLES)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    N_STATIONS = args.stations
    MIN_SPREAD_M = args.min_spread
    MIN_SAMPLES = args.min_samples

    spec = TRACKS[args.track]
    country = spec.get("country")
    sessions = get("sessions", year=args.year, country_name=country,
                   session_name=args.session)
    if not sessions:
        print("[bank] no session", file=sys.stderr)
        return 2
    sk = sessions[0]["session_key"]
    print(f"[bank] session {sk} ({sessions[0].get('circuit_short_name')}) "
          f"{args.year} {args.session}")

    # --- spine from the session's fastest lap -------------------------------
    laps = [l for l in get("laps", session_key=sk)
            if l.get("lap_duration") and l.get("date_start")]
    if not laps:
        print("[bank] no laps", file=sys.stderr)
        return 2
    fast = min(laps, key=lambda l: l["lap_duration"])
    t0 = datetime.fromisoformat(fast["date_start"])
    t1 = t0 + timedelta(seconds=float(fast["lap_duration"]) + 0.5)
    spine_raw = get("location", session_key=sk,
                    driver_number=fast["driver_number"],
                    **{"date>": t0.isoformat(), "date<": t1.isoformat()})
    spine_raw = [p for p in spine_raw if p.get("x") is not None]
    spine_raw.sort(key=lambda p: p["date"])
    if len(spine_raw) < 200:
        print(f"[bank] spine too short ({len(spine_raw)})", file=sys.stderr)
        return 2
    sxy = np.array([[p["x"] / 10.0, p["y"] / 10.0] for p in spine_raw])
    spine, spine_len = resample_closed(sxy, N_STATIONS)
    print(f"[bank] spine: drv {fast['driver_number']} lap "
          f"{fast['lap_number']} {fast['lap_duration']:.3f}s, "
          f"{spine_len:.0f} m, {N_STATIONS} stations")

    tang = np.roll(spine, -1, axis=0) - np.roll(spine, 1, axis=0)
    tang /= np.maximum(np.linalg.norm(tang, axis=1, keepdims=True), 1e-9)
    nrm = np.column_stack([-tang[:, 1], tang[:, 0]])       # left-hand normal

    # --- sample the field ----------------------------------------------------
    drivers = sorted({d["driver_number"] for d in get("drivers", session_key=sk)})
    w0 = datetime.fromisoformat(sessions[0]["date_start"]) + timedelta(
        minutes=args.start_offset_min)
    w1 = w0 + timedelta(minutes=args.minutes)
    print(f"[bank] sampling {len(drivers)} drivers over "
          f"{args.minutes:.0f} min from +{args.start_offset_min:.0f} min")

    from scipy.spatial import cKDTree
    tree = cKDTree(spine)
    st_all, lat_all, z_all = [], [], []
    for i, dn in enumerate(drivers):
        pts = get("location", session_key=sk, driver_number=dn,
                  **{"date>": w0.isoformat(), "date<": w1.isoformat()})
        pts = [p for p in pts if p.get("x") is not None and p.get("z") is not None]
        if not pts:
            continue
        P = np.array([[p["x"] / 10.0, p["y"] / 10.0, p["z"] / 10.0] for p in pts])
        idx = tree.query(P[:, :2])[1]
        rel = P[:, :2] - spine[idx]
        lat = np.einsum("ij,ij->i", rel, nrm[idx])
        keep = np.abs(lat) <= MAX_LAT_M
        st_all.append(idx[keep]); lat_all.append(lat[keep]); z_all.append(P[keep, 2])
        print(f"[bank]   drv {dn:>2}: {keep.sum():6d} pts "
              f"({i + 1}/{len(drivers)})")
        time.sleep(0.4)                      # be kind to the API

    if not st_all:
        print("[bank] no samples", file=sys.stderr)
        return 2
    st = np.concatenate(st_all); lat = np.concatenate(lat_all)
    z = np.concatenate(z_all)
    print(f"[bank] {len(st):,} samples across {len(np.unique(st))} stations")

    # --- per-station cross-slope fit ----------------------------------------
    deg = np.full(N_STATIONS, np.nan)
    nsamp = np.zeros(N_STATIONS, dtype=int)
    spread = np.zeros(N_STATIONS)
    r2 = np.full(N_STATIONS, np.nan)
    order = np.argsort(st, kind="stable")
    st_s, lat_s, z_s = st[order], lat[order], z[order]
    bounds = np.searchsorted(st_s, np.arange(N_STATIONS + 1))
    for i in range(N_STATIONS):
        a, b = bounds[i], bounds[i + 1]
        nsamp[i] = b - a
        if b - a < 4:
            continue
        L, Z = lat_s[a:b], z_s[a:b]
        spread[i] = np.percentile(L, 95) - np.percentile(L, 5)   # robust span
        if b - a < MIN_SAMPLES or spread[i] < MIN_SPREAD_M:
            continue
        slope, icpt = np.polyfit(L, Z, 1)
        pred = slope * L + icpt
        ss_res = float(((Z - pred) ** 2).sum())
        ss_tot = float(((Z - Z.mean()) ** 2).sum())
        r2[i] = 1.0 - ss_res / ss_tot if ss_tot > 1e-9 else np.nan
        deg[i] = abs(np.degrees(np.arctan(slope)))

    ok = np.isfinite(deg)
    have = spread > 0
    print(f"[bank] fitted {ok.sum()}/{N_STATIONS} stations "
          f"({100 * ok.mean():.0f}%), median n={int(np.median(nsamp))}")
    if have.any():
        print(f"[bank] lateral spread across ALL stations: "
              f"p10={np.percentile(spread[have], 10):.1f} "
              f"p50={np.percentile(spread[have], 50):.1f} "
              f"p90={np.percentile(spread[have], 90):.1f} m "
              f"(need >= {MIN_SPREAD_M:.1f})")
    if ok.sum() < N_STATIONS * 0.5:
        print("[bank] TOO FEW STATIONS FITTED — widen --minutes", file=sys.stderr)
        return 2

    # fill gaps circularly, then smooth
    idx = np.arange(N_STATIONS)
    deg_f = np.interp(idx, idx[ok], deg[ok], period=N_STATIONS)
    from scipy.ndimage import gaussian_filter1d
    deg_s = gaussian_filter1d(deg_f, 8.0, mode="wrap")

    # --- validation against the documented corners ---------------------------
    checks = {"zandvoort": [("T3 Hugenholtz", 0.185, 19.0),
                            ("T14 Arie Luyendyk", 0.810, 18.0)]}
    print("[bank] VALIDATION vs documented figures:")
    worst = 0.0
    for name, frac, expect in checks.get(args.track, []):
        j = int(frac * N_STATIONS)
        w = np.r_[deg_s[(j - 40) % N_STATIONS:j], deg_s[j:(j + 40) % N_STATIONS or None]]
        got = float(np.nanmax(w)) if len(w) else float("nan")
        worst = max(worst, abs(got - expect))
        print(f"[bank]   {name:20s} measured {got:5.1f} deg vs documented "
              f"{expect:4.1f} deg   ({got - expect:+.1f})")
    print(f"[bank] profile: min {deg_s.min():.1f}, median {np.median(deg_s):.1f}, "
          f"max {deg_s.max():.1f} deg  ({len(np.unique(np.round(deg_s,1)))} distinct)")

    out_path = args.out or os.path.join(
        REPO_ROOT, "F1_Pipeline_Assets", "tracks",
        os.path.basename(spec["outline"])
        .replace("_outline.json", "_banking_display.json"))
    json.dump(dict(
        track=args.track, kind="display_only",
        warning="MEASURED banking for display. Not the fitted physics channel.",
        source=f"openf1 location z-vs-lateral regression, session {sk} "
               f"({args.year} {args.session}), {len(st)} samples, "
               f"{ok.sum()}/{N_STATIONS} stations fitted",
        method="per-station least squares z = a*lateral + b; banking = atan(a)",
        validation={n: dict(measured_deg=round(float(np.nanmax(
            deg_s[max(0, int(f * N_STATIONS) - 40):int(f * N_STATIONS) + 40])), 2),
            documented_deg=e) for n, f, e in checks.get(args.track, [])},
        baseline_deg=round(float(np.median(deg_s)), 2),
        n_samples=int(len(st)),
        stations_fitted=int(ok.sum()),
        banking_deg=[round(float(v), 3) for v in deg_s],
        confidence=dict(median_r2=round(float(np.nanmedian(r2[ok])), 3),
                        median_n=int(np.median(nsamp[ok])),
                        median_spread_m=round(float(np.median(spread[ok])), 2)),
    ), open(out_path, "w", encoding="utf-8"))
    print(f"[bank] wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
