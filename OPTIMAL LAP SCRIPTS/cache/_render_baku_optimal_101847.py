"""Render the validated Baku optimal pace with the existing title and zoom 46."""

import argparse
import runpy
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()

    # The precomputed-raceline renderer never calls the QP optimizer. Supply a
    # load-only stub if cvxopt is not installed in this Python environment.
    try:
        import cvxopt  # noqa: F401
    except ImportError:
        stub = types.ModuleType("cvxopt")
        stub.matrix = lambda *a, **kw: None
        stub.solvers = types.SimpleNamespace(options={})
        sys.modules["cvxopt"] = stub

    output = (ROOT / "cache/baku_optimal_101847_zoom46_borderless_preview.avi"
              if args.preview else
              ROOT / "cache/baku_optimal_101847_zoom46_borderless.avi")
    sys.argv = [
        "raceline_video.py",
        "--outline", str(ROOT / "F1_Pipeline_Assets/tracks/azerbaijan_grand_prix_outline_new_svg.json"),
        "--raceline", str(ROOT / "F1_Pipeline_Assets/tracks/azerbaijan_grand_prix_raceline_new_svg_final.json"),
        "--telemetry-csv", str(ROOT / "F1_Pipeline_Assets/exports/baku_2026_optimal_pace_1p5s_faster_with_modes.csv"),
        "--elevation-json", str(ROOT / "F1_Pipeline_Assets/tracks/azerbaijan_grand_prix_elevation_new_svg.json"),
        "--track-name", "Azerbaijan Grand Prix",
        "--title-line1", "THE OPTIMAL LAP",
        "--zoom", "46",
        "--fps", "1" if args.preview else "30",
        "--telemetry-prealigned",
        "--no-text-stroke",
        "--out", str(output),
    ]
    print(f"[baku] rendering {output} at zoom 46, title THE OPTIMAL LAP, no text stroke", flush=True)
    runpy.run_path(str(ROOT / "raceline_video.py"), run_name="__main__")


if __name__ == "__main__":
    main()
