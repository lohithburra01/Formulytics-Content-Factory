# Variable inventory: F1 optimal-lap pipeline (sandbox)

Repo: `D:\f1_hot_lap\OPTIMAL LAP SCRIPTS_sandbox`. Read-only audit, 2026-10-19.
Scope: make_{singapore,bahrain(+what_could_have_been),sepang,silverstone}_2026_lap.bat (other make_*_2026 bats are used only for flag comparison), fetch_openf1_lap.py, svg_to_outline.py,
cache/_track_registry.py, _predict_track.py, _transfer_2026.py, _autofit_2026.py, _gate_2026.py, _check_ontrack.py,
cache/era2017/_opt_line_2017.py, cache/bahrain/_apex_gaps.py, sim_2026_lap.py, raceline_video.py,
F1_Pipeline_Assets/calibration/vehicle_calibration.json. The wrappers these bats call were also read where they
override something: cache/bahrain/_opt_line_2026.py, cache/singapore/_opt_line_2026_sg.py, cache/_sim_singapore.py,
cache/singapore/_sg_grip.py, cache/_autofit_singapore.py, cache/singapore/_autofit_rl_in_sg.py,
cache/bahrain/_autofit_rl_in.py, cache/singapore/_build_official_outline.py (header), cache/_sepang_t1_apex.py (args).

Origin key: **MEASURED** = read from a real-data file. **COMPUTED** = a script derived it from data. **KNOWLEDGE** = from a cited source or regulation note.
**HUMAN** = chosen by the user (memory/feedback note). **ASSUMED** = hard-coded with no recorded origin (magic number, AI-picked, or a rationale with no data).
Abbreviations: sim = sim_2026_lap.py, rv = raceline_video.py, reg = cache/_track_registry.py, SG/BH/SP/SV = Singapore/Bahrain/Sepang/Silverstone bats.

| # | Variable | Stage | Where set | Current value(s) | Origin | Evidence |
|---|---|---|---|---|---|---|
| 1 | OpenF1 API base / data source | fetch | fetch_openf1_lap.py:22 | https://api.openf1.org/v1 | KNOWLEDGE | docstring: OpenF1 publishes sooner than FastF1 |
| 2 | HTTP retry/backoff (6 tries, 5*2^n s, 429 >= 30 s, timeout 90) | fetch | fetch_openf1_lap.py:27-45 | as stated | ASSUMED | comment re lost Monza fetch; operational only |
| 3 | --year | fetch | BH:18 / SG:19 / SV:18 | 2025 (BH, SG), 2026 (SV) | HUMAN | memory prefp1-transfer-calibration (2025 Q ref method); SV re-pinned to 2026 FP1 (memory silverstone-2026-calibration) |
| 4 | --session | fetch | bats; default fetch:60 | Qualifying (BH, SG), "Practice 1" (SV); default Qualifying | HUMAN | same as #3 |
| 5 | --country | fetch | bats; reg | Bahrain, Singapore, "United Kingdom" (SV bat) vs reg "Great Britain" | KNOWLEDGE | OpenF1 country_name; the two Silverstone spellings differ |
| 6 | --circuit filter | fetch | BH:18 / reg | Sakhir (BH); none for SG/SV | KNOWLEDGE | reg:126: the 2026 Bahrain GP meeting is at Sepang |
| 7 | Lap pick = fastest valid non-pit-out lap of session, any driver (--driver default None) | fetch | fetch:88-99 | fastest | ASSUMED | no recorded rationale |
| 8 | Telemetry window = start + duration + 0.5 s | fetch | fetch:102 | +0.5 s | ASSUMED | none |
| 9 | Min telemetry samples | fetch | fetch:116 | 20 | ASSUMED | guard |
| 10 | Distance = trapezoid integral of speed (~3-4 Hz) | fetch | fetch:128 | integrated: BH 5389 m vs 5412, SG 4888 vs 4940 | COMPUTED | reg:121,141 comments give the drift |
| 11 | ers_deploy column | fetch | fetch:138 | 0 | KNOWLEDGE | OpenF1 does not expose it (docstring) |
| 12 | Reuse cached ref CSV (`if not exist`) | fetch | BH:18, SG:19 | skips the fetch if the file exists; SV always refetches, and a failure is non-fatal, so the old CSV is reused | ASSUMED | bat comment (SV:20) |
| 13 | SVG source file | geometry | BH:20, SG:21, SP:20, SV:5 | Bahrain_International_Circuit--Grand_Prix_Layout_with_DRS.svg; Marina_Bay_circuit_2023.svg; Sepang.svg; RaceCircuitSilverstone.svg | ASSUMED | BH bat describes its SVG (5.9 seg/turn); no record of who chose any of them |
| 14 | --track-length | geometry | svg_to_outline:507 default; bats | default 4361 (Canada); BH 5412, SG 4940 (SVG frame) then 4927 (official outline), SP 5543, SV 5891 | KNOWLEDGE | reg docstring "official length"; SG "FIA 4927"; no external citation |
| 15 | --road-width (constant along lap) | geometry | svg_to_outline:509 default; bats | default 13.0; BH 15.0, SG 12.0 (SVG) then 10.0 (official), SP 16.0, SV 15.0 | ASSUMED | SG 10 m is COMPUTED (_build_official_outline:3 "12 m gave worst corner 46 km/h, 10 m 18"); others have no source |
| 16 | --min-corner-radius | geometry | svg_to_outline:511 default 0; bats | BH 9.0, SP 9.0, SV 9.0, SG 10.0 | ASSUMED | docstring: "real circuits no R below ~6-8 m" (no cite) |
| 17 | HAIRPIN_NARROW_M / ratio | geometry | svg_to_outline:20-21 | 10.5 m / 13 -> 0.8077 x width, applied at the global abs(kappa) peak of EVERY track | ASSUMED | Canada-derived; always active, no flag to disable |
| 18 | HAIRPIN_HALF_RANGE_M | geometry | svg_to_outline:26 | 60 m | ASSUMED | none |
| 19 | N_OUTPUT_POINTS | geometry | svg_to_outline:27 | 2000 | ASSUMED | none |
| 20 | BEZIER_SAMPLES_PER_SEG | geometry | svg_to_outline:28 | 40 | ASSUMED | none |
| 21 | Centreline spline smoothing s | geometry | svg_to_outline:458 | 30.0 | ASSUMED | none |
| 22 | SF_LINE_KAPPA_THRESH (S/F proxy = midpoint of the longest straight) | geometry | svg_to_outline:29,362 | 0.001 1/m | ASSUMED | sim:506 docstring says the proxy is wrong (Canada) |
| 23 | SCALE_SANITY_MIN/MAX | geometry | svg_to_outline:30-31 | 0.5 / 50 m per SVG unit | ASSUMED | guard |
| 24 | SVG path picker = the densest d= path | geometry | svg_to_outline:391 | densest | COMPUTED | memory new-track-bringup-recipe (Catalunya clipPath bug) |
| 25 | Orientation forced CCW, then y-flip | geometry | svg_to_outline:192,463 | CCW | COMPUTED | signed area; convention needed by the normals |
| 26 | limit_min_radius iterations / Laplacian weights | geometry | svg_to_outline:275-305 | 600 iters; 0.25/0.5/0.25 | ASSUMED | none |
| 27 | Singapore mirror (x -> -x) | geometry | reg:138; cache/_singapore_prep.py | mirrored outline | KNOWLEDGE | Marina Bay runs anticlockwise; engine drives CW (reg comment, memory singapore-2026-ccw) |
| 28 | Singapore centreline = official map-matched path of the top-10 2025 Q laps | geometry | _build_official_outline:2 | path_samples.json | MEASURED | memory f1-position-feed-map-matched |
| 29 | Singapore centreline built at 12 m width, then re-edged at 10 m ("as built") | geometry | _build_official_outline:12-13 | 12 m -> 10 m | ASSUMED | inline comment only |
| 30 | Registry altitude_m | geometry | reg:44-146 | canada 13, catalunya 130, austria 680, silverstone 150, miami 2, china 4, spa 420, hungary 250, zandvoort 55, monza 162, bahrain 7, singapore 15 | ASSUMED | Zandvoort is MEASURED (OpenF1 z-channel); Monza and Bahrain are marked "placeholder"; the others have no source |
| 31 | rho_isa formula | geometry | reg:156-158 | 1.225*(1-2.25577e-5 h)^4.2561 | KNOWLEDGE | ISA troposphere model |
| 32 | Registry length_m | geometry | reg | e.g. bahrain 5412, singapore 4927, silverstone 5891 | KNOWLEDGE | "official length" (no citation) |
| 33 | Corridor inset per track | racing line | reg:135,151; SP:24; SV:28; autofit:56 | BH 1.2; SG 1.0; SP 0.5 (CLI); SV 0 (CLI); a registry track with no inset gets 0 via autofit | COMPUTED | BH: candidate sweep (0/2682 off, worst 0.29 m); SP: "inset 0 cut apex 0.67 m"; SG: "0 put line 0.55 m over edge"; SV 0 is ASSUMED ("run-off") |
| 34 | Zandvoort effective banking | geometry | reg:101-104 | T3 8.62 deg, T14 0.45 deg | COMPUTED | fitted by cache/_apply_banking.py --fit (not the surveyed ~19/18 deg) |
| 35 | KNOTS_V25 | targets | _transfer:34 | [80,140,200,260,320] km/h | ASSUMED | none |
| 36 | MIN_PAIR_RATE | targets | _transfer:35 | 0.8 | ASSUMED | none |
| 37 | MAJOR_PROM_KMH | targets | _transfer:36 | 15 km/h | ASSUMED | none |
| 38 | VTOP_PCTL | targets | _transfer:37, _predict:24, _autofit:36 | 99.5 (same in all 3) | ASSUMED | none |
| 39 | corner_minima prominence / min separation | targets | reg:181-182 | 8 km/h / 80 m | ASSUMED | none |
| 40 | pair_minima tol_frac | targets | reg:201 | 0.015 of lap | ASSUMED | none |
| 41 | align_pair grid n | targets | reg:236 | 2048 | ASSUMED | none |
| 42 | r(v25) shape = monotone non-increasing (PAVA) | targets | reg:262; _transfer:124 | constraint | ASSUMED | design spec doc (internal); no data test recorded here |
| 43 | Transfer anchor set (Q pairs only; FP1 = validation) | targets | reg kind26 | canada, catalunya, miami, china, spa, hungary, zandvoort | HUMAN | memory prefp1-transfer-calibration: "FP1 = verification only" |
| 44 | r_knots | targets | cache/transfer_2026.json | [0.96709, 0.94294, 0.9261, 0.9261, 0.9261] | COMPUTED | _transfer_2026.py on 7 Q pairs |
| 45 | lap_delta_pct mean / sd | targets | transfer_2026.json | +2.994 % / 1.290 | COMPUTED | same |
| 46 | vtop_delta_kmh mean / sd | targets | transfer_2026.json | +2.38 / 8.68 km/h (sd > 3x the mean) | COMPUTED | same |
| 47 | sd fallback when only 1 pair | targets | _transfer:148,153 | 0.5 % / 3.0 km/h | ASSUMED | none |
| 48 | CDA0_DEFAULT (autofit start) | targets | _predict:25 | 0.75 | ASSUMED | none; differs from the sim default 0.80 |
| 49 | CL0_DEFAULT (autofit start) | targets | _predict:26 | 4.6 | ASSUMED | none; differs from the sim default 4.20 |
| 50 | LAP_BAND_FLOOR_PCT | targets | _predict:27 | +0.8 % | ASSUMED | none |
| 51 | Lap band width | targets | _predict:90-91 | mean +/- 2 sd | ASSUMED | none |
| 52 | Ref-distance tolerance / 2024 fallback | targets | _predict:54-66 | abort >5 %, warn >2 %, fall back to the 2024 CSV | ASSUMED | none |
| 53 | Min corners in ref | targets | _predict:80 | 4 | ASSUMED | guard |
| 54 | predicted t25_s | targets | cache/predicted_*.json | BH 90.119, SG 89.241, SV 84.892 | COMPUTED | load_ref max(t)-min(t) of the 2025 CSV |
| 55 | predicted vtop_target_kmh | targets | predicted_*.json | BH 317.4, SG 318.4, SV 328.7 | COMPUTED | v25 p99.5 + transfer mean |
| 56 | predicted lap_band_s | targets | predicted_*.json | BH [90.84,95.14], SG [89.96,94.22], SV [85.57,89.79] | COMPUTED | #45, #50, #51 |
| 57 | predicted corners (s_frac, v26 target) | targets | predicted_*.json | BH 8, SG 12, SV 8 corners | COMPUTED | corner_minima x r(v25) |
| 58 | predicted rho | targets | predicted_*.json | BH 1.2242, SG 1.2232, SV 1.2075 | COMPUTED | rho_isa(altitude #30) |
| 59 | TOL_TOP | calibration | _autofit:37 | 2.0 km/h | ASSUMED | none |
| 60 | TOL_HS | calibration | _autofit:38 | 3.0 km/h | ASSUMED | none |
| 61 | LAP_RAIL_S (2026 lap > 2025 + rail) | calibration | _autofit:39; _gate:29 | 0.8 s (same in both) | ASSUMED | the principle is HUMAN/KNOWLEDGE (memory fp1-calibration-playbook "2026 is SLOWER"); the 0.8 s value has no source |
| 62 | CDA_LIM | calibration | _autofit:40 | (0.45, 1.30) | ASSUMED | none |
| 63 | CL_LIM | calibration | _autofit:41 | (3.00, 6.50) | ASSUMED | none |
| 64 | MATCH_TOL_FRAC (corner window) | calibration | _autofit:42 | 0.015 | ASSUMED | none |
| 65 | --max-iters | calibration | _autofit:122 | 4 (=> at most 5 sims) | ASSUMED | none |
| 66 | CL tier thresholds | calibration | _autofit:96-101 | v25 > 170, then >= 130, then all; >= 2 corners | ASSUMED | docstring rationale only |
| 67 | Trimmed median (drop worst if >= 3) | calibration | _autofit:112 | drop 1 | ASSUMED | comment: "backtest v1 lesson" |
| 68 | CDA step: cube-law Newton, then secant; clip +/-25 % | calibration | _autofit:180-187 | as stated | KNOWLEDGE | v_term ~ CdA^-1/3 (physics); the 25 % clip is ASSUMED |
| 69 | CL step: first bump 0.4, rail-violation cap -0.15, clip +/-0.8 | calibration | _autofit:192-201 | as stated | ASSUMED | none |
| 70 | Best-state score | calibration | _autofit:166 | rail first, then abs(f2) + 0.5 abs(f1) | ASSUMED | none |
| 71 | Autofit S/F anchor = csv25 (never the 2026 csv) | calibration | _autofit:54 | 2025 Q | HUMAN | pre-FP1 method (memory) |
| 72 | Fitted knobs, Bahrain | calibration | cache/autofit_bahrain.json | cda 0.7875, cl 3.6387, rho 1.2242, lap 92.197 | COMPUTED | the file now holds the v2b refit (v2 line); the v1 bat writes the same files (see conflicts) |
| 73 | Fitted knobs, Singapore | calibration | cache/autofit_singapore.json | cda 0.5581, cl 4.3233, rho 1.2232, lap 93.008 | COMPUTED | _autofit_rl_in_sg.py on the k3w line |
| 74 | Fitted knobs, Silverstone (registry autofit) | calibration | cache/autofit_silverstone.json | cda 0.7397, cl 4.70, converged=False; NOT used by the SV bat | COMPUTED | SV bat uses the sim defaults 0.80/4.20 instead |
| 75 | Sepang knobs (fleet median) | calibration | SP:24,27 | cda 0.6139, cl 4.97 | COMPUTED | memory noref-track-method (median of 7 autofit tracks; backtest sd 2.1 %) |
| 76 | Sepang rho | calibration | SP:24,27 | 1.2202 (ISA at ~40 m) | KNOWLEDGE | ISA; the ~40 m altitude has no source; Sepang is not in the registry |
| 77 | SG_MECH street-grip factor (scales mu*g only) | car model | SG:18 env -> _sg_grip.py:7 | 0.7230 (default 1.0) | MEASURED | street_grip.json k=0.72295, fitted on a 2025 car vs the RUS 2025 pole (_fit_street_grip.py) |
| 78 | SG_MU_SCALE (MU_LAT multiplier) | car model | env; _sim_singapore:35; _opt_line_2026_sg:24 | unset -> 1.0 | ASSUMED | applied by both modules if set |
| 79 | Singapore GAIN_CAP (replaces sim guard 32) | sim | _sim_singapore:13 | 36.3 = 23.9 x 1.52 | COMPUTED | real 2025 Q gain median x max shipped sim/real ratio |
| 80 | Singapore optimiser knobs (hard-coded copies) | racing line | SG:34,36,42 | r1 cda 0.618 / cl 6.327; r2 0.554 / 4.348; r3 0.559 / 4.363; rho 1.2232 | COMPUTED | carried from previous autofit rounds; r1 cl 6.327 is close to CL_LIM 6.5 |
| 81 | Singapore T8-T9 wide-entry constraint | racing line | SG:41-42 | seed_wide 2040 2140 0.8; --touch 2060,2120,1980 | HUMAN | bat comment "v4b (user)"; RUS 2025 onboard |
| 82 | Bahrain v2 optimiser knobs | racing line | what_could_have_been.bat | 0.8005/4.4693 -> 0.777/4.200 -> 0.787/3.400, rho 1.2242 | COMPUTED | carried from fits; the origin of 3.400 is unknown |
| 83 | N_CORRIDOR_POINTS | racing line | rv:52 | 800 | ASSUMED | "fast solve" |
| 84 | CORR_SMOOTH_S | racing line | rv:54 | 30.0 | ASSUMED | none |
| 85 | INSET_M (used when --inset is omitted) | racing line | rv:56 | 1.0 m | ASSUMED | Monaco tuning comment (1.3 too far, <1 hits the barrier) |
| 86 | VEH_WIDTH (IQP) | racing line | rv:64 | 2.0 m (sim refinement uses 1.9) | ASSUMED | none |
| 87 | KAPPA_BOUND | racing line | rv:63 | 0.4 1/m | ASSUMED | none |
| 88 | RACELINE_STEPSIZE | racing line | rv:65; sim:432 | 2.0 m | ASSUMED | none |
| 89 | IQP_ITERS / ALPHA_TOL | racing line | rv:66-67 | 30 / 0.10 m | ASSUMED | none |
| 90 | IQP_DAMP | racing line | rv:68 | 0.5 | ASSUMED | comment (undamped did not converge) |
| 91 | SAFETY_MARGIN (IQP) | racing line | rv:72 | 0.15 m | ASSUMED | none |
| 92 | IQP_OUTPUT_SMOOTH | racing line | rv:73 | 0.8 | ASSUMED | none |
| 93 | Corridor width floor / width gaussian | racing line | rv:520-523 | VEH_WIDTH/2 + 0.5; sigma 3 | ASSUMED | none |
| 94 | IQP final spline s | racing line | rv:~762 | max(1, 0.005*N) | ASSUMED | none |
| 95 | Corridor reversal (travel direction) | racing line | sim:334-335 | always reversed after CCW enforcement => every track is driven CW | KNOWLEDGE | verified only on Canada 2025 telemetry (sim:321-333); CCW circuits need a mirror (SG) |
| 96 | Tangent stencil +/-3 | racing line | sim:351; rv:510 | 3 stations | ASSUMED | none |
| 97 | J_MAX_LAT_JERK | racing line | sim:39 | 12.0 m/s^3 | ASSUMED | "addon defaults, validated 2026-05-10" (no data) |
| 98 | UNWIND_RATIO | racing line | sim:40 | 3.0 | ASSUMED | same |
| 99 | STRAIGHT_STIFF | racing line | sim:41 | 5.0 | ASSUMED | same |
| 100 | KAPPA_FLOOR | racing line | sim:42 | 0.005 1/m | ASSUMED | same |
| 101 | LAMBDA_SLACK | racing line | sim:43 | 1e3 | ASSUMED | same |
| 102 | SAFETY_MARGIN_REFINE | racing line | sim:44 | 0.30 m | ASSUMED | same |
| 103 | FB_TOL / warm max_outer | racing line | sim:45,125 | 1e-4 / 200 | ASSUMED | numerics |
| 104 | WARM_MASS_KG | racing line | sim:49 | 768 | KNOWLEDGE | "2026 mass (rough is fine)" |
| 105 | WARM_A_LAT_MAX | racing line | sim:50, overridden at sim:97-100 | 4.5 g -> 19.19^2 x (1/15) = 24.55 m/s^2 (2.50 g) | COMPUTED | from vehicle_calibration.json (Canada 2025 hairpin) |
| 106 | kappa_hairpin used in that override | racing line | sim:99 | 1/15 m ("Canada T10"), applied to all tracks | ASSUMED | comment only |
| 107 | WARM_A_ACC_MAX | racing line | sim:51 | 4.0 g | ASSUMED | none |
| 108 | WARM_A_BRK_MAX | racing line | sim:52, overridden at :92 | 5 g -> 4.827 g | COMPUTED | mu_long_obs (Canada 2025) |
| 109 | WARM_P_MAX_W | racing line | sim:53, overridden at :95 | 750 kW -> 1038.3 x 768 = 797 kW | COMPUTED | P_over_m_obs (Canada 2025) |
| 110 | WARM_CDA | racing line | sim:54 | 0.55 (NOT updated by --cda) | ASSUMED | none |
| 111 | WARM_V_CAP | racing line | sim:55 | 110 m/s | ASSUMED | none |
| 112 | WARM_RHO | racing line | sim:56; set from --rho at sim:1651 | 1.225 / per-track rho | KNOWLEDGE | ISA |
| 113 | w_veh (refinement) | racing line | sim:381 | 1.9 m | ASSUMED | none |
| 114 | v_floor (rate bound) | racing line | sim:387 | 5.0 m/s | ASSUMED | none |
| 115 | LINE_WOBBLE_SIG (env) | racing line | sim:451 | default 2.5 stations | ASSUMED | env override |
| 116 | LINE_WOBBLE_ADAPTIVE (env) | racing line | sim:452 | default 1 (on) | ASSUMED | rationale: backtest v1 hairpin R8->R23 |
| 117 | Adaptive de-wobble params | racing line | sim:461-474 | KAPPA_LO 1/250, KAPPA_HI 1/80, SIG_LIGHT 0.8, prefilter 3.0, kmag 2.0 | ASSUMED | none |
| 118 | S/F locate (kappa vs 1/v cross-correlation) | racing line | sim:503-561 | N_GRID 2048; needs >= 50 ref rows | COMPUTED | from --reference-csv |
| 119 | --reference-csv (S/F anchor) | racing line | sim:1679-1690 | DEFAULT = reference_2025_canada_q.csv; BH/SG via autofit = csv25; SP "NONE" (S/F stays at the longest-straight proxy); SV = 2026 FP1 csv | ASSUMED | silent default, see conflicts |
| 120 | --raceline-in (bypasses optimiser and S/F) | racing line | sim:1701 | SP T1 line; BH v2; SG k3w | HUMAN | memory feedback-line-apex-touch |
| 121 | Sepang T1 edit | racing line | SP:26; _sepang_t1_apex.py args | --half 60; window 560,640 (default); gap 1.0 m (default, not passed) | ASSUMED | the intent is HUMAN (apex touch); the bat comment says 1.2 m gap but the script runs 1.0 |
| 122 | Optimiser --margin (road eroded) | racing line | _opt_line_2017:80; BH-v2/SG bats | default 0.5; 0.3 in SG and in BH v2 stages 2+ | ASSUMED | none |
| 123 | Optimiser --every (knot spacing) | racing line | _opt_line_2017:81; _opt_line_2026 | 12 stations (~24 m) | ASSUMED | none |
| 124 | Optimiser --steps / --max-sweeps | racing line | _opt_line_2017:82-83; bats | default 2,1,0.5,0.25 / 30; bats use 1,0.5,0.25 | ASSUMED | none |
| 125 | Corridor probe range | racing line | _opt_line_2017:32 | +/-20 m, step 0.05 (caps corridor half-width at 20 m) | ASSUMED | none |
| 126 | Violation penalty | racing line | _opt_line_2017:72; _opt_line_2026 cost | 2.0 s/m | ASSUMED | none |
| 127 | --smooth-w | racing line | _opt_line_2017:87; bahrain/_opt_line_2026:50 | 0.0 (2017) vs 0.006 (2026 variants) | ASSUMED | none |
| 128 | --apex-w (apex-touch penalty) | racing line | bats | 1.5 (SG, BH final); 0.3 (BH opt3); default 0 | HUMAN | memory feedback-line-apex-touch; the magnitude is ASSUMED |
| 129 | --apex-tol / --apex-win | racing line | bahrain/_opt_line_2026:53 | 0.15 m / 20 stations | ASSUMED | none |
| 130 | _apex_gaps.corners rmax / sep / stencil | racing line | _apex_gaps:9 | 250 m / 120 m / 8 | ASSUMED | none |
| 131 | --touch-w | racing line | _opt_line_2026_sg | 1.5 | ASSUMED | none |
| 132 | Pattern-search accept rules | racing line | _opt_line_2017:117-130 | improvement > 1e-4 s; knots >= 3 apart | ASSUMED | none |
| 133 | --apex-knots zero_k (one corner set across rounds) | racing line | SG:30-42 | zeros | ASSUMED | bat comment |
| 134 | _opt_line_2017 default --base/--outline | racing line | _opt_line_2017:77-78 | Malaysian raceline/outline | ASSUMED | silent default (the SG bat calls setup() directly) |
| 135 | MASS_KG | car model | sim:735 | 768 kg | KNOWLEDGE | "FIA 2026 min" |
| 136 | G | car model | sim:736 | 9.81 | KNOWLEDGE | constant |
| 137 | RHO (default if --rho omitted) | car model | sim:737,1709 | 1.225; per-track via autofit; SV bat omits it -> 1.225 (reg ISA 1.2075) | KNOWLEDGE | ISA sea level; see conflicts |
| 138 | P_ICE_MAX_W | car model | sim:740 | 400 kW | KNOWLEDGE | spec doc section 3 (2026 regs) |
| 139 | P_MGU_DEPLOY_MAX_W | car model | sim:741 | 350 kW | KNOWLEDGE | 2026 regs |
| 140 | P_MGU_NORMAL_CAP_W | car model | sim:742 | 250 kW | KNOWLEDGE | comments disagree: "pre-Miami" (742) vs "post-Miami non-key-zone limit" (846) |
| 141 | P_MGU_REGEN_MAX_W | car model | sim:743 | 350 kW | KNOWLEDGE | regs |
| 142 | E_DEPLOY_BUDGET_J | car model | sim:744 | 9 MJ, defined but never used | KNOWLEDGE | dead constant |
| 143 | E_BATTERY_CAP_J | car model | sim:745 | 4 MJ | ASSUMED | "4 MJ usable store", no cite |
| 144 | CDA_STRAIGHT_M2 (default --cda) | car model | sim:759,1698 | 0.80; per-track BH 0.7875, SG 0.5581, SP 0.6139; SV uses the default 0.80 | COMPUTED | re-pinned to Silverstone 2026 FP1 top 317 (memory silverstone-2026-calibration); the stale comment says 0.76 |
| 145 | CDA_CORNER_M2 | car model | sim:774 | 1.79 (fixed; not scaled with --cda) | ASSUMED | comment says ~1.6x straight within 1.5-1.7x; 1.79/0.80 = 2.24x, and 3.2x at SG cda 0.558 |
| 146 | CL_STRAIGHT_M2 | car model | sim:775 | 1.40 | ASSUMED | no comment |
| 147 | CL_CORNER_M2 (default --cl) | car model | sim:789,1706 | 4.20; BH 3.6387, SG 4.3233, SP 4.97 | COMPUTED | re-pinned to Silverstone FP1 (memory) |
| 148 | MU_LONG | car model | sim:809 | 1.35 | ASSUMED | the comment argues for 1.60; no record for 1.35 |
| 149 | MU_DRIVE | car model | sim:818 | 1.00 | ASSUMED | rationale only |
| 150 | MU_LAT | car model | sim:827 | 1.95 (SG x SG_MECH on the mu*g term) | COMPUTED | Canada 2025 hairpin apex 19.19 m/s |
| 151 | A_ACC_LONG_MAX | car model | sim:836 | 1.65 g | COMPUTED | "matches real 2026 peak corner-exit gain ~55-58 km/h/s" |
| 152 | KAPPA_CORNER_THRESH (aero-mode switch and deploy-window reset) | car model | sim:839 | 0.005 1/m (R < 200 m) | ASSUMED | none |
| 153 | SOC_SUPERCLIP_THRESH | car model | sim:840 | 0.30, defined but never used | ASSUMED | dead constant |
| 154 | KEY_ACCEL_WINDOW_S | car model | sim:847 | 7.0 s | KNOWLEDGE | post-Miami regs definition (comment); the number itself is an estimate |
| 155 | SUPERCLIP_MAX_S | car model | sim:853 | 3.0 s | KNOWLEDGE | "FIA / motorsport.com, Apr 2026" |
| 156 | SUPERCLIP_SPEED_FRAC | car model | sim:74 | 0.96 | ASSUMED | the comment says 0.975 |
| 157 | P_SUPERCLIP_NET_W | car model | sim:79 | 335 kW | COMPUTED | tuned to China 2026 Q decline 5-7 km/h/s |
| 158 | SOC_INIT | car model | sim:856 | 1.0 | ASSUMED | none |
| 159 | Braking aero mode forced to CORNER | car model | sim:999 | CORNER | KNOWLEDGE | memory fp1-calibration-playbook (active-aero braking) |
| 160 | TRAIL_V_FULL_KMH | car model | sim:969 | 235 km/h | ASSUMED | rationale only |
| 161 | TRAIL_FRAC_MIN | car model | sim:970 | 0.40 | ASSUMED | rationale only |
| 162 | TRAIL_EXP | car model | sim:971 | 1.6 | ASSUMED | rationale only |
| 163 | V_DEPLOY_FULL/MID/ZERO_KMH (+100 kW at mid) | car model | sim:1192-1195 | 200 / 270 / 300 km/h; 0.286 frac | KNOWLEDGE | "hard regulatory power cap" (memory fp1-calibration-playbook) |
| 164 | Banking channel | car model | outline "banking_deg" -> sim:1758 | absent on BH/SG/SP/SV (flat) | COMPUTED | only Zandvoort is banked |
| 165 | BANK_DENOM_FLOOR | car model | sim:891 | 1e-3 | ASSUMED | numerics |
| 166 | vehicle_calibration.json mu_long_obs / P_over_m_obs / v_apex_hairpin_obs | car model | F1_Pipeline_Assets/calibration/vehicle_calibration.json | 4.827 g / 1038.3 W/kg / 19.19 m/s | MEASURED | from reference_2025_canada_q.csv + 2026 China; calibrate_from_telemetry() is not called by any script (static artifact) |
| 167 | Calibration extraction thresholds | car model | sim:583-678 | DECEL_WINDOW_S 0.40; brake > 50; throttle >= 99; flatline 0.3 m/s^2; >250 km/h; min zone 0.5 s | ASSUMED | only used to (re)build #166; not on the main path |
| 168 | V_FLOOR_MS / v_grip cap on straights | sim | sim:857,945 | 5.0 m/s / 300 m/s | ASSUMED | numerics |
| 169 | KGRIP_STENCIL (env) | sim | sim:1365 | 4 stations (~8 m) | ASSUMED | env override; also read by era2017/sim_2017_car.py:70 |
| 170 | Grip-kappa median filter size | sim | sim:1374 | 5 | ASSUMED | none |
| 171 | Backward brake pass iterations | sim | sim:982 | 3 | ASSUMED | none |
| 172 | BRAKE_DECEL_THRESH | sim | sim:1044 | 4.0 m/s^2 | ASSUMED | none |
| 173 | Braking-zone _clean_runs min_run | sim | sim:1089 | 6 stations | ASSUMED | none |
| 174 | Closure loop | sim | sim:1344,1379,1404 | max 8 iters; tol 1.0 m/s; v0 60 m/s; damping 0.5 | ASSUMED | numerics |
| 175 | smooth_longitudinal | sim | sim:1408,1792 | win 0.45 s; grid 120 Hz; brake_mask never passed (brake preservation never active) | ASSUMED | see conflicts |
| 176 | suppress_microhumps | sim | sim:1459 | max gap 1.6 s; prominence 22 km/h | ASSUMED | Red Bull Ring example only |
| 177 | CSV output | sim | sim:1487-1529 | 30 fps; throttle/brake 100/0 binary; gear and rpm 0 | ASSUMED | none |
| 178 | Sanity T_lap band | sim | sim:1551 | [60, 130] s | ASSUMED | "track-agnostic" |
| 179 | Sanity peak v band | sim | sim:1553 | [250, 360] km/h | ASSUMED | same |
| 180 | Sanity slowest-corner band | sim | sim:1558 | [40, 160] km/h | ASSUMED | same |
| 181 | Sanity superclip required / drop cap | sim | sim:1560,1580 | >= 1 zone; drop <= 60 km/h | ASSUMED | "real F1 caps near 50" (no cite) |
| 182 | Sanity GAIN median band | sim | sim:1615 | [12, 32] km/h/s (SG patched to <= 36.3) | ASSUMED | "real 2026 ~17-25" |
| 183 | Sanity DROP median band | sim | sim:1620 | [28, 60] km/h/s | ASSUMED | "real 2026 ~37-48" |
| 184 | Rate masks (sim and gate) | sim | sim:1605-1611; gate:77-80 | 0.5 s window; spd < 0.88 top; rate > 2 | ASSUMED | none |
| 185 | t_2025 passed to gate | gates | BH:28, SG:47, SP:30 | BH 89.841 (official pole PIA); SG 89.241 (CSV span; official pole 89.158); SP 90.076 (2017 pole) | KNOWLEDGE | per-bat comments; references are inconsistent (see conflicts) |
| 186 | TARGET_TOP_TOL_KMH | gates | gate:26 | 6.0 | ASSUMED | none |
| 187 | TARGET_CORNER_MED_TOL_KMH | gates | gate:27 | 6.0 | ASSUMED | none |
| 188 | TARGET_WINDOW_FRAC | gates | gate:28 | 0.015 | ASSUMED | none |
| 189 | WIN_S | gates | gate:31 | 0.5 s | ASSUMED | none |
| 190 | GAIN_MED_LO/HI | gates | gate:34 | 14 / 28 km/h/s | MEASURED | real medians 16.6/24.2 (spain/canada 2026 refs); the margins are ASSUMED |
| 191 | GAIN_PEAK_MAX | gates | gate:35 | 64 | MEASURED | real peaks 55/61 |
| 192 | DROP_MED_LO/HI | gates | gate:36 | 32 / 52 | MEASURED | real medians 36.5/44.2 |
| 193 | DROP_PEAK_MIN | gates | gate:37 | 85 | MEASURED | real peaks 104/154 |
| 194 | LAP_DELTA_LO/HI (no --targets mode) | gates | gate:39 | +1.0 .. +3.5 s | ASSUMED | "~+1.5-2.5 s"; applied to SP against a 2017 pole |
| 195 | SUPERCLIP_FRAC_MAX / PEAK_MIN | gates | gate:42-43 | 0.45 / 35 | ASSUMED | none |
| 196 | Gate throttle/brake masks | gates | gate:77-80 | th > 80, br < 5, br > 15, v > 0.85 top, th > 90 | ASSUMED | none |
| 197 | Gate/on-track checks are non-blocking | gates | BH:28-29, SG:47-48, SP:30-31 | no exit-on-error after these calls -> the bat renders even when they fail | ASSUMED | bat structure |
| 198 | _check_ontrack TOL | gates | _check_ontrack:23 | 0.30 m | ASSUMED | "resample/normal jitter" |
| 199 | On-track metric = unsigned distance to nearest centre station vs half of abs(outer-inner) | gates | _check_ontrack:14-22 | as stated | ASSUMED | none |
| 200 | --zoom | render | rv:78 default; bats | default 30; BH 18, SP 18, SV 23, SG 28 | HUMAN | memory feedback-video-zoom: 28; BH/SP/SV still use older values |
| 201 | --display-laptime | render | SV:32 | 86.833 (= 2025 pole + 1.94 s) while the sim lap is 1:27.97 | ASSUMED | bat comment; the origin of +1.94 is unknown |
| 202 | --elevation-json | render | BH:33 | BH only (of the 4) | HUMAN | memory madring (user wants 3D flyover) |
| 203 | --elev-scale | render | rv:1172 | 1.0 | ASSUMED | default |
| 204 | DEFAULT_FPS / DEFAULT_TRAIL | render | rv:77,79 | 30 / 180 frames | ASSUMED | none |
| 205 | Visual edges | render | rv:53,55 | N_VISUAL_POINTS 4000; VISUAL_SMOOTH_S 10 | ASSUMED | none |
| 206 | VISUAL_OUTSET_M | render | rv:62 | 0 (skipped when --raceline is given) | ASSUMED | Miami-only comment |
| 207 | Kerb geometry | render | rv:91-96 | kappa 0.005; depth 1.5 m; dilate 10; taper/block/gap 0.8 m | ASSUMED | none |
| 208 | Telemetry alignment skipped for synthetic CSV | render | rv:1236-1239 | skip if soc column present | COMPUTED | path choice |
| 209 | 3D elevation camera | render | rv:136-156 | EXAG 2.6, HALF_W 10, angle 15 deg, DIST 3400, FOCAL 1080 | ASSUMED | none |
| 210 | Title / tagline / flights | render | rv:103; BH-v2 bat | "THE OPTIMAL LAP"; tagline "The lap that never was"; b2/sr71 flights | HUMAN | memory feedback-video-overlays-titles, bahrain-2026-bringup |
| 211 | Singapore render track = official outline (unmirrored raceline) | render | SG:44-45,52 | singapore_grand_prix_outline.json | HUMAN | memory singapore-2026-ccw (v4 official geometry) |
| 212 | MODE_COLORS / text styling | render | rv:123 | white text except DEPLOY/BRAKING/SUPERCLIP/DRS | HUMAN | memory dual-video-style |

## Counts

Total variable rows: **212** (some rows group closely related constants).

By ORIGIN: ASSUMED 136, COMPUTED 31, KNOWLEDGE 26, HUMAN 12, MEASURED 7 (primary origin per row; mixed cases are explained in the evidence column).

By stage: racing line 56, car model 35, targets 24, geometry 21, calibration 18, sim 18, gates 15, render 13, fetch 12.

## Conflicts: one variable, different values in different places

1. **Corridor inset default**: sim `--inset` omitted means rv INSET_M = **1.0** (sim:1691, rv:56), but `_autofit_2026.py:56` passes `spec.get('inset', 0)` = **0** for every registry track without an inset (Hungary, Spa, Zandvoort, Silverstone, etc.).
2. **Vehicle width**: rv VEH_WIDTH **2.0** (IQP) vs sim w_veh **1.9** (refinement) vs "car half-width **0.95**" (_sepang_t1_apex, _opt_line_2017 docstring).
3. **Safety margin**: rv SAFETY_MARGIN **0.15** vs sim SAFETY_MARGIN_REFINE **0.30** vs optimiser --margin **0.5** default / **0.3** in the bats.
4. **GAIN median band**: sim sanity **[12,32]**, gate **[14,28]**, Singapore wrapper **<= 36.3**. **DROP median band**: sim **[28,60]** vs gate **[32,52]**.
5. **Start knobs**: _predict CDA0/CL0 **0.75/4.6** vs sim defaults CDA_STRAIGHT/CL_CORNER **0.80/4.20**.
6. **Silverstone knobs**: the shipped bat uses the sim defaults **0.80/4.20, rho 1.225**, while cache/autofit_silverstone.json holds **0.7397/4.70, rho 1.2075** and the registry altitude of 150 m implies rho **1.2075**.
7. **Silverstone country**: SV bat `--country "United Kingdom"` vs registry `country="Great Britain"`.
8. **Singapore length**: SVG stage `--track-length 4940` vs registry/official outline **4927**. **Width**: 12.0 (SVG stage, and the "as built" centreline) vs 10.0 (final edges).
9. **t_2025 reference used by the gate**: Bahrain uses the official pole **89.841**; Singapore uses the CSV time span **89.241** (official pole 89.158, per registry comment); `_predict` t25 for Bahrain is **90.119** (CSV span), so the Bahrain rail and band use different references. Sepang passes a **2017** pole (90.076) into bands built for a 2025 reference.
10. **Sepang T1 gap**: bat comment says a **1.2 m** centre gap; `_sepang_t1_apex.py` default `--gap 1.0` is used because the bat does not pass `--gap`.
11. **smooth_w default**: _opt_line_2017 **0.0** vs bahrain/_opt_line_2026 **0.006**.
12. **Stale comments vs values in sim**: MU_LONG comment justifies 1.60, value **1.35**; SUPERCLIP_SPEED_FRAC comment 0.975, value **0.96**; CDA_STRAIGHT comment re-derives 0.76 (Austria), value **0.80**; CDA_CORNER "~1.6x within 1.5-1.7x", actual ratio **2.24x** (3.2x at SG cda); P_MGU_NORMAL_CAP comments disagree (pre- vs post-Miami).
13. **Warm-profile drag**: WARM_CDA stays **0.55** while the per-track `--cda` changes CDA_STRAIGHT; only WARM_RHO follows the CLI.
14. **Shared Bahrain outputs**: the v1 bat and the v2 "what could have been" bat both write cache/autofit_bahrain{,_sim,_rl}.*. The file now holds the v2b refit (0.7875/3.6387). Re-running v1 overwrites it.
15. **Zoom**: memory says 28 (feedback-video-zoom), but BH and SP use **18** and SV uses **23**; the rv default is 30.

## Silent defaults

- `sim --reference-csv` defaults to **reference_2025_canada_q.csv** (sim:1679). Sepang passes "NONE", which does not exist, so the S/F stays at svg_to_outline's longest-straight proxy. Only a stderr note is printed.
- `svg_to_outline` `--track-length` 4361 and `--road-width` 13.0 are Canada defaults. Hairpin narrowing (10.5/13 ratio, ±60 m) is applied to **every** track at its global abs(kappa) peak, with no flag to turn it off.
- `sim --rho` defaults to 1.225 (SV bat omits it). `--cda`/`--cl` default to Silverstone-FP1-pinned values for any track that does not pass them.
- The vehicle_calibration.json override is applied silently on import. It changes the WARM_* line-shaping params for every track using **Canada** numbers, including kappa_hairpin = 1/15 m ("Canada T10"). If the file is missing, it falls back silently. Its generator calibrate_from_telemetry() is not called anywhere.
- Corridor reversal at sim:334 is unconditional and was verified only on Canada.
- `_opt_line_2017` `--base`/`--outline` default to the Malaysian files. `fetch` `--session` defaults to Qualifying, and `--driver` defaults to the session's fastest.
- smooth_longitudinal's `brake_mask` is never passed (sim:1792), so the documented "preserve solved braking profile" branch never runs.
- Gate and on-track checks in the bats are not fatal: the video renders even when a gate fails.
- Bahrain and Monza altitudes are registry **placeholders** (7 m, 162 m) and feed rho.
- Sepang bat line 23 contains a literal TAB: `cache\sepang<TAB>1_h60.json`. The T1 line is written to a stray file in cache\ rather than cache\sepang\t1_h60.json.

## Env-var and monkey-patch overrides

- Env: `LINE_WOBBLE_SIG` (2.5), `LINE_WOBBLE_ADAPTIVE` (1), `KGRIP_STENCIL` (4; also sim_2017_car), `SG_MECH` (bat sets 0.7230), `SG_MU_SCALE` (1.0; applied in both _sim_singapore and _opt_line_2026_sg).
- Monkey patches: `_sg_grip.apply` replaces sim.a_lat_max_banked / v_grip_static. `_sim_singapore` replaces sim.assert_sanity (GAIN cap 36.3) and scales MU_LAT. `_opt_line_2026` / `_opt_line_2026_sg` init() reassign S.CDA_STRAIGHT_M2 / CL_CORNER_M2 / RHO / WARM_RHO / BANKING_RAD=None. `_autofit_singapore` / `_autofit_rl_in_sg` set A.SIM to the Singapore wrapper. `_autofit_rl_in*` wrap subprocess.run to append `--raceline-in`. sim `_apply_car_overrides` rewrites globals from the CLI.
