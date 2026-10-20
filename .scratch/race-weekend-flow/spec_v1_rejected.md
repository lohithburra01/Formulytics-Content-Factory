# Spec: Race-weekend flow — from "open Claude" to the optimal-lap video

Status: SUPERSEDED (rejected by user 2026-10-20) — see grill-decisions.md
Test weekend: Austin (United States GP), 2026-10-23..25
Seams: proposed below — awaiting user OK

## Problem Statement

Every race weekend I make an optimal-lap video by chatting with an AI agent. The chat has no fixed shape, so the agent is inconsistent: it forgets rules, invents physics, edits the engine, renders at the wrong zoom, and claims "done" without checking. Over the last 13 sessions I corrected it about 53 times, sessions grew to hundreds of millions of tokens, and I tunnel with the agent until neither of us knows what is what. The pipeline itself has drifted into ~120 per-track scripts, 6 simulators and 3 optimiser copies that reach into each other's internals, so changing one part (e.g. the line optimiser or the car model) breaks others silently.

I cannot make the AI consistent. I need the *process around it* to be consistent, and I need to understand why each part exists — while still learning the standard agentic-engineering tools (Pydantic, pytest/pre-commit, Claude Code hooks, LangGraph, Langfuse).

## Solution

A fixed, versioned weekend flow where code does everything code can do, the AI is used only for judgment calls, every AI judgment is checked against data before it is trusted, rules are enforced by the machine instead of remembered, and every decision is recorded.

From my side it looks like this:

1. **Resume** — I open Claude. It reads a small map index and this weekend's node only, and tells me: track, current stage, last decision. No history replay.
2. **Fetch** [code] — reference data (2025 Q, 2026 practice) for the track.
3. **Track** [code + me ✋] — geometry from SVG; I approve one picture of the track shape.
4. **Racing line** [code] — optimiser writes the racing-line plug file. ⛔ Auto-check: on track, touches every apex.
5. **Car setup** [AI judgment + check + me ✋] — the only creative step. The AI proposes knobs, each with value, allowed range and source. ⛔ Rejected automatically if a source or range is missing. I approve.
6. **Sim** [code] — lap time and speed trace. ⛔ Auto-check: gate vs practice data; engine still reproduces shipped laps.
7. **Preview** [code + me ✋] — short low-res render; I say "looks right".
8. **Render** [code] — full video. ⛔ Enforced: zoom 28, no deletions.
9. **Record** [code] — decisions and numbers saved to the weekend node, committed to git.

I steer at exactly three ✋ points. Everything else either runs or blocks by itself (⛔).

## User Stories

1. As the video maker, I want Claude to resume from a small map index plus the current weekend node, so that a new session costs little and never replays history.
2. As the video maker, I want Claude to state the track, current stage and last decision at the start, so that I know where we are before anything runs.
3. As the video maker, I want the weekend to always follow the same ordered stages, so that the method stops changing every weekend.
4. As the video maker, I want each stage marked as code, AI judgment, or my approval, so that I know who decides what.
5. As the video maker, I want deterministic stages (fetch, geometry, line, sim, render) to run without the AI improvising, so that they behave identically every weekend.
6. As the video maker, I want the AI used only at the car-setup judgment step, so that creativity is confined to where it is needed.
7. As the video maker, I want every car-setup knob to carry a value, an allowed range and a cited source (telemetry file, FIA document or peer-reviewed paper), so that invented physics is rejected automatically.
8. As the video maker, I want a car setup without sources to fail validation before the sim runs, so that I never discover fake physics after a render.
9. As the video maker, I want the racing line passed between stages only through one fixed-shape plug file, so that I can swap the optimiser algorithm without breaking the sim, calibration or renderer.
10. As the video maker, I want the car setup passed only through one fixed-shape setup file, so that I can change the car model without monkey-patching globals.
11. As the video maker, I want the plug files validated at every stage boundary, so that a wrong output fails where it is produced, not three stages later in the video.
12. As the video maker, I want the line checked automatically for apex touch and staying on track, so that I stop correcting "the line is not touching the apexes".
13. As the video maker, I want the sim checked automatically against practice data (the gate), so that a bad lap blocks the pipeline instead of printing a warning.
14. As the video maker, I want a golden regression test proving the engine still reproduces shipped laps bit-for-bit, so that an agent editing the engine is caught immediately.
15. As the video maker, I want the existing test suite to run automatically before every commit, so that broken code cannot be committed.
16. As the video maker, I want renders without zoom 28 blocked by a hook, so that I never repeat the zoom correction.
17. As the video maker, I want delete commands blocked by the agent harness, so that "never delete anything" is enforced, not remembered.
18. As the video maker, I want a short low-res preview before the full render, so that a wrong video costs seconds, not a long render.
19. As the video maker, I want long jobs to run in the background without sleep-poll loops, so that sessions stay fast and cheap.
20. As the video maker, I want exactly three approval points (track shape, car setup, preview), so that I steer briefly and do not tunnel.
21. As the video maker, I want the flow to pause at each approval point and resume after my answer, so that collaboration lives in a framework rather than a chat.
22. As the video maker, I want every decision recorded with what was chosen, the alternatives and why, so that wrong turns stay visible later.
23. As the video maker, I want the weekend record committed to git, so that knowledge is replaced and versioned instead of piled up.
24. As the video maker, I want the map to be a small index pointing to small nodes, so that the agent opens only what it needs.
25. As the video maker, I want a check-in at the end of each piece of work showing the map with "you are here", so that neither of us drifts from the goal.
26. As the video maker, I want each check-in to include one line on "things you might not know you are missing", so that unknown unknowns surface early.
27. As the video maker, I want unfamiliar areas researched from primary sources before building, so that the agent does not guess.
28. As the video maker, I want the current version of each stage named explicitly and legacy versions archived (renamed, never deleted), so that the agent never picks the wrong file.
29. As a learner, I want each tool introduced by what it is, which retro problem it fixes and how it works, so that I understand why, not just how.
30. As a learner, I want to run each new tool myself and see it reject something bad, so that I trust it from evidence.
31. As a learner, I want Pydantic, pytest/pre-commit, Claude Code hooks and LangGraph each applied to a real Austin stage, so that I learn on real work.
32. As a learner, I want every AI call recorded and inspectable (Langfuse), so that I can see what the agent did and what it cost.
33. As a job seeker, I want the finished flow to be explainable as "how I made an LLM workflow reliable", so that it answers a core AI-engineer interview question.
34. As the video maker, I want this setup judged by one kill test — fewer corrections on the Austin weekend — so that it is dropped if it does not pay off.

## Implementation Decisions

- **Framework principle:** make the process consistent, not the AI. Five parts: fixed steps; code for code, AI for judgment; check every answer; enforce rules mechanically; record everything.
- **Weekend runner (LangGraph):** the weekend is a graph of the nine stages above. Deterministic stages are nodes that call existing pipeline scripts. Approval points are interrupt nodes that pause and resume on my answer. The car-setup node is the only node that calls an AI.
- **Contracts (Pydantic):**
  - *Car setup*: each knob = value + min/max range + source (kind: telemetry / FIA / paper, plus reference). Missing source or out-of-range value is a validation error.
  - *Racing line plug*: points, arc length, curvature, track length, start/finish alignment. Every optimiser must write this shape; every consumer reads only this shape.
- **Checks that block:** existing gate and on-track checks become blocking (non-zero exit stops the flow); apex-touch check added at the line boundary; golden engine regression (shipped knobs reproduce shipped sim output exactly) added as a test; existing tests run in a pre-commit hook.
- **Harness rules (Claude Code hooks / permissions):** render commands without zoom 28 are blocked; delete commands are denied.
- **Map / memory:** a small index node plus one node per stage and one per weekend, linked, in git. Content is replaced, not appended; git keeps history. Decisions recorded as short ADRs.
- **Observability (Langfuse):** traces of AI calls in the car-setup node; added after the core flow works.
- **Scope rule:** only build what the Austin weekend uses. Per-track legacy scripts are not refactored now.
- **Work location:** the sandbox copy only; the original folder is untouched. Nothing is ever deleted (archive by renaming).

## Testing Decisions

- Good tests check external behaviour at stage boundaries (does this stage's output satisfy its contract and checks?), never internals.
- **Proposed seams (highest first):**
  1. *Weekend runner* — run the graph for a track with recorded inputs; assert the stage order, the pauses at the three approval points, and that a failing check stops the run.
  2. *Contract boundaries* — car-setup and racing-line validation: valid inputs pass; missing source, out-of-range knob or malformed line are rejected.
  3. *Engine golden test* — shipped knobs reproduce a shipped sim output exactly.
- **Prior art:** the existing tests suite (76 tests), the gate script, the on-track check, and the Zandvoort bit-identical regression recipe.

## Out of Scope

- Solving the car-setup physics itself (the flow only frames and checks it).
- Refactoring the ~120 per-track scripts, the 6 simulators or the delta engines.
- Docker, GCP, Terraform, Redis.
- Publishing to GitHub or job-application material.
- Lap-comparison videos.

## Further Notes

- Source evidence for this spec: today's grilling session, the retro (53 corrections across 13 sessions; top patterns: racing line, invented models, slowness, video style, unauthorized engine edits), and the pipeline map (10 stages, coupling hot spots).
- Known bug found during mapping: the Sepang build script has an accidental tab character inside a file path.
- Kill test: if the Austin weekend does not need fewer corrections, drop the setup.
