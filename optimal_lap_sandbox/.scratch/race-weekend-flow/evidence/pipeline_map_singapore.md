# Singapore 2026 pipeline map: `make_singapore_2026_lap.bat`, end to end (2026-10-20)

This was a read-only study. Nothing in the repo was run that writes into it.
Line refs use the form `file:line`, and `bat:N` means `make_singapore_2026_lap.bat` line N.
Repo root is `D:\f1_hot_lap\OPTIMAL LAP SCRIPTS_sandbox`, called ROOT below. Other names used below: `SG` = `cache\singapore`, `T` = `F1_Pipeline_Assets\tracks`, `M` = `T\singapore_grand_prix_mirror_outline.json`.

## 0. Headline facts (checked in memory, nothing written)

| Check | Result |
|---|---|
| `svg_to_outline.build_outline_from_svg(SVG, 4940, 12, 10)` == `cache/singapore_outline_autoSF.json` | byte-identical |
| `prep()` roll of autoSF (k=346) == `T/singapore_grand_prix_outline_svgraw.json` | byte-identical |
| `_official_path.py` maths on `path_samples.json` + svgraw == `SG/official_path.json` | byte-identical (S/F shift -14.6 m, scale 1.0065, rms 6.2 m) |
| `_build_official_outline.py` maths == shipped `singapore_grand_prix_outline.json` and `..._mirror_outline.json` | byte-identical (also == `SG/outline_v4_installed.json`, `outline_official_w10[_mir].json`) |
| `sim.build_raceline(mirror outline, inset 1.0)` + `locate_start_finish` (sf=2) == `SG/base_k_rl.json` raceline | exact (`tolist()` equal), 58 s, does NOT depend on cda/cl |
| `zero_k.npy` == zeros(205) | yes (also == `zero_knots.npy`) |
| `line_of(kX_knots.npy)` == `kX_rl.json` for k1, k2, k3w | exact |
| `_seed_wide` maths on `k2_knots.npy` == `seed26_wide.npy` | exact (4 knots moved) |
| `mirror_raceline.json` coords == `k3w_rl.json` coords; un-mirror == `singapore_grand_prix_raceline.json` | exact |
| `autofit_singapore_sim_best.csv` == `autofit_singapore_sim.csv` == `exports/singapore_2026_synthetic.csv` | same md5 |
| `_gate_2026.py` on the shipped CSV (read-only run) | 9/9 PASS. GAIN median **27.9 vs the 28.0 limit**, only 0.1 of margin |
| `_corner_compare.py` (read-only run) | corr 0.969, pairing 92 %, median resid +3.4, max 25, 5/11 corners off by more than 10 km/h |

**Not checked** (each needs a multi-minute ProcessPool optimiser run, or a run that writes): whether the optimiser rounds k1, k2 and k3w reproduce their knots byte-for-byte, and whether the 3 autofit rounds reproduce. The code for those has no randomness (see section G).

The shipped outputs were **not** made by one run of this bat. The logs carry the path `D:\f1_hot_lap\OPTIMAL LAP SCRIPTS\...` (the original folder, not the sandbox). File mtimes are out of bat order: the outlines are dated 18:59, *after* `base_k_rl` (18:34), k1 (18:43) and k2 (18:47). The svgraw is dated 12:05 and autoSF 11:43. Steps were run one at a time, and the bat was assembled afterwards (the v4b comments). Because the geometry rebuilds byte-identically, the late outline rewrite did no harm.

---

## 1. Steps in order (27 commands: 23 Python runs + 4 `copy`)

The environment for every step comes from `bat:11-18`: `ROOT`, `PYTHON` (Python310, absolute user path), `T`, `SG`, `M`, `REF25`, `CSV`, and **`SG_MECH=0.7230`**. `SG_MECH` is inherited by every child process, including the sims that autofit launches with `subprocess`. Any `SG_MU_SCALE`, `KGRIP_STENCIL`, `LINE_WOBBLE_SIG` or `LINE_WOBBLE_ADAPTIVE` already set in the user's shell would also leak in, because the bat does not clear them.

### S0 (bat:19): fetch the 2025 Q reference (conditional)
1. `fetch_openf1_lap.py --year 2025 --country Singapore --session Qualifying --out REF25` downloads the fastest valid 2025 Singapore Q lap's car telemetry from OpenF1 and writes it as a speed/distance CSV.
2. Inputs: network only (`https://api.openf1.org/v1`, `fetch_openf1_lap.py:22`). `--circuit` and `--driver` are not passed, so the script takes the fastest valid lap of the session (`:92-94`). That lap is RUS 1:29.158 per the registry comment `_track_registry.py:141`. Distance is the trapezoid integral of speed (`:128`), which gives 4888 m against 4940 m. The time window is `lap_duration + 0.5 s` (`:102`). It retries 6 times with exponential backoff (`:27-48`).
3. Output: `F1_Pipeline_Assets/exports/reference_2025_singapore_q.csv`, with columns frame, time_s, distance, speed, throttle, brake, gear, rpm, ers_deploy (ers=0). Read by S8 predict (via the registry `csv25`), S9/S13/S15/S19 autofit sims (`--reference-csv`, S/F anchor), S25 corner compare, and `_fit_street_grip.py`.
4. Network: yes, skipped by `if not exist`. There is no `|| exit`: if the fetch fails, S8 aborts later with "no 2025 ref".
5. Risks: what comes back depends on the date of the fetch (it was fetched 2026-10-08, long after the session; OpenF1 can revise data). The time span of the CSV is 89.241 s, not the official 89.158.
6. Hard-coded copies: none.

### S1 (bat:21): SVG to outline (frame only)
1. `svg_to_outline.py --svg Marina_Bay_circuit_2023.svg --out cache/singapore_outline_autoSF.json --track-length 4940 --road-width 12.0 --min-corner-radius 10.0` builds an outer/inner outline from the hand-drawn SVG. In v4 it is used only to fix the coordinate frame.
2. Inputs: `ROOT/Marina_Bay_circuit_2023.svg`. Constants: `N_OUTPUT_POINTS=2000` (`:27`), `BEZIER_SAMPLES_PER_SEG=40` (`:28`), `SF_LINE_KAPPA_THRESH=0.001` (`:29`), scale sanity 0.5-50 (`:30-31`), spline smoothing `s=30.0` (`:461`), `limit_min_radius(max_iters=600)` (`:275`), and hairpin narrowing to `width*10.5/13` over ±60 m at the highest-|κ| peak (`:20-26`, `:484-486`). It forces CCW (`:466`).
3. Output: `cache/singapore_outline_autoSF.json`, read by S2.
4. Local; no network.
5. Deterministic: rebuilt byte-identically in memory.
6. 4940 is the SVG frame length. The final track length is 4927 (S7). 12 m width and R10 match S7's "as built" 12 m.

### S2 (bat:22): `cache/_singapore_prep.py prep`
1. Rolls the autoSF outline so index 0 sits at arc 855 m (`SF_ARC_M=855.0`, `:17`), then writes the real-frame outline and its x-mirror.
2. Inputs: `cache/singapore_outline_autoSF.json` (S1).
3. Outputs: `T/singapore_grand_prix_outline.json` and `T/singapore_grand_prix_mirror_outline.json`. **S7 overwrites both.** Only the S3 copy of the real outline is ever used.
4. Local.
5. The 855 m roll only affects the svgraw frame, and through it the Procrustes fit in S6. The final S/F comes from RUS's lap start (S6).
6. 855 m is hard-coded, from a docstring finding (`:2-4`, corr 0.942).

### S3 (bat:23): `copy outline.json -> outline_svgraw.json`
Snapshots the rolled SVG outline. S6 reads it. The copy has no error check. If S7 from a previous run had already overwritten `outline.json`, the copy would capture the S7 version, but S2 always runs first, so this is safe in order.

### S4 (bat:24): `SG/_fetch_path_multi.py` (conditional)
1. Downloads OpenF1 map-matched `location` samples for the fastest valid Q lap of each of the top-10 drivers.
2. Inputs: network. **Hard-coded `session_key=9892`** (`:6`, `:13`). Top 10 by lap_duration (`:10`).
3. Output: `SG/path_samples.json` (`[{drv,t,x,y,z}]`, decimetres), read by S6.
4. Network: yes, skipped `if not exist`. `|| exit` is present.
5. Risk: the result depends on the date of the fetch. Cached since 2026-10-08 17:27.

### S5 (bat:25): `SG/_rus2025_car.py` (conditional): DEAD IN THIS BAT, and breaks a clean run
1. Fetches RUS 2025 lap-17 car_data (session 9892, driver 63) to `SG/rus2025_car_data.json` if it is missing. It then always warps that data onto a sim CSV and writes `SG/rus2025_on_2026_line.csv`.
2. Inputs: network (the first time), and **`exports/singapore_2026_synthetic.csv`** (the default SIM, `:16`). That CSV is this bat's own *final* output (S20). `OFFICIAL=89.158` (`:18`). find_peaks prominence 12 and pairing tolerance 0.02 (`:34-38`).
3. Outputs: `rus2025_car_data.json` and `rus2025_on_2026_line.csv`. **Nothing later in this bat reads either.** They are used by the dual-video bat and by `_car2025.drs_zones`.
4. Network on the first run, skipped `if not exist rus2025_car_data.json`.
5. **On a fresh checkout, the synthetic CSV does not exist yet, so `genfromtxt` raises and `|| exit /b 1` stops the bat.**

### S6 (bat:26): `SG/_official_path.py`
1. Orders all map-matched samples by their projection onto RUS's (drv 63) polyline. It then smooths them (gaussian σ=1.5, wrap), resamples at 2 m, and fits a similarity transform onto the SVG centreline with Procrustes, over 1000 arc-fraction samples and an S/F shift search of -30..+30 samples.
2. Inputs: `SG/path_samples.json` (S4) and `T/..._outline_svgraw.json` (S3). Constants: dedup at 0.05 m (`:18`), σ 1.5 (`:19`), 2.0 m step (`:21`), 1000 samples (`:27`), shift range ±30 (`:31`), reflections rejected (`:34`). RUS = 63 is hard-coded (`:9`).
3. Outputs: `SG/official_path.json` (xy in the SVG frame, length_m 4866.8, scale, rms, sf_shift_m), read by S7. Also `SG/official_vs_svg.png` (diagnostic, matplotlib).
4. Local.
5. Deterministic (checked). Note that the path's index 0 is RUS's lap start, so the final S/F is the official timing line, not the 855 m roll.

### S7 (bat:27): `SG/_build_official_outline.py`
1. Scales the official path to the FIA length, resamples it to 2000 stations, limits the radius to R≥10, builds 12 m edges and takes their midline ("as built"), and then builds final edges at a constant 10 m width. It writes the real outline and the mirror.
2. Inputs: `SG/official_path.json`. It imports `svg_to_outline` (`limit_min_radius`, `generate_edges_constant_width`). Hard-coded: **4927.0** (`:9`), 2000 stations (`:10`), **R 10.0** (`:12`), **12.0 then 10.0 m width** (`:12-13`).
3. Outputs (overwriting S2's): `T/singapore_grand_prix_outline.json` (render, on-track check) and `T/singapore_grand_prix_mirror_outline.json` (= `M`, read by every sim and optimiser step).
4. Local.
5. Deterministic (checked). Docstring: "10 m width (fitted: 12 m gave worst corner 46 km/h, 10 m 18)". That width was chosen by an earlier experiment and is not re-fitted here.

### S8 (bat:29): `cache/_predict_track.py --track singapore`
1. Predicts the 2026 targets from the track's own 2025 lap and the cross-track 2025→2026 transfer: lap band, top-speed target, and a 2026 target speed for each corner.
2. Inputs: the registry entry `_track_registry.py:137-152` (csv25 = REF25, `altitude_m=15.0`, `length_m=4927.0`, `inset=1.0`, outline = mirror) and `cache/transfer_2026.json` (made by `_transfer_2026.py`, which is not in this bat; dated 2026-09-04). Constants: `VTOP_PCTL=99.5` (`:24`), `CDA0_DEFAULT=0.75` (`:25`), `CL0_DEFAULT=4.6` (`:26`), `LAP_BAND_FLOOR_PCT=0.8` (`:27`), distance-error abort/fallback at >5 % (`:54`), corner detection `corner_minima(prominence 8 km/h, min_sep 80 m)` (`_track_registry.py:180-182`), `rho_isa` (`:156-158`).
3. Output: `cache/predicted_singapore.json`, with `t25_s` 89.241, `lap_band_s` [89.955, 94.216], `vtop_target_kmh` 318.4, 12 corners, `cda0` 0.75, `cl0` 4.6 and `rho` 1.2232. Read by all four autofit runs, and by S23 gate `--targets`.
4. Local. Shared name per track, overwritten on every run.
5. Deterministic. The transfer is an input with no recorded origin in this bat.

### S9 (bat:30): `cache/_autofit_singapore.py` (autofit on the sim's own line)
1. Runs `_autofit_2026.main()` for Singapore with `SIM` swapped to `cache/_sim_singapore.py`. It fits cda and cl in a closed loop, with up to 5 sims, each building its own min-curvature line.
2. Inputs: monkey-patch `af.SIM = _sim_singapore.py` (`_autofit_singapore.py:5`) and argv rewrite (`:6`). Each sim is called with `--outline M --reference-csv REF25 --inset 1.0 --cda/--cl/--rho` at 4 decimals (`_autofit_2026.py:50-57`). The `_sim_singapore.py` wrapper monkey-patches `sim.assert_sanity` (GAIN guard 36.3, `:13-32`), multiplies `sim.MU_LAT` by env `SG_MU_SCALE` (default 1.0, `:35-36`), and calls `_sg_grip.apply(sim)`, which reads env `SG_MECH` and **replaces `sim.a_lat_max_banked` and `sim.v_grip_static`** (`_sg_grip.py:7-20`). Importing the sim also applies **`F1_Pipeline_Assets/calibration/vehicle_calibration.json`** to the WARM_* constants (`sim_2026_lap.py:81-103`). That is a hidden input; every log prints "[calibrate] overrides applied". Fit logic: see section D.
3. Outputs (shared per-track names, **overwritten by S13, S15 and S19 too**): `cache/autofit_singapore.json`, `cache/autofit_singapore_sim.csv`, `cache/autofit_singapore_sim_best.csv`, and `cache/autofit_singapore_rl.json`. **The rl.json is written by the LAST sim run, not by the best iteration** (`run_sim` writes `rl_out` on every iteration, `_autofit_2026.py:48-57`). Logged result (`cache/_autofit_singapore.log`): 5 iterations, not converged, best = it3 **cda 0.618, cl 6.327**, lap 90.64. it4 (0.549, 6.5, CL at its upper limit) was a rail violation.
4. Local.
5. The line does not depend on cda or cl: the build uses WARM_* plus RHO only (`warm_vel_profile`, `sim_2026_lap.py:125-137`). So the last-vs-best rl mismatch is harmless here (checked exact). It does depend on env `LINE_WOBBLE_SIG` and `LINE_WOBBLE_ADAPTIVE` (`sim:451-452`), on the cvxopt IQP (30 iterations, converges at iteration 5) and on `trajectory_planning_helpers`.
6. The round-1 knobs 0.618/6.327 in bat:34 are the 3-decimal printout of this step's best iteration. `cache/singapore_2026.md:116` confirms it.

### S10 (bat:31): `copy autofit_singapore_rl.json -> SG/base_k_rl.json`
Freezes the sim-built line (2451 stations) as the **base line P**. Every optimiser offset, corridor bound and knot is measured from it. Read by S11, S12, S14, S16, S17, S18 and by the dual-video bat. No error check.

### S11 (bat:32): inline `python -c` builds `SG/zero_k.npy`
Runs `_opt_line_2017.setup(base_k_rl, M, None, None, 0.3, 12)` and saves `zeros(len(kidx))` = 205 zeros. Only the knot count matters. The margin 0.3 and every 12 are copies of the optimiser args. Read by S12, S14 and S18 as `--apex-knots`, which detects the apex corners on the base line itself, so all rounds use one corner set.

### S12 (bat:34): optimiser round 1: `SG/_opt_line_2026_sg.py ... --cda 0.618 --cl 6.327 --rho 1.2232 --margin 0.3 --apex-w 1.5 --apex-knots zero_k --out SG/k1`
1. Pattern search over 205 lateral-offset knots, minimising the 2026 car's raw lap plus penalties. Details in section E.
2. Inputs: base_k_rl, M and zero_k. Defaults used: `--every 12`, `--steps 2,1,0.5,0.25`, `--max-sweeps 30`, `--smooth-w 0.006`, `--workers 12`, `--apex-tol 0.15`, `--apex-win 20` (`_opt_line_2026_sg.py:57-66`). Worker `init()` (`:18-24`) sets sim globals `CDA_STRAIGHT_M2`, `CL_CORNER_M2`, `RHO`, `WARM_RHO` and `BANKING_RAD=None`, applies `_sg_grip` (env SG_MECH) and the `SG_MU_SCALE` env. It imports `cache/bahrain/_apex_gaps.py` (Bahrain folder) and `cache/era2017/_opt_line_2017.py`.
3. Outputs: `SG/k1_knots.npy` (saved after every sweep) and `SG/k1_rl.json` (`{"raceline"}` only), read by S13 and S14.
4. Local. Log `SG/k1.log`: base 263.915 s (the apex penalty dominates), final 84.400, pure lap 82.733, 575 s.
5. See section G. The 12 workers are hard-coded.

### S13 (bat:35): `SG/_autofit_rl_in_sg.py SG/k1_rl.json`
1. Same `_autofit_2026.main()`, but every sim is told `--raceline-in k1_rl.json`.
2. Monkey-patching: `A.SIM = _sim_singapore.py` (`:8`), and **`A.subprocess.run` is replaced process-wide** to append `--raceline-in` (`:9-13`).
3. Outputs: the same 4 shared `cache/autofit_singapore*` files. Log `SG/k1_refit.log`: converged at it2, **cda 0.554, cl 4.348**, lap 93.52.
4. Local. Every refit restarts from cda0/cl0 = 0.75/4.6 (from `predicted_singapore.json`), not from the previous knobs.

### S14 (bat:36): optimiser round 2: `--cda 0.554 --cl 4.348 ... --steps 1,0.5,0.25 --init-knots SG/k1_knots.npy --apex-knots zero_k --out SG/k2`
Outputs `SG/k2_knots.npy` and `SG/k2_rl.json`. Log: base 94.390 → 93.582, pure lap 92.097, 218 s. The 0.554/4.348 are the 3-decimal copy of the S13 log.

### S15 (bat:37): `_autofit_rl_in_sg.py SG/k2_rl.json`
Log `SG/k2_refit.log`: **cda 0.559, cl 4.363**, lap 92.73. Overwrites the shared autofit files. The bat never uses the outputs of this refit except as the hand copies on bat:42.

### S16 (bat:38): `SG/_scan_crossings.py base_k_rl M SG/k2_rl.json` (report only)
Prints, for each pair of opposite-direction corners, how far the line swings toward the next corner's outside. No `|| exit`, no file output, nothing consumes it. It runs on **k2 (before the wide entry)**. `singapore_2026.md` says this metric "was misleading here".

### S17 (bat:41): `SG/_seed_wide.py base_k_rl M SG/k2_knots.npy SG/seed26_wide.npy 2040 2140 0.8`
1. Pushes the knots between arc 2040 and 2140 m toward the bound opposite their current side, by 0.8 of the way, weighted by sqrt(sin). This seeds the T8→T9 wide entry.
2. `setup(..., 0.3, 12)` hard-coded (`:9`). The arguments 2040, 2140 and 0.8 are user-decision numbers (bat:39 comment "v4b (user)", RUS 2025 onboard).
3. Output: `SG/seed26_wide.npy` (S18). 4 knots moved (checked).

### S18 (bat:42): optimiser round 3: `--cda 0.559 --cl 4.363 ... --steps 1,0.5,0.25 --init-knots seed26_wide.npy --apex-knots zero_k --touch 2060,2120,1980 --out SG/k3w`
Adds the touch constraint (section E). Log: "touch constraint: 2060-2120 m, side +1 (as at 1980 m)", base 96.774 → 93.691, pure lap 92.113, 197 s. Outputs `SG/k3w_knots.npy` and **`SG/k3w_rl.json`**, which is the shipped line and the pack's `raceline_in_file`.

### S19 (bat:43): `_autofit_rl_in_sg.py SG/k3w_rl.json`
Final refit. Log `SG/k3w_refit.log`: it0 (0.75/4.6) 92.14, it1 (0.678/4.2) 93.96, **it2 cda 0.558 cl 4.323 → 93.01 s, converged**. The JSON stores **0.5581 / 4.3233**, lap 93.008. These are the pack's FITTED values. Outputs `cache/autofit_singapore.json`, `_sim.csv`, `_sim_best.csv` and `_rl.json` (the k3w coords plus arc_length, kappa, track_length_m and banking_deg []).

### S20 (bat:44): `copy cache/autofit_singapore_sim_best.csv -> exports/singapore_2026_synthetic.csv` (= CSV)
The shipped lap CSV (frame, time_s, distance, speed, throttle, brake, gear, rpm, soc_pct, mode, power_kw; 30 fps). Used by the gate, corner compare and the render, and also by the dual-video bat and `_rus2025_car.py`.

### S21 (bat:45): `copy cache/autofit_singapore_rl.json -> T/singapore_grand_prix_mirror_raceline.json`
The golden raceline (`weekend/golden/singapore_2026.json`).

### S22 (bat:46): `_singapore_prep.py unmirror mirror_raceline.json raceline.json`
Flips x to -x and negates kappa (`:37-42`). Output: `T/singapore_grand_prix_raceline.json` (render, on-track check, dual bat).

### S23-S25 (bat:48-50): checks
Covered in section C. None of them has `|| exit`.

### S26 (bat:52): render: `raceline_video.py --outline T/singapore_grand_prix_outline.json --raceline T/singapore_grand_prix_raceline.json --telemetry-csv CSV --track-name "Singapore Grand Prix" --zoom 28 --out ROOT/singapore_grand_prix_2026_optimal_lap.mp4`
Covered in section B. The mp4 is not in the sandbox (videos excluded).

---

## A. Data flow

```
Marina_Bay_circuit_2023.svg --S1 svg_to_outline--> cache/singapore_outline_autoSF.json
  --S2 prep (roll 855 m)--> T/outline.json (+mirror; both later overwritten)
  --S3 copy--> T/outline_svgraw.json ----------------------------------+
OpenF1 location, session 9892, top-10 --S4--> SG/path_samples.json ---+--S6 _official_path--> SG/official_path.json
  --S7 _build_official_outline (4927 m, R10, 12->10 m)--> T/singapore_grand_prix_outline.json (real frame) + M (mirror)
OpenF1 car_data 2025 Q --S0--> exports/reference_2025_singapore_q.csv (REF25)
REF25 + registry + cache/transfer_2026.json --S8 _predict_track--> cache/predicted_singapore.json
M + REF25 + predicted + [vehicle_calibration.json, env SG_MECH] --S9 autofit (5 sims, own line)-->
     cache/autofit_singapore.json (best 0.618/6.327, typed into bat:34 by hand) + autofit_singapore_rl.json
  --S10 copy--> SG/base_k_rl.json --S11--> SG/zero_k.npy
base_k_rl + M + zero_k + [cda .618 cl 6.327] --S12 opt--> SG/k1_knots.npy, SG/k1_rl.json
k1_rl --S13 refit--> (0.554/4.348, typed into bat:36)
k1_knots --S14 opt--> SG/k2_knots.npy, k2_rl.json --S15 refit--> (0.559/4.363, typed into bat:42)
k2_rl --S16 scan (print only)
k2_knots --S17 seed_wide (2040,2140,0.8)--> SG/seed26_wide.npy
seed26_wide --S18 opt (+touch 2060,2120,1980)--> SG/k3w_knots.npy, SG/k3w_rl.json
k3w_rl --S19 refit--> cache/autofit_singapore.json (0.5581/4.3233, 93.008 s), autofit_singapore_sim_best.csv, autofit_singapore_rl.json
  --S20 copy--> exports/singapore_2026_synthetic.csv (CSV)
  --S21 copy--> T/singapore_grand_prix_mirror_raceline.json --S22 unmirror--> T/singapore_grand_prix_raceline.json
CSV + predicted --S23 gate;  real outline + raceline --S24 on-track (-> cache/_ontrack_singapore.png);  CSV + REF25 --S25 corner compare
real outline + raceline + CSV + fonts (D:\f1_hot_lap\fonts) --S26 raceline_video--> ROOT/singapore_grand_prix_2026_optimal_lap.mp4
(S5 _rus2025_car: reads CSV from the PREVIOUS run -> SG/rus2025_on_2026_line.csv; nothing in this bat consumes it)
```

The existing `weekend/run.py` covers only S19's last sim, which is the same as `sim_2026_lap.py --raceline-in k3w_rl.json --cda 0.5581 --cl 4.3233 ...`.

## B. Render (`raceline_video.py`)

| Setting | Value | Where | CLI? |
|---|---|---|---|
| zoom | **28** (default 30) | bat:52; `DEFAULT_ZOOM` `:76`; `cam_scale = min(W, H*0.5)/max(track_w,h) * zoom` `:869` | CLI |
| resolution | 1080x1920 | `WIDTH, HEIGHT` `:74` | hard |
| fps | 30 | `DEFAULT_FPS` `:75` | CLI (not passed) |
| trail | 180 frames, thickness 18, speed heat-map red→yellow→cyan | `:77`, `:81`, `speed_color_bgr` `:798-805` | trail CLI (not passed) |
| duration | `ceil(lap_time*fps)`, where lap_time = CSV t[-1]-t[0] = 93.008 → 2791 frames | `:852` | from CSV |
| lap label | `LAP TIME m:ss.sss` from the CSV, unless `--display-laptime` | `:1129-1131` | CLI (not passed) |
| title | "THE OPTIMAL LAP" (y 320, font 42 bold) + track name upper-cased (y 400, font 26) | `:98`, `:109-110`, `:906-907` | `--title`/`--track-name` |
| speed readout | y 1112, font 72, "KM/H" at +78, font 28 | `:111-112` | hard |
| mode label | y 1050, font 24; colours DEPLOY (60,220,100), SUPERCLIP (255,140,0), REGEN (255,230,0), BRAKING (255,80,60); unknown modes are not drawn | `:120-127`, `:839-843` | hard |
| watermark | "@formulytics" y 1288, font 24, grey 150 | `:88`, `:114` | hard |
| colours | track fill (40,40,40); edge white thickness 4; raceline (90,90,90) thickness 3; dot r 28 + white ring 4; kerbs (240,240,240) | `:78-87`, `:105`, `:1008-1010` | hard |
| kerbs | κ>0.005, depth 1.5 m, dilate 10, taper/block/gap 0.8 m | `:93-98` | hard |
| minimap | 240 px at (W-280, 460), rotated 45° | `:116-118`, `:880` | hard |
| camera | follows the dot; dot at y=0.45·H | `CAMERA_Y_FRAC` `:111` | hard |
| visual edges | outline resampled 4000 pts, s=10; outset 0 when `--raceline` is given | `:55-58`, `:1206-1213` | hard |
| raceline | loaded as-is (`--raceline`); S/F alignment **skipped** because the CSV has `soc_pct` ("synthetic") | `:1230-1235` | — |
| dot position | CSV distance × (raceline arc / CSV distance) | `:953-958` | — |
| fonts | first match of `D:\f1_hot_lap\fonts\Formula1-*.ttf` (**outside the repo**, present), then `C:\Users\91910\Downloads\Formula1\...`, Arial, PIL default | `:811-827` | hard, hidden input |
| codec | OpenCV `mp4v` | `:948-949` | hard |
| unused here | `--fence`, `--tagline`, `--flights`, `--elevation-json`, `--elev-scale`, `--max-seconds` | `:1161-1179` | CLI |

Byte-determinism of the mp4: **unknown**. The pipeline itself is deterministic (no time, no randomness), but whether OpenCV/FFmpeg writes identical bytes has not been tested. A double-render byte compare is needed. Font choice depends on the machine.

## C. Checks (none stops the bat: bat:48-50 have no `|| exit`, and the render runs regardless)

**S23 `_gate_2026.py CSV 89.241 --targets predicted_singapore.json`** exits 1 on failure, which is ignored. With `--targets`: lap ≥ t25 + 0.8 (`LAP_RAIL_S` `:29`); lap inside the predicted band [89.955, 94.216]; top speed within ±6 of 318.4 (`:26`); median corner-min error within ±6 over 12 corners, window ±0.015 lap fraction (`:27-28`). Always applied: GAIN median 14-28 (`:34`), GAIN peak ≤64 (`:35`), DROP median 32-52 (`:36`), DROP peak ≥85 (`:37`), superclip fraction ≤0.45 and peak ≥35 (`:42-43`), rates over 0.5 s windows (`:31`). Reference data: `predicted_singapore.json` plus bands measured on Catalunya FP1 and Canada 2026 (docstring `:10-11`). The **89.241** is hard-coded in the bat; it equals `t25_s` (CSV span), while the official pole is 89.158. Current result is 9/9, but GAIN 27.9 is only 0.1 under the limit.

**S24 `_check_ontrack.py real-outline raceline singapore`**: for each raceline point, distance to the nearest centreline station minus local half-width must be ≤ **TOL 0.30 m** (`:23`). The distance is unsigned. Prints "ON-TRACK OK" or "OFF-TRACK"; the exit code is always 0. Writes **`cache/_ontrack_singapore.png`** (`:43-44`).

**S25 `_corner_compare.py CSV REF25 4927`**: aligns the two traces with an FFT cross-correlation (`_track_registry.align_pair`, n=2048), finds corner minima (prominence 8, separation 80 m) and pairs them greedily within 1.5 %. The target is v25·r(v25) from `cache/transfer_2026.json` (read implicitly, `:10`). It flags residuals beyond ±10 km/h (`:21`). Report only, exit 0. 4927 is hard-coded in the bat.

**S16 `_scan_crossings.py`**: corners are |κ| peaks with R<250 m separated by >120 m (`_apex_gaps.corners`). It flags "stays inside" when the swing is <0.6 with a gap >80 m (`:19`). Report only, and it runs on k2.

Inside the sim itself, sanity checks **do** stop a sim (exit 1). In autofit, a failed sim becomes a back-off (`_autofit_2026.py:58-65`). The checks are: lap 60-130 s (`sim:1551`), vmax 250-360 (`:1553`), vmin 40-160 (`:1558`), superclip drop >60 (`:1580`), GAIN median 12-32 (`:1615`, replaced by ≤36.3 in the Singapore wrapper), DROP median 28-60 (`:1620`). So three different GAIN bands are in play: 12-32 (sim), ≤36.3 (wrapper) and 14-28 (gate).

## D. Fitting

**`cache/_autofit_2026.py`**, used by S9, S13, S15 and S19:
- Knob → feature: **CDA → f1 = sim vtop (p99.5 of speed) − `vtop_target_kmh`** (318.4 = 2025 p99.5 + transfer mean +2.38). **CL → f2 = trimmed median of corner-minimum errors** over a tier set. Tier 1 is v25>170 if there are ≥2 such corners; Singapore has only one (215), so it falls through to **tier 2, v25≥130**: the 5 corners at 145, 158, 144, 155 and 215. With ≥3 errors, the single worst |err| is dropped (`:93-114`). Sim corner speed = minimum within ±0.015 lap fraction, circular (`:69-90`, `MATCH_TOL_FRAC` `:42`). Low-speed corners (v25<130) are reported (`ls_median_err_kmh`, +5.86 now) and **not fitted**. Lap time is not a target. It is only a rail (lap > t25+0.8, `:39`) and a ranking key.
- Start: cda0 0.75, cl0 4.6 (from the predicted JSON). Limits: `CDA_LIM (0.45, 1.30)`, `CL_LIM (3.00, 6.50)` (`:40-41`). Tolerances: `TOL_TOP 2.0`, `TOL_HS 3.0` km/h (`:37-38`). Iterations: `--max-iters 4` → at most 5 sims (`:122`).
- Updates: CDA uses a cube-law step `cda·(vtop/target)^3` first, then a secant (needs Δcda > 1e-4 and Δf1 > 0.2), clamped to ±25 % per step (`:180-187`). CL uses a first bump of 0.4 against sign(f2), then a secant, clamped to ±0.8 per step; from a rail-violating state, CL must drop by ≥0.15 (`:192-201`). If a sim fails sanity, the knobs are halved back toward the last good point (`:147-157`).
- Best state: rail-passing first, then |f2| + 0.5|f1| (`:166`). The best CSV is copied, but **rl.json is from the last sim**.
- Singapore results: S9 not converged (best 0.618/6.327, which is next to CL_LIM 6.5); S13 0.554/4.348; S15 0.559/4.363; S19 **0.5581/4.3233** (lap 93.008, top err +1.63, hs err +0.18).

**`cache/_predict_track.py`** (section 1, S8) supplies the targets. **`cache/predicted_singapore.json`** is 12 corners with s_frac and v25 → v26 (r-knots 80/140/200/260/320 → 0.967/0.943/0.926/0.926/0.926), plus lap band and vtop.

**`SG/_fit_street_grip.py`** (NOT run by the bat; a one-off whose result is typed into bat:18 as `SG_MECH=0.7230`):
- On the *2025* car (era-2017 model `cache/era2017/sim_2017_car.py` via `SG/_car2025.py`, parameters from `SG/car2025_phys.json`: mass 800, cl 4.277, cda 1.607, mu_lat 2.058…), it bisects k in [0.3, 1.0] for **25 iterations** until the lap equals 89.158 s (RUS), on line `SG/off25_rl.json` (made by another script, `_opt_line_2025.py`).
- k scales only the gravity term `mu·(k·g + DF/m)` (`_sg_grip.py:12-18`). The result is `SG/street_grip.json`, k = 0.7229534 (rounded by hand to 0.7230 in the bat).
- It also compares corner minima against a cl-trim alternative (`car2025_off2.json`). The fit depends on `car2025_phys.json`, `off25_rl.json` and `rus2025_car_data.json` (DRS zones), none of which the bat produces.

**`cache/singapore/_fit_mu.py`** exists for the rejected `SG_MU_SCALE` knob (`_sim_singapore.py:33-38`). Unused (default 1.0).

## E. Line building (`SG/_opt_line_2026_sg.py` + `cache/era2017/_opt_line_2017.py` + `cache/bahrain/_apex_gaps.py`)

**Corridor** (`_opt_line_2017.setup`, `:21-48`). The base line P = `base_k_rl` (2451 stations, about 2 m apart); normals come from central differences. The road polygon is `outer − inner` eroded by **margin 0.3 m** with shapely. Each station's normal is probed from −20 to +20 m in 0.05 m steps (`:32`, so the half-width is capped at 20 m), giving lo/hi. The corridor is then forced to contain 0 (`:45`). Knots sit every **12 stations** (about 24 m), giving **205 knots**. Note that margin 0.3 is the line centre to the road edge; it is a different number from the sim's inset 1.0, the renderer's INSET 1.0 and VEH_WIDTH 2.0.

**Line** (`line_of`, `:55-61`). A periodic cubic spline of knot offsets gives an offset per station. Violation = sum of the excess beyond lo/hi, and the offset is clipped to the corridor.

**Cost** (`_opt_line_2026_sg.cost`, `:34-49`):
`raw bang-bang simulate_lap time` (the un-smoothed lap, no jerk filter, no sanity checks)
+ `2.0 × violation`
+ `smooth_w (0.006) × Σ(2nd difference of knots)²`
+ touch term
+ apex term.

**Apex touch.** The corners are |κ| peaks with R<250 m, separated by >120 m, from an 8-station stencil (`_apex_gaps.corners`). They are computed **once, on the `--apex-knots` line** (zero_k = the base line): 17 corners at 394, 541, 663, 943, 1787, 1995, 2191, 2633, 2755, 2877, 3021, 3569, 3823, 4299, 4421, 4665 and 4791 m. For each corner, the gap = minimum over ±**20 stations** of the distance to the inside bound (inside = hi if κ>0, else lo). Penalty: `apex_w (1.5) × Σ max(gap − apex_tol 0.15, 0)²`.

**`--touch a0,a1,ref`** (`:75-80`, `:40-43`). Station indices are taken where arc is in [a0, a1]. The side is fixed once, from the **initial** line (init knots) at arc `ref`: +1 if that point is nearer hi. Penalty: `touch_w (1.5) × max(min gap to that side's bound in the window − apex_tol, 0)²`. So it is a soft penalty, not a hard constraint. For k3w the side is +1 "as at 1980 m" (the T8 apex), window 2060-2120 m. The direction comes from the seed, not from a declared side.

**Search** (`:86-105`). Parallel pattern search with `ProcessPoolExecutor(12)`. For each step size in `--steps` (round 1: 2, 1, 0.5, 0.25 m; rounds 2-3: 1, 0.5, 0.25), and for up to **30 sweeps**, every knot is tried at ±step. Improving candidates have cost < best − **1e-4**, sorted by (cost, i, s). A greedy non-adjacent set (indices ≥3 apart, circular) is combined. The combined move is accepted if it beats the best single move; otherwise the best single move is taken. A step size ends when a sweep has no improvement. Knots are saved after every sweep.

**Seeds and rounds.** Round 1 starts from zeros (= base line). Round 2 starts from k1 knots. `_seed_wide` takes k2 knots, moves the knots in (2040, 2140) toward the opposite bound by 0.8·w, with w = sqrt(sin), and that becomes round 3's init. **Three optimiser rounds** (k1, k2, k3w) and four autofits. The bat header calls it "2 rounds → fixed point", but it is not one: k3w was optimised at 0.559/4.363 and refitted to 0.558/4.323.

## F. Singapore-specific vs shared

| Script | Status |
|---|---|
| `fetch_openf1_lap.py`, `svg_to_outline.py`, `sim_2026_lap.py`, `raceline_video.py`, `cache/_predict_track.py`, `cache/_autofit_2026.py`, `cache/_gate_2026.py`, `cache/_check_ontrack.py`, `cache/_corner_compare.py`, `cache/_track_registry.py`, `cache/transfer_2026.json` | shared |
| `cache/era2017/_opt_line_2017.py` (Sepang 2017 origin), `cache/bahrain/_apex_gaps.py` | shared, imported from other tracks' folders |
| `cache/_singapore_prep.py`, `cache/_sim_singapore.py`, `cache/_autofit_singapore.py`, `SG/_fetch_path_multi.py`, `SG/_rus2025_car.py`, `SG/_official_path.py`, `SG/_build_official_outline.py`, `SG/_sg_grip.py`, `SG/_fit_street_grip.py`, `SG/_seed_wide.py`, `SG/_scan_crossings.py`, `SG/_autofit_rl_in_sg.py` (copy of `cache/bahrain/_autofit_rl_in.py`) | Singapore only |
| `SG/_opt_line_2026_sg.py` | copy of `cache/bahrain/_opt_line_2026.py`, plus `_sg_grip`, `SG_MU_SCALE`, `--apex-knots` and `--touch`. Its docstring says "identical except SG_MU_SCALE", which is stale |

Stages used by the other bats (from a grep of the .py names called):
- bahrain_2026_lap: fetch, svg_to_outline, predict, autofit_2026, gate, check_ontrack, corner_compare, _fetch_elevation, render (zoom 18)
- bahrain_what_could_have_been: bahrain `_opt_line_2026` ×6 + `_autofit_rl_in` ×2, gate, check_ontrack, render (zoom 18)
- canada: svg_to_outline, sim_2026_lap, render (default zoom 30)
- catalunya: svg_to_outline, fetch, sim_2026_lap, render (zoom 30 default)
- hungary / spa / zandvoort: fetch, _overlay_speed, fetch, svg_to_outline, predict, autofit_2026, gate, render (zoom 26 / 30 / 30)
- monaco: svg_to_outline, sim_monaco_2026_lap, render
- monza: fetch, svg_to_outline, _verify_outline, predict, autofit_2026, gate, _fetch_elevation, render, _build_3d_viewer (zoom 30)
- sepang_2026: _noref_backtest, _era_ratio_2017_2026, _sepang_t1_apex, svg_to_outline, sim ×2, gate, check_ontrack, render (zoom 18)
- silverstone: fetch, svg_to_outline, sim_2026_lap, render (zoom 23)
- **singapore_2025_vs_2026** (depends on this bat): reads `SG/base_k_rl.json`, `zero_k.npy`, `k2_knots.npy`, `street_grip.json`, `exports/singapore_2026_synthetic.csv` and `T/singapore_grand_prix_raceline.json`; runs `_opt_line_2025`, `_seed_wide`, `_finish2025_v4`, `_rus2025_exact` and `dual_lap_video_v3` (zoom 28).

## G. Broken, dead, contradictory, or able to make two runs differ

1. **S5 `_rus2025_car.py` is dead here, and it blocks a fresh run.** It needs this bat's own final CSV and exits 1 if it is missing. Its outputs are unused by this bat.
2. **Hand-copied knobs** (bat:34, :36, :42): 0.618/6.327, 0.554/4.348 and 0.559/4.363 are 3-decimal copies of earlier log lines; the 4-decimal JSON values were overwritten. Round 1 comes from a **non-converged** autofit with CL next to its 6.5 limit. To reproduce the shipped line exactly, the pack must carry these three pairs exactly as typed (labelled with that origin), or the chain must compute them using the same 3-decimal rounding rule. Recomputing from the autofit JSON (4 decimals) would change k1, k2 and k3w.
3. **"Fixed point" is false.** The line was optimised at 0.559/4.363 but the final knobs are 0.5581/4.3233. Another round would move the line.
4. **Shared outputs are overwritten 4× in one run:** `cache/autofit_singapore.json`, `_sim.csv`, `_sim_best.csv` and `_rl.json`. Also `cache/predicted_singapore.json` and `cache/_ontrack_singapore.png`. The autofit rl.json is the last iteration's, not the best one's: harmless for --raceline-in and for the own-line build (the line does not depend on cda/cl), but fragile.
5. **Checks never stop the bat.** The gate's GAIN median is 27.9 against the 28.0 limit, so tiny numeric drift could flip it. There are three GAIN bands (12-32, ≤36.3, 14-28). The gate's t_2025 is hard-coded at 89.241 (CSV span), versus the official 89.158 used elsewhere (`_rus2025_car.py:18`, `_fit_street_grip`).
6. **Hidden inputs:**
   - `F1_Pipeline_Assets/calibration/vehicle_calibration.json`, applied on sim import (`sim:81-103`), which sets the WARM_* values that shape the base line.
   - `cache/transfer_2026.json`
   - registry constants (altitude 15, length 4927, inset 1.0)
   - fonts outside the repo
   - env vars inherited from the shell: `SG_MU_SCALE`, `KGRIP_STENCIL` (`sim:1365`), `LINE_WOBBLE_SIG` and `LINE_WOBBLE_ADAPTIVE` (`sim:451-452`)
   - absolute Python path in `bat:12`
   - unpinned library versions (numpy, scipy, shapely, cvxopt, trajectory_planning_helpers, opencv): unknown
7. **Monkey-patching:**
   - `_autofit_singapore`: `af.SIM`
   - `_autofit_rl_in_sg`: `A.SIM` and the process-wide `subprocess.run`
   - `_sim_singapore`: `sim.assert_sanity` and `sim.MU_LAT`
   - `_sg_grip`: `sim.a_lat_max_banked`, `sim.v_grip_static` and `sim._sg_mech`. Note `apply(S, 1.0)` returns early without restoring the originals.
   - optimiser `init()`: CDA, CL, RHO, WARM_RHO, BANKING_RAD and MU_LAT globals in each worker
   - `raceline_video`: `globals()` for TITLE, FENCE, MAX_SECONDS, TAGLINE and JETS, and `EL3D_FOCAL`

   Street grip reaches the optimiser only through the env var (`_sg_grip.apply(_S)` without k), while `weekend/run.py` passes k explicitly.
8. **S2's outline writes are dead**: S7 overwrites them. Only the svgraw copy matters.
9. **`_scan_crossings` runs on the wrong line** (k2, before the wide entry). Its output is discarded, and the md calls the metric misleading.
10. **The touch "constraint" is a soft penalty** (weight 1.5, quadratic). Its side comes from the seed line, not from a declared inside/outside. The window, ref and seed numbers (2040, 2140, 0.8, 2060, 2120, 1980) are bare metres in the bat, which conflicts with grill D6 (direction-only constraints).
11. **Randomness: none found.** No RNG, no time-dependence in maths. ProcessPool `ex.map` keeps order, cost is a pure function, and sim functions keep no state between calls. Results should not depend on worker count, though that was not tested. Remaining risks: BLAS/cvxopt floating-point reproducibility across machines or versions, and the network fetches (S0, S4) if their caches are deleted.
12. **Iteration and tolerance knobs that change results:**
    - optimiser: steps, max-sweeps 30, accept 1e-4, knot every 12, margin 0.3, probe 0.05 m / ±20 m, smooth_w 0.006, apex_w 1.5, apex_tol 0.15, apex_win 20, touch_w 1.5, workers 12 (no effect on results)
    - autofit: max-iters 4, TOL 2/3, rails, step clamps
    - sim: `simulate_lap(max_iters=8, tol_v=1.0)` (`sim:1344`); IQP 30 iterations, `ALPHA_TOL 0.10`, damping 0.5 (`raceline_video.py:64-67`)
    - `limit_min_radius` 600 iterations; street-grip bisection 25 iterations
13. **Inconsistent widths and margins in one chain:** road 10 m (S7); optimiser margin 0.3; sim inset 1.0 (S9 own line only); on-track TOL 0.30; render VEH_WIDTH 2.0 and INSET 1.0 (unused with `--raceline`).
14. The pack's `inset_m` (1.0) has no effect in `weekend/run.py`, because `--raceline-in` skips `build_raceline`.
15. `copy` lines (bat:23, :31, :44, :45) have no error check. `if not exist` guards use only file existence, not content, so stale caches are silently reused.

## H. Runtimes (from logs and mtimes; the machine is the original, not the sandbox)

| Stage | Time | Source |
|---|---|---|
| S9 autofit (5 sims with own-line build) | unknown in total; a single own-line build + S/F = **58 s** measured today (in memory, IQP converged at iteration 5, about 7.5 s per iteration) → roughly 5-6 min | today's check |
| S12 k1 optimiser | **575 s** (+ final report sim) | `SG/k1.log` |
| S13 refit k1 | ~4 s after k1.log closed (3 sims, --raceline-in) | mtimes 18:43:54 → 18:43:58 |
| S14 k2 optimiser | **218 s** | `SG/k2.log` |
| S15 refit k2 | ~4 s | mtimes 18:47:56 → 18:48:00 |
| S17 seed → S18 k3w | seed 20:32:30, k3w done 20:36:00 (**197 s** of search) | `SG/k3w.log` |
| S19 refit k3w | ~18 s | 20:36:00 → 20:36:18 |
| S20-S24 | ~4 s (raceline 20:36:20, on-track png 20:36:22) | mtimes |
| S0-S8, S26 render | unknown (no logs; the render log for the single video was not kept; `SG/dual.log` covers the dual video only) | — |

Rough total for a clean run with caches present: about 25 min plus the render (unknown).
