"""Build a track elevation profile from the OpenF1 `location` z-channel.

The F1 position stream carries the car's altitude (z, decimetres, true
metres-above-sea-level x10 — verified at Spa: 3655..4678 = 365.5..467.8 m,
span 102.3 m vs the documented ~102 m sweep). Sampling one clean quali lap
gives elevation vs lap distance in EXACTLY the domain the rest of the
pipeline uses (distance from the S/F line, driving direction) — the same
domain as the reference csv, the sim csv and the raceline stations.

  python cache/_fetch_elevation.py --track spa [--year 2025]
        [--session Qualifying] [--out F1_Pipeline_Assets/tracks/<...>.json]

Output JSON:
  track, source, alt_min_m, alt_max_m, span_m,
  dist_frac[N], elev_m[N]          absolute altitude on a uniform lap grid
  stations[[x,y,z], ...]           raceline stations lifted to 3D (metres,
                                   sim/video coordinate frame) — the 3D model
Validation gates (track-agnostic): span 2..150 m (rejects a dead z-channel or a
dropped dm->m scaling; the summit can be anywhere, so peak location is NOT
gated), closure |z_end - z_start| < 8 m before detrend. A PNG profile is written
for eyeballing next to the JSON.
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
from scipy.ndimage import gaussian_filter1d

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _track_registry import REPO_ROOT, TRACKS  # noqa: E402

BASE = "https://api.openf1.org/v1"
GRID_N = 700


def get(endpoint, **params):
    url = f"{BASE}/{endpoint}?" + urllib.parse.urlencode(params, safe="><=:+")
    for attempt in range(6):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                return json.load(r)
        except Exception as e:               # noqa: BLE001
            if attempt == 5:
                raise
            # 429 = rate limited: retrying immediately is guaranteed to fail
            # again (that is how the first 2025 Monza fetch was lost, right
            # after the live-session lockout lifted). Back off exponentially
            # and honour Retry-After when the server sends one.
            wait = 5.0 * (2 ** attempt)
            if getattr(e, "code", None) == 429:
                ra = None
                try:
                    ra = float(e.headers.get("Retry-After"))
                except Exception:                    # noqa: BLE001
                    pass
                wait = max(wait, ra or 30.0)
            print(f"[elev] retry {attempt+1} on {endpoint} in {wait:.0f}s: {e}",
                  flush=True)
            time.sleep(wait)
    return []


def fastest_lap(session_key):
    laps = get("laps", session_key=session_key)
    valid = [l for l in laps if l.get("lap_duration") and not l.get("is_pit_out_lap")]
    if not valid:
        raise RuntimeError("no valid laps")
    valid.sort(key=lambda l: l["lap_duration"])
    return valid[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", required=True, choices=sorted(TRACKS))
    ap.add_argument("--year", type=int, default=2025)
    # Country comes from the registry so --track alone picks the right session.
    # (Was hardcoded "Belgium" from the Spa-first version: any other --track
    # silently fetched Spa's elevation and wrote it under the new track's name.)
    ap.add_argument("--country", default=None)
    # Multi-GP countries (Italy: Imola + Monza, US: Miami/Austin/Vegas) return
    # several meetings for one country_name; sessions[0] is the earliest, i.e.
    # the WRONG circuit. Registry 'circuit' (or this flag) picks the right one.
    ap.add_argument("--circuit", default=None,
                    help='circuit_short_name filter, e.g. "Monza"')
    ap.add_argument("--session", default="Qualifying")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    spec = TRACKS[args.track]
    country = args.country or spec.get("country")
    if not country:
        print(f"[elev] no country for track {args.track}", file=sys.stderr)
        return 2
    out_path = args.out or os.path.join(
        REPO_ROOT, "F1_Pipeline_Assets", "tracks",
        os.path.basename(spec["outline"]).replace("_outline.json", "_elevation.json"))

    circuit = args.circuit or spec.get("circuit")
    sessions = get("sessions", year=args.year, country_name=country,
                   session_name=args.session)
    if circuit:
        sessions = [s for s in sessions
                    if s.get("circuit_short_name", "").lower() == circuit.lower()]
    if not sessions:
        print("[elev] no session", file=sys.stderr); return 2
    names = {s.get("circuit_short_name") for s in sessions}
    if len(names) > 1:
        print(f"[elev] ambiguous circuits {sorted(names)} — pass --circuit or "
              f"add 'circuit' to the registry entry", file=sys.stderr)
        return 2
    sk = sessions[0]["session_key"]
    lap = fastest_lap(sk)
    drv, dur = lap["driver_number"], float(lap["lap_duration"])
    t0 = datetime.fromisoformat(lap["date_start"])
    t1 = t0 + timedelta(seconds=dur + 0.5)
    print(f"[elev] session {sk} ({sessions[0].get('circuit_short_name')}) "
          f"drv {drv} lap {lap['lap_number']} {dur:.3f}s")

    win = {"date>": t0.isoformat(), "date<": t1.isoformat()}
    loc = get("location", session_key=sk, driver_number=drv, **win)
    cd = get("car_data", session_key=sk, driver_number=drv, **win)
    loc = sorted({p["date"]: p for p in loc if p.get("z") is not None}.values(),
                 key=lambda p: p["date"])
    cd = sorted({c["date"]: c for c in cd if c.get("speed") is not None}.values(),
                key=lambda c: c["date"])
    if len(loc) < 100 or len(cd) < 100:
        print(f"[elev] too little data (loc {len(loc)}, car {len(cd)})",
              file=sys.stderr); return 2

    # distance along the lap from integrated speed (same method as the ref csv)
    tc = np.array([(datetime.fromisoformat(c["date"]) - t0).total_seconds()
                   for c in cd])
    vc = np.array([float(c["speed"]) for c in cd]) / 3.6
    dist_c = np.concatenate([[0.0], np.cumsum(0.5 * (vc[1:] + vc[:-1]) * np.diff(tc))])
    total = float(dist_c[-1])

    # Cross-track sanity: the fetched lap must BE this track's lap. A wrong
    # session (wrong country / a multi-GP country picking the other circuit)
    # is internally consistent and sails through the span/closure gates, so
    # compare the integrated lap distance against the registry length.
    want = float(spec["length_m"])
    if not (0.95 * want <= total <= 1.05 * want):
        print(f"[elev] VALIDATION FAILED: lap distance {total:.0f} m is not "
              f"{args.track} ({want:.0f} m +-5%) — wrong session? "
              f"got '{sessions[0].get('circuit_short_name')}'", file=sys.stderr)
        return 2

    tl = np.array([(datetime.fromisoformat(p["date"]) - t0).total_seconds()
                   for p in loc])
    z = np.array([float(p["z"]) for p in loc]) / 10.0          # dm -> m ASL
    xy = np.array([[float(p["x"]) / 10.0, float(p["y"]) / 10.0] for p in loc])
    dist_l = np.interp(tl, tc, dist_c)

    closure = float(z[-1] - z[0])
    # remove the (small) start/end mismatch so the lap loops seamlessly
    z_c = z - closure * (dist_l / max(dist_l[-1], 1e-9))
    z_s = gaussian_filter1d(z_c, 2.0, mode="nearest")

    frac = np.linspace(0.0, 1.0, GRID_N, endpoint=False)
    elev = np.interp(frac * total, dist_l, z_s)
    span = float(elev.max() - elev.min())
    peak_frac = float(frac[int(np.argmax(elev))])
    low_frac = float(frac[int(np.argmin(elev))])

    print(f"[elev] alt {elev.min():.1f}..{elev.max():.1f} m ASL  span {span:.1f} m  "
          f"peak@{peak_frac:.2f}  low@{low_frac:.2f}  closure {closure:+.1f} m  "
          f"lap dist {total:.0f} m")
    # Track-agnostic physical-plausibility gates (was Spa-specific: span
    # 85..115 m, peak_frac 0.20..0.40 for Les Combes). Real F1 elevation spans
    # run ~5 m (flat Miami/Monza) to ~102 m (Spa); the summit sits wherever the
    # track's high point is, so peak_frac is NOT gated. Reject only impossible
    # data: a near-dead span (<2 m), an implausibly large span (>150 m — e.g. a
    # dropped dm->m /10), or a lap that fails to close in elevation (>8 m).
    ok = 2.0 <= span <= 150.0 and abs(closure) < 8.0
    if not ok:
        print(f"[elev] VALIDATION FAILED (span {span:.1f} m outside [2,150] or "
              f"closure {closure:+.1f} m >= 8) — not writing", file=sys.stderr)
        return 1

    # lift the raceline stations to 3D (station order == driving direction,
    # anchored to the same S/F — established by the ship overlay: shift 0)
    stations = None
    rl_path = spec["outline"].replace("_outline.json", "_raceline.json")
    if os.path.exists(rl_path):
        with open(rl_path, encoding="utf-8") as f:
            rl = json.load(f)
        pts = np.asarray(rl["raceline"], dtype=float)
        arc = np.asarray(rl["arc_length"], dtype=float)
        sf = arc / float(rl["track_length_m"])
        zi = np.interp(sf, frac, elev, period=1.0)
        stations = np.column_stack([pts[:, 0], pts[:, 1], zi]).round(2).tolist()
        print(f"[elev] lifted {len(stations)} raceline stations to 3D")

    out = dict(track=args.track,
               source=f"openf1 location.z session {sk} drv {drv} "
                      f"lap {lap['lap_number']} ({args.year} {args.session})",
               alt_min_m=round(float(elev.min()), 1),
               alt_max_m=round(float(elev.max()), 1),
               span_m=round(span, 1),
               dist_frac=[round(float(x), 5) for x in frac],
               elev_m=[round(float(x), 2) for x in elev],
               stations=stations)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f)
    print(f"[elev] wrote {out_path}")

    # eyeball PNG with landmark guides
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(14, 4))
    ax.fill_between(frac * total, elev, elev.min() - 5, color="#e8890c", alpha=0.35)
    ax.plot(frac * total, elev, color="#e8890c", lw=2)
    if args.track == "spa":
        for fx, name in [(0.055, "La Source"), (0.125, "Eau Rouge"),
                         (0.30, "Les Combes"), (0.45, "Pouhon"),
                         (0.65, "Stavelot"), (0.82, "Blanchimont"),
                         (0.95, "Bus Stop")]:
            ax.axvline(fx * total, color="#888", lw=0.6, ls=":")
            ax.text(fx * total, elev.max() + 2, name, rotation=90,
                    fontsize=7, ha="center", va="bottom", color="#555")
    ax.set_xlabel("lap distance [m]"); ax.set_ylabel("altitude [m ASL]")
    ax.set_title(f"{args.track} elevation — {out['source']} — span {span:.1f} m")
    ax.grid(alpha=0.3)
    png = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       f"elevation_{args.track}.png")
    fig.tight_layout(); fig.savefig(png, dpi=90); plt.close(fig)
    print(f"[elev] wrote {png}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
