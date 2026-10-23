# 15 — Any weekend: a new track makes its own notes

**Status:** in progress - step 1 done (shared track-build settings -> season/track_build_defaults_2026.yaml, Singapore values identical); step 2 done (weekend/cards/austin.yaml + singapore.yaml: name, OpenF1 names, length, direction, altitude, street); step 3 done (weekend/new_track.py, runner calls it; Austin pack 135 values 0 ASSUMED; test vs Singapore hand notes); step 4 run 1 done (lineage fc4dfb6): pattern 0.964, lap 96.80 NOT in band 93.86-94.36, knob conflict; 1.8 s lost at 3900-4340 m (T12-T15), fitted grip k 0.676

## Why
Tickets 01-14 proved the pipeline on Singapore, whose notes were written by hand.
User order 2026-10-23: finish the tickets, THEN make it work for any weekend.
Austin 2026 (FP1 done, data fetched) is the first test track, but nothing may be Austin-only.

## What
`python -m weekend <track> <year>` on a track with no notes:
1. Fetch (weekend/fetch_weekend.py, already built) if cache/<track>/fetch_facts.json is missing.
2. Write `track/<track>_<year>_layout.yaml` + `weekend/<track>_<year>.yaml` from:
   - fetch_facts.json -> MEASURED (ref CSVs, lap times, sectors, path samples, path ref driver);
   - one small per-track card (length, direction, altitude, event name) -> KNOWLEDGE with source;
   - formulas -> COMPUTED (RHO from altitude, mirror_x from direction, gain cap from real Q gain);
   - season-level defaults for path/frame settings (moved out of Singapore notes, same values) -> USER_DECISION;
   - grip / CdA / CL / width -> FITTED by the existing tune stage, not hand-set.
3. Run the normal chain: track -> base_line -> refs -> car_and_line -> time_knob -> final -> checks -> video.

## Done when
- Austin 2026 runs end to end with zero hand-written Austin values beyond the card, 0 ASSUMED.
- Lap inside the FP1-derived band; video renders; user judges the three outcomes (FP1 pattern, line, lap-in-band).
- Singapore golden replay still passes (moving shared defaults must not change Singapore output).
