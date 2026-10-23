# 16 — Review pictures before the video (spec D27)

**Status:** code written 2026-10-23 (weekend/stages_review.py, weekend/approve.py, runner gate); first Austin review render running

## What
- Stage `review` (after `checks`, before `video`): `line.svg` + `speed.svg` in runs/<track>_<year>/review/<key>/.
- Runner stops there (returns paused + the two paths) until `python -m weekend.approve <track> <year>` writes
  `approved.json` into that review dir; the next `python -m weekend <track> <year>` then renders the video.

## Done when
- Austin: pictures render, run stops before video, approve -> rerun renders video from cache.
- Two runs give byte-identical SVGs (svg.hashsalt fixed, no date metadata).
