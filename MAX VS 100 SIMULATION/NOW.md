# NOW — Max vs 100 simulation
Updated: 2026-09-16.

Read memory/MEMORY.md and docs/DESIGN.md to resume. This folder is the only writable project location for the new race simulation.

## Confirmed
2D overhead animation, same visual language as the optimal-lap videos, 100 opponents plus Max, identical karts, actual custom event track. No 3D. Never change the original weekly simulation folder.

## Completed
Created isolated sibling directories. Copied renderer source as reference only, copied Formula 1 fonts, and stored a inspected British-video reference frame here. Saved config/style.json and revised 2D design. Original-folder baseline and renderer hash support preservation verification.

## Required next input
User was asked for a file path/link containing the custom track map. No accepted event geometry is available locally. User rejected using the Silverstone GP circuit as a temporary preview.

## Next work
Trace/validate the provided event map, then build independent kart/traffic computation and local 2D replay rendering. Start with one kart and a small group; expand to 101 only after blocking/passing/containment work. Deadline, video duration and predictive-versus-directed outcome remain unconfirmed.

## Guardrails
Never import or execute assets/reference/raceline_video_reference.py. Do not use the original F1 physics or batch launchers. All outputs, logs, tests, caches and temporary files stay here. Use original sources only for read-only inspection. No deletion or commit requested.

