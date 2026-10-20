# Grill decisions — race-weekend system (2026-10-19/20)

Source of truth for the rebuild. Supersedes spec.md (v1, rejected: it wrapped the user's nudges instead of removing them). [2026-10-21: spec v2 = spec.md is built from this file; v1 kept as spec_v1_rejected.md]
Evidence files (evidence/ folder next to this file): retro_evidence.md, nudge_catalogue.md, variable_inventory.md.

## Objectives
1. Learn agentic engineering deeply (job: AI/agentic engineer, India + remote) — explainable in interviews.
2. Make the F1 pipeline genuinely better: line + speed graph right without user nudges.
Rule: real problem first, then the tool that fits it. Never force a tool to learn it (other pipelines exist for that).

## Evidence (why)
- 36 user nudges in past sessions. Group A (~25, computable from data we already have: speed-trace shape, lap time, apex gaps, delta) — scripts exist but never run before showing the user. Group B (line ≠ real car's line, deploy) — no data in pipeline; user judges from onboard video + own knowledge.
- 212 pipeline variables: 136 ASSUMED (no origin), 31 computed, 26 knowledge, 12 user decision, 7 measured. Many conflicts (car width 2.0/1.9/0.95, 4 edge margins, Canada defaults applied silently, zoom 18 vs 28, Sepang bat TAB path bug, brake-preservation never runs).
- Sepang anarchy: lowered downforce to hit time → line went wide (real car inside) → forced line + agent picked "other variables" to refit. Root: agent chose what to change.

## Decisions
- D1 Determinism covers EVERYTHING incl. video/render/zoom/style. Every variable has exactly one origin: MEASURED | COMPUTED | FITTED (tuned to target, labelled not-physics) | KNOWLEDGE (graph note + source) | USER DECISION (recorded + reason). Goal: all sources plugged so the run never stops; stop = safety net only.
- D2 No source possible → ask user once, record as decision, never ask again for that scope. [Narrowed by D22: values outside the 3 user outcomes (pattern, line, lap time) are recorded as decided under D22, never asked.]
- D3 Lap-time target: interim rule = user decision: FP1 −1.5..−2.0 s when FP1 exists (wins), else 2025 car +1.5..+3.0 s. Stored per weekend. [Reconfirmed by user 2026-10-21: the FP1 rule is the decided time shown in the video (D25), even when it is faster than the real pole (Singapore 2026).]
- D4 Lap-time PREDICTOR = separate parallel spec (later grill): probabilistic (median + range), features: track type, pace vs same-year average, patterns same-track-multi-year / multi-track-same-year / both, weighted; FIA regs; blind backtest on completed 2026 races; use papers/repos/transfer from similar problems.
- D5 Fitting is a fixed script, never agent choice. Each car value fitted only to the speed-graph feature it controls: braking slope→braking grip/brake model; straight peaks→drag/power/deploy cap; corner minimums→downforce/lateral grip; exit acceleration→traction/power.
- D6 User line observations = HARD constraints, direction only (corner, phase entry/apex/exit, inside/outside); optimiser computes the amount. Leftover time gap → ONE declared "time knob" (chosen by a test: least line change), labelled FITTED; gap reported per sector. Fitted values have plausible ranges; if target needs out-of-range → show conflict, user chooses. [Narrowed by D22/D24: the knob may never worsen the speed pattern; if none qualifies the gap is shown as sim-vs-FP1 on the graph, never as numbers to choose.]
- D7 Checks = features, not just correlation: per braking zone onset + decel rate, per straight peak, per corner min speed, accel-vs-speed. Start from existing gate bands (corr ≥0.95 kept), labelled user decision. These are also the fitting targets and the self-correcting loop's pass criteria (Group A loop: compare → adjust → rerun; user sees only in-tolerance results). [Narrowed by D23 + done criterion 3: gaps the loop cannot close (track-model limits, e.g. SG T1/T12) are SHOWN per corner/sector, not looped forever or hidden.]
- D8 Sensitivity scan ranks the 136 assumed values; high-impact → fitted or sourced (with citation, user approves one line each); low-impact → one table, one user approval, recorded as decisions. [Superseded by D22: no value tables to the user; one blanket decision covers them.]
- (gap, 2026-10-21) Elevation is available from position data (D9) but the track model is flat (D23); not planned.
- D9 Knowledge store = layered notes. Layers (most specific wins): regulations → season → car → driver → track (versioned per layout/year) → weekend (conditions) → session (fuel, tyres) → run (code version, output settings) + an output/video-style layer. Driver layer = measured telemetry + observed line directions only; position API data is NOT a line source (only S/F, elevation, distance axis).
- D10 Knowledge system = 4 parts, ONE store: (1) YAML notes in git = the only source of truth; (2) links written inside the notes; (3) meaning search (local sentence-transformers on GPU, rebuildable cache); (4) own local MCP server (tools: find_node, neighbours, search, add_node w/ Pydantic validation), auto-started by Claude Code via .mcp.json, no Docker/Neo4j (Neo4j swappable later behind same interface).
- D11 WEEKEND PACK: one script resolves all layers for a run into one file = every value + origin; Pydantic-validated; sim/line/render read ONLY the pack; pack committed to git = lineage record. Re-run → identical output.
- D12 The LLM = Claude Code session (no API key). Its jobs only: translate nudges → notes, source values from documents with citations, explain. Never decides a number.
- D13 Nudge flow: user says it in plain words → Claude writes note → Pydantic check → one-line confirm → git commit → re-run affected steps only.
- D14 No slash commands; user just names the track.
- D15 LangGraph = step runner with NO AI inside (resume after crash, pause for user, visible flow), called by Claude Code.
- D16 Sim refactor: reads all values from one config object (from the pack); remove globals/monkey-patching.
- D17 Guards: golden test (saved pack → identical result) in pre-commit; no-delete hook for Claude Code. Zoom/style via pack, no hook needed.
- D18 Langfuse parked (no code-side LLM calls here). Observability for Claude Code sessions: see open item.
- D19 Teaching: every built piece explained by ONE traced real example (actual text moving between parts), then user runs it. No pages, no analogies.

## Done-tonight criteria (Singapore 2026 proof run)
1. Two runs → identical output. 2. Zero ASSUMED variables. 3. Feature checks pass or gaps reported per sector. 4. Logged Singapore nudges satisfied with no new nudges. 5. Lineage pack committed. 6. Video renders with zoom/style from the pack.

## Build order (most important first)
1. Determinism core: pack + Pydantic + sim reads only pack.
2. Fitting rules + feature checks.
3. Knowledge notes seeded with Singapore nudges + MCP server.
4. LangGraph runner.
5. Lineage commit + render.

## Open
- D20 Observability: ccusage now (before/after tokens + corrections = kill test); Claude Code OpenTelemetry parked.
- Shared understanding CONFIRMED 2026-10-20. Spec v2 + tickets 01-13 written and built 2026-10-20. [2026-10-21 next: fold D22-D26 into spec v2, then tickets 14, 12, 11, 13.]

- D22 (2026-10-20, user) The user reviews ONLY two things: (1) the racing line, visually, after the first pass -> nudges; (2) the speed graph vs FP1 / real data, as a picture. Every other value = kept as is under one blanket user decision (all 39 pending_review values approved, reason prefixed "approved under D22") and never shown again. Speed-graph misses are shown as sim-vs-FP1 gaps per corner/sector on the graph, never as a list of numbers. Narrows D6 "user chooses" and D8 "one table".
- D23 (2026-10-20, user) Track model limits, so speed-graph gaps vs FP1 are expected and are not by themselves a car-tuning target: the road is built as a uniform-width band around the official shape line (not real edges), and it is 2D/flat (no elevation). Priorities stay: speed pattern + racing line.
- D24 (2026-10-20, user) Pattern first, lap time second. The car is tuned to the real speed pattern (D21); the lap time comes out of that car. If it is already inside the D3 band, no time knob is used. Otherwise the time knob may only be a candidate that does NOT make the speed pattern vs the real lap worse (knob.max_pattern_drop = 0); if none qualifies, nothing is applied and the gap is shown to the user ("pattern-matched lap = X s, band Y, pattern Z"). Replaces the D6 knob behaviour that cut P_ICE_MAX_W to 0.70x on Singapore run 2. Superclip/deployment count as part of the pattern via the speed trace.
- D25 (2026-10-21, user) The video TEXT shows the decided lap time (D3 target now; the D4 predictor later); the user speeds the upload to ~40 s, so real-time playback does not matter. The sim's job: match the FP1 speed pattern, a bit faster (pole-like). Evidence 2026 season (14 clean races, scratchpad fp1_vs_q_season.py): FP1->pole shape corr median 0.986, pole avg speed +0.6..2.9%, lap gap median 1.76 s; Singapore 2026 outlier (pole 91.373 = FP1 -0.9 s, so the D3 band 90.27-90.77 is faster than real pole). Time knob keeps D24 (never worsens pattern).
- D26 (2026-10-21, user) ORDER: finish the video workflow first (minimal user input, consistent, spec updated with D22-D25), THEN the D4 pole-time predictor. D4 addition: inputs are optional; missing inputs (e.g. no FP1 yet, pre-weekend) still give a prediction = median + range + confidence score, with less confidence the fewer inputs.
- D21 (2026-10-20) Tuning copies the speed-graph SHAPE of the 2026 FP1 lap (same car generation); lap TIME target stays D3. Supersedes the old "Do NOT recalibrate to FP1" note in cache/singapore_2026.md.
