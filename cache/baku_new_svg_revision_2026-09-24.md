# Baku replacement SVG: corrected line and video

User supplied `RaceCircuitGillesBaku.svg` after rejecting the first Baku render. The first map was a filled, self-intersecting road ribbon. Its medial-axis trace joined close streets and the `--road-stroke` renderer concealed, rather than fixed, the geometry. The first video remains at `azerbaijan_grand_prix_2026_optimal_lap.mp4` as a superseded artifact.

## Geometry and algorithm

- The replacement SVG is a single stroked centerline: 43 cubic segments, 1,679 sampled points. `svg_to_outline.py` now parses relative SVG `S/s` shorthand cubics (reflected prior control point). `tests/test_svg_parser.py` covers it.
- Generated `F1_Pipeline_Assets/tracks/azerbaijan_grand_prix_outline_new_svg.json` from that exact SVG, scaled to 6,003 m, 12 m nominal road width, 7.5 m minimum-radius setting. The source's sparse corner detail is a limitation. The road edge loops are simple polygons; the inner is contained within the outer. Closest distinct centerline passes are 38.26 m apart. Standard polygon renderer keeps the two roads separate and preserves the black gap. Do not use `--road-stroke` on this route.
- `sim_2026_lap.py` refinement used a left-pointing normal with reversed physical side widths. Corrected the QP width ordering and clipped the separately resampled IQP seed to the vehicle-width corridor. The resulting line is `...raceline_new_svg_fixed.json`.
- `cache/_constrain_baku_line.py` smoothly moves the handful of post-spline body-clearance violations inside the SVG corridor. Final `...raceline_new_svg_final.json`: 2,981 points, 0 off-track, minimum center-to-edge distance 0.94 m for a 1.9 m vehicle. The maximum local adjustment is 1.38 m, and maximum curvature after smoothing is 0.068 1/m.
- `raceline_video.py` accepts `--title-line1`, and primary HUD labels have a dark outline for readability over the road. Default title remains unchanged for other renders.

## Timing and rendering

- A pure model run on this sparse SVG yielded 96.911 s and speed-trace correlation 0.931 to 2026 FP2. That is too quick to present as a credible optimal-lap prediction. It was not used for animation timing.
- The new video follows the optimized line geometry with **2026 FP2 observed speed and time** (Russell, 103.347 s). Elevation display comes from 2025 qualifying position.z. It is a racing-line visualization at real practice pace, not a 96.911 s prediction. The final public videos retain the original `THE OPTIMAL LAP` main title at the user's request; the FP2 timing provenance is documented here.
- Render command for the final zoom-23 version: `raceline_video.py --outline F1_Pipeline_Assets/tracks/azerbaijan_grand_prix_outline_new_svg.json --raceline F1_Pipeline_Assets/tracks/azerbaijan_grand_prix_raceline_new_svg_final.json --telemetry-csv F1_Pipeline_Assets/exports/reference_2026_baku_fp2.csv --track-name "Azerbaijan Grand Prix" --zoom 23 --elevation-json F1_Pipeline_Assets/tracks/azerbaijan_grand_prix_elevation_new_svg.json --fps 30 --out cache/baku_zoom23_original_title.avi`, then transcode with ffmpeg/H.264. Use `--zoom 46` and `cache/baku_zoom46_original_title.avi` for the other public version.
- Preview at `cache/baku_new_svg_preview.mp4`. Contact sheet `cache/baku_new_svg_preview_contact.png`. The paired close-pass frames at 47 and 89 s are at `cache/baku_new_svg_parallel_passes.png`, visibly separated.

## Verification

- `python -m pytest tests/test_svg_parser.py tests/test_outline_geometry.py tests/test_smoke.py -q`: 24 passed.
- `python cache/_check_ontrack.py ...outline_new_svg.json ...raceline_new_svg_final.json baku_new_svg_final`: 0/2,981 center points beyond edge; worst offset -0.94 m.
- OpenCV's first long MP4 pass emitted an unindexed file (preserved as `cache/baku_new_svg_failed_mp4.mp4`). Re-rendered to `cache/baku_new_svg_intermediate.avi` (MJPEG, 3,101 frames), then transcoded with ffmpeg H.264 CRF 18 and `+faststart` into the final MP4.
- `python cache/_verify_baku_new_video.py`: final MP4 decoded **3,101/3,101 frames**, 1080×1920, 30 fps, 103.367 s, 17,035,563 bytes. Start, corner, both close passes (47/89 s), and finish inspected in `cache/baku_new_svg_final_checks.png`.

Official source: https://www.formula1.com/en/latest/article/fp2-russell-leads-antonelli-and-verstappen-in-second-azerbaijan-gp-practice.37CqNf2uaAyxvDPmvbt3Iw

## 2026-09-25: doubled zoom

User requested the main camera zoom doubled from 23 to 46. Preview `cache/baku_new_svg_zoom46_preview.mp4` was inspected at corner and close-pass frames. Full render used the same AVI/MJPEG to ffmpeg/H.264 path as above. Output `azerbaijan_grand_prix_2026_optimal_line_new_svg_zoom46.mp4`; all 3,101/3,101 frames decoded, 1080×1920, 30 fps, 103.367 s, 16,418,684 bytes. Start, turn, both close-road passes, and finish were inspected in `cache/baku_new_svg_zoom46_final_checks.png`. Zoom-23 final is preserved.

## 2026-09-25: title restored

User rejected the unrequested main-title change. Both public new-SVG MP4s were re-rendered with the renderer default `THE OPTIMAL LAP`, preserving the original file paths and the observed FP2 timing in the HUD. The zoom-46 replacement decoded 3,101/3,101 frames, 16,363,949 bytes; the zoom-23 replacement decoded 3,101/3,101 frames, 16,964,872 bytes. Their encoded title frames are in `cache/baku_original_title_final_checks.png` and `cache/baku_zoom23_original_title_final_checks.png`. Altered-title files were moved to `cache/baku_zoom46_changed_title.mp4` and `cache/baku_zoom23_changed_title.mp4` rather than deleted.
