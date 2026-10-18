# NOW — Agentic upgrade sandbox

## Objective
Learn agentic-AI engineering hands-on by applying it to this F1 optimal-lap
pipeline, so the weekly video process becomes more deterministic, cheaper
(tokens/time/money), and more trustworthy — with fewer correction nudges.
Learning the tools and understanding *why* they work is the primary goal;
improving the project is the vehicle.

## Rules
- This folder is a SANDBOX copy of `D:\f1_hot_lap\OPTIMAL LAP SCRIPTS` (videos excluded).
  The original is never touched by sandbox work.
- Never delete anything (move/rename instead).
- One step per session; update this file before `/clear`.
- Pipeline resume state (tracks, calibration history) lives in `NOW_pipeline_resume.md`.

## Roadmap
1. [~] Safety net — sandbox copy ✅, git init + baseline commit ✅, golden regression tests ⬜
2. [ ] Observability — run manifest per video, ccusage / Claude Code OpenTelemetry, `/retro`
3. [ ] Hooks — turn feedback memories (zoom 28, apex touch, no deletes, Baku quarantine) into enforced rules
4. [ ] `/new-track` project skill + Pydantic per-track config & manifest
5. [ ] Weekly loop rehearsal — `/grill-me` → Research/Plan/Implement → `/handoff`
6. [ ] Knowledge layer — graphify, GLOSSARY.md + ADRs, memory prune
7. [ ] Docker → GCP (Cloud Run Job + GCS + Cloud Scheduler, optional Terraform)
8. [ ] Stretch — own weekly agent with LangGraph + Langfuse + Pydantic

## Known caveats
- 3 scripts hard-code the ORIGINAL folder path (don't run from sandbox until repointed):
  `elevation_3d_toy.py`, `_open_elevation_toy.py`, `LAP COMPARISON\_template_baker.py`
- Git-ignored (re-fetchable/heavy): videos, `cache/fastf1_http_cache.sqlite`, `cache/ext/saxena_zip/*.zip`

## Next action
Step 1 remainder: golden regression tests for shipped tracks (generalise the Zandvoort bit-identical recipe).
