---
name: era-comparison
description: Side-by-side of this weekend's optimal 2026 lap against a car from another era (2017 high-downforce, 2018 pole, 2025) on the same track. Use when a viral matchup exists (legend pole vs 2026).
---
# Era comparison

**Toolkit:** era car models fitted to real telemetry (2017 car fitted to real 2018 qualifying
traces, the 2025 car identified per track), each car's own optimiser line, and the dual video
renderer (`cache/era2017/dual_lap_video_v3.py`).

## Rules
- The matchup has to be viral: a legend or record pole vs 2026 (e.g. HAM 2018 at Interlagos).
- Each car drives its own line from the optimiser; never reuse the other car's line.
- Dual-video style: no graph; white text except the DEPLOY / BRAKING / SUPERCLIP mode
  labels; DRS in green; SVG track, not satellite; zoom 28 unless the track has an exception.
- The gap shown is the real pole lap time minus the simulated 2026 lap time; both are in the facts.
