"""Build an FP1 reference preview with measured, relative track elevation.

Uses the existing SVG, renderer and viewer. Does not tune the simulated lap,
modify shared render code, delete files, or relabel practice as an optimal lap.
Outputs are exclusive: reruns refuse to overwrite an existing artifact.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--render", action="store_true", help="Render the saved FP1 preview inputs")
    args = parser.parse_args()
    dest = ROOT / "cache/madring_fp1_elevation"
    outline_path = ROOT / "F1_Pipeline_Assets/tracks/madring_grand_prix_outline_provisional.json"
    line_path = dest / "madring_fp1_raceline.json"
    elevation_path = dest / "madring_fp1_elevation.json"
    ref_path = ROOT / "F1_Pipeline_Assets/exports/reference_2026_madring_fp1.csv"

    if args.render:
        import raceline_video as video
        out = ROOT / "madring_2026_FP1_ELEVATION_PREVIEW.mp4"
        if out.exists():
            raise FileExistsError(out)
        # Registration was established from actual FP1 XY. A second curvature-
        # based roll would move only the 2D line, leaving the 3D stations behind.
        video.align_raceline_to_telemetry = lambda raceline, *unused: raceline
        video.TITLE_LINE_1 = "FP1 ELEVATION"
        sys.argv = ["raceline_video.py", "--outline", str(outline_path),
                    "--raceline", str(line_path), "--telemetry-csv", str(ref_path),
                    "--track-name", "MADRING - RUSSELL", "--zoom", "30",
                    "--elevation-json", str(elevation_path), "--out", str(out)]
        return video.main()

    dest.mkdir(exist_ok=True)
    html_path = ROOT / "madring_fp1_elevation_3d.html"
    audit_path = dest / "validation.json"
    png_path = dest / "geometry_speed_elevation.png"
    for path in (line_path, elevation_path, html_path, audit_path, png_path):
        if path.exists():
            raise FileExistsError(path)

    import _madring_fp1_geometry_audit as audit
    match = audit.best["rotation"]
    assert match["rms_m"] < 15.0, "SVG/FP1 position registration needs investigation"
    assert match["p95_m"] < 25.0
    assert 0.97 < match["scale"] < 1.03
    assert match["rms_m"] < audit.best["reflection"]["rms_m"] / 5

    shift_idx = int(round(match["shift_frac"] * len(audit.points))) % len(audit.points)
    line = np.roll(audit.points, -shift_idx, axis=0)
    kappa = np.roll(np.asarray(audit.rl["kappa"]), -shift_idx)
    seg = np.linalg.norm(np.diff(np.vstack([line, line[0]]), axis=0), axis=1)
    arc = np.r_[0.0, np.cumsum(seg)[:-1]]
    length = float(seg.sum())
    with line_path.open("x", encoding="utf-8") as stream:
        json.dump(dict(raceline=line.tolist(), arc_length=arc.tolist(),
                       kappa=kappa.tolist(), track_length_m=length, banking_deg=[],
                       source="Provisional SVG racing line, origin registered to FP1 position XY",
                       sf_source_shift_idx=shift_idx, sf_source_shift_frac=shift_idx/len(line)), stream)

    grid = np.linspace(0.0, 1.0, 2000, endpoint=False)
    raw_z = audit.pos.Z.to_numpy(dtype=float) / 10.0
    z_smooth = gaussian_filter1d(raw_z, 2.0, mode="wrap")
    height = np.interp(grid, audit.pos_frac, z_smooth, period=1.0)
    raw_datum = float(height.min())
    height -= raw_datum
    station_height = np.interp(arc/length, grid, height, period=1.0)
    stations = np.column_stack([line, station_height])
    span = float(height.max())
    assert np.isfinite(stations).all() and 2 < span < 150
    assert abs(float(raw_z[-1]-raw_z[0])) < 8
    assert abs(float(height[-1]-height[0])) < 0.5
    elevation = dict(track="madring", source="F1 official archive, 2026 Madring FP1, Russell lap 20 (94.077 s); Z/10, periodic Gaussian sigma=2",
                     altitude_reference="metres above smoothed lap low point; absolute vertical datum unverified",
                     raw_height_min_m=float(raw_z.min()), raw_height_max_m=float(raw_z.max()),
                     raw_span_m=float(np.ptp(raw_z)), removed_raw_datum_m=raw_datum,
                     alt_min_m=0.0, alt_max_m=round(span,2), span_m=round(span,2),
                     dist_frac=grid.round(5).tolist(), elev_m=height.round(3).tolist(),
                     stations=stations.round(3).tolist(),
                     sf_source="Rigid XY registration to the timed FP1 lap; same origin as 2D line")
    with elevation_path.open("x", encoding="utf-8") as stream:
        json.dump(elevation, stream)

    # Reuse the existing self-contained viewer template, changing labels only
    # for this artifact. Reference timing is 94.077 s, not a simulated pole.
    import _build_3d_viewer as viewer
    reference = pd.read_csv(ref_path)
    dist = reference.distance.to_numpy() - reference.distance.iloc[0]
    distance = float(dist[-1])
    replay = [[round(float(t),4), round(float(d/distance),7), round(float(v),1)]
              for t,d,v in zip(reference.time_s, dist, reference.speed)]
    template = viewer.TEMPLATE.replace(
        "pre-FP1 optimal lap __LAPTIME__ · real altitude from F1 position telemetry (span __SPAN__ m)",
        "Russell FP1 reference __LAPTIME__ · measured relative elevation · SVG line preview (span __SPAN__ m)")
    template = template.replace("M ASL", "M ABOVE LOW POINT").replace("m ASL", "m above low point")
    replacements = {"__IMPORTMAP__": viewer.importmap(), "__NAME__": "MADRING · FP1",
                    "__LAPTIME__": "1:34.077", "__SPAN__": f"{span:.2f}",
                    "__ALTMIN__": "0", "__ALTMAX__": f"{span:.2f}",
                    "__STATIONS__": json.dumps(elevation["stations"],separators=(",",":")),
                    "__EFRAC__": json.dumps(elevation["dist_frac"],separators=(",",":")),
                    "__ELEV__": json.dumps(elevation["elev_m"],separators=(",",":")),
                    "__LAPROWS__": json.dumps(replay,separators=(",",":")),
                    "__TOTAL__": str(length)}
    for key,value in replacements.items():
        template = template.replace(key,value)
    assert all(token not in template for token in replacements)
    assert "pre-FP1 optimal lap" not in template and "M ASL" not in template
    with html_path.open("x", encoding="utf-8") as stream:
        stream.write(template)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    mapped_xy = audit.xy @ np.asarray(match["rotation"]) * match["scale"] + np.asarray(match["translation"])
    fig, axes = plt.subplots(3,1,figsize=(12,12),gridspec_kw={"height_ratios":[2,1,1]})
    axes[0].plot(line[:,0],line[:,1],label="SVG provisional racing line",lw=1.5)
    axes[0].plot(mapped_xy[:,0],mapped_xy[:,1],label="FP1 positions, rigid alignment",lw=1,alpha=.8)
    axes[0].scatter(*line[0],color="green",label="FP1 timing-line anchor",zorder=4)
    axes[0].set_aspect("equal"); axes[0].legend(fontsize=8)
    axes[0].set_title(f"Madring geometry check | XY RMS {match['rms_m']:.1f} m (includes differing racing lines)")
    sim = pd.read_csv(ROOT / "cache/madring_geometry_verified.csv")
    sim_frac = (sim.distance / length - shift_idx/len(line)) % 1
    sort = np.argsort(sim_frac)
    axes[1].plot(dist/distance*100,reference.speed,label="Russell FP1 1:34.077")
    axes[1].plot(sim_frac.iloc[sort]*100,sim.speed.iloc[sort],label="Unbanked default-knob diagnostic 1:37.537",alpha=.8)
    axes[1].set_ylabel("Speed (km/h)"); axes[1].legend(fontsize=8); axes[1].grid(alpha=.2)
    axes[2].fill_between(grid*100,height,0,color="#e8890c",alpha=.3)
    axes[2].plot(grid*100,height,color="#e8890c",label=f"Measured relative height, smoothed span {span:.2f} m")
    axes[2].set_ylabel("Height above low point (m)"); axes[2].set_xlabel("Lap distance from FP1 timing line (%)")
    axes[2].legend(fontsize=8); axes[2].grid(alpha=.2)
    fig.tight_layout(); fig.savefig(png_path,dpi=130); plt.close(fig)
    results = dict(registration=match, sf_index=shift_idx, line_length_m=length,
                   reference_lap_s=94.077, reference_distance_m=distance,
                   raw_elevation_span_m=float(np.ptp(raw_z)), smoothed_span_m=span,
                   height_seam_m=float(height[-1]-height[0]), relative_height_only=True,
                   banking_panel=False, preview_only=True)
    with audit_path.open("x", encoding="utf-8") as stream:
        json.dump(results, stream, indent=2)
    print(json.dumps(results,indent=2))
    print("Viewer:",html_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
