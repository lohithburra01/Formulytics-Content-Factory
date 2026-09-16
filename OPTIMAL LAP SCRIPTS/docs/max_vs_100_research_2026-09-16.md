# Max vs 100: research and proposed build sequence

Research date: 16 September 2026. Status: planning only; no race engine or video built. User confirmed Max drives the same kart as the 100 opponents. Deadline, reference Instagram video, exact output style, and custom layout are still outstanding. This is a decision brief, not an approved implementation specification.

## Recommendation

Build a lightweight, rule-based kart race simulation in Python, store the resulting trajectories and events, and render those records separately. First verify an overhead replay with all 101 racers. Then use Blender EEVEE for a cinematic video if that is the intended deliverable. Use the same simulation data for both renderers.

Do not start with reinforcement learning. The urgent problems are geometry, traffic, believable overtaking, rule handling, and presentation. Training adds observations, actions, reward design, training environments, and policy evaluation before those problems are solved. Unity's official documentation describes that workflow: https://github.com/Unity-Technologies/ml-agents/blob/develop/com.unity.ml-agents/Documentation~/Learning-Environment-Create-New.md and https://unity-technologies.github.io/ml-agents/Training-Configuration-File/ . If RL is pursued later, multiple opponents can share a policy with different parameters; 100 separately trained models are not required.

Do not guarantee Max wins in a predictive run. His controller represents an assumed expert driver; it is not a learned or measured reproduction of Verstappen. A guaranteed P101-to-P1 video is a directed scenario, and should be described that way. Separate these objectives before calibrating pace.

## Event facts and source confidence

The current official Red Bull explanation confirms 101 identical karts, Max starting P101, qualifying ordering the other 100, a standing start, and up to 30 laps. Passed challengers leave the challenge. Each challenger gets a one-use shortcut in the first half; Max gets one in the second half. The course combines the kart circuit with a custom extension onto the GP circuit. Source: https://www.redbull.com/int-en/max-vs-100-karting-race-explained . The original announcement identifies David Terrien as the designer: https://www.redbull.com/int-en/max-verstappen-vs-100-drivers . Neither page provides enough surveyed geometry for reconstruction.

A search-indexed Canadian Red Bull version provides more detailed rules: full-clear overtakes, a five-kart-length following gap, classification at an arch between the final two corners, then a pit return. It also describes a same-lap shortcut recovery exception and restrictions after neutralisations. Its direct URL returned 404 during research, while the current international article is shorter. Treat these as provisional rules requiring reconciliation with final regulations or broadcast information, rather than silently implementing irreversible removal at every pass. Source: https://www.redbull.com/ca-en/max-vs-100-karting-race-explained .

A published Red Bull Content Pool infographic was located, identifier SI202609090574, on https://www.photosportmagazine.com/a-silverstone-arriva-max-vs-100/ . Its image could not be fetched for inspection. It is a lead for obtaining the map, not a traced or verified track asset. A Motorsport-Magazin search result also describes a map and extension; no dimensions were verified. Do not infer exact track length, widths, direction, shortcut geometry, kart model, power, top speed, minimum weight, or expert pace from those leads.

## Tool choices

| Approach | What it offers | Main constraint | Recommendation |
|---|---|---|---|
| Python race engine + overhead replay + Blender | Custom rules, reproducible race, independent video production | Kart dynamics and traffic logic must be implemented; 3D assets needed | Preferred for this project |
| Existing game: BeamNG or rFactor 2/KartSim | Vehicle rendering and existing AI | Exact course, 101-kart grid, shortcut/elimination rules, kart assets, and performance need proof | Consider if a suitable scene already exists |
| Unity/Godot custom real-time application | Interactive controls and reusable game | More application and vehicle setup than an offline video needs | Choose if interactivity is essential |

BeamNG officially supports custom hotlap routes with AI racing, and provides a race/path editor. Its documentation warns AI quality depends on vehicles, navigation layout, and risk settings. This does not prove a reliable 101-kart race. Sources: https://www.beamng.com/game/support/portal/gameplay/hotlapping/ and https://docs.beamng.com/world_editor/windows/race_path_editor/ . A release note removed an opponent-count restriction in the AI challenge editor; an unrestricted editor count is not a performance benchmark: https://beamng.com/game/news/patch/beamng-drive-v0-35/ .

rFactor 2 has KartSim content and an official custom-track/AI-waypoint workflow. A new layout still requires track and AI preparation, and no 101-kart implementation of these event rules was verified. Sources: https://www.studio-397.com/tag/kartsim/ and https://docs.studio-397.com/display/DG/Track%2BStructure .

Blender EEVEE supports interactive previews and final rendering; Python can insert animation keyframes and command-line rendering can produce frames unattended. It supplies the visual production stage, not racing intelligence. Sources: https://docs.blender.org/manual/en/5.0/render/introduction.html , https://docs.blender.org/api/4.2/bpy.types.bpy_struct.html , https://docs.blender.org/manual/id/4.2/advanced/command_line/arguments.html . A browser preview is another option: Three.js supports instanced repeated meshes to reduce draw calls, but final performance still needs a benchmark: https://threejs.org/docs/pages/InstancedMesh.html .

The unidentified Instagram account's software cannot be inferred from the description. Its reference video is needed to distinguish game footage, procedural 3D animation, and simplified map simulation.

## How the racers would work

All racers share one vehicle definition: dimensions, mass assumptions, acceleration/drag, braking capability, steering limits, and grip. Driver differences control how effectively they use that vehicle. Keep mechanical differences separate from driver parameters.

Give each driver a fixed profile: braking margin, cornering grip utilisation, line accuracy, reaction delay, overtaking confidence, defensive tendency, and a small rate of bounded mistakes. Include some quick opponents; do not make all 100 equally slow. Use actual qualification data if available. Otherwise generate mixed profiles and order the grid by a synthetic qualifying session, clearly marked as assumed.

Max uses the same physical limits with better line choice, smaller braking margins, stronger anticipation, and lower error variability. Absolute pace and advantage remain scenario assumptions until measured. Giving him unlimited acceleration or simply advancing his position would invalidate a prediction.

Each driver follows a path using a conventional lookahead steering controller, then chooses among short local trajectories. Pure-pursuit path following is documented in the F1TENTH autonomous racing stack: https://github.com/f1tenth-dev/pure_pursuit . It is a starting point for steering, not a complete crowd-racing system.

Proposed behaviours:

1. Race toward the preferred line when space permits.
2. Follow and brake behind a blocked kart.
3. Compare inside/outside passing trajectories against nearby opponents' predicted footprints.
4. Commit to a feasible pass, with a minimum commitment interval to prevent lateral oscillation.
5. Defend within track and vehicle limits, with bounded changes of direction.
6. Yield or brake when a manoeuvre becomes unsafe.
7. Decide whether a legal shortcut saves enough time after accounting for merge traffic.
8. Follow the applicable caught/classification/pit-return rules.

The opponents compete against one another too. Their incentive is race progress and survival ahead of Max, so they should not automatically yield to him. Congestion, side-by-side entries, and mistakes should emerge from interaction.

Start with a planar vehicle model suitable for a visual simulation: speed, heading, steering and acceleration limits, with curvature-dependent grip and coupled braking/cornering limits. A kart has handling characteristics that a simple car model does not reproduce, including a rigid rear axle and chassis effects. This first model is an approximation; measured kart data would be needed for a validated prediction. Rich contact dynamics, chassis flex, wheel lift and tyre thermal models are later work unless visibly required by the reference.

## Track and data architecture

Track data must include metric centreline/boundaries, local widths, direction, start/finish, grid slots, shortcut branches and merge points, and pit/classification routes. Use a directed route graph rather than a single closed loop. Include penalty routes only when confirmed necessary.

Acquire an official map or sufficiently clear overhead footage, then trace and scale it against known dimensions. Check the result with a human familiar with the event. A map without a scale can support a labelled illustrative animation, but not trustworthy times. Boundary tracing matters more than decorative scenery because it determines whether passing space exists.

Proposed modules: track geometry; kart dynamics; driver profiles; local traffic planner; race rules; replay/event writer; overhead renderer; Blender replay importer. Keep this new system separate from the frozen F1 physics.

Use a fixed simulation timestep, initially targeting 50–100 Hz subject to benchmarking. Planning can run less frequently with short-horizon predictions. Compute decisions from a shared snapshot and then integrate everyone, to avoid giving earlier-updated drivers an advantage. Maintain both physical XY footprints and route/checkpoint progress. A shortcut must advance valid race progress without crediting fictitious metres travelled.

Use swept collision checks and track-corridor checks. Neighbour searches must find nearby karts in physical space, including where route branches merge. When no trajectory is safe, slow down; do not teleport karts to correct congestion. Detailed crash physics is outside the initial scope; any approximate contact response must be explicit.

Store time, driver ID, route, position, heading, speed, control state, lap/checkpoint state, and status. Store overtakes, shortcut use, contacts, classification and pit events separately. Frame-rate conversion and interpolation must preserve steering continuity and avoid introducing collisions in the rendered replay.

Render the replay with one repeated kart/driver model, varied colours and numbers, and a distinctive Max livery. First show the full grid from above. Then add a chase camera, trackside passing shots, selected onboard views, a mini-map, lap count, and number of challengers remaining. Render only the selected highlights if the deliverable is a short reel; the simulation can still cover the whole race.

## Build order and acceptance gates

1. Confirm output, deadline, reference style, track map and whether the outcome is predictive or directed. Deliver a checked geometry preview before adding scenery.
2. Calibrate one kart's acceleration, braking and cornering on that layout. Verify full-lap containment, closure and plausible speed. Record which values are assumed.
3. Run a small field to verify queues, a blocked pass, side-by-side travel, a pass that fully clears, shortcut merges, and pit departures. Rule variants remain configurable until reconciled.
4. Run all 101 from a non-overlapping physical grid. Check first-corner congestion, stable driving, lap/checkpoint counting, footprint intersections and simulation time. Benchmark before committing to a live frame rate.
5. Save a complete replay and render an overhead draft. Inspect crowded corners and branch merges visually. Check that the remaining-driver counter matches events and that shortcut benefits are not counted twice.
6. Add 3D assets/cameras and render a short representative test. Measure actual seconds per frame, then estimate the remaining render budget. Inspect highlights, final frame, HUD, duration and decoded frame count before exporting the final reel.
7. If the goal is prediction, run sensitivity scenarios over expert pace advantage, opponent distribution, defensive strength, grid spacing and shortcut benefit. Report assumptions and the range of outcomes. Scenario frequency is not an evidence-based probability that Max wins.

Useful regression checks include timestep refinement, same-seed reproducibility, valid checkpoint sequencing, no duplicate final eliminations, only one legal shortcut per driver, and a stationary blocked kart that cannot be driven through. These checks test the behaviour rather than merely the implementation.

## Schedule expectations

These are planning estimates, not measured delivery commitments. Given a usable scaled map, an overhead proof is the first several-hour target. A polished 3D reel is more plausibly a multi-day effort if kart models, environment and camera design must be created; it can be faster if suitable assets already exist. Photorealism and validated race prediction add distinct work beyond producing believable footage. Exact timing depends on the pending deadline/style and a render benchmark.

The hard deadline should select the first deliverable: overhead race evidence, stylised 3D highlight reel, or a full real-time application. Training ML policies should not be on the urgent critical path.

## Existing project reuse and constraints

Read-only project exploration found:

- Python 3.10.11 at `C:\Users\91910\AppData\Local\Programs\Python\Python310\python.exe`, with the existing numerical/video stack; ffmpeg and ffprobe available.
- Blender installations under `C:\Program Files\Blender Foundation\Blender {4.0,4.2,4.4,4.5,5.0}\blender.exe`; Blender is not on PATH. No renderer or asset scene was launched during this research.
- `svg_to_outline.py::build_outline_from_svg` and geometry/raceline utilities in `raceline_video.py` and `sim_2026_lap.py` can inform geometry processing. Their direction, S/F and hairpin-width heuristics need explicit review for this custom layout.
- Existing `sim_2026_lap.py` computes one fixed F1 raceline/speed profile. It has no kart vehicle definition, traffic or dynamic overtaking. Its frozen car parameters and GP calibration accuracy do not transfer to this challenge.
- `raceline_video.py` provides map/HUD export patterns but currently renders one vehicle. `cache/_build_3d_viewer.py` provides a vendored Three.js track/replay pattern with one car, not a 101-kart scene.
- The existing `RaceCircuitSilverstone.svg` and British GP outline represent the 5,891 m GP course, not the event course. Do not use them as the final layout.
- Large parent-repo Blender scenes and addons exist, including `D:\f1_hot_lap\builder addon.blend`; contents and readiness are unverified. No ready kart assets were found in this workspace.
- Preserve every existing file; never delete. Leave unrelated work and frozen F1 physics untouched. No commit requested.

The external historical memory index is `C:\Users\91910\.claude\projects\D--f1-hot-lap\memory\MEMORY.md`. This research brief is the durable in-workspace record for the new task; `NOW.md` links it so the next session can resume without replaying research.
