# 18 — Map-SVG track, speed-matched S/F, elevation and zoom preview inside the pipeline (spec D29-D31)

**Status:** ready (written 2026-10-24). The Austin video was made by the fast-path scripts in weekend/_fastpath/;
this ticket makes `python -m weekend <track> <year>` do the same by itself, fast.

## What (each = one stage or stage change; keep total run time short)
1. Card field `map_svg: {file, path_id, source}`; track stage: SVG -> FIA length, width = map stroke x m/px,
   mirror by direction. NO OpenF1 x/y anywhere in track/line (D29).
2. base_line: physics line on the map track; direction + S/F found by matching the sim speed trace to the
   reference speed trace (corr; Austin 0.973, S/F 2272 m along the drawn path).
3. Elevation stage (main-folder method, OpenF1 location z only) -> elevation json -> video `--elevation-json`.
4. Review step also writes zoom preview frames (video.zoom_preview [15,20,25,30]) before the real render (D30).
5. Speed: one line round when shape.enabled; skip time_knob when shape.enabled (shape_fit sets lap time);
   rule weights carried across rounds (done c3e877d); local retries (done).
6. Keep: shape_fit as is (user approved 2026-10-24, do not change its method).

## Done when
- `python -m weekend austin 2026` reproduces runs/austin_2026/svg_line result (lap in band, >= 9/10 sections,
  4/4 clips) and stops at review with line.svg, speed.svg and 4 zoom frames; full fresh run <= ~12 min.
- Singapore golden replay still byte-identical.

## Open (user to judge later, not blocking)
- T1 "apex off" rule not applied on the SVG physics line.
- C9 approach section 12.7 km/h RMSE (user: "all good").
