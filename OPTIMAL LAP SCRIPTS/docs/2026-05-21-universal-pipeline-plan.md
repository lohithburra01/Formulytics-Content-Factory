# Universal Race-Weekend Pipeline — Plan / Resume Point

**Date:** 2026-05-21
**Status:** Future work — captured for later, **not started**. Deferred mid-discussion
to do other work.

## Goal

Turn the Canada-specific optimal-lap pipeline into a **universal** one: drop in a
new track (SVG, GeoJSON, **or a 3D model**), run one bat-file-style command, get a
finished race-weekend video. Today the pipeline is hardwired to Circuit Gilles
Villeneuve, so a new video can't be made for another Grand Prix without editing
code.

## Current pipeline (works, Canada only)

Three stages chained by `make_canada_2026_lap.bat`:

1. `svg_to_outline.py` — SVG centerline → road outline JSON
2. `sim_2026_lap.py` — racing line + 2026 physics sim → raceline JSON + synthetic telemetry CSV
3. `raceline_video.py` — outline + raceline + CSV → MP4

## What's hardcoded to Canada (the actual work)

### `make_canada_2026_lap.bat`
- Every path is Canada-specific. → Replace with a generic `make_lap.bat <track>`
  that reads a per-track config.

### `svg_to_outline.py`
- `TRACK_LENGTH_M = 4361.0` — Canada's length. → Per-track input, or auto-derive
  from a georeferenced GeoJSON.
- `HAIRPIN_NARROW_M` / `HAIRPIN_HALF_RANGE_M` / `apply_hairpin_narrowing` — assumes
  the track has a hairpin to narrow. Not every track does. → Make optional /
  config-driven / auto-detect.
- Reads SVG only. → Add a GeoJSON reader; possibly 3D-model centerline extraction.
- `find_start_finish_index` (longest-straight proxy) — already superseded by the
  sim's reference-telemetry cross-correlation; fine to keep as a fallback.

### `sim_2026_lap.py`
- `--reference-csv` default → Canada 2025 Q. → Per-track reference lap.
- `_CALIB_PATH` → Canada calibration JSON. → Per-track.
- `kappa_hairpin = 1.0/15.0` ("Canada T10") in the calibration override. →
  Generalize / derive from geometry.
- `assert_sanity` bands — `T_lap [70,80]`, `peak [290,350]`, `hairpin v [52,85]`.
  The lap-time band is very track-specific (Monaco ~71 s vs Spa ~104 s vs Vegas
  ~95 s). → Derive the lap-time band from the reference lap (e.g. 2026 ≈
  ref_time + [0, ~4 s]); generalise or config the rest.
- The 2026 physics constants themselves are universal (regulation/calibration, not
  track-specific) — keep. Calibration values (mu_long, P/m, v_apex) are already
  telemetry-driven; they just need the right per-track reference lap.

### `raceline_video.py`
- Already mostly generic — `--track-name`, `--outline`, `--raceline`,
  `--telemetry-csv`, `--out` are all args. Font path is machine-specific (fine).

## Per-track inputs the pipeline needs

1. Geometry file — SVG / GeoJSON / 3D model.
2. Real track length (m) — unless a georeferenced GeoJSON makes it derivable.
3. Track name.
4. A real reference lap (telemetry CSV) — anchors the start/finish line and
   calibrates the vehicle physics. Sourced via FastF1 (`fetch_fastest_lap.py`
   already exists) or user-provided.
5. Hairpin present? (for road narrowing) — or auto-detect from curvature.

## Proposed architecture (a starting point, not decided)

- `tracks/<track>.json` — per-track config: name, geometry path, length (optional),
  reference spec (FastF1 event/year/session OR a csv path), flags.
- `make_lap.bat <track>` → thin wrapper → `make_lap.py <track>` orchestrator that
  reads the config, chains the three stages, and auto-fetches the reference lap if
  it's missing.
- Generalise `svg_to_outline.py` → `track_to_outline.py`: multi-format geometry
  reader (SVG, GeoJSON LineString, maybe 3D) + a `--track-length` argument.
- `sim_2026_lap.py`: reference lap + sanity bands come from the config.
- `raceline_video.py`: unchanged.

## Open questions — decide before building

1. **Reference-lap sourcing** — auto-fetch from FastF1, user-provided CSV, or both
   (fetch with CSV fallback)? Depends on what's available per track. *Undecided.*
2. **GeoJSON coordinate system** — georeferenced lat/lon (track length
   auto-derives, needs a projection step) vs projected/abstract XY (length must be
   supplied). *Undecided — varies by file.*
3. **3D-model input** — sometimes the only track source is a 3D model. How to
   extract a centerline from a mesh? `extract_track_outline.py` (repo root) and the
   Blender addon under `launch_control_auto_car_rig/` may help. *New requirement,
   unscoped.*

## Where to resume

Start here. The hardcoded-bits inventory above is the concrete task list. Resolve
the three open questions first (they change the architecture), then follow the
brainstorming → spec → plan flow. The Canada pipeline must keep working unchanged
throughout (it is the reference implementation and the regression check).
