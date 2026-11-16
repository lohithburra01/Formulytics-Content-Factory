# 13: Singapore proof run

**What to build:** Full chain on Singapore 2026 twice, from naming the track to the video.

**Blocked by:** 11, 12

**Status:** done (2026-10-23): run 1 runs/ + run 2 runs_proof2/ (clean) -> every stage output byte-identical incl. video.mp4 sha 8eab1481 (only wall-clock 'seconds' in car_and_line/rounds.json differs); lineage 5fbb42e, run 2 lineage 'unchanged'; 143 values, 0 ASSUMED, 0 pending; lap 90.464 in band 90.274-90.774, pattern 0.953; checks all_ok False -> gaps per sector reported (D23); T9 rule satisfied (gap 0.058 m), apex gaps <= 0.24 m; video zoom 28 + LAP TIME 1:30.524

- [x] Two runs identical
- [x] Zero ASSUMED / TEMPORARY values
- [x] Checks pass or gaps reported per sector
- [x] Logged Singapore nudges satisfied
- [x] Pack committed
- [x] Video rendered with zoom/style from the pack

Spec: ../spec.md. Pipeline facts: ../evidence/pipeline_map_singapore.md
