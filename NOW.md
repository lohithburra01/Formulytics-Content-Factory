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
- Git-ignored (re-fetchable/heavy): videos, `cache/fastf1_http_cache.sqlite`, `cache/ext/saxena_zip/*.zip`,
  `cache/ext/kadiri/` (third-party clone with its own .git)
- D: drive records no file ownership → sandbox added to global git `safe.directory`.
- Many small loose git objects bloat on this drive (2.2 GB → 279 MB after `git gc`); run `git gc` after big commits.

## 2026-10-20 — REBUILD IN PROGRESS (supersedes roadmap below)
Grill + retro done. ALL decisions: `.scratch/race-weekend-flow/grill-decisions.md` (read first).
v1 renamed to `spec_v1_rejected.md` / `flow_v1_rejected.html`. **Spec v2 = `.scratch/race-weekend-flow/spec.md` (Status: ready-for-agent; seams: resolve_pack, run(pack), knowledge store API — user-approved).** `learn/` lessons = rejected format (user wants traced examples in chat).
Today's goal: Singapore 2026 thin end-to-end proof (see done criteria in grill-decisions.md).

## RESUME HERE (2026-10-23 late) - ticket 15 'any weekend' in progress
Ticket: .scratch/race-weekend-flow/issues/15-any-weekend.md (5-step plan agreed by user).
Step 1 done (0b54cb3): shared track-build settings -> weekend/notes/season/track_build_defaults_2026.yaml.
Step 2 done: track cards weekend/cards/<track>.yaml (Austin alt 171 m from airdensityonline 561 ft, length 5513).
Step 3 done: weekend/new_track.py (runner node_resolve calls ensure_notes); Austin notes generated, pack 135 values 0 ASSUMED.
  Austin choices to tune from data later: width 12 m (no width fit), grip start 1.0, inset 0 (run-off), gain cap 32.
  _sg_grip.py stays in cache/singapore (generic code; moving it would change cache keys).
Step 4 run 1 DONE (lineage fc4dfb6, log runs/austin_2026_run.log, video runs/austin_2026/video/b1177936051a5cb7/video.mp4):
  pattern 0.964 (SG 0.953); lap 96.80 s NOT in band 93.86-94.36; tuned car alone 96.19 (slower than FP1 95.86!);
  knob conflict (MU_LAT/CL reach band but worsen pattern). Loss = 1.8 s at 3900-4340 m (T12-T15): sim corner mins
  ~30 m late and 10-35 km/h slower; fitted street_grip_k 0.676 (street-only factor, range 0.3-1.0, now cuts a permanent track).
  User review of run 1 (2026-10-23, angry: 're-debugging the same things after the spec'):
   line: T1 (~610 m, video 9 s) sim touches apex, real does NOT; T12-T15 (3780-4440 m, video 1:02+) sim hugs inside,
   real goes in-out-in-out-in (wider). Energy: sim clip zones do not match FP1 -> spec D28 + ticket 17.
  NEW PROCESS (spec D27, ticket 16): review stage writes line.svg + speed.svg and the run STOPS before the video;
   user OKs -> `python -m weekend.approve <track> <year>` -> rerun renders video. Show the user the SVGs, not the video.
  User (2nd, angrier): I showed run-1 SVGs and asked them to repeat line comments already given -> NEVER re-ask;
   convert given comments into rules immediately. Whole-lap correlation 0.964 is meaningless to the user.
  Done: line rules note be0b433 (T1 646 apex outside; 3735 exit/3963 entry+exit/4223 entry outside);
   ticket 17 code 5d6b7a9: sim CLIP_ZONES from FP1 (zone flush to sim braking start, FP1 rate), grip fixed 1.0
   off-street (fit.range collapsed), checks all_ok now needs: no corner >10 km/h off, every section RMSE<=8 km/h
   (features.segment_shapes), FP1 clip zones matched (features.clip_match). Run-1 lap fails 9/10 sections.
  Austin run 2 DONE (log runs/austin_2026_run2.log, stopped at review, not shown as a result): lap 96.35, 9/10 sections
   fail, clip zones not matched, rules T12-exit + 3963-exit unmet (gap 0.17/0.16 m). Diagnosis (scratchpad align_diag.py,
   radius_diag.py): (a) sim corners sit +16..+44 m later than FP1's on the distance axis -> checks must align on corners;
   (b) fast esses ~1300-1400 m and T19 ~4900 m: sim line radius ~1.5x what FP1 speed implies (sim 298 vs 241 km/h);
   (c) braking before T1/T12: sim 32-53 km/h slower = brakes early. Was: NEXT: read checks; if sections/clips fail, fix BEFORE
   showing the user; show SVGs only when checks are green or with a clear per-section gap list.

## RESUME HERE (2026-10-23, Austin FP1 weekend)
User order (2026-10-23): "follow the spec and finish the tickets first" -> THEN make it work for any weekend.
Done 2026-10-23 (commit baad75d): spec D21-D26 folded in; ticket 14 video text = decided time (1:30.524 shown);
ticket 12 guards (pre-commit golden replay via core.hooksPath weekend/hooks; no-delete PreToolUse hook);
ticket 11 nudge flow (python -m weekend.nudge preview|apply <note.json> <track> <year>); stage keys include own source file.
Pack: 143 values, 0 ASSUMED, 0 pending_review.
Ticket 13 DONE 2026-10-23: two runs byte-identical (incl. video), lineage 5fbb42e. Tickets 01-14 done/closed.
Austin data FETCHED 21:00: reference_2025_austin_q.csv (VER pole 92.510), cache/austin/path_samples.json (top-10),
reference_2026_austin_fp1.csv (#3 95.860, sectors 25.634/38.237/31.989), cache/austin/fetch_facts.json.
Known: no-delete hook false-positives on command TEXT that quotes 'rm'/'Remove-Item' -> put such text in a script file.
NEXT after 13 (not in spec yet = new ticket 15 "any weekend"): `python -m weekend <track> <year>` must create
a new track's notes itself. Pieces already built: weekend/fetch_weekend.py (waits out OpenF1 401, fetches last-year Q
lap + top-10 path samples + this-year FP1 lap + facts -> cache/<track>/fetch_facts.json; running for Austin:
runs/austin_fetch.log), track stage works without an SVG. Austin = COTA 5513 m, anticlockwise (mirror_x true).
Wikimedia Austin_circuit.svg is unusable (multi-path) -> cache/austin/dl/_unused_*.
Gap noticed: car_and_line needs an FP1 shape ref (pre-FP1 branch has none) - fine for post-FP1 runs.

## Next action (old, 2026-10-20 late)
Goal (user): the WHOLE pipeline finished, tested on Singapore 2026. Plan = `.scratch/race-weekend-flow/spec.md`
+ tickets `.scratch/race-weekend-flow/issues/01-13` (each file has a Status line - read those first).
Pipeline map (how the old bat works): `.scratch/race-weekend-flow/evidence/pipeline_map_singapore.md`.

What exists (`weekend/`): notes (YAML layers) -> `python -m weekend.resolve singapore 2026` -> pack (142 values,
all with origin) -> stages in clean child processes, cached per input key under `runs/<track>_<year>/<stage>/<key>/`:
track -> base_line -> refs -> car_and_line (tune <-> line rounds) -> time_knob -> final -> checks -> video.
One stage: `python -m weekend.pipeline <stage> weekend/packs/singapore_2026.json`. Whole thing: `python -m weekend singapore 2026` (LangGraph runner, commits lineage).
Verified: track + base_line byte-identical to shipped; ported final step byte-identical; target band 90.274-90.774 s.

Session 2026-10-20 night: brake_preserve bug fixed (run 1 invalid). Run 2 = lap 90.463 in band, BUT time knob cut P_ICE_MAX_W to 0.70x (edge of +-30% span = should be a conflict per D6); corners off vs FP1: T1 +38, T8 +18, T11 +19, T12 -38 km/h; gates fail: GAIN median 28.9 (>28), DROP median 57 (>52).
D22 (user reviews ONLY line visually + speed graph vs FP1; all other values blanket-approved, 0 pending_review) and D23 (track = uniform-width band, 2D flat -> FP1 gaps expected) recorded in grill-decisions.md.
Cache key now hashes only value + file sha (note text ignored; test added). Fast tests 19 pass / 1 skip.
Run 3 done: final lap.csv byte-identical to run 2 (done criterion 1 MET). Fixed null-value KeyError (video.max_seconds) in pipeline.py. Video: runs/singapore_2026/video/b2a013318d106f57/video.mp4 (zoom 28, full lap).

D24 done (pattern first; knob may not worsen FP1 pattern; knob.max_pattern_drop=0). Run 4: tuned car alone = 89.288 s (1.0 s faster than band); power-cut knob REJECTED (worsened pattern); chosen knob CL_CORNER_M2 x0.92 -> lap 90.464 in band, pattern 0.953 (old shipped 0.950). Superclip 3 zones / 4.2 s (old 2 / 1.8). Gates still fail: GAIN median 31.3, DROP median 56.8. Corners off: T1 +29, T3 -12, T8 +12, T11 +17, T12 -44. Video: runs/singapore_2026/video/9eaca95754a7b15a/video.mp4

2026-10-21: D25 (video text shows decided time, user speeds to 40 s; sim = FP1 pattern a bit faster) + D26 (finish video workflow FIRST, then D4 predictor with optional inputs + confidence) in grill-decisions.md. Season FP1-vs-pole study: scratchpad fp1_vs_q_season.py (shape 0.986 median, gap 1.76 s). Pole 2026 SG = 91.373 s (F1_Pipeline_Assets/exports/reference_2026_singapore_q.csv).
FINISH PLAN (user agreed 2026-10-21; grill contradictions D2/D6/D7/D8 annotated, lap rule = FP1 reconfirmed). START HERE NEXT SESSION with step 1: spec v2 update w/ D22-D26 -> new ticket 14 video decided-time label -> ticket 12 guards -> ticket 11 nudge flow -> ticket 13 proof run + commit -> then predictor grill.

To do next, in order:
1. User re-checks line in run 4 video (downforce cut -8% moved the line ~0.5 m) and judges pattern result.
2. Read the checks report (runs/singapore_2026/checks/*/report.json) when run 1 finishes; then video stage.
3. `python -m weekend.golden record runs/singapore_2026 weekend/golden/singapore_2026_chain` -> golden replay test.
4. Ticket 12: pre-commit (golden replay + fast tests) and the no-delete hook (use the update-config skill).
5. Ticket 11: nudge flow; Ticket 13: two full runs identical + all 6 done criteria.
6. Show the user ONE review table: every value with pending_review: true (grep notes) + tuning conflicts
   (low-speed braking -38%, mid-speed accel +30-60%, corners 1/7/8/11 +16..35 km/h and 12 -22 vs FP1 = track/line, not car).
Decisions made tonight: D21 (tune to FP1 shape) in grill-decisions.md; brake preservation tested and left off (COMPUTED note);
rejected SG_MU_SCALE knob removed. Nothing committed yet (lineage commit happens at the end of a runner run).

## Next action (old)
Step 1 remainder: golden regression tests for shipped tracks (generalise the Zandvoort bit-identical recipe).
