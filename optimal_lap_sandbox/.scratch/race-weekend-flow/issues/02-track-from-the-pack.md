# 02: Track geometry built from the pack

**What to build:** The Singapore track (official map-matched path -> 4927 m, R>=10, 10 m outline, mirror) is built by a stage whose every number is in the pack; the cached OpenF1 samples are pinned inputs (MEASURED, sha256). Same method works for any track given its session key and length.

**Blocked by:** 01

**Status:** done (2026-10-20): outline + mirror byte-identical

- [ ] Outline + mirror outline byte-identical to the shipped ones
- [ ] Hard-coded numbers (4940, 12, 10, 855, sigma 1.5, 2 m step, 4927, R10, 12->10 m, RUS=63, session 9892) are pack values with origins
- [ ] Dead steps dropped (S2 outline writes, _rus2025_car)

Spec: ../spec.md. Pipeline facts: ../evidence/pipeline_map_singapore.md
