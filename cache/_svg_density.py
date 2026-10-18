"""Screen a circuit SVG for geometric fidelity BEFORE running the pipeline on it.

SVG quality is this pipeline's #1 accuracy lever (NOW.md): a coarse outline
shows up later as per-corner errors of +-30-40 km/h in BOTH directions, which
no CDA/CL knob can fix. This tells you in seconds whether a candidate is worth
building on, instead of finding out after predict+autofit+gate.

  python cache/_svg_density.py <candidate.svg> --track-length 5793 --turns 11
  python cache/_svg_density.py --table            # every SVG in the repo root

Two densities, because either one alone misleads:
  seg/km    path detail per unit distance. PENALISES straight-heavy circuits -
            Monza is 74% straight, so a faithful Monza scores low here.
  seg/turn  detail per CORNER (needs --turns). The causally relevant one:
            rounded-off corners are the failure mode, and a straight needs
            exactly one Bezier segment. Prefer it whenever the turn count is
            known; the verdict uses it in preference to seg/km.
Anchors are this repo's own outcomes: Spa (cleanest traces) through Silverstone
(weakest ship, corr 0.945).
"""
from __future__ import annotations

import argparse
import glob
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import svg_to_outline as s2o                                    # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Official length (m) / turn count for the SVGs already in the repo root, so
# --table reports comparable densities rather than raw counts.
KNOWN_M = {
    "Spa-Francorchamps_of_Belgium.svg": 7004,
    "Formula1_Circuit_Catalunya_2021.svg": 4657,
    "Catalunya-2023.svg": 4657,
    "Zandvoort.svg": 4259,
    "Hungaroring.svg": 4381,
    "CANADA CIRCUIT.svg": 4361,
    "RaceCircuitSilverstone.svg": 5891,
    "Circuit_Red_Bull_Ringtrack.svg": 4318,
    "Circuit_Monaco.svg": 3337,
    "RaceCircuitAutodromaDiMonza.svg": 5793,
    "Monza_track_map.svg": 5793,
}
KNOWN_TURNS = {
    "Spa-Francorchamps_of_Belgium.svg": 19, "Zandvoort.svg": 14,
    "Hungaroring.svg": 14, "CANADA CIRCUIT.svg": 14,
    "Formula1_Circuit_Catalunya_2021.svg": 16, "Catalunya-2023.svg": 14,
    "RaceCircuitSilverstone.svg": 18, "Circuit_Red_Bull_Ringtrack.svg": 10,
    "Circuit_Monaco.svg": 19, "RaceCircuitAutodromaDiMonza.svg": 11,
    "Monza_track_map.svg": 11,
}

GOOD_SEG_PER_KM = 10.0       # Spa/Zandvoort/Catalunya territory
MARGINAL_SEG_PER_KM = 5.0    # Silverstone shipped here, corr 0.945
GOOD_SEG_PER_TURN = 3.5      # Hungaroring 3.7 and up = every clean ship
MARGINAL_SEG_PER_TURN = 2.4  # Catalunya-2023 2.6: worked, needed global fixes


def measure(path, length_m=None, turns=None):
    text = io.open(path, encoding="utf-8", errors="ignore").read()
    d = s2o._select_track_path_d(text, path)
    cmds = s2o.parse_svg_path_d(d)
    n_cubic = sum(1 for k, _ in cmds if k == "C")
    n_line = sum(len(c) for k, c in cmds if k == "L")
    pts = s2o.commands_to_polyline(cmds)
    seg = n_cubic + n_line
    # A stroked path with no fill is a centreline (what we want); a filled path
    # is usually a closed road RIBBON, which needs different handling.
    low = text.lower()
    kind = ("centreline (stroked, fill:none)"
            if 'fill="none"' in low or "fill:none" in low
            else "FILLED - may be a road ribbon, not a centreline")
    return dict(seg=seg, cubic=n_cubic, line=n_line, pts=len(pts), kind=kind,
                bytes=os.path.getsize(path),
                seg_km=(seg / (length_m / 1000.0)) if length_m else None,
                pts_km=(len(pts) / (length_m / 1000.0)) if length_m else None,
                seg_turn=(seg / turns) if turns else None)


def verdict(seg_km, seg_turn):
    if seg_turn is not None:
        if seg_turn >= GOOD_SEG_PER_TURN:
            return f"GOOD ({seg_turn:.1f} seg/turn) - every clean ship sits here"
        if seg_turn >= MARGINAL_SEG_PER_TURN:
            return (f"MARGINAL ({seg_turn:.1f} seg/turn) - Catalunya-2023 level: "
                    "usable, but check per-corner residuals hard")
        return (f"POOR ({seg_turn:.1f} seg/turn) - at or below Silverstone (1.9, "
                "corr 0.945); corners will be rounded off")
    if seg_km is None:
        return "pass --track-length and --turns for a verdict"
    if seg_km >= GOOD_SEG_PER_KM:
        return "GOOD - comparable to Spa/Catalunya, build on it"
    if seg_km >= MARGINAL_SEG_PER_KM:
        return "MARGINAL - Silverstone territory (shipped at corr 0.945)"
    return ("POOR by seg/km - but pass --turns before trusting that: a "
            "straight-heavy circuit scores low here even when faithful")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("svg", nargs="?")
    ap.add_argument("--track-length", type=float, default=None,
                    help="official circuit length in metres")
    ap.add_argument("--turns", type=int, default=None,
                    help="official turn count - enables the seg/turn verdict")
    ap.add_argument("--table", action="store_true",
                    help="measure every SVG in the repo root instead")
    args = ap.parse_args()

    if args.table or not args.svg:
        rows = []
        for f in sorted(glob.glob(os.path.join(REPO_ROOT, "*.svg"))):
            base = os.path.basename(f)
            try:
                rows.append((base, measure(f, KNOWN_M.get(base),
                                           KNOWN_TURNS.get(base))))
            except Exception as e:                              # noqa: BLE001
                print(f"{base:44s} FAILED: {type(e).__name__}: {e}")
        hdr = f"{'svg':44s} {'bytes':>7s} {'seg':>5s} {'seg/km':>7s} {'seg/turn':>9s}"
        print(hdr)
        for base, m in sorted(rows, key=lambda r: -(r[1]["seg_turn"] or 0)):
            sk = f"{m['seg_km']:7.1f}" if m["seg_km"] else "      ?"
            st = f"{m['seg_turn']:9.1f}" if m["seg_turn"] else "        ?"
            print(f"{base:44s} {m['bytes']:7d} {m['seg']:5d} {sk} {st}")
        print(f"thresholds: seg/turn GOOD >= {GOOD_SEG_PER_TURN}, MARGINAL >= "
              f"{MARGINAL_SEG_PER_TURN}  |  seg/km GOOD >= {GOOD_SEG_PER_KM:.0f}, "
              f"MARGINAL >= {MARGINAL_SEG_PER_KM:.0f}")
        return 0

    m = measure(args.svg, args.track_length, args.turns)
    print(f"file        {args.svg}  ({m['bytes']} bytes)")
    print(f"path type   {m['kind']}")
    print(f"segments    {m['seg']}  ({m['cubic']} cubic + {m['line']} line)")
    print(f"flattened   {m['pts']} points at {s2o.BEZIER_SAMPLES_PER_SEG}/segment")
    if m["seg_km"]:
        st = f"   {m['seg_turn']:.1f} segments/turn" if m["seg_turn"] else ""
        print(f"density     {m['seg_km']:.1f} segments/km{st}")
    print(f"VERDICT     {verdict(m['seg_km'], m['seg_turn'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
