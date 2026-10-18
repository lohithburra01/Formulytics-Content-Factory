"""Final Madring optimal-lap assets: elevation for the chosen line, then the render.

Elevation = mean height of the 73 FP1+FP2 push laps (cache/madring_gps_line),
relative to the lap low point (absolute datum unverified), mapped onto the
FINAL line's stations by projection onto the measured practice path. The render
reuses raceline_video.py unchanged (3D elevation flyover, no banking panel);
the sim CSV carries soc/mode so the renderer skips its telemetry re-alignment:
line and CSV share the line's own origin (the measured timing line).
New files only; refuses to overwrite.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "cache"))
sys.stdout.reconfigure(encoding="utf-8")
from _madring_calib_v2 import GPS, project_s  # noqa: E402


def build_elevation(line_path, out_path):
    line = json.loads(Path(line_path).read_text(encoding="utf-8"))
    p = np.asarray(line["raceline"], float)
    arc = np.asarray(line["arc_length"], float)
    L = float(line["track_length_m"])
    meas = json.loads((GPS / "madring_gps_raceline.json").read_text(encoding="utf-8"))
    melev = json.loads((GPS / "madring_gps_elevation.json").read_text(encoding="utf-8"))
    Lm = float(meas["track_length_m"])
    s_meas = project_s(np.asarray(meas["raceline"], float), p)
    z = np.interp(s_meas / Lm, np.asarray(melev["dist_frac"]), np.asarray(melev["elev_m"]), period=1.0)
    z -= z.min()
    grid = np.linspace(0.0, 1.0, 2000, endpoint=False)
    elev = dict(track="madring",
                source=f"F1 official archive, 2026 Madring FP1+FP2, mean of the push laps "
                       f"({melev['source'].split('mean of ')[-1]}); mapped onto the optimal line",
                altitude_reference="metres above the lap low point; absolute vertical datum unverified",
                alt_min_m=0.0, alt_max_m=round(float(z.max()), 2), span_m=round(float(z.max()), 2),
                dist_frac=grid.round(5).tolist(),
                elev_m=np.interp(grid * L, arc, z, period=L).round(3).tolist(),
                stations=np.column_stack([p, z]).round(3).tolist(),
                sf_source="measured timing line; same origin as the 2D line and the sim CSV")
    with Path(out_path).open("x", encoding="utf-8") as fh:
        json.dump(elev, fh)
    print(f"[elev] {len(p)} stations, span {elev['span_m']} m -> {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--line", required=True)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--outline", required=True)
    ap.add_argument("--elev-out", required=True)
    ap.add_argument("--out", default=str(ROOT / "madring_2026_optimal_lap.mp4"))
    ap.add_argument("--track-name", default="Spanish Grand Prix")
    ap.add_argument("--zoom", default="30")
    ap.add_argument("--render", action="store_true")
    a = ap.parse_args()
    if not Path(a.elev_out).exists():
        build_elevation(a.line, a.elev_out)
    if not a.render:
        return 0
    if Path(a.out).exists():
        raise FileExistsError(a.out)
    import raceline_video as video
    sys.argv = ["raceline_video.py", "--outline", a.outline, "--raceline", a.line, "--telemetry-csv", a.csv,
                "--track-name", a.track_name, "--zoom", a.zoom, "--elevation-json", a.elev_out, "--out", a.out]
    video.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
