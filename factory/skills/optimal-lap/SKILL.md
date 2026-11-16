---
name: optimal-lap
description: Produce the weekend's "optimal lap" - the fastest physically realistic 2026 lap on this track, simulated before any running (pre-FP1) - with caption. Use for every race weekend.
---
# Optimal lap

**Toolkit (fixed per track, filled with fresh data each weekend):** the SVG track outline,
a reviewed apex-touching racing line, the 2026 lap simulator (`sim_2026_lap.py`: energy-limited
power unit, measured superclip, active aero, grip map), the realism gate, and the renderer
(`raceline_video.py`).

## Steps
1. Researcher: read the weekend toolkit, the predicted targets (2025 Q reference x
   2025->2026 transfer), what memory says about this track and how past predictions scored.
2. Simulator: run the simulation with the calibrated setup first. Then run the realism gate,
   the speed-trace check and the apex check.
   - If a gate fails, change ONE knob within the physical bounds and say why. Don't fit to lap
     time alone (rule R4). At most 3 re-runs, then report the failure.
3. Critic: run all gates and judge whether the result is physically credible against the
   targets and memory. Reject anything that only matches because a knob was pushed.
4. Packager: write the caption from verified facts only.
5. Queue for publish only when every blocking gate passes.

## Hook patterns that worked on the page
- Contrast with a known number ("slower than the 2025 pole: here's why")
- Engineering reveal ("where 2026 cars lose time: the battery runs out on the straight")
- Never invent comparisons that are not in the facts.
