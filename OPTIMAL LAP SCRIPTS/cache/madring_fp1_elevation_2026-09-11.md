# Madring FP1 data and elevation — 2026-09-11

The user now authorizes using completed Madring practice data and requests the 3D elevation flyover instead of the banking cross-section. This supersedes the initial pre-session-only scope for Madring. The prohibition on deleting anything remains in force.

## Data obtained

OpenF1 returned HTTP 401 with its global live-session lockout, including when rechecked after the user reported access was back. Formula 1's public timing archive was available. FastF1 3.9.0.dev2 successfully loaded FP1 using the `f1timing` backend, with caching disabled via `Cache.set_disabled()`; no existing cache was modified.

- Official archive: `https://livetiming.formula1.com/static/2026/2026-09-13_Spanish_Grand_Prix/2026-09-11_Practice_1/`.
- Official archive session key: 11362; event 1294; circuit Madring. Do not assume this is an OpenF1 session key.
- George Russell (#63), lap 20, 94.077 s, lap start 2026-09-11 12:14:11.218 UTC. Matches [Formula 1's official FP1 classification](https://www.formula1.com/en/results/2026/races/1294/spain/practice/1).
- Reference: `F1_Pipeline_Assets/exports/reference_2026_madring_fp1.csv`, 704 merged/interpolated rows spanning exactly 94.077 s. Recorded speed range 78–315 km/h.
- Original selected-lap samples: 354 car records and 348 position records in `cache/madring_fp1_20260911/`. All positions are original `pos` records, OnTrack, unique and chronological.
- Provenance: `cache/madring_fp1_20260911/provenance.json`; successful extraction log: `cache/madring_fp1_fetch_20260911_attempt2.log`. The first attempt's API-name error log is preserved separately.
- Integrated reference distance is 5345.468 m before subtracting its initial 0.325 m, giving a 5345.143 m lap span (~1.27% below the 5414 m scale). No hidden rescaling of the stored reference was applied.
- FP2 was checked through the public archive index; it still lacked a published session Path. No FP2 reference has been downloaded.

## Geometry and timing alignment

Both raw streams share exactly the timed lap origin (`Date - Time = 12:14:11.218 UTC`). Position time is mapped through reference distance, with the initial 0.325 m removed before fraction normalization. Raw car distance must not be re-zeroed at the first car sample, which is already 17.533 m into the lap.

Rigid XY registration (rotation, translation and one uniform scale) aligns the telemetry to the supplied SVG line: scale 1.003650; RMS 9.18 m; median 6.78 m; 95th percentile 18.54 m; maximum 27.00 m. Residuals include different racing lines and map/source error. A reflected fit is much worse (RMS 402.6 m), supporting the current direction.

The FP1 origin maps to source racing-line station 2590/2665 (roughly 151 m before the original proxy). A separate curvature/speed correlation suggested station 2583, within about 14 m. Use the XY-derived origin consistently for the preview's 2D line and 3D stations. The preview deliberately skips a second renderer correlation, which would otherwise roll only the 2D line.

Analysis: `cache/_madring_fp1_geometry_audit.py`, `cache/madring_fp1_geometry_audit.log`, and `cache/madring_fp1_elevation/validation.json`.

## Elevation and requested presentation

FastF1's documented coordinate scale is tenths of a metre. Dividing Z by ten gives a raw range 724.1–748.7 m, a 24.6 m span, and zero endpoint mismatch. Absolute ASL is unverified: the circuit operator lists 671–697 m. Do not label the telemetry's raw baseline ASL or force both extrema to those design values.

The profile is therefore **height above the smoothed lap low point**. Periodic Gaussian smoothing with sigma 2 position samples yields a 23.9798 m span and seamless closure. Low point is around 10.5% and high point around 35.3% of lap distance, consistent with the early low section and hill in the operator's circuit description. Retain the raw coordinates and removed datum in provenance.

- Data and aligned line: `cache/madring_fp1_elevation/madring_fp1_elevation.json` and `madring_fp1_raceline.json`.
- Diagnostic figure: `cache/madring_fp1_elevation/geometry_speed_elevation.png` (geometry, measured vs baseline speed, elevation).
- Interactive output: `madring_fp1_elevation_3d_overview.html`. Uses the existing vendored Three.js viewer, corrected relative-height/FP1 labels and a wider initial camera; 4x display exaggeration. Browser-checked: scene loads, whole track fits, play/pause and scrubbing update speed/time/height. Earlier close-camera output `madring_fp1_elevation_3d.html` is retained.
- Loopback preview server: port 8767, bound only to 127.0.0.1, started via exec session 42558. The HTML is self-contained and can also be opened directly without that server.
- Video render: `madring_2026_FP1_ELEVATION_PREVIEW.mp4`, launched from `cache/_build_madring_fp1_elevation_preview.py --render`; log `cache/madring_fp1_elevation_render.log`. Uses existing `raceline_video.py` with `--elevation-json` and no `--banking-json`. Title is FP1 ELEVATION; actual Russell FP1 speed/timing is used and no synthetic ERS modes are added. Check final log and video verification below before claiming render completion.

## What remains for the optimal lap

The FP1 replay is a reference and visual check, not the final simulated optimal lap. The earlier unbanked default-knob 97.537 s diagnostic differs from FP1 especially through the middle sector. Next work is to assess local geometry/corner constraints and banking in the physics, choose per-track CDA/CL/rho using the actual speed/rate evidence, and verify the resulting synthetic lap. Keep the requested elevation flyover for that final render, regardless of whether banking is present in the physical track model.

No files were deleted. Existing Monza work and shared physics, registry and rendering modules were retained. New scripts/artifacts use separate paths and exclusive-create checks where practical.

## Final verification and calibration handoff

- Video render completed with exit code 0: 2823 frames at 30 fps, 1080x1920, 94.1 s container duration (94.077 s timed lap rounded to frame duration), 69,464,550 bytes.
- Successfully decoded checkpoints at 0, 33, 57 and 85 seconds plus the final frame. Visually inspected `cache/madring_fp1_elevation/video_contact_sheet.png`: elevation flyover and car are visible in the lower band, FP1 title and true lap time are displayed, and no banking panel is drawn.
- Interactive overview was browser-verified with full-track framing, relative-height labels, live speed/time updates and working pause/scrub. It is the preferred HTML deliverable; preserve the earlier closer-camera HTML as well.
- Phase-registered baseline vs FP1: correlation 0.94833, MAE14.55 km/h, RMSE20.04 km/h. Baseline is 3.460 s slower. Largest local minimum residuals at reference lap fractions44.04%,61.28%,79.20% are -44.5,-35.1,-53.7 km/h. These are detected speed minima, not assigned turn numbers.
- Low/medium major-corner median residual is only -4.7 km/h and signs are mixed. Evidence does not justify a global CL increase or indiscriminate SVG edits. Investigate those local constraints and their alignment first.
- Existing rate audit, FP1 vs baseline: drop median37.6 vs46.3; drop p9098.5 vs90.9; gain median21.2 vs28.4 km/h/s. Different sample rates and brake masks matter; equality is not a justified calibration target.
- Final calibrated simulation remains outstanding. The delivered video is explicitly an FP1 reference/elevation preview and contains no claimed new optimal-lap prediction.
