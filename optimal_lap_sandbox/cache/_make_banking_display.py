"""Build the DISPLAY-ONLY banking profile for the video's cross-section panel.

⚠️  NOT THE PHYSICS CHANNEL. Never feed this to the sim.
    outline["banking_deg"] holds EFFECTIVE angles FITTED so the sim reproduces
    apex speeds (Hugenholtz 8.62, Luyendyk 0.45). Those are calibration values,
    deliberately not real geometry. This file is the circuit's real shape.

PROVENANCE — read before trusting any number here.

  What this is:  a CONTINUOUS profile whose SHAPE follows the published account
  of the 2021 Dromo redesign (progressive spiral into T3; a long constant-slope
  plateau through T13-14; ordinary aerodynamic cross-fall of 2-4 deg across the
  dune sector; 0 deg cross-fall on the pit straight for race starts), with every
  POSITION anchored to this track's own measured raceline curvature.

  What it is NOT:  a survey. Only the two peak figures are documented
  (T3 ~18.7 deg, T14 ~18.0 deg). The mid-sector values are the design intent
  band, distributed by curvature, not per-metre measurements.

  Why it is not measured:  the OpenF1 `location` channel is SNAPPED to a
  reference path — sampling 266,702 points from 20 drivers over 60 min of
  practice gave a median lateral spread of 0.2 m, and two different drivers
  returned identical coordinate ranges to 0.1 m. Cross-slope cannot be
  recovered from it. (cache/_measure_banking.py implements the regression and
  documents the failure; keep it for a data source that does resolve lateral
  position.)

POSITIONS — corrected against cache/_measure_banking-style curvature analysis:
  wide-stencil radius puts the final corner complex at ~3400-3800 m and shows
  ~3850 m onward genuinely straight (R > 20 km). Published accounts placing
  T13-14 at "3900-4200 m" would sit it on the pit straight; an earlier version
  of this file placed it at 3439 m, which is the tighter T12/13 (R=81 m). The
  Luyendyk plateau used here is 3500-3800 m.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _track_registry import REPO_ROOT, TRACKS  # noqa: E402

N_STATIONS = 2000


def _ramp(x, x0, x1):
    """Smoothstep 0->1 over [x0,x1] (a spiral-ish transition, not a step)."""
    t = np.clip((x - x0) / max(x1 - x0, 1e-9), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def zandvoort_profile(frac, kappa_norm):
    """Banking [deg] vs lap fraction. Distances quoted in official-lap metres
    (4259 m) and converted to fraction."""
    M = 4259.0
    d = frac * M
    deg = np.zeros_like(d)

    # --- dune sector baseline: ordinary aero cross-fall 2-4 deg, distributed by
    # curvature so tighter corners carry more camber. NOT a flat constant.
    deg += 2.0 + 2.0 * kappa_norm

    # --- pit straight: 0 deg cross-fall (FIA race-start requirement) ----------
    on_straight = np.minimum(_ramp(d, 3850.0, 3980.0),
                             1.0 - _ramp(d, 190.0, 300.0))
    # wrap: it is one straight spanning S/F
    straight = np.where(d > 3500.0, _ramp(d, 3850.0, 3980.0),
                        1.0 - _ramp(d, 190.0, 300.0))
    deg *= (1.0 - straight)

    # --- T1 Tarzan: traditional positive camber 4-5 deg, 320-450 m -----------
    tarzan = _ramp(d, 290.0, 340.0) * (1.0 - _ramp(d, 450.0, 560.0))
    deg = np.maximum(deg, 4.5 * tarzan)

    # --- T3 Hugenholtz: progressive spiral, peak 18.7 deg at the apex --------
    # asymmetric on purpose: climbs across the entry, sheds faster on exit.
    hug_up = _ramp(d, 600.0, 800.0)
    hug_dn = 1.0 - _ramp(d, 820.0, 990.0)
    deg = np.maximum(deg, 18.7 * hug_up * hug_dn)

    # --- T13-14 Arie Luyendyk: linear ramp into a constant 18.0 deg plateau --
    # plateau placed 3500-3800 m from this track's own curvature.
    luy_up = _ramp(d, 3330.0, 3500.0)
    luy_dn = 1.0 - _ramp(d, 3800.0, 3870.0)
    deg = np.maximum(deg, 18.0 * luy_up * luy_dn)
    return deg


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", required=True, choices=["zandvoort"])
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    spec = TRACKS[args.track]
    rl_path = spec["outline"].replace("_outline.json", "_raceline.json")
    with open(rl_path, encoding="utf-8") as f:
        rl = json.load(f)
    P = np.asarray(rl["raceline"], dtype=float)
    n = len(P)

    # wide-stencil curvature: a fast banked sweeper has a big radius and is
    # invisible to the tight 3-point Menger estimate.
    S = 25
    k = np.zeros(n)
    for i in range(n):
        a, b, c = P[(i - S) % n], P[i], P[(i + S) % n]
        ab, bc, ac = b - a, c - b, c - a
        cross = ab[0] * bc[1] - ab[1] * bc[0]
        den = np.linalg.norm(ab) * np.linalg.norm(bc) * np.linalg.norm(ac)
        k[i] = 0.0 if den < 1e-9 else 2.0 * cross / den
    k = np.abs(k)

    frac_src = np.arange(n) / n
    frac = np.arange(N_STATIONS) / N_STATIONS
    kap = np.interp(frac, frac_src, k, period=1.0)
    from scipy.ndimage import gaussian_filter1d
    kap = gaussian_filter1d(kap, 14.0, mode="wrap")
    kap_n = np.clip(kap / max(np.percentile(kap, 95), 1e-9), 0.0, 1.0)

    deg = zandvoort_profile(frac, kap_n)
    deg = gaussian_filter1d(deg, 5.0, mode="wrap")
    deg = np.maximum(deg, 0.0)

    out_path = args.out or os.path.join(
        REPO_ROOT, "F1_Pipeline_Assets", "tracks",
        os.path.basename(spec["outline"])
        .replace("_outline.json", "_banking_display.json"))
    json.dump(dict(
        track=args.track, kind="display_only",
        warning="Display banking. SHAPE from the published 2021 Dromo redesign "
                "account, POSITIONS anchored to this track's measured raceline "
                "curvature. Only the two peak figures are documented; the "
                "mid-sector 2-4 deg is design-intent, distributed by curvature. "
                "Not a survey. Not the fitted physics channel.",
        source="Dromo 2021 redesign (published): T3 progressive spiral to "
               "~18.7 deg; T13-14 linear ramp to a constant 18.0 deg plateau "
               "(32% gradient); dune sector 2-4 deg aero cross-fall; pit "
               "straight 0 deg cross-fall. Positions from wide-stencil "
               "curvature of dutch_grand_prix_raceline.json.",
        documented=[dict(name="T3 Hugenholtz", peak_deg=18.7, at_m=800),
                    dict(name="T13-14 Arie Luyendyk", peak_deg=18.0,
                         plateau_m=[3500, 3800])],
        baseline_deg=round(float(np.median(deg)), 2),
        banking_deg=[round(float(v), 3) for v in deg],
    ), open(out_path, "w", encoding="utf-8"))

    flat = float((np.round(deg, 1) == round(float(np.median(deg)), 1)).mean())
    print(f"[bankdisp] {args.track}: min {deg.min():.1f}  median "
          f"{np.median(deg):.1f}  max {deg.max():.1f} deg")
    print(f"[bankdisp] distinct 0.1-deg values: "
          f"{len(np.unique(np.round(deg, 1)))}  |  share sitting on the median: "
          f"{100 * flat:.1f}%  (was 87.5% flat)")
    for lo, hi, lbl in [(0.00, 0.07, "pit straight"), (0.075, 0.11, "T1 Tarzan"),
                        (0.17, 0.20, "T3 Hugenholtz"), (0.40, 0.60, "dune sector"),
                        (0.82, 0.89, "T13-14 Luyendyk"), (0.92, 1.00, "pit straight")]:
        m = (frac >= lo) & (frac < hi)
        print(f"[bankdisp]   {lbl:18s} frac {lo:.2f}-{hi:.2f}: "
              f"{deg[m].min():5.1f} .. {deg[m].max():5.1f} deg")
    print(f"[bankdisp] wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
