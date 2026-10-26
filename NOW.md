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

## Next
User decides: next spike (settled wake + top-down picture + Ahmed-body drag check) or other direction.
