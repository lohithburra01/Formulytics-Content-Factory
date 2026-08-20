"""Write an EFFECTIVE per-station banking channel into a track outline.

Banking is TRACK geometry, so it lives on the outline (`banking_deg`, one value
per outline station) rather than in the frozen 2026 car constants. A track with
no banking spec gets no channel, and sim_2026_lap.py then takes the exact
pre-banking code paths.

  python cache/_apply_banking.py --track zandvoort            # write from spec
  python cache/_apply_banking.py --track zandvoort --fit      # solve the angles
  python cache/_apply_banking.py --track zandvoort --clear    # remove channel

EFFECTIVE, not surveyed. MU_LAT (1.95) is an aero-inclusive coefficient fitted
on flat tracks, and its friction angle arctan(1/mu) is only ~27 deg, so feeding
Hugenholtz's surveyed ~19 deg into the closed form saturates it (the corner
stops binding at all). The fitted effective angle absorbs that, and every other
simplification, into one number per corner — the same "calibrate against real
data" approach used for CDA/CL/RHO.

--fit solves v_grip_static(kappa_apex, theta) = v_target for theta at each
banked corner, where v_target is that corner's predicted 2026 apex speed. NOTE
that this makes those corners FITTED rather than PREDICTED: they no longer serve
as independent validation stations. The unbanked corners still do.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _track_registry import REPO_ROOT, TRACKS  # noqa: E402


def raised_cosine(frac: np.ndarray, centre: float, half_width: float) -> np.ndarray:
    """Smooth 0->1->0 bump, periodic in lap fraction. Avoids a step change in
    lateral capacity, which would put a discontinuity into the speed profile."""
    d = np.abs(((frac - centre + 0.5) % 1.0) - 0.5)      # periodic distance
    w = np.clip(1.0 - d / max(half_width, 1e-9), 0.0, 1.0)
    return 0.5 * (1.0 - np.cos(np.pi * w))


def build_channel(n: int, corners: list[dict]) -> np.ndarray:
    frac = np.arange(n) / n
    out = np.zeros(n)
    for c in corners:
        out = np.maximum(out, float(c["deg"]) *
                         raised_cosine(frac, float(c["s_frac"]),
                                       float(c["half_width_frac"])))
    return out


def solve_effective_angle(kappa: float, v_target_ms: float) -> float:
    """Smallest effective bank angle [deg] whose v_grip_static reaches the
    target apex speed. Bisection on a monotone function; returns 0.0 if the flat
    car is already fast enough."""
    from sim_2026_lap import v_grip_static
    if v_grip_static(kappa, 0.0) >= v_target_ms:
        return 0.0
    lo, hi = 0.0, 25.0
    if v_grip_static(kappa, np.radians(hi)) < v_target_ms:
        return hi
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if v_grip_static(kappa, np.radians(mid)) < v_target_ms:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def apex_kappa(rl_path: str, s_frac: float, half_width_frac: float) -> float:
    """Representative curvature at a corner: the 80th percentile of |kappa| over
    the corner window. Not the max (a Menger spike) and not the mean (diluted by
    entry/exit)."""
    with open(rl_path, encoding="utf-8") as f:
        rl = json.load(f)
    k = np.abs(np.asarray(rl["kappa"], dtype=float))
    n = len(k)
    frac = np.arange(n) / n
    d = np.abs(((frac - s_frac + 0.5) % 1.0) - 0.5)
    win = k[d <= half_width_frac]
    if win.size == 0:
        return float(k[int(s_frac * n) % n])
    return float(np.percentile(win, 80))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", required=True, choices=sorted(TRACKS))
    ap.add_argument("--fit", action="store_true",
                    help="solve effective angles from predicted apex targets")
    ap.add_argument("--clear", action="store_true", help="remove the channel")
    args = ap.parse_args()

    spec = TRACKS[args.track]
    outline_path = spec["outline"]
    with open(outline_path, encoding="utf-8") as f:
        outline = json.load(f)
    n = len(outline["outer"])

    if args.clear:
        outline.pop("banking_deg", None)
        with open(outline_path, "w", encoding="utf-8") as f:
            json.dump(outline, f)
        print(f"[bank] cleared channel -> {outline_path}")
        return 0

    corners = spec.get("banking")
    if not corners:
        print(f"[bank] no banking spec for {args.track}; nothing to do")
        return 0

    if args.fit:
        pred_path = os.path.join(REPO_ROOT, "cache", f"predicted_{args.track}.json")
        rl_path = outline_path.replace("_outline.json", "_raceline.json")
        for p in (pred_path, rl_path):
            if not os.path.exists(p):
                print(f"[bank] --fit needs {p}", file=sys.stderr)
                return 2
        with open(pred_path, encoding="utf-8") as f:
            pred = json.load(f)
        for c in corners:
            tgt = min(pred["corners"],
                      key=lambda p: abs(p["s_frac"] - float(c["s_frac"])))
            k = apex_kappa(rl_path, float(c["s_frac"]),
                           float(c["half_width_frac"]))
            deg = solve_effective_angle(k, float(tgt["v26_target_kmh"]) / 3.6)
            print(f"[bank] {c.get('name', c['s_frac'])}: kappa={k:.5f} "
                  f"(R={1/max(k,1e-9):.0f} m) target={tgt['v26_target_kmh']:.1f} km/h "
                  f"-> effective bank {deg:.2f}deg (spec had {c['deg']})")
            c["deg"] = round(deg, 2)

    outline["banking_deg"] = [round(v, 4) for v in build_channel(n, corners)]
    with open(outline_path, "w", encoding="utf-8") as f:
        json.dump(outline, f)
    peak = max(outline["banking_deg"])
    nz = sum(1 for v in outline["banking_deg"] if v > 1e-9)
    print(f"[bank] wrote banking_deg: {nz}/{n} stations, peak {peak:.2f}deg "
          f"-> {outline_path}")
    if args.fit:
        print("[bank] fitted angles (paste into the registry):")
        print("        banking=[")
        for c in corners:
            print(f"            dict(name={c.get('name','')!r}, "
                  f"s_frac={c['s_frac']}, half_width_frac={c['half_width_frac']}, "
                  f"deg={c['deg']}),")
        print("        ],")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
