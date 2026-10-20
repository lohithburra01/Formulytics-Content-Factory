# 06: Racing line from the pack with direction-only line rules

**What to build:** Line optimiser (apex-touch pattern search) runs from the pack. The user's line observations are rules of the form (corner, entry/apex/exit, inside/outside); the optimiser works out the amount. Optimise <-> tune repeats until the line stops moving (no hand-typed car values).

**Blocked by:** 02, 05

**Status:** code done; run 1 completed but INVALID (brake_preserve bug, fixed 2026-10-20); needs rerun

- [ ] T8->T9 wide entry stored as a direction-only rule and satisfied
- [ ] No car value typed by hand between rounds; loop stops when the line change is below a pack tolerance
- [ ] Apex-touch check passes

Spec: ../spec.md. Pipeline facts: ../evidence/pipeline_map_singapore.md
