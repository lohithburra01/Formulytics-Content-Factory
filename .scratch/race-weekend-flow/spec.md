# Spec v2: Race-weekend system — every value has one origin, the run never needs a nudge

Status: ready-for-agent
Source: grill-decisions.md (D1–D26; D1–D20 confirmed 2026-10-20, D21–D26 added 2026-10-20/21). Evidence: evidence/ (nudge_catalogue, retro_evidence, variable_inventory).
Supersedes: spec_v1_rejected.md (it wrapped the user's nudges in approval steps instead of removing them).
Proof weekend: Singapore 2026.
Test seams (user-approved 2026-10-20): (1) pack resolver, (2) run-from-pack, (3) knowledge store API.

## Amendments D21–D26 (2026-10-20/21, user) — these win over anything below

- **D21 Tune to the FP1 shape.** The car is fitted to the speed-graph SHAPE of this year's FP1 lap (same car generation). Before FP1 exists there is no shape reference.
- **D22 The user judges three things only:** the racing line (visually, from the video, gives nudges), the speed graph vs FP1 (as a picture), and the lap time vs the decided band. Every other value is approved under one blanket decision and is never shown again. This replaces "user chooses" in stories 20/36/37 and the review table of the sensitivity scan.
- **D23 Track-model limits.** The road is a uniform-width band around the official path, flat (2D). Speed gaps vs FP1 caused by that are expected, shown per corner/sector, and not chased by car tuning.
- **D24 Pattern first, lap time second.** The lap time comes out of the pattern-tuned car. If it is in the band, no time knob. Otherwise the knob may only be a candidate that does not make the speed pattern worse (knob.max_pattern_drop = 0). If none qualifies, nothing is applied and the gap is shown ("pattern-matched lap = X s, band Y, pattern Z"). Replaces stories 32/33's "least line change" as the only rule.
- **D25 Video text = decided lap time** (the D3 target now; the D4 predictor later). The user speeds the upload to ~40 s, so real-time playback does not matter.
- **D26 Order.** Finish this video workflow first, then the D4 predictor (separate spec; inputs optional, prediction = median + range + confidence).

## Problem Statement

I make an optimal-lap video each race weekend. Over past sessions I corrected the agent 36 times. About 25 of those corrections were about things the pipeline could have computed itself from data it already had (speed-trace shape, lap time, apex gaps, delta). The check scripts existed, but nobody ran them before showing me the result. The rest were about the line not matching the real car's line, which the pipeline has no data for. Only I know it, from onboard video and what I know about F1.

Underneath that, the pipeline has 212 variables. 136 of them have no recorded origin. The same quantity has different values in different places (car width 2.0 / 1.9 / 0.95, four different edge margins, zoom 18 vs 28). Canada defaults get applied silently to other tracks. Env-vars and monkey-patched globals change the sim behind its back. Brake preservation never actually runs. Because nothing pins values down, the agent picks which values to change. At Sepang, I gave it a lap-time target. It lowered downforce, which pushed the line wide when the real car ran inside. Then it forced the line and refitted "other variables". Each weekend's run comes out differently. I can't tell why, and I can't reproduce it.

I want to stop nudging, and I want to be able to explain in an interview how the system works and why each part exists.

## Solution

Every value the pipeline uses has exactly one recorded origin: MEASURED, COMPUTED, FITTED, KNOWLEDGE or USER DECISION. Values come from layered notes in git. A single script resolves them into one **Weekend Pack** per run. The sim, line optimiser and renderer read only the pack. A fixed fitting script, never the agent, tunes each car value against the speed-graph feature that value controls. Feature checks (braking zones, straight peaks, corner minimums, acceleration vs speed) run before I see anything. Results that fail are corrected in a loop or reported per sector. My line observations become hard direction-only constraints. When a value can't be sourced, I'm asked once and my answer is recorded. I'm never asked again for that scope.

From my side, a weekend looks like this. I open Claude Code and name the track. A step runner builds the pack, fits, checks, optimises the line, simulates and renders. It pauses only for a question that has no source yet. When I see a result, it is already within tolerance, or it comes with a per-sector gap report. If I notice something, I say it in plain words. Claude turns it into a note, validates it, shows me one confirmation line, commits it, and re-runs only the affected steps. Two runs from the same pack give identical output, including the video. The pack is committed as the lineage record.

## User Stories

### Origins and determinism
1. As the video maker, I want every variable in a run to carry exactly one origin (MEASURED, COMPUTED, FITTED, KNOWLEDGE, USER DECISION), so that I can say where any number came from.
2. As the video maker, I want a run to refuse to start if any value is ASSUMED or has no origin, so that silent defaults can never return.
3. As the video maker, I want the video settings (zoom, style, resolution, overlays) to be pack values with origins too, so that render output is as deterministic as the physics.
4. As the video maker, I want two runs from the same pack to produce identical outputs (line, speed trace, lap time, video settings), so that I can trust the result.
5. As the video maker, I want conflicting values for the same quantity (e.g. car width) to resolve to one value through layer precedence, so that the conflicts listed in the variable inventory disappear.
6. As the video maker, I want no per-track defaults borrowed from another track (e.g. Canada) unless a note says so explicitly, so that tracks stop contaminating each other.
7. As the video maker, I want env-var and monkey-patch overrides removed from the sim, so that nothing changes the physics outside the pack.
8. As the video maker, I want FITTED values labelled as "fitted, not physics", so that I never mistake a fitted knob for a measured fact.
9. As the video maker, I want KNOWLEDGE values to carry a source (document, URL, regulation article) shown in the notes, so that every knowledge claim is traceable.
10. As the video maker, I want USER DECISION values to carry my reason and the date, so that I remember why I chose them.

### Asking once
11. As the video maker, I want the run to ask me only when a value has no possible source, so that I'm interrupted only when it's genuinely necessary.
12. As the video maker, I want my answer recorded as a USER DECISION for its scope (season, track, weekend…), so that I'm never asked the same question again for that scope.
13. As the video maker, I want the pause-for-question to be the only reason a run stops other than a safety failure, so that the run otherwise completes on its own.

### Lap-time target
14. As the video maker, I want the lap-time target to follow the interim rule (FP1 −1.5 to −2.0 s when FP1 exists, else 2025 car +1.5 to +3.0 s), so that the target is computed, not argued about.
15. As the video maker, I want the FP1-based target to win whenever FP1 exists, so that the freshest data takes priority.
16. As the video maker, I want the chosen target and its rule stored per weekend, so that I can see later which rule was applied.

### Fitting
17. As the video maker, I want fitting done by a fixed script, never by the agent choosing which value to change, so that Sepang-style "pick other variables" drift can't happen.
18. As the video maker, I want each car value fitted only to the speed-graph feature it controls (braking slope → braking grip/brake model; straight peaks → drag/power/deploy cap; corner minimums → downforce/lateral grip; exit acceleration → traction/power), so that fitting one feature can't silently wreck another.
19. As the video maker, I want each fitted value to have a plausible range, so that the fit can't produce nonsense physics.
20. [D22/D24: shown as sim-vs-FP1 gap on the graph, not a choice of numbers] As the video maker, I want an out-of-range requirement shown as a conflict, with the choice left to me, so that the system doesn't quietly bend physics to hit a target.

### Feature checks and the correction loop
21. As the video maker, I want per-braking-zone checks (onset point and deceleration rate) against reference telemetry, so that braking-shape errors are caught before I look.
22. As the video maker, I want per-straight peak-speed checks, so that the drag/power balance is verified.
23. As the video maker, I want per-corner minimum-speed checks, so that grip and downforce are verified corner by corner.
24. As the video maker, I want acceleration-vs-speed checks, so that traction and power on exits are verified.
25. As the video maker, I want the existing gate bands (correlation ≥ 0.95 kept) used as the starting tolerances, labelled as my decision, so that current practice carries over and is recorded.
26. As the video maker, I want the feature checks to be the same things the fitting script targets, so that "fit" and "pass" mean the same thing.
27. As the video maker, I want the pipeline to compare, adjust and rerun on its own until the checks pass, so that I only ever see in-tolerance results.
28. As the video maker, I want any remaining gap reported per sector, so that I know exactly where the sim and reality differ.
29. As the video maker, I want apex-touch checks run automatically, so that "the line isn't touching the apexes" never needs saying again.

### Line constraints
30. As the video maker, I want my line observations stored as hard constraints with direction only (corner, phase entry/apex/exit, inside/outside), so that the optimiser respects what I saw without me guessing metres.
31. As the video maker, I want the optimiser to compute the amount for each constraint, so that the physics decides the magnitude.
32. [D24: knob may never worsen the pattern] As the video maker, I want any time left over after the line constraints to go into ONE declared time knob, labelled FITTED, so that hitting the target never reshapes the line.
33. As the video maker, I want the time knob chosen by a test (the one that changes the line least), so that the choice is evidence-based and repeatable.
34. As the video maker, I want position-API data never used as a line source (only for start/finish, elevation and the distance axis), so that map-matched data doesn't masquerade as driver lines.

### Sensitivity scan
35. [D22: superseded by the blanket decision] As the video maker, I want a sensitivity scan that ranks the 136 assumed values by impact on the outputs, so that effort goes where it matters.
36. As the video maker, I want high-impact values turned into FITTED or sourced values (with a citation I approve in one line each), so that the important numbers are grounded.
37. As the video maker, I want low-impact values approved in one table with one approval and recorded as decisions, so that clearing them doesn't cost a session.

### Knowledge store
38. As the video maker, I want notes organised in layers (regulations → season → car → driver → track per layout/year → weekend conditions → session fuel/tyres → run code version/output settings, plus an output/video-style layer), with the most specific layer winning, so that one value can be overridden precisely where it differs.
39. As the video maker, I want the driver layer to hold only measured telemetry and observed line directions, so that driver "character" isn't invented.
40. As the video maker, I want YAML notes in git to be the only source of truth, so that history, diff and rollback come for free.
41. As the video maker, I want links between notes written inside the notes, so that the graph lives in the same files as the facts.
42. As the video maker, I want meaning-based search over the notes (local sentence-transformers on my GPU, as a cache I can rebuild), so that Claude finds the relevant note without me naming it.
43. As the video maker, I want a local MCP server exposing find_node, neighbours, search and add_node, so that Claude Code reads and writes knowledge through one validated interface.
44. As the video maker, I want add_node to validate every note with Pydantic before it's written, so that malformed knowledge never enters the store.
45. As the video maker, I want the MCP server started automatically by Claude Code from the project config, with no Docker or Neo4j, so that there's nothing to run by hand.
46. As the video maker, I want the store interface kept narrow enough that Neo4j could replace it later, so that I can upgrade without rewriting callers.

### Weekend Pack
47. As the video maker, I want one script to resolve all layers for a run into one Weekend Pack file listing every value and its origin, so that the run's whole input is in one place.
48. As the video maker, I want the pack validated by Pydantic, so that a missing or mistyped value fails at resolve time, not in the video.
49. As the video maker, I want the sim, line optimiser and renderer to read only the pack, so that nothing else can influence a run.
50. As the video maker, I want the pack committed to git as the run's lineage record, so that any past video can be reproduced and explained.

### Nudge flow
51. As the video maker, I want to state a correction in plain words, so that I never have to learn a format or slash command.
52. As the video maker, I want Claude to turn my words into a note, check it with Pydantic, and show me one confirmation line, so that I approve the exact recorded meaning.
53. As the video maker, I want the confirmed note committed to git, so that each correction is permanent and versioned.
54. As the video maker, I want only the steps affected by the new note re-run, so that a correction costs minutes, not a full rebuild.
55. As the video maker, I want to start a weekend by just naming the track, with no slash commands, so that the entry point is trivial.

### Role of the LLM
56. As the video maker, I want Claude's jobs limited to translating nudges into notes, sourcing values from documents with citations, and explaining, so that the LLM never decides a number.
57. As the video maker, I want this to work in a Claude Code session with no API key, so that it runs on my existing subscription.

### Step runner
58. As the video maker, I want a LangGraph step runner with no AI inside, so that the flow is visible and deterministic.
59. As the video maker, I want the runner to resume after a crash from the last completed step, so that a failure late in the run doesn't cost the earlier steps.
60. As the video maker, I want the runner to pause for my answer and resume after it, so that ask-once questions fit into the flow.
61. As the video maker, I want Claude Code to call the runner, not re-implement it turn by turn, so that the flow is code, not chat.

### Guards
62. As the video maker, I want a golden test (saved pack → identical result) in pre-commit, so that a code change that alters results can't be committed silently.
63. As the video maker, I want a Claude Code hook that blocks delete operations, so that "never delete anything" is enforced rather than remembered.

### Observability and learning
64. As the video maker, I want token usage and correction counts recorded before and after (ccusage), so that I can prove whether the system actually reduced nudges and cost.
65. As the video maker, I want each built piece explained with ONE traced real example (the actual text moving between parts), so that I understand it well enough to explain it in an interview.
66. As the video maker, I want to run each piece myself after its traced example, so that I learn by doing.

### Singapore 2026 proof
67. As the video maker, I want a Singapore 2026 run where two runs give identical output, so that determinism is proven on a real track.
68. As the video maker, I want that run to have zero ASSUMED variables, so that the origin rule is proven.
69. As the video maker, I want its feature checks to pass, or report gaps per sector, so that verification is proven.
70. As the video maker, I want every logged Singapore nudge (apex touch, T8→T9 wide entry, FP1 pace, geometry spacing) satisfied with no new nudges, so that the system is shown to remove nudges, not just record them.
71. As the video maker, I want the Singapore lineage pack committed, so that the proof is reproducible.
72. As the video maker, I want the Singapore video rendered with zoom and style from the pack, so that the render is shown to be covered by determinism too.
73. (D25) As the video maker, I want the video text to show the decided lap time (target band centre), not the sim's raw lap, so that the video states the number I stand behind.

## Implementation Decisions

**Build order** (most important first; each is a vertical slice that must work before the next starts):
1. Determinism core: Weekend Pack schema + resolver + sim reading only the pack.
2. Fitting rules + feature checks.
3. Knowledge notes seeded with the Singapore nudges + MCP server.
4. LangGraph step runner.
5. Lineage commit + render from the pack.

**Origin model.** One enum of origins: MEASURED, COMPUTED, FITTED, KNOWLEDGE, USER_DECISION. ASSUMED is not a valid origin in a pack; it exists only as a migration label in the inventory. Each value record holds: name, value, unit, origin, plus origin-specific fields. KNOWLEDGE needs a source/citation. USER_DECISION needs a reason, date and scope. FITTED needs a target feature, a plausible range and the fitting-script version. MEASURED and COMPUTED need the data file or computation that produced them.

**Knowledge notes (store).** YAML files in git, one node per file, grouped by layer. Layers in precedence order (least to most specific): regulations, season, car, driver, track (keyed by layout + year), weekend, session, run, plus an output/video-style layer. A node declares its layer, scope keys, values with origins, and links to other nodes. Pydantic models define the note schema. An invalid note is never written.

**Knowledge store API (seam 3).** A plain Python module exposing `find_node`, `neighbours`, `search` and `add_node`. `search` uses local sentence-transformers embeddings on GPU. The embeddings are a cache that can be rebuilt from the YAML, are never committed as truth, and are git-ignored. The local MCP server is a thin wrapper over these same functions, registered in the project MCP config so Claude Code starts it automatically. No Docker, no Neo4j. The interface is kept narrow so a graph DB could sit behind it later.

**Pack resolver (seam 1).** `resolve_pack(notes, weekend) → WeekendPack`. It is a pure function: it collects every node in scope for the weekend, and the most specific layer wins per value. Output is one Pydantic-validated file holding every value with its origin and the layer it came from. A value with no origin in any layer is not a failure. It becomes a **question**: the resolver returns the unresolved names. The runner asks the user once and records the answer as a USER_DECISION note at the stated scope. The resolver then runs again.

**Run-from-pack (seam 2).** `run(pack) → RunResult`. RunResult contains the racing line, speed trace, lap time, fitted values, the per-feature check report with per-sector gaps, and resolved video settings. Nothing outside the pack affects the result.

**Sim refactor.** The 2026 sim takes one config object built from the pack. Module globals that act as config (mass, aero, mu, banking, etc.), env-var reads (e.g. line wobble, grip stencil) and monkey-patching are removed. Existing per-function sim tests stay where they still apply, but they are not the new contract. Brake preservation is either wired in properly or recorded as off (USER_DECISION). It must not be silently inert.

**Lap-time target.** This is a COMPUTED value from the interim rule: FP1 −1.5..−2.0 s if FP1 exists (wins), else 2025 car +1.5..+3.0 s. The rule itself is a USER_DECISION note at season scope. The resolved target and the branch taken are stored in the weekend layer.

**Fitting script.** A fixed mapping from car value to the feature it controls:
- braking slope → braking grip / brake model
- straight peaks → drag / power / deploy cap
- corner minimums → downforce / lateral grip
- exit acceleration → traction / power

Each fitted value is bounded by a plausible range taken from notes. If the target needs a value out of range, the result is a **conflict** surfaced to the user, not a clamp or a substitution. The agent has no path to choose which values to fit.

**Feature checks.** Per braking zone: onset distance and deceleration rate. Per straight: peak speed. Per corner: minimum speed. Plus acceleration vs speed. Reference comes from fetched telemetry (FP1, or 2025 Q). Starting tolerances come from the existing gate bands (keeping correlation ≥ 0.95), recorded as a USER_DECISION. The same features are the fitting targets and the pass criteria of the correction loop (compare → adjust → rerun). Apex-touch is checked on every line. The existing check scripts (gate, overlay, rate-vs-speed, corner compare, apex gaps, crossing scan) are the prior art to fold in.

**Line constraints.** A constraint is (corner, phase ∈ {entry, apex, exit}, side ∈ {inside, outside}). Constraints are stored in the driver/track/weekend layers and passed to the optimiser as hard constraints. The optimiser computes the magnitude. After the constraints, the remaining time gap goes into exactly one declared **time knob** (FITTED). The knob is chosen by a test: candidate knobs are ranked by how much the line moves, and the least-moving one is picked. The gap is reported per sector. Position-API data is used only for start/finish, elevation and the distance axis.

**Sensitivity scan.** A script perturbs each currently ASSUMED value within a stated band and ranks them by effect on lap time and feature checks. High-impact values become FITTED, or sourced KNOWLEDGE, with the user approving the citation in one line each. Low-impact values are approved in one table and recorded as USER_DECISIONs. Zero ASSUMED is the exit condition.

**Step runner.** LangGraph graph with nodes resolve → (ask) → fit/check loop → line → sim → render → lineage. It has no LLM nodes. Checkpointing allows resume after a crash. An interrupt node handles ask-once questions. Claude Code invokes the runner and does not reimplement its steps. A note change re-runs only the steps downstream of the changed values.

**LLM boundary.** Claude Code (subscription, no API key) translates plain-words nudges into notes, sources values from documents with citations, and explains. It never writes a number into the pack except through a validated note the user has confirmed in one line. Langfuse is parked, because there are no code-side LLM calls.

**Entry point.** The user names the track in plain words. There are no slash commands.

**Guards.** Pre-commit runs the golden test: the committed Singapore pack must reproduce the committed result exactly. A Claude Code hook blocks delete operations (rename/move only). Zoom and style need no hook, because they are pack values.

**Lineage.** Each completed run commits its pack (and result summary) to git.

**Observability.** ccusage before/after numbers (tokens, correction count) are recorded as the system's kill test. Claude Code OpenTelemetry is parked.

**Teaching (D19).** Each slice ships with one traced real example: the actual text and values moving between parts, shown in chat, followed by the user running it. No lesson pages, no analogies.

## Testing Decisions

- **Good test** = drives a seam with real inputs and checks external results only: the pack contents, the run result, the store's returned nodes. No assertions on sim internals, private helpers or call order.
- **Seam 1, pack resolver.** Fixture note trees cover: precedence (the same value at track and weekend layers, weekend wins); every value carries one origin; an ASSUMED or origin-less value produces a question, never a silent default; Pydantic rejects a KNOWLEDGE value without a source, a USER_DECISION without a reason, and a FITTED value without a range; no cross-track leakage (a Canada note never resolves into a Singapore pack); the lap-time target picks the FP1 branch when FP1 exists and the 2025 branch otherwise.
- **Seam 2, run-from-pack.** Golden test: the saved Singapore 2026 pack must give a byte-identical RunResult (line, trace, lap time, fitted values, check report, video settings), and it runs in pre-commit. Determinism test: two consecutive runs give identical output. Fitting test: change one feature target and only its mapped car value moves. Out-of-range test: the result is a conflict, not a clamped value. Line-constraint test: a T8→T9 "entry, outside" constraint is satisfied, and the time gap lands in the single declared knob. Feature-check test: every braking zone, straight and corner appears in the report with pass/fail or a per-sector gap. Runner test: kill the run mid-way and resume from the checkpoint gives the same result; a pause for a question resumes after the answer.
- **Seam 3, knowledge store.** `add_node` rejects invalid notes and writes valid ones as YAML. `find_node` and `neighbours` follow the links written inside the notes. `search` returns the right Singapore nudge note for a plain-words query. Rebuilding the search cache from YAML gives the same results. The MCP server is not tested separately (thin wrapper).
- **Prior art.** The existing pytest suite (physics sim, outline geometry, svg parser, banking, transfer) shows the style and conftest setup. The Zandvoort bit-identical recipe in the pipeline resume notes is the model for the golden test. The existing gate and check scripts provide the feature definitions and tolerances.

## Out of Scope

- **Lap-time predictor** (D4): a probabilistic model with backtesting is a separate spec after its own grill. This spec uses only the interim target rule.
- Langfuse and any code-side LLM calls; Claude Code OpenTelemetry.
- Neo4j / Docker / GCP deployment.
- Slash commands or project skills as the entry point.
- Migrating every past track. Only Singapore 2026 is the proof. Other tracks follow once the core works.
- Driver-comparison / lap-comparison videos (the LAP COMPARISON tooling), except where they share the pack.
- Inferring driver lines from position data.
- Touching the original (non-sandbox) folder.

## Further Notes

- **Done criteria for the Singapore 2026 proof:** (1) two runs give identical output; (2) zero ASSUMED variables; (3) feature checks pass or gaps are reported per sector; (4) the logged Singapore nudges are satisfied with no new nudges; (5) the lineage pack is committed; (6) the video renders with zoom and style from the pack, and its lap-time text shows the decided time (D25).
- The Singapore nudges to seed as notes (from the nudge catalogue): apex touch (#25); T8→T9 wide entry touching the far side, from the RUS 2025 onboard (#26, #29); FP1 pace gap with T1/T5 speed mismatch (#30); official-path geometry instead of SVG spacing (#28); street-grip value 0.723 (to be re-labelled with its true origin).
- Three scripts hard-code the original folder path. They must be repointed before they're used from the sandbox.
- Never delete: retired files are renamed or moved (e.g. spec_v1_rejected.md, flow_v1_rejected.html).
- Next: /to-tickets from this spec, following the build order above.
