# F1 Hot Lap — Session Handoff (2026-04-30)

Continuation of `STYLED_LINE_DEBUG_HANDOFF.md` (2026-04-27). Read that one first for prior context (V2 styled-line history, user communication preferences, rejected options A/B/C).

User's situation today: testing Miami GP for the first time with the merged extension. Two cars queued (NOR + SAI). The styled-line + auto-align flow was producing a "rubber band suspended around the track that flips and shortest-paths back when off-track."

---

## What was committed-ready today (none committed)

All edits pass `python -c "import ast; ast.parse(...)"`. Nothing has been git-committed.

### 1. Standalone vs merged addon collision — RESOLVED via rename

**Symptom:** Tracebacks pointed at `scripts\addons\f1_track_visualizer_addonLastLastLasttry5.py` (the standalone), not the merged extension. Both addons registered the same `bl_idname`s/class names; standalone won the resolution. Every fix to the merged file was invisible.

**User constraint:** They want to keep the standalone installed for a separate workflow. We had to rename in the MERGED extension only.

**Fix in `launch_control/operators/f1_track_viz.py`:**

| Old | New |
|---|---|
| `OBJECT_OT_InstallF1Dependencies` | `F1_OT_InstallTrackVizDeps` |
| `OBJECT_OT_GenerateCenterline` | `F1_OT_GenerateCenterline` |
| `OBJECT_OT_GenerateRacingLine` | `F1_OT_GenerateRacingLine` |
| `OBJECT_OT_GenerateAllStyledRacingLines` | `F1_OT_GenerateAllStyledRacingLines` |
| `OBJECT_OT_LoadStyleFromJson` | `F1_OT_LoadStyleFromJson` |
| `OBJECT_OT_AlignPathToRacingLine` | `F1_OT_AlignPathToRacingLine` |
| `OBJECT_OT_AlignAllDriverPaths` | `F1_OT_AlignAllDriverPaths` |
| `bl_idname object.install_f1_dependencies` | `f1.install_track_viz_deps` |
| `bl_idname object.generate_centerline` | `f1.generate_centerline` |
| `bl_idname object.generate_racing_line` | `f1.generate_racing_line` |
| `bl_idname object.generate_all_styled_racing_lines` | `f1.generate_all_styled_racing_lines` |
| `bl_idname object.load_style_from_json` | `f1.load_style_from_json` |
| `bl_idname object.align_path_to_racing_line` | `f1.align_path_to_racing_line` |
| `bl_idname object.align_all_driver_paths` | `f1.align_all_driver_paths` |
| `bpy.types.Scene.f1_track_props` | `bpy.types.Scene.f1_track_viz_props` |

Callers updated:
- `launch_control/operators/f1_pipeline.py` — auto-chain `bpy.ops.f1.*` calls
- `launch_control/ui/f1_track_setup_panel.py` — operator buttons + `scene.f1_track_viz_props`

NOT renamed (no collision with standalone):
- `F1TrackVizProperties` PropertyGroup class (standalone uses `F1TrackProperties`)
- `PANEL_PT_F1_TrackSetup` panel
- `modules/f1_track_viz_deps` deps folder

### 2. `NameError: skipped` in styled-line BATCH — FIXED

`OBJECT_OT_GenerateAllStyledRacingLines.execute()` had `written = []` but never `skipped = []`, then crashed on the final print. Added `skipped = []` initialization. Curves were already getting written before the crash, but the operator returned `CANCELLED` and triggered `auto-chain: generate_all_styled_racing_lines failed` — even though the curves existed.

### 3. Z-floating ("rubber band suspended around the track") — FIXED in align operator only

**Diagnosis confirmed by inspecting JSONs:**
- `temp_data/{driver}_*_hifi_path.json` has every point at `z = 0.0` (verified for NOR, SAI). FastF1 hifi-path bake never carries elevation.
- `Q_RACING_LINE` is also written at Z=0 (`f1_track_viz.py:1445`: `co = (raceline[i,0], raceline[i,1], 0.0, 1.0)`).
- Therefore the styled racing lines are at Z=0 too, AND Kabsch input/output is at Z≈0.
- Track .blend has 3D elevation (Miami has the bridge, etc.), so a Z=0 path floats above the surface in some sections and dives under in others.

**Fix in `OBJECT_OT_AlignPathToRacingLine.execute()`:** after `P_out` is computed, raycast each output point's XY downward against the track mesh and snap Z to the hit point. Track mesh source: `props.track_mesh` → fallback to `bpy.data.objects.get("Track")`. On miss, leaves Z untouched. Logs `[ALIGN] Z-snap to '<mesh>': N/M pts hit`.

**NOT FIXED:** the styled racing lines themselves are still at Z=0. The `raceline_z` array I added to `OBJECT_OT_GenerateAllStyledRacingLines` reads Z off `Q_RACING_LINE`, but Q is always 0. The styled lines visually float at Z=0 — only the driving paths get Z-snapped. If the user wants the styled-line CURVES to also lie on the track (purely cosmetic since they're reference geometry), `OBJECT_OT_GenerateRacingLine` itself needs to either raycast Z onto the track mesh when writing Q_RACING_LINE, or the styled-line gen needs its own raycast pass. Tomorrow's call.

### 4. Kabsch search picking wrong R ("flipped/oriented wrong") — FIXED via direction reversal

**Diagnosis:** With Z-snap added, console showed `[ALIGN] Z-snap to 'Track': 115/1066 pts hit` — only 11% on track. Path was wildly XY-off. Cause: F1 telemetry from FastF1 traverses Miami in the OPPOSITE cyclic direction from `Q_RACING_LINE` (which is built from the centerline of the .blend mesh). The original best-shift loop only rolled Q's index — it never reversed P. With opposite traversal, no shift gives a low RMS, Kabsch picks a tortured rotation = "flipped" output.

**Fix:** in the best-shift search, try forward AND reversed P, pick lowest RMS overall. Final Kabsch uses the winning direction. R is applied to FORWARD `P_raw` so the output curve's index order is preserved (car still drives in telemetry direction). Projection's `expected_k` formula was also updated to flip when `dir=reversed`.

Logs `[ALIGN] best fit: dir=<forward/reversed>, shift=N, rms=Xm`.

**Result on Miami:** `dir=reversed, shift=377, rms=6.73m`. Z-snap hit rate doubled from 115/1066 → 529/1066 at blend=0.0.

### 5. `alignment_blend` defaulted to 0.0 (no UI to change it) — FIXED

The standalone addon's `VIEW3D_PT_F1TrackPanel` exposed this slider; the merge dropped that panel. The merged `F1 Track Setup` subpanel doesn't expose it either. User had no UI to change blend.

**Fix:**
- Default `alignment_blend = 0.9` in `F1TrackVizProperties` (was 0.0).
- Slider added to F1 Studio panel just under GENERATE SCENE button.

For existing .blends the saved value persists, so the user must drag the slider once on each pre-existing scene. New scenes get 0.9 default.

### 6. Stale Bahrain JSONs leaking into Miami — FIXED via auto-chain extension

`OBJECT_OT_GenerateAllStyledRacingLines` filters JSONs by `source.grand_prix` and `source.season` ONLY when `props.style_json_path` is set. If empty, processes every JSON in `style_params/`. Without an auto-export step, the user only had old Bahrain JSONs sitting there → styled lines built from Bahrain corner data applied to Miami's Q.

**Fix in `_pipeline_finish` (`f1_pipeline.py`):** the auto-chain now does:
1. `bpy.ops.object.export_driver_style()` — writes fresh per-driver style JSONs for the current queue into `<db.root>/style_params/`. (Operator already existed and iterates the queue; just wasn't auto-called.)
2. Glob `style_params/*_<gp_slug>_<year>_*.json`, pick the most recently modified, set as `f1_track_viz_props.style_json_path`. This activates the styled-line generator's GP+year filter so stale JSONs from other tracks are skipped.
3. Then `f1.generate_all_styled_racing_lines` and `f1.align_all_driver_paths` as before.

Console now logs `[F1 Studio] auto-chain: filter pinned via NOR_miami_grand_prix_2025_lapXX.json` and the BATCH log shows `filter_gp='miami grand prix' filter_yr='2025'`.

If FastF1 export fails (no internet etc.), step 1 prints a warning and the chain still runs against pre-existing JSONs. If glob finds zero matches, `style_json_path` is cleared and styled-line gen falls back to processing every JSON.

---

## Last verified state on Miami (end of today's session)

```
[F1 Studio] auto-chain: filter pinned via SAI_miami_grand_prix_2025_lap19.json
[BATCH] 5 JSON(s) | filter_gp='miami grand prix' filter_yr='2025'
[BATCH] NOR: 10/12 per-corner JSON matched | wrote Q_RACING_LINE_STYLED_NOR
[BATCH] SAI:  8/12 per-corner JSON matched | wrote Q_RACING_LINE_STYLED_SAI
[BATCH] Done: 2 written, 0 skipped

[ALIGN] best fit: dir=reversed, shift=377, rms=6.73m
[ALIGN] Z-snap to 'Track': 529/1066 pts hit
Info: Reshaped 'driving_path_Mclaren' (1066 pts, target=Q_RACING_LINE_STYLED_NOR, blend=0.00)
[ALIGN] best fit: dir=reversed, shift=377, rms=6.65m
[ALIGN] Z-snap to 'Track': 479/1066 pts hit
Info: Reshaped 'driving_path_Ferrari_Sainz' (1066 pts, target=Q_RACING_LINE_STYLED_SAI, blend=0.00)
[ALIGN] Done: 2 aligned, 0 skipped
```

User said "ATLEAST THE DIRECTION IS CORRECT NOW, BUT THE ALIGNMENT STILL IS NOT RIGHT, I MOSTLY THINK THE BLEND IS A BIT LOW, WE CAN MAKE IT 0.9 OR EVEN 1."

User has NOT yet re-tested with `alignment_blend = 0.9`. They closed Blender for the day. The slider is set to 0.0 in the saved Miami .blend and won't update from the new default.

---

## First action tomorrow

1. **Open the Miami .blend, drag the new "Racing Line Blend" slider in the F1 Studio panel from 0.0 → 0.9.** Click Generate Scene. Watch console for:
   - `Reshaped ... blend=0.90` (confirms slider is applied)
   - `[ALIGN] Z-snap to 'Track': N/1066 pts hit` — should jump from ~500 to >900.
   - Visually check whether NOR and SAI's driving paths now sit on the track and follow the Miami racing line shape.

2. **Test Bahrain regression.** Queue HAM + VER (or whoever) for Bahrain, click Generate Scene, watch:
   - `[ALIGN] best fit: dir=<forward/reversed>, shift=N, rms=...m` — note which direction wins.
   - Confirm Bahrain's saved alignment in `tracks.json` still applies (should see `[F1 Studio] Loaded saved alignment for 'bahrain_grand_prix'` in console).
   - Visually check the paths still fit Bahrain's track.

3. If Miami at blend=0.9 still has a meaningful fraction of points off-track (Z-snap hit rate < 90%), the residual is XY-shape mismatch — telemetry polygon shape doesn't quite equal Q's polygon shape, possibly a true reflection (Y-flip) rather than just direction reversal. Add Y-flip + X-flip candidates to the search (4 candidates total: forward, reversed, Y-flipped, Y-flipped-reversed). Pick lowest RMS.

4. (Cosmetic, low priority) If user wants the styled racing lines themselves to also lie on the track surface (currently float at Z=0), add a raycast Z-snap pass to `OBJECT_OT_GenerateRacingLine` so `Q_RACING_LINE` itself has track-elevation Z. Then the cached `raceline_z` in `OBJECT_OT_GenerateAllStyledRacingLines` would write styled lines at proper Z automatically.

---

## Files touched today (uncommitted)

```
launch_control_auto_car_rig/launch_control_auto_car_rig/launch_control/
  operators/f1_track_viz.py
    - 7 class renames (OBJECT_OT_* → F1_OT_*)
    - 7 bl_idname renames (object.* → f1.*)
    - Scene.f1_track_props → Scene.f1_track_viz_props
    - skipped = [] init in OBJECT_OT_GenerateAllStyledRacingLines
    - raceline_z capture (read Q's Z) + write to styled curve points
    - OBJECT_OT_AlignPathToRacingLine.execute():
      - direction-reversal candidate in best-shift search
      - final Kabsch uses winning direction's resampled P
      - projection's expected_k flipped when dir=reversed
      - replaced P_out[:, 2] = 0.0 with raycast Z-snap to track mesh
    - alignment_blend default 0.0 → 0.9

  operators/f1_pipeline.py
    - _pipeline_finish auto-chain extended:
      step 0: bpy.ops.object.export_driver_style()
      step 0b: glob style_params/, pin style_json_path for GP/year filter
      step 1+2: unchanged (styled lines + align)
    - bpy.ops.object.* → bpy.ops.f1.* for the two track-viz ops

  ui/f1_track_setup_panel.py
    - "object.install_f1_dependencies" → "f1.install_track_viz_deps"
    - "object.generate_centerline"     → "f1.generate_centerline"
    - "object.generate_racing_line"    → "f1.generate_racing_line"
    - context.scene.f1_track_props → context.scene.f1_track_viz_props

  ui/f1_studio_panel.py
    - alignment_blend slider exposed under GENERATE SCENE button
```

---

## Outstanding risks / things I'm not sure about

- Bahrain regression untested. The direction-reversal change is "try both, pick lowest RMS" so it should be a strict improvement, but if Bahrain's saved alignment + previous behaviour relied on a quirk, it could shift. Easy verify (item 2 above).
- The auto-chain now ALWAYS calls `export_driver_style` on every Generate Scene click. That's a FastF1 round-trip per click. If user runs Generate Scene many times in succession, they'll hammer FastF1 (cached after first call). Not a real problem but worth knowing.
- The filter pin reads the most-recently-modified matching JSON. If user has both `Lap14.json` and `Lap19.json` for the same driver/track/year (different lap selections), the pin picks one arbitrarily. Both should have the same `source.grand_prix`/`season`, so the filter behaves the same — irrelevant in practice.
- Z-snap only fires when a track mesh is reachable (`props.track_mesh` set, or scene object named `Track`). For Miami, `Track` exists — good. For tracks where neither is true, Z-snap silently skips and the path stays at Z≈0. The console line `[ALIGN] Z-snap skipped: no track mesh` will say so.

End of handoff.
