# Madring 2026 optimal lap — calibration and render (2026-09-11)

Continues `madring_bringup_2026-09-11.md` and `madring_fp1_elevation_2026-09-11.md`.
User authorised practice data for calibration and asked for the 3D elevation flyover.
User rule still in force: never delete anything. No existing file was modified; every
output below is a new, exclusive-create file.

## Result

- Video: `madring_2026_optimal_lap.mp4` (verification at the end of this file).
- Sim lap **92.363 s (1:32.363)**, v 70-328 km/h, built-in sanity PASS.
- References, F1 official archive via FastF1 (`backend="f1timing"`, cache disabled):
  FP2 fastest ANT **93.662**; FP1 fastest RUS 94.077; ideal lap from best sectors
  FP2 **93.260** (FP1 93.933); top-10 push-lap median trace 93.766; push-lap p90
  envelope 91.711 (an envelope, not a lap).
- Sim vs top-10 trace on the measured distance axis: corr **0.9554**, MAE 13.6 km/h,
  corner median +1.3 km/h (MAD 4.3). Top speed 324 = top-10 324 (p90 333).
- Rates: gain median 26.2, drop median 46.2 km/h/s (real FP1 drop 37.6; shipped sims
  run +8-9 over their real trace, so in family).

## Final configuration

| Item | Value |
|---|---|
| Line | `cache/madring_opt_lines/relax3r_raceline.json`: SVG optimiser line (FP1-registered origin, 8.2 m from the measured timing line) + 3 FITTED local relaxations |
| Fitted sites (measured axis) | 2340 m @ 204.5 km/h: R 61.7→76.4 m, shift 3.9 m · 3267 m @ 147: R 39.5→54.4, shift 9.2 · 4194 m @ 207.4: R 62.9→77.5, shift 3.3 (targets = top-10 minima at CL 5.0) |
| Drawn road | `F1_Pipeline_Assets/tracks/madring_grand_prix_outline_relax3r.json`: provisional SVG outline moved with the same tapered displacement (max 9.18 m); valid, simple rings, line 100% inside (0.3 m tol) |
| Knobs | CDA 0.66, CL 5.0, rho = ISA(684 m) = 1.1466 |
| La Monumental | EFFECTIVE bank 4° (physical 24% slope = 13.5°), 2436-3021 m on the line's arc, 40 m ramps |
| Elevation | mean Z of 73 push laps, height above lap low point (datum unverified), span 24.5 m: `cache/madring_opt_lines/relax3_elevation.json` |
| Sim output | `cache/madring_calib_v2/relax3r_c066_l50_b4.csv` (+ `.json` metrics, `_stations.npz`) |

Knob choice: CDA 0.66 matches the top-10 top speed exactly (0.70 gave 321). CL 5.0 puts
the unfitted corners' median at ~0 (4.2 gave median -8). Bank 4° vs 6°: equal trace corr
(0.9554 vs 0.9556), lower MAE (13.6 vs 14.1), and real throttle in the loop's first half
is 66-72% with no brake (grip-limited at 232-244 km/h), where 6° ran the sim at ~258.

## Evidence chain

1. Codex baseline (SVG line, default knobs, 684 m): 98.65 s; the three fast bends
   -36..-57 km/h while slow corners were within ±15. `cache/madring_final_calibration/`.
2. Diagnosis `cache/madring_diagnosis/`: every deficit is a 149-225 km/h bend; the SVG
   line's radius there (62/40/63 m) is below what the frozen grip model needs for FP1's
   speed (82/58/87 m). Slow corners agree.
3. Practice GPS (`cache/madring_practice_laps/`: 593 timed laps; `cache/madring_gps_line/`):
   **the F1 position feed is map-matched**. 73 push laps sit within 0.033 m RMS of one
   reference path, and speed-integrated distance / path length = 1.0003. Its large-scale
   shape is accurate, but its corners are centreline-tight: driven directly it gives
   105.97 s with every corner -11..-63 km/h. It also flattens chicanes: the optimiser in a
   12 m corridor around it gives 88.49 s and takes the 1532 m chicane at 286 vs 113 km/h
   (14 m: 87.43 s). So it is used only for the timing-line origin, elevation and the
   comparison distance axis.
4. The two fast kinks (2340, 4194 m) stay ~-40..-50 km/h in every geometry tried (SVG,
   raw GPS, GPS corridors 12/14 m), so no available map resolves them; fitted locally.
5. T1 fit refused: local smoothing cannot reach the target (R 27→11.9 m, 18 m shift).
   `relax4` line/outline retained but unused; the tool now refuses unreachable sites.
6. Distance mapping of practice laps: speed-integrated distance scaled to the measured
   path plus a slow position correction (70 of 73 push laps kept).

## Residuals (documented, not hidden)

- **T1/T2**: the SVG has one tight corner ~60 m early; the real complex has two apexes
  (116 then 106 km/h). Sim min 93 at the wrong place, brakes ~50 m early: costs ~1.0 s.
- **4200-4550 m**: the SVG is too straight (real throttle 36-81% = bends); sim +25-30 km/h.
- **La Monumental 2nd half**: real cars flat out (throttle 100%) but held at 268-283 km/h
  by energy clipping; the frozen 2026 energy model deploys to ~302.
- Hairpin 4730 m -8 km/h; 4881 m corner +17; 1896 m +14.
- These partly cancel. The sim is 1.40 s under the top-10 median trace, 0.90 s under the
  FP2 ideal lap and 0.65 s over the p90 envelope.
- Three corners are FITTED, not predictions: 2340, 3267, 4194 m. Unfitted corners:
  -12, +6, +14, 0, -8, +17, -2 km/h.

## Scripts (new)

`cache/_madring_deficit_diagnosis.py`, `_fetch_madring_fp2.py`,
`_fetch_madring_practice_laps.py`, `_madring_gps_line.py`, `_madring_calib_v2.py`,
`_madring_opt_line.py`, `_madring_overlay_v2.py`, `_madring_line_relax.py`,
`_madring_final_assets.py`. Shared pipeline code (`sim_2026_lap.py`, `raceline_video.py`,
registry, frozen car physics) untouched. Evidence plots: `cache/madring_diagnosis/*.png`,
`cache/madring_gps_line/gps_line_check.png`, `cache/madring_calib_v2/overlay_*.png`.

Reproduce (outputs are exclusive: use new names):

```
python cache/_madring_line_relax.py --name <new> --cl 5.0 --site 2340:204.5:70 --site 3267:147:80 --site 4194:207.4:70
python cache/_madring_calib_v2.py --name <new> --line cache/madring_opt_lines/<new>_raceline.json --cda 0.66 --cl 5.0 --bank-peak 4 --bank-start 2436 --bank-end 3021 --bank-ramp 40
python cache/_madring_final_assets.py --line <line> --csv <csv> --outline <outline> --elev-out <new.json> --render --out <new.mp4>
```

## Next

- After qualifying (Sat 2026-09-12): fetch Q the same way (`_fetch_madring_fp2.py`
  pattern) and compare lap and trace. Madring still has no registry entry.
- Better geometry would fix the residuals: a survey-grade layout (T1/T2 complex,
  4200-4550 m bends, La Monumental's shape).

## Video verification (done)

- `madring_2026_optimal_lap.mp4`: exit 0 (log `cache/madring_optimal_render.log`); 70,147,136 bytes,
  1080x1920 @ 30 fps; container 2770 frames and **all 2770 decoded** (92.33 s), via
  `cache/_madring_verify_video.py`.
- Inspected `cache/madring_optimal_video_check/contact_sheet.png` (0/15/30/46/62/78 s): title
  "THE OPTIMAL LAP / SPANISH GRAND PRIX", car on the drawn road with its speed trail, minimap,
  DEPLOY/REGEN + speed readouts sane (246/290/149/263/233/77 km/h), 3D elevation flyover band
  present, no banking panel.
- Final-frame HUD crop reads **LAP TIME 1:32.329**: the 30 fps CSV span the renderer always
  shows (same path as every shipped track); the sim's own lap is 92.363 s.
- The renderer skipped telemetry re-alignment (synthetic CSV with soc/mode), so line, CSV and 3D
  stations share one origin.
