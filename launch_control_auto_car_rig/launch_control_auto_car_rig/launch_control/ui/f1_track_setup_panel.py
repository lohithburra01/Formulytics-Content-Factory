"""f1_track_setup_panel — minimal UI for the one-time-per-track setup.

Most of the user's flow is back-end: queue drivers → Generate Scene → done.
But two things have to happen ONCE for any new track .blend before the auto-
chain can produce styled lines:

  1. Install F1 track-viz dependencies (scipy, fastf1, quadprog, etc.) into
     the isolated modules/f1_track_viz_deps folder. ~one-time per machine.
  2. Generate CENTERLINE + Q_RACING_LINE for the track mesh. ~one-time per
     track .blend; saved with the file so it carries forward.

This subpanel surfaces those three operators (which would otherwise only be
reachable via F3 search). After setup is complete on a track, the panel
shows ✓ markers and the user never needs to touch it again — Generate Scene
in the F1 Studio panel auto-chains everything.
"""
import bpy
from bpy.types import Panel


def _deps_ok():
    try:
        from ..operators.f1_track_viz import dependencies_available
        return dependencies_available()
    except Exception:
        return False


class PANEL_PT_F1_TrackSetup(Panel):
    bl_label = "F1 Track Setup (one-time per track)"
    bl_idname = "PANEL_PT_f1_track_setup"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'F1 Studio'
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        cl = bpy.data.objects.get("CENTERLINE") is not None
        ql = bpy.data.objects.get("Q_RACING_LINE") is not None
        if cl and ql and _deps_ok():
            self.layout.label(text="✓", icon='CHECKMARK')

    def draw(self, context):
        layout = self.layout
        try:
            props = context.scene.f1_track_viz_props
        except AttributeError:
            layout.label(text="Track-viz module not registered yet.", icon='ERROR')
            return

        # Step 1 — dependencies
        box = layout.box()
        box.label(text="1. Dependencies", icon='IMPORT')
        if _deps_ok():
            box.label(text="✓ Installed (scipy / fastf1 / quadprog / etc.)", icon='CHECKMARK')
        else:
            box.label(text="Required: scipy, fastf1, quadprog, trajectory_planning_helpers", icon='INFO')
            box.operator("f1.install_track_viz_deps", icon='IMPORT')
            box.label(text="Restart Blender after install if prompted.", icon='QUESTION')

        deps = _deps_ok()

        # Step 2 — centerline
        box = layout.box()
        box.label(text="2. Centerline (one-time per track)", icon='SNAP_MIDPOINT')
        col = box.column(align=True)
        col.prop(props, "track_mesh", icon='MESH_PLANE')
        col.prop(props, "centerline_iterations")
        col.prop(props, "centerline_ray_step")
        col.prop(props, "centerline_max_width")
        col.prop(props, "centerline_smooth_sigma")
        row = box.row()
        row.enabled = deps
        row.operator("f1.generate_centerline", icon='SNAP_MIDPOINT')
        if bpy.data.objects.get("CENTERLINE") is not None:
            box.label(text="✓ CENTERLINE in scene", icon='CHECKMARK')

        # Step 3 — Q racing line
        box = layout.box()
        box.label(text="3. Q Racing Line (one-time per track, ~150s)", icon='GP_MULTIFRAME_EDITING')
        col = box.column(align=True)
        col.prop(props, "racing_line_inset")
        col.prop(props, "racing_line_kappa_bound")
        col.prop(props, "racing_line_veh_width")
        col.prop(props, "racing_line_stepsize")
        row = box.row()
        row.enabled = deps and bpy.data.objects.get("CENTERLINE") is not None
        row.operator("f1.generate_racing_line", icon='GP_MULTIFRAME_EDITING')
        if bpy.data.objects.get("Q_RACING_LINE") is not None:
            box.label(text="✓ Q_RACING_LINE in scene — save the .blend", icon='CHECKMARK')

        # Footer
        layout.separator()
        if (
            _deps_ok()
            and bpy.data.objects.get("CENTERLINE") is not None
            and bpy.data.objects.get("Q_RACING_LINE") is not None
        ):
            layout.label(
                text="Setup complete. Generate Scene auto-runs styled lines + alignment.",
                icon='CHECKMARK',
            )


class PANEL_PT_F1_StyleTune(Panel):
    """Iterative tuning of the per-driver styled racing line.

    Lives next to the one-time TrackSetup panel but is conceptually different:
    these sliders re-shape EXISTING styled lines without re-generating Q or
    re-running the centerline. Apply Style Changes calls only
    f1.generate_all_styled_racing_lines, which reads Q from the scene and
    rebuilds the Q_RACING_LINE_STYLED_<driver> curves in-place.
    """

    bl_label = "F1 Per-Driver Style Tuning"
    bl_idname = "PANEL_PT_f1_style_tune"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'F1 Studio'
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        # ✓ when there's at least one styled line in the scene
        n = sum(
            1 for o in bpy.data.objects
            if o.type == 'CURVE'
            and o.name.startswith("Q_RACING_LINE_STYLED_")
            and o.name != "Q_RACING_LINE_STYLED"
        )
        if n > 0:
            self.layout.label(text=f"{n}", icon='OUTLINER_OB_CURVE')

    def draw(self, context):
        layout = self.layout
        try:
            props = context.scene.f1_track_viz_props
        except AttributeError:
            layout.label(text="Track-viz module not registered yet.", icon='ERROR')
            return

        q_present = bpy.data.objects.get("Q_RACING_LINE") is not None
        if not q_present:
            layout.label(text="Generate Q_RACING_LINE first (TrackSetup panel above).", icon='INFO')
            return

        # Algorithm choice
        box = layout.box()
        box.label(text="Algorithm", icon='NODETREE')
        box.prop(props, "style_offset_mode", text="")

        mode = getattr(props, 'style_offset_mode', 'SUBTLE')

        if mode == 'SUBTLE':
            # SUBTLE: Q-anchored, hard per-station headroom clip. Sliders are
            # the lap-wide spread amplifier (separates near-identical drivers)
            # and the headroom fraction (how close to the safe edge any line
            # is allowed to get).
            box = layout.box()
            box.label(text="Subtle Tuning", icon='MOD_CURVE')
            col = box.column(align=True)
            col.prop(props, "style_subtle_max_headroom_frac", slider=True)
            col.prop(props, "style_spread_amplify", slider=True)
            col.separator()
            col.prop(props, "style_master", slider=True)
            box.label(text="Strictly on-track. Lower headroom = closer to Q.",
                      icon='INFO')
        else:
            # APEX_WARP / PER_CORNER / GLOBAL: same shared tunables as before
            is_warp = (mode == 'APEX_WARP')
            box = layout.box()
            box.label(text="Apex-Warp Tuning", icon='MOD_CURVE')
            col = box.column(align=True)
            col.enabled = is_warp
            col.prop(props, "style_spread_amplify", slider=True)
            col.separator()
            col.prop(props, "style_apex_warp_k_apex", slider=True)
            col.prop(props, "style_apex_warp_max_shift_frac", slider=True)
            col.prop(props, "style_apex_warp_post_smooth", slider=True)
            col.separator()
            col.prop(props, "style_master", slider=True)
            if not is_warp:
                box.label(text="Tunables apply only in APEX_WARP mode.", icon='INFO')

        # Apply button — chained operator that rebuilds styled lines AND
        # re-aligns each driving_path_<driver> onto its new styled curve.
        # Without the alignment step the rigs keep following the OLD
        # driving paths, so the slider changes wouldn't move the cars.
        # Q, centerline, and raycasts are NOT touched.
        layout.separator()
        row = layout.row()
        row.scale_y = 1.5
        row.operator(
            "f1.apply_style_tuning",
            text="Apply Style Changes",
            icon='FILE_REFRESH',
        )
        layout.label(
            text="Updates styled lines AND realigns driving paths (cars move).",
            icon='INFO',
        )


classes = (PANEL_PT_F1_TrackSetup, PANEL_PT_F1_StyleTune)
