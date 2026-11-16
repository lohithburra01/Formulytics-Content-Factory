# 09: Step runner (LangGraph, no AI inside)

**What to build:** Runs track -> references/targets -> tune -> line -> time knob -> checks -> video -> lineage in order; resumes after a crash from the last finished step; pauses only for a question with no source; reruns only steps whose inputs changed.

**Blocked by:** 02, 03, 04, 05, 06, 07, 08

**Status:** superseded 2026-10-23 by ticket 13 proof run (all stages ran clean twice, identical). Old note: run 1 went track..checks (shows the runner works); results invalid (brake_preserve bug); video + lineage commit pending

- [ ] `python -m weekend singapore 2026` runs the whole chain
- [ ] Killed mid-run -> resumes without redoing finished steps (test)
- [ ] A changed note reruns only the affected steps (test)

Spec: ../spec.md. Pipeline facts: ../evidence/pipeline_map_singapore.md
