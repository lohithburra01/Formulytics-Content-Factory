# 16 — Review pictures before the video (spec D27)

**Status:** done (2026-10-24): review stage (line.svg + speed.svg, corner-aligned FP1, section RMSE, SUPERCLIP clip bars) + approve gate; zoom preview frames -> ticket 18.

## What
- Stage `review` (after `checks`, before `video`): `line.svg` + `speed.svg` in runs/<track>_<year>/review/<key>/.
- Runner stops there (returns paused + the two paths) until `python -m weekend.approve <track> <year>` writes
  `approved.json` into that review dir; the next `python -m weekend <track> <year>` then renders the video.

## Done when
- Austin: pictures render, run stops before video, approve -> rerun renders video from cache.
- Two runs give byte-identical SVGs (svg.hashsalt fixed, no date metadata).
