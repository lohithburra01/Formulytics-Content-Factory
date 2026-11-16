

## Backtest v1 — leave-one-out, 4 tracks

| track | ref | cda | cl | rho | lap sim | real | corr | top err | corner med | worst | fails |
|---|---|---|---|---|---|---|---|---|---|---|---|
| canada | Q | 0.619 | 5.20 | 1.224 | 71.54 | 72.58 | 0.968 | +2.2 | +13.2 | +24.4 | **2** |
| catalunya | Q | 0.731 | 6.50 | 1.210 | 68.48 | 75.04 | 0.979 | -10.0 | +10.6 | +35.0 | **4** |
| austria | FP1 | 0.572 | 4.05 | 1.147 | 66.07 | 67.84 | 0.971 | +1.9 | +10.4 | -20.8 | **0** |
| silverstone | FP1 | 0.747 | 5.18 | 1.208 | 83.68 | 89.64 | 0.931 | +13.6 | +8.6 | +42.4 | **3** |

### canada (v1)
- PASS `corr`: 0.968 (>= 0.94)
- FAIL `lap_rail`: 71.54s > 71.70s
- PASS `lap_band`: 71.54s in [71.08,72.58] (Q ref)
- PASS `top`: +2.2 km/h (band +-11.8)
- FAIL `corners`: median +13.2, worst +24.4
- corners (sim vs real 2026): 0.073:+17, 0.165:-11, 0.285:+24, 0.460:-19, 0.614:+17, 0.900:+10

### catalunya (v1)
- PASS `corr`: 0.979 (>= 0.94)
- FAIL `lap_rail`: 68.48s > 72.35s
- FAIL `lap_band`: 68.48s in [73.54,75.04] (Q ref)
- FAIL `top`: -10.0 km/h (band +-5.0)
- FAIL `corners`: median +10.6, worst +35.0
- corners (sim vs real 2026): 0.186:+2, 0.376:+17, 0.461:+4, 0.551:+1, 0.626:+35, 0.756:-1, 0.816:+32, 0.934:+30

### austria (v1)
- PASS `corr`: 0.971 (>= 0.94)
- PASS `lap_rail`: 66.07s > 64.77s
- PASS `lap_band`: 66.07s in [64.34,66.84] (FP1 ref)
- INFO `top`: +1.9 km/h (band +-11.8, informational: FP1 ref)
- PASS `corners`: median +10.4, worst -20.8 (FP1 rule [-5,+15] on median)
- corners (sim vs real 2026): 0.106:-21, 0.323:+18, 0.511:+10, 0.633:+10, 0.705:-19, 0.880:+12, 0.927:+11

### silverstone (v1)
- FAIL `corr`: 0.931 (>= 0.94)
- FAIL `lap_rail`: 83.68s > 85.69s
- FAIL `lap_band`: 83.68s in [86.14,88.64] (FP1 ref)
- INFO `top`: +13.6 km/h (band +-11.8, informational: FP1 ref)
- PASS `corners`: median +8.6, worst +42.4 (FP1 rule [-5,+15] on median)
- corners (sim vs real 2026): 0.156:+4, 0.179:-6, 0.342:-24, 0.371:+22, 0.538:+42, 0.683:-14, 0.860:+18, 0.938:+13


## Backtest v2 — leave-one-out, 4 tracks

| track | ref | cda | cl | rho | lap sim | real | corr | top err | corner med | worst | fails |
|---|---|---|---|---|---|---|---|---|---|---|---|
| canada | Q | 0.560 | 5.09 | 1.224 | 73.51 | 72.58 | 0.968 | +8.5 | +7.0 | -32.0 | **2** |
| catalunya | Q | 0.713 | 5.00 | 1.210 | 73.66 | 75.04 | 0.985 | -12.0 | -10.6 | +17.3 | **2** |
| austria | FP1 | 0.750 | 4.60 | 1.147 | 66.35 | 67.84 | 0.963 | -10.6 | +8.2 | -25.0 | **0** |
| silverstone | FP1 | 0.750 | 4.60 | 1.208 | 86.32 | 89.64 | 0.940 | +10.4 | -3.9 | -41.9 | **0** |

### canada (v2)
- PASS `corr`: 0.968 (>= 0.94)
- PASS `lap_rail`: 73.51s > 71.70s
- FAIL `lap_band`: 73.51s in [71.08,72.58] (Q ref)
- PASS `top`: +8.5 km/h (band +-11.8)
- FAIL `corners`: median +7.0, worst -32.0
- corners (sim vs real 2026): 0.073:+16, 0.165:-19, 0.285:+15, 0.460:-32, 0.614:+15, 0.900:-1

### catalunya (v2)
- PASS `corr`: 0.985 (>= 0.94)
- PASS `lap_rail`: 73.66s > 72.35s
- PASS `lap_band`: 73.66s in [73.54,75.04] (Q ref)
- FAIL `top`: -12.0 km/h (band +-5.0)
- FAIL `corners`: median -10.6, worst +17.3
- corners (sim vs real 2026): 0.185:-16, 0.374:-8, 0.460:-6, 0.550:-15, 0.625:-4, 0.755:-14, 0.815:+17, 0.932:-14

### austria (v2)
- PASS `corr`: 0.963 (>= 0.94)
- PASS `lap_rail`: 66.35s > 64.77s
- PASS `lap_band`: 66.35s in [64.34,66.84] (FP1 ref)
- INFO `top`: -10.6 km/h (band +-11.8, informational: FP1 ref)
- PASS `corners`: median +8.2, worst -25.0 (FP1 rule [-5,+15] on median)
- corners (sim vs real 2026): 0.106:-25, 0.323:+16, 0.511:+8, 0.633:+17, 0.705:-12, 0.880:+16, 0.927:+3

### silverstone (v2)
- PASS `corr`: 0.940 (>= 0.94)
- PASS `lap_rail`: 86.32s > 85.69s
- PASS `lap_band`: 86.32s in [86.14,88.64] (FP1 ref)
- INFO `top`: +10.4 km/h (band +-11.8, informational: FP1 ref)
- PASS `corners`: median -3.9, worst -41.9 (FP1 rule [-5,+15] on median)
- corners (sim vs real 2026): 0.156:+0, 0.178:-8, 0.342:-30, 0.370:+9, 0.538:+37, 0.683:-42, 0.860:-23, 0.938:+4

## Spa pre-FP1 ship checks (2026-07-16)

- autofit converged it3: cda 0.737, cl 5.355, rho 1.1764 -> lap 101.91s
  (2025 pole 100.562 +1.35s), top 343. Gate 9/9 (predicted bands + rails).
- SHAPE overlay vs 2025 NOR real lap: corr 0.978, shift 0. La Source 77=77,
  mean 269=269; sim slower mid-corner at Les Combes/Pouhon (-15..-20, the
  -30% DF), higher on Blanchimont run (+20, X-mode) - both correct-direction
  2026 signatures, mirroring the real catalunya 2025->2026 pair.
- a(v) rate-vs-speed vs real 2026 Q laps: gain peaks ~39 @140-180 collapsing
  to 4.3 @300+ (deploy cliff) - in family (real 43-45 peak, 8-9 @300+);
  drop grows to ~105 @260-300 vs real 107/140.
- FP1 WATCH ITEMS (verify Fri, do NOT recalibrate): (1) Eau Rouge held flat
  (2025 had a breath of lift; no 2025 corner-minimum -> transfer silent);
  (2) sim gain 220-260 = 25.6 vs catalunya 15.6 / canada 21.6;
  (3) sim drop 140-180 = 48 vs 27/34 (real bins n<40, single-lap noise).

## Zandvoort (Dutch GP) pre-FP1 ship checks (2026-08-20)

Shipped BEFORE FP1 (Fri 2026-08-21), zero 2026-session data for this track.

- 2025 ref: OpenF1 Q, PIA 1:08.662 (the actual 2025 pole), 4243 m integrated
  vs 4259 official (-0.4%). Provenance clean (fetched 2026-08-20, long after
  the 2025-08-30 session).
- Outline: Zandvoort.svg (1 closed path, 62 cubic segments / 374 coords —
  denser than Hungaroring's 314, below Spa's 638) -> 2000 stations, perimeter
  4258.6 m, no pinch, min-radius limiter did not clamp (|k|max 0.099 unchanged).
- Transfer REFIT this session: Spa + Hungary 2026 Q added as pairs (6 Q pairs,
  was 4). lap_delta mean +2.55% sd 1.61 -> +2.83% sd 1.33 (slower AND tighter);
  r(v25) at 200+ 0.904 -> 0.933. Pairing rates 0.86-0.90, all above the 0.8 guard.
- Autofit converged it2: cda 0.563, cl 4.968, rho 1.2185 -> lap 71.31s
  (2025 pole 68.662 +2.64s = +3.95%), top 331 (target 330.5, err -0.0).
  cda 0.563 is the LOWEST of any track fitted — dense low-altitude air means
  less CdA for the same vtop. Physically consistent.
- GATE 9/9 against predicted bands.
- SHAPE overlay vs 2025 PIA real lap: corr 0.967 (>= 0.95), shift 0.1%.
- a(v) vs real 2026 Q (Spa/Hungary/Canada): GAIN peaks 41.8 @140-180 (real
  26.6/43.3/43.1), collapses to 8.6 @300+ (real 6.7/8.3/8.8) — deploy cliff
  reproduces. GAIN @220-260 21.5 vs real 21.1/21.7/21.6 (near-exact).
  DROP grows 6.8 -> 83.6 through 260-300.

### BANKING — new capability this session (see also tests/test_banking.py)

Zandvoort is the only meaningfully banked track on the calendar (2021 rebuild:
Hugenholtz T3 ~19 deg, Arie Luyendyk T14 ~18 deg). The flat sim was -50.0 km/h
at Hugenholtz, which alone failed the gate (all-8 corner median -6.5 vs +-6.0).

Diagnosis that mattered: the error was NOT uniform. 5 of 8 corners were within
+-7.4; three ADJACENT early corners carried it (Tarzan -20.6, Gerlach -29.2,
Hugenholtz -50.0). Raising CL would have inflated the 5 healthy corners to shove
the median past threshold while leaving the broken section broken — the
"CL cannot fix geometry" invariant. Confirmed single-defect: banking Hugenholtz
alone moved Gerlach -29.2 -> -13.3 with no banking of its own (the backward
brake pass had been starting from a wrongly-slow apex and propagating upstream).

Implementation: banking is TRACK geometry, so it rides on the outline as an
optional per-station `banking_deg` channel; the frozen 2026 CAR constants are
untouched. Lateral limit becomes
    v^2 = g(mu cos0 + sin0) / [ |k|(cos0 - mu sin0) - mu rho Cl / 2m ]
which at 0 deg reduces EXACTLY to the flat form — so a track with no channel is
bit-identical and the LOO backtest is unchanged by construction (27 unit tests,
incl. exact-equality checks at zero banking).

EFFECTIVE, NOT SURVEYED ANGLES. MU_LAT 1.95 is an aero-inclusive coefficient
fitted on flat tracks; its friction angle arctan(1/mu) is only ~27 deg, so the
surveyed ~19 deg SATURATES the closed form (denominator flips sign; the corner
stops binding — a 6.85x gain). Angles are therefore FITTED to the corner's
predicted apex target by cache/_apply_banking.py --fit:
    Hugenholtz  8.62 deg effective (surveyed ~19)
    Luyendyk    0.45 deg effective (surveyed ~18)
Luyendyk needing ~nothing is a good independent sanity check — the fit did not
invent banking where the sim was already right (-5.6 km/h flat).

*** CAVEAT: the two banked corners are now FITTED, not predicted. They are no
longer independent validation stations. The honest number is the unbanked-6
median, -5.1 km/h (vs all-8 -5.5) — the gate is NOT being carried by the
fitted corners. ***

### Residual known limitations (measured — do not re-litigate silently)

- Hugenholtz still -24.2 km/h after banking. The --fit inversion is OPEN LOOP
  (solves v_grip = target), but the achieved apex is also brake/jerk-smoothing
  limited, so the fitted angle undershoots in practice. A closed-loop fit
  (iterate sims until the ACHIEVED apex matches) would close it; not done —
  higher overfit risk and FP1 was next day.
- T1 Tarzan -20.7, UNEXPLAINED. Not one of the banked corners and not fixed by
  banking Hugenholtz, so it is not brake-pass propagation either. Suspect SVG
  fidelity through the Tarzan-Gerlach sequence. First thing to check against FP1.
- Gerlach -13.3 (was -29.2).
- DROP median falls to 33.2 in the 300-340 bin instead of continuing to climb.
  Real 2026 Q data there is n=0/1/2 — nothing solid to compare against. Peak
  bite check passes (136.4 >= 85). Watch item only.
- altitude: registry initially had 5 m (assumed sea level); the measured
  OpenF1 z-channel puts the track at 51-59 m ASL (dunes). Corrected to 55 m,
  rho 1.2244 -> 1.2185, and the fit was re-run on the corrected value.

### FP1 WATCH ITEMS (Fri 2026-08-21 — VERIFY ONLY, do not recalibrate)

  python fetch_openf1_lap.py --year 2026 --country Netherlands --session "Practice 1" --out F1_Pipeline_Assets/exports/reference_2026_zandvoort_fp1.csv

Expect FP1 ~ sim +2..3.5s (FP1 runs ~+3.2% over its own Q), corr >= 0.95.
  1. Tarzan (frac 0.077): is the real 2026 apex ~119, or is the sim's 98.7
     right and the 2025-derived target wrong? This decides SVG-vs-target.
  2. Hugenholtz (frac 0.185): how much of the remaining -24.2 is real?
  3. Whether 8.62 deg effective is too small once a closed-loop fit is possible.

### Bug fixed this session (would have silently poisoned any new track)

cache/_fetch_elevation.py hardcoded `--country` default "Belgium" (Spa-first
version). `--track zandvoort` therefore fetched SPA's elevation (session 9935,
365-467 m ASL, span 102 m, 6974 m lap) and wrote it to
dutch_grand_prix_elevation.json. It passed every existing validation gate
because Spa's data is internally consistent. Fixed: country now comes from the
registry (new `country` field on every track), plus a cross-track guard that
rejects a lap whose integrated distance is not within +-5% of the registry
length. Correct Zandvoort elevation: 51.0-59.2 m ASL, span 8.3 m, closure +0.0.

### Alignment bug fixed this session (banking looked applied but wasn't)

First banked run moved the lap only 0.13s and left Hugenholtz at exactly -50.0.
The channel was being built PRE-S/F-roll from raw station-index fractions, but
the corner positions authoring it (registry s_frac, predicted_*.json) are
S/F-referenced ARC fractions. The bump landed at frac 0.166 instead of 0.185 —
~96 m upstream, sitting on the near-straight approach (kappa 0.003-0.0098) where
nothing was ever grip-limited. Nothing failed loudly. Fixed by building the
channel AFTER the roll, indexed by arc fraction (banking_channel_for_arc);
guarded by 8 alignment regression tests.


## Backtest v1 — leave-one-out, 4 tracks

| track | ref | cda | cl | rho | lap sim | real | corr | top err | corner med | worst | fails |
|---|---|---|---|---|---|---|---|---|---|---|---|
| canada | Q | 0.569 | 5.18 | 1.224 | 73.35 | 72.58 | 0.968 | +7.6 | +7.5 | -31.7 | **2** |
| catalunya | Q | 0.707 | 5.00 | 1.210 | 73.64 | 75.04 | 0.985 | -11.4 | -10.6 | +17.3 | **1** |
| austria | FP1 | 0.596 | 4.85 | 1.147 | 65.12 | 67.84 | 0.960 | +0.9 | +9.2 | +27.2 | **0** |
| silverstone | FP1 | 0.740 | 4.70 | 1.208 | 85.90 | 89.64 | 0.938 | +12.8 | -3.5 | -40.5 | **2** |

### canada (v1)
- PASS `corr`: 0.968 (>= 0.94)
- PASS `lap_rail`: 73.35s > 71.70s
- FAIL `lap_band`: 73.35s in [71.08,72.58] (Q ref)
- PASS `top`: +7.6 km/h (band +-15.1)
- FAIL `corners`: median +7.5, worst -31.7
- corners (sim vs real 2026): 0.073:+16, 0.165:-19, 0.285:+15, 0.460:-32, 0.614:+15, 0.900:+0

### catalunya (v1)
- PASS `corr`: 0.985 (>= 0.94)
- PASS `lap_rail`: 73.64s > 72.35s
- PASS `lap_band`: 73.64s in [73.54,75.04] (Q ref)
- PASS `top`: -11.4 km/h (band +-13.0)
- FAIL `corners`: median -10.6, worst +17.3
- corners (sim vs real 2026): 0.185:-16, 0.374:-8, 0.460:-6, 0.550:-15, 0.625:-4, 0.755:-14, 0.815:+17, 0.932:-14

### austria (v1)
- PASS `corr`: 0.960 (>= 0.94)
- PASS `lap_rail`: 65.12s > 64.77s
- PASS `lap_band`: 65.12s in [64.34,66.84] (FP1 ref)
- INFO `top`: +0.9 km/h (band +-14.4, informational: FP1 ref)
- PASS `corners`: median +9.2, worst +27.2 (FP1 rule [-5,+15] on median)
- corners (sim vs real 2026): 0.106:-24, 0.323:+17, 0.512:+9, 0.633:+24, 0.706:-7, 0.880:+27, 0.927:+7

### silverstone (v1)
- FAIL `corr`: 0.938 (>= 0.94)
- PASS `lap_rail`: 85.90s > 85.69s
- FAIL `lap_band`: 85.90s in [86.14,88.64] (FP1 ref)
- INFO `top`: +12.8 km/h (band +-14.4, informational: FP1 ref)
- PASS `corners`: median -3.5, worst -40.5 (FP1 rule [-5,+15] on median)
- corners (sim vs real 2026): 0.156:+0, 0.178:-8, 0.342:-29, 0.370:+10, 0.538:+40, 0.683:-40, 0.860:-21, 0.938:+5

### baku (2026-09-24, practice-checked video)
- User SVG is a dense filled ribbon; the traced 6,003 m anti-clockwise outline uses its medial axis guided by the official 2025 Q position path. Direct SVG parsing would double the route.
- 2025 Q VER 101.117 s; 2026 FP1 RUS 105.387 s; FP2 RUS 103.347 s. Final synthetic 102.884 s, 340 km/h, CdA 0.717 / ClA 4.45 / rho 1.2274. FP2 speed correlation 0.978 with forward direction and zero shift.
- Realism gate **8/9**: gain median 30.5 km/h/s exceeds the 28 ceiling (FP1 25.5, FP2 26.6). Other checks pass. The automatic transfer fit was discarded because its 105.889 s lap was slower than both practices. This remains a provisional synthetic lap, not fully gate-passing.
- 15/2,974 raw racing-line points exceed the SVG edge by >0.3 m (max 1.45 m) at three corners. The video uses the display-only `--road-stroke` option to avoid overlapping filled-road/kerb artifacts at close streets. Full evidence and reproduce commands: `cache/baku_optimal_lap_2026-09-24.md`.
