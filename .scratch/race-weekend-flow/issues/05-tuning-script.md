# 05: Fixed tuning of the car numbers

**What to build:** A fixed script (never the agent) tunes each car number only against the speed-graph feature it controls: braking shape -> braking grip + trail-off; straight peaks -> drag / deploy; corner minimums -> downforce / lateral grip; exit acceleration -> traction. Each has a plausible range from the notes; needing a value outside it is reported as a conflict.

**Blocked by:** 04

**Status:** done with 1 conflict (low-speed braking -38%); 7 numbers held for review

- [ ] The 11 TEMPORARY numbers are replaced by FITTED values with target + range
- [ ] Changing one feature target moves only its own car numbers (test)
- [ ] Out-of-range need -> conflict in the report, not a clamp (test)

Spec: ../spec.md. Pipeline facts: ../evidence/pipeline_map_singapore.md
