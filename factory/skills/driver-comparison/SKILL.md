---
name: driver-comparison
description: Two real drivers' qualifying laps compared with the delta engine (where one gains or loses time around the lap). Use after qualifying, e.g. pole vs P2.
---
# Driver lap comparison

**Toolkit:** `LAP COMPARISON/hifi_delta_v2.py`, an exact port of F1InsightsHub's delta
(car data from their backend, laps from OpenF1). Never use `delta_engine_v2.py` (rule R8).

## Rules
- The pair is the official Q3 classification order (grid), not the session's fastest laps.
- Each driver's line comes from the optimiser re-run with about 1% setup variation based on that
  car's character (V vs U corner shape). Never fit bumps to make the lines look different.
- The car positions are validated against F1's official "ghost car" footage (docs/media).
