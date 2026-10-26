# NOW — Airflow sim on track

## Objective
Airflow simulation of a car on a race track. A project of its own; it borrows only
selected pieces (e.g. the racing line) from `D:\f1_hot_lap\OPTIMAL LAP SCRIPTS`.
Scope and goals: to be set by the first spec (see Next).

## Rules
- Separate project with its own git (`main`). The parent `D:\f1_hot_lap` repo ignores this folder.
- `OPTIMAL LAP SCRIPTS` is read-only from here: copy what we need into this repo and record
  where it came from (source path + commit) in `docs/imports.md`. Never edit the source folder.
- Never delete anything (move/rename instead) — enforced by `hooks/no_delete.py`.
- One step per session; update this file before `/clear`.

## Workflow (same as the optimal-lap sandbox)
- Spec/design first: `.scratch/<feature>/spec.md`, tickets `.scratch/<feature>/issues/NN-<slug>.md`
  (conventions: `docs/agents/issue-tracker.md`). Longer design/plan docs: `docs/YYYY-MM-DD-<topic>-design.md` / `-plan.md`.
- Commit after each finished step; message says what changed and why, ending with the Co-Authored-By line.

## Roadmap
1. [x] Scaffold — folder, git, NOW.md, tracker conventions, no-delete hook (2026-10-26)
2. [ ] Spec — brainstorm/grill what "airflow sim on track" means (2D/3D, CFD vs reduced model, outputs)
3. [ ] Import racing line (and anything else the spec needs) from OPTIMAL LAP SCRIPTS

## Research (2026-10-26)
Notes: `research_notes/Lightweight CFD for F1 lap airflow/` (round 1) and `research_notes/Wide search light airflow solutions/` (round 2,
Python/AI focus). User rejected: FluidX3D/OpenFOAM/ParaView/big LBM (too heavy, tried), commercial real-time products, game/VFX fluids,
creator prior art, licensing research. Findings worth keeping: 2D top-view sim not meaningful (downforce = 3D ground effect); quasi-steady
lap snapshots OK; NVIDIA PhysicsNeMo checkpoints on HF (road car only); WaterLily.jl = top light solver; Python: XLB, lettuce, Homebrew-CFD,
PteraSoftware (wings + ground effect only).

## WaterLily spike (throwaway, spikes/waterlily/)
Julia 1.13.3 via juliaup + WaterLily + CUDA.jl works on the RTX 4060 Laptop. Ahmed-proportion box over moving ground, Float32:
0.26M cells 5.4 ms/step | 2.1M 17.8 ms | 7.1M 59 ms | 16.8M 138 ms (~8.3 ns/cell/step, ~170 B/cell). GPU hit 82 C / 95 W at 16.8M.
Forces printed are NOT meaningful (include ground plane, 100 steps only). Raw: spikes/waterlily/bench_2026-10-26.txt

## PteraSoftware spike (throwaway, spikes/pterasoftware/, py3.11 venv; 5.1 needs py>=3.11)
F1-ish front+rear wing (NACA0012, -8 deg, 70 m/s, front 8 cm off ground): free wake 180 steps 47 s CPU; steady 37 ms/case.
Total 2252 N; front wing 981 N free air -> 1747 N at 8 cm (inviscid, keeps rising, no stall). Wake rises (upwash) - correct sign.
Picture: spikes/pterasoftware/pterasoftware_f1_wings.png. Wings only, no floor/body/wheels.
WaterLily settled wake: 7.3M cells, 8 body lengths in 115 s -> spikes/waterlily/wake_384.png (domain small: 0.5 L upstream, 2.5 L wake).

## DECISION (user, 2026-10-26): go with PteraSoftware
Reason: fast and light (CPU, no GPU heat). Known and accepted limits: wings only (no floor/diffuser/body/wheels),
no separated wake, inviscid ground effect (no stall close to the ground). WaterLily spikes kept for reference only.

## Austin hairpin spike (spikes/hairpin/, 2026-10-26) - plan WORKS
Per frame: lap data (raceline + FP1 2026 speed aligned by speed shape, corr 0.68) -> Ptera steady VLM in ground effect
(49 ms) -> 4 tip trails released in WORLD frame, moved by Biot-Savart + ground image, 4 substeps (44 ms) -> draw north-up.
Trails follow the hairpin by themselves (no bending step). Video: spikes/hairpin/out/austin_hairpin_trails.mp4,
still: out/hairpin_entry_apex_exit.png. Known: slight jitter in front trails (vortex 8 cm off ground), crude wings
(NACA0012 single element, -8 deg) -> downforce far below a real 2026 car; constant ride height; no straight mode; no
corner speed difference across the span.

## Hairpin v2-v6 (2026-10-26) - CURRENT = v6 STREAMLINES, user: "very very rough draft, far from usable"
- spikes/hairpin/hairpin_v4.py = physics core: per frame Ptera steady VLM strip circulations (N_SPAN 6) -> ring-vortex
  lattice in WORLD frame (streamwise + spanwise shed legs, bound at 1/4 chord, ground image), wake row shed every substep
  (6/frame), numba Biot-Savart. Substep times end at frame time (bug fixed: rows were drawn ahead of the car).
- v5 = same in the original Ptera plot style (dots) -> user REJECTED dots ("why are they points").
- v6 (hairpin_v6.py) = streamlines of air velocity relative to the turning car frame (u_ind - V*fwd - yaw_rate x r),
  seeds: rake ahead of each wing + rings round tips. Lines curve with the hairpin. Frames: spikes/hairpin/out_v6/
  (v6_entry_apex_exit.png, austin_hairpin_v6.mp4). 0.9 s/frame (Ptera 34 ms, wake 0.2 s, streamlines+draw 0.66 s).
- Not done / known: tip-vortex corkscrew real but ~10 cm wide -> invisible at 12 m view (an x10 tip close-up inset was
  drafted, user stopped it - not applied); colour range too wide (all teal); front wake rises ~1.1 m in 1 s (check core
  params); placeholder wings (NACA0012 -8 deg) -> downforce far too low; constant ride height; no straight mode.

## v7 (2026-10-26) - jitter FIXED (user feedback on v6: streamlines look bad + video jittery)
- Root cause: heading from the raw 0.5 m raceline zigzagged ~0.6 deg/frame -> yaw rate jumped 0 <-> 1 rad/s per frame
  -> yaw_rate x r term in the car-frame streamlines jumped up to 17 m/s at 11 m -> the whole field whipped about.
- hairpin_v7.py: Gaussian-smooth the raceline (sigma 1 m) before heading. Yaw-rate jump/frame median 0.44 -> 0.013 rad/s,
  line shift max 4 cm. Output spikes/hairpin/out_v7/ (austin_hairpin_v7.mp4). Consecutive frames checked: steady shape.
- NOTE: hairpin_v6.py (and so v7) contains the x10 tip close-up inset + colour norm 0.85-1.15 that the user had stopped;
  they ARE drawn in v7 frames. Ask the user whether to keep or remove.

## v8 (2026-10-27) - user confirmed v7 smooth, asked "fix all" (colour, wake rise, tip vortex, wings)
- wings_v8.py: cambered inverted NACA-type sections (custom outline), tuned in Ptera to ClA front 0.92 / rear 0.72 m^2
  (ASSUMED 2026 level; no published wing split found). Front-wing outer 0.35 m/side lifted 0.15 m (user's choice).
  At 84 km/h: front 308 N, rear 242 N (were 201 / 51).
- hairpin_v8.py: wake shed from real panel TE/quarter-chord points; diverging colour (blue slower / grey / red faster),
  range frozen at first frame; x10 inset REMOVED (user ok); two slices across the car 1 m behind each wing (streamplot
  of induced flow over streamwise vorticity) -> tip vortices clearly visible. 1.8 s/frame, 6 min render. out_v8/.
- WAKE RISE NOT FIXED. Diagnosis (front wing only, scratch runs): ground image pushes the downforce tip vortices
  INWARD (tip spacing 1.90 -> 0.68 m in 0.1 s); close pair then self-lifts fast. Without image: spacing ~1.5 m, rise
  ~0.9 m/s = textbook Gamma/(2 pi b). Rear-wing upwash ~doubles it. Raised tips did NOT help (0.5 s: spacing 0.17 m,
  rise +2.2 m). Missing physics: front tyres behind the tips, endplates, viscous ground secondary vorticity (rebound).
- Diverging colour is dominated by the yaw-rate term in corners (inside faster) - physically right, note for the user.

## Next
User decides wake-rise remedy (options: no ground image for wake advection; damped image / rebound model; accept).
