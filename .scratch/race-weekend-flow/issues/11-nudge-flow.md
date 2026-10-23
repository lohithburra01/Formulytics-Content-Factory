# 11: Nudge flow + Singapore nudges as notes

**What to build:** User says a correction in plain words -> Claude writes a note via add_node -> one-line confirm -> git commit -> runner reruns affected steps. The logged Singapore nudges (apex touch, T8->T9 wide entry, FP1 pace, official geometry, zoom 28) are entered this way.

**Blocked by:** 09, 10

**Status:** flow built (2026-10-23): weekend/nudge.py preview|apply (Pydantic check, one confirm line, git commit; reruns = only stages reading the changed values, tested). Nudges already notes: apex touch (line.apex_w), T8->T9 wide entry (line.rule.t9_entry_outside), FP1 pace (ref.fp1_* + D21 tune), official geometry (track.path_*), zoom 28 (video.zoom). "Satisfied by the run" checked in ticket 13

- [ ] All logged Singapore nudges exist as notes and are satisfied by the run

Spec: ../spec.md. Pipeline facts: ../evidence/pipeline_map_singapore.md
