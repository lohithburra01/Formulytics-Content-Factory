# Max vs 100 — isolated 2D race simulation

This project is separate from `D:\f1_hot_lap\OPTIMAL LAP SCRIPTS`. All new code, assets, tests, caches, logs, temporary files and exports belong inside this folder. The optimal-lap project is a read-only reference.

## Agreed direction
- 2D overhead map video matching the existing optimal-lap visual style.
- 100 opponents plus Max in an identical kart.
- Custom Max vs 100 event layout; the Silverstone GP outline is not an accepted substitute.
- Rule-based traffic and overtaking; no reinforcement-learning training needed for the first version.
- Max remains the camera focus and highlighted marker; opponents use smaller numbered markers.
- Keep the black/dark road, white boundaries/kerbs, Formula 1 typography, trail, minimap and vertical video format.
- Race-specific HUD: Max speed, lap, challengers remaining and elapsed time. F1 battery/regen/active-aero logic does not apply to this kart race.

## Current status
Separate directory, visual reference, copied fonts, style configuration, design and resume notes are prepared. No kart race engine or race video has been produced.

The required input is the custom event track map or a file/link containing it, with a known scale if lap timing matters. The old GP circuit has not been copied into the track assets directory. The exact deadline and reel duration are also unconfirmed.

## Reference assets
- `assets/reference/optimal_british_style_reference.png`: frame sampled from the existing British optimal-lap video.
- `assets/reference/raceline_video_reference.py`: a copied source reference only. Do not execute or import it; the new renderer must use local paths and kart replay data.
- `assets/fonts/`: local copies of the original typography.
- `config/style.json`: explicit visual constants for the new renderer.

## Isolation
No new runtime may import scripts from the optimal-lap folder, launch its batch files, use its caches, or export to its assets directories. Resolve every writable path from this project's root. Use a local NOW.md and memory/MEMORY.md, not the original project's resume files.

`docs/original_folder_baseline.json` records original-folder file names, sizes and modification times at the start of this preparation. `docs/reference_source_hash.json` records the renderer reference source hash. `docs/isolation_verification.json` records the final comparison for this preparation.

