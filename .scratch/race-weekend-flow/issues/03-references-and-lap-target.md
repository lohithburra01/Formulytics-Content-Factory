# 03: Real reference laps and the lap-time target

**What to build:** 2025 Q and 2026 FP1 laps are pinned inputs. The lap-time target is computed from the user's rule (D3): FP1 -1.5..-2.0 s when FP1 exists, else 2025 +1.5..+3.0 s. Per-corner/top-speed targets (predict step) come from the pack incl. transfer_2026.json.

**Blocked by:** 01

**Status:** done (2026-10-20): target 90.274-90.774 s (FP1 92.274)

- [ ] Singapore target = FP1 lap -2.0..-1.5 s, branch recorded in the pack
- [ ] Without FP1 the 2025 branch is used (test)
- [ ] predicted targets byte-identical to cache/predicted_singapore.json when fed the same inputs

Spec: ../spec.md. Pipeline facts: ../evidence/pipeline_map_singapore.md
