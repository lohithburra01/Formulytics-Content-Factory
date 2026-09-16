# Max vs 100: revised 2D design
Date: 2026-09-16. User-approved direction: original optimal-lap map video style, isolated sibling project, custom event circuit.

## Scope
Produce a 1080 × 1920, 30 fps overhead video of 100 opponents and Max. Reuse the original visual language through locally copied fonts and a reference source file. The race computation is a new, independent kart/traffic engine; the existing fixed-raceline F1 model cannot produce interactive passing.

The initial milestone is a verified replay of a small racing group on the supplied custom geometry, followed by all 101 racers. The final video follows Max and shows nearby racers in detail, with all active racers represented on the minimap. A full-grid opening shot can establish scale.

## Visual contract
Use config/style.json and the reference PNG. The reference source's current HUD is slightly more compact than the sampled older shipped video. Preserve the main map appearance and type treatment, adapting HUD labels to kart racing. Opponent marker sizes must be smaller than Max's focal dot; final sizes should remain legible without implying physically oversized karts.

Race physics uses real kart footprints independently of display-marker size. Do not treat the original 28 px dot as a collision body. Only Max needs a long speed-coloured trail; 101 simultaneous trails would obscure the track and passing.

Use the same non-rotating overhead camera convention. Show Max's speed rather than field-average speed. Remove F1-specific deployment/regen displays and replace them with remaining challengers and race progress.

## Data and component boundaries
- assets/tracks/event_track.json: metric boundary/route geometry after the actual map is obtained and checked.
- src/track.py: validated custom geometry, route graph, grid positions, checkpoint order, local widths.
- src/kart.py: identical mechanical capabilities, dimensions and planar dynamics.
- src/drivers.py: stable skill and decision profiles for Max and opponents.
- src/race.py: simultaneous updates, traffic, bounded passing/defence, route choices, race statuses and events.
- src/replay.py: trajectories and events written to outputs/run directories.
- src/render_2d.py: video frames from geometry/replay and config/style.json, with local font paths.
- tests/: containment, blocking, pass completion, legal route/lap counting and reproducible replay checks.

Each component reads only local project data. A runner must reject output paths escaping the project root. The simulation and renderer run separately so graphics changes do not alter the race.

## Race behaviour
All karts share a vehicle definition. Driver profiles vary braking margin, line accuracy, reaction time, overtaking commitment, defensive tendency and bounded mistakes. Include strong opponents alongside beginners. Max's advantage comes from better execution, not a different engine or an arbitrary positional boost.

When blocked, racers brake or find a physically feasible local passing route. Check opponent footprints and road boundaries through the manoeuvre, not only at its endpoints. Racers also compete against one another.

Event rules require a configuration separate from movement. The official international article confirms elimination and one-use shortcuts by race half. Detailed regional descriptions include continued movement to classification/pits and a same-lap shortcut recovery exception, so final elimination must not be assumed equivalent to instant visual disappearance until those rules are reconciled. Use route/checkpoint progress rather than raw shortcut distance when counting laps.

## Input still needed
The custom event map is required; user explicitly chose it over the GP outline. Obtain the map's direction, start/finish, scale/widths, grid and shortcut/merge routes. If dimensions are unmeasured, label geometry/timing assumptions. Do not use fabricated geometry as the event course.

The exact deadline and output duration determine rendering scope. Whether Max's eventual success must emerge from assumptions or be directed remains unconfirmed; do not guarantee a predictive win.

## Verification
Verify one-kart containment and pace, then a small traffic field, then the 101-kart start. Inspect congested corners and merges. Check replay/event counters, reproducibility and performance. Decode and inspect the final output's first/last frames and crowded passing scenes before claiming a race video is complete.

## Project preservation
Preserve all existing files. No original weekly-pipeline edits, test runs, imported modules or cache writes are authorized for this task. No commits or deletions requested. Earlier research notes from the preceding turn already exist in the original project and are left unchanged after the user's isolation instruction.

