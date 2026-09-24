# Baku 2026 optimal lap — 2026-09-24

## Sources and track

- User SVG: `Baku_Formula_One_circuit_map.svg` (418 segments, dense filled road ribbon). Direct `svg_to_outline.py` use would trace both edges as one lap. `cache/_build_baku_outline.py` rasterizes its road, follows the medial line with the official 2025 Q position trace, and repairs the close Old City passes. Registration residual to the SVG medial line: median 0.31 SVG units, p95 1.24. Output has 2,000 stations, 6,003 m perimeter, anti-clockwise direction, road width 7.6–13.0 m. Centreline is simple; the inner edge overlaps locally where the two roads pass close to each other.
- F1 timing archive via FastF1 (`cache/_fetch_baku_refs.py`): 2025 Q VER 101.117 s, 5,937 m integrated; 2026 FP1 RUS 105.387 s, 5,943 m; 2026 FP2 RUS 103.347 s, 5,955 m. Metadata are in `cache/reference_*_baku_*_provenance.json`. The 1% distance deficit is from timing telemetry integration; official length is 6,003 m. OpenF1 returned 404 on its `laps` endpoint, so its fetcher was not used.
- 2025 Q position z gives -24.6 to +1.9 m ASL, 26.6 m span, -0.1 m lap closure. `cache/_build_baku_elevation.py` lifts the simulated raceline to 3D. The HUD and flyover show this physical profile; no banking model is applied.

## Simulation choice

- The 2025-to-2026 transfer predicted a 101.926–106.754 s lap and 341.1 km/h top speed. The automatic fit converged at CdA 0.6991 / ClA 3.4 and 105.889 s, which is slower than the already observed 2026 FP1 and FP2 best laps. It was rejected for this video.
- Practice-checked setting: CdA **0.717**, ClA **4.45**, density **1.2274 kg/m³**. Simulated lap **102.884 s**, top **340 km/h**; 30 fps telemetry/HUD span **102.851 s** (1:42.851). Against FP2: speed-trace correlation **0.978**, forward orientation and zero circular shift, about **0.46 s faster** than Russell's FP2 lap. The video represents a synthetic optimal lap, not an actual driver lap or a certain qualifying prediction.
- Project realism gate: **8/9**. The acceleration median is **30.5 km/h/s** against the gate's 28 limit; measured FP1 and FP2 medians are 25.5 and 26.6. Other gate checks pass. The car model's acceleration remains a limitation and the video should be treated as provisional.
- Raw outline on-track check: 15/2,974 racing-line points are more than 0.3 m past the SVG edge, worst 1.45 m, at three corners. The video uses `--road-stroke`, a display-only locally width-matched road rendering, to keep the car and two close streets visually coherent. It removes the black polygon-fill holes and overlapping kerbs at the Old City passes. The simulated trajectory and telemetry are unchanged.

## Reproduction

1. Run `python cache/_fetch_baku_refs.py` with a Python environment containing FastF1 if the reference CSVs or 2025 Q position CSV are missing.
2. Run `python cache/_build_baku_outline.py`.
3. Run `python cache/_predict_track.py --track baku` for the 2025-transfer targets.
4. With the repo's Python 3.10 environment, run `sim_2026_lap.py --outline F1_Pipeline_Assets/tracks/azerbaijan_grand_prix_outline.json --raceline-out F1_Pipeline_Assets/tracks/azerbaijan_grand_prix_raceline.json --csv-out F1_Pipeline_Assets/exports/baku_2026_synthetic.csv --reference-csv F1_Pipeline_Assets/exports/reference_2025_baku_q.csv --inset 0 --drive-ccw --cda 0.717 --cl 4.45 --rho 1.2274`.
5. Run `python cache/_build_baku_elevation.py`.
6. Run `raceline_video.py --outline F1_Pipeline_Assets/tracks/azerbaijan_grand_prix_outline.json --raceline F1_Pipeline_Assets/tracks/azerbaijan_grand_prix_raceline.json --telemetry-csv F1_Pipeline_Assets/exports/baku_2026_synthetic.csv --track-name "Azerbaijan Grand Prix" --zoom 23 --elevation-json F1_Pipeline_Assets/tracks/azerbaijan_grand_prix_elevation.json --road-stroke --out azerbaijan_grand_prix_2026_optimal_lap.mp4`.

## Verification

- `pytest tests/test_smoke.py tests/test_outline_geometry.py tests/test_transfer.py -q`: 19 passed.
- SVG corridor check: 2,000 stations, perimeter 6,003.0 m, width 7.6–13.0 m, no pinch. Direction check: simulated vs 2025 Q speed trace forward, correlation 0.986 at the default probe; final vs FP2 correlation 0.978, shift 0.
- Final MP4 `azerbaijan_grand_prix_2026_optimal_lap.mp4`: renderer exit 0, 85,724,868 bytes, 1080×1920 at 30 fps, 3,086/3,086 frames decoded, 102.867 s. Opening, final, and the three flagged-corner frames were inspected in `cache/baku_clean_video_check/contact_sheet.png` and the full-size PNGs there. The car stays on the displayed road at the inspected points; the close-street section is continuous without black holes or crossing kerbs. An earlier polygon-fill render is preserved in `cache/baku_polygon_render_2026-09-24.mp4` for comparison.

Official source pages: [2025 Azerbaijan qualifying](https://www.formula1.com/en/results/2025/races/1269/azerbaijan/qualifying), [2026 FP1](https://www.formula1.com/en/results/2026/races/1295/azerbaijan/practice/1), [2026 FP2 report](https://www.formula1.com/en/latest/article/fp2-russell-leads-antonelli-and-verstappen-in-second-azerbaijan-gp-practice.37CqNf2uaAyxvDPmvbt3Iw), [Baku circuit](https://www.bakucitycircuit.com/news/bakus-tenth-race-what-to-expect-from-the-2026-azerbaijan-grand-prix).
