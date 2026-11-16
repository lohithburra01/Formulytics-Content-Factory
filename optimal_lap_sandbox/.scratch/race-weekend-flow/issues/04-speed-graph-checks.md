# 04: Speed-graph checks with per-sector gaps

**What to build:** Given a sim lap and a reference lap, report per braking zone (onset point, decel rate), per straight (peak speed), per corner (minimum speed), acceleration vs speed, apex touch on the line, and the time gap per sector. Starting tolerances = existing gate bands, recorded as user decision.

**Blocked by:** 01, 03

**Status:** superseded 2026-10-23 by ticket 13 proof run (all stages ran clean twice, identical). Old note: code done; run 1 report (GAIN median 31.8 fail) is INVALID - made with brake_preserve bug on (fixed simdoor.py 2026-10-20); needs rerun

- [ ] Report lists every braking zone / straight / corner of Singapore with value, reference, error, pass/fail
- [ ] Per-sector time gaps (3 official sectors) reported
- [ ] Same report used as the tuning target and the pass criteria

Spec: ../spec.md. Pipeline facts: ../evidence/pipeline_map_singapore.md
