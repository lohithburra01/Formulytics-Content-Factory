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

## Next
User reviews the v6 frames FIRST and gives feedback; only then read/judge frames. Then iterate the look toward usable.
