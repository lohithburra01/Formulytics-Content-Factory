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

## Next
Start the spec session: brainstorm the project, write `.scratch/airflow-sim/spec.md`.
