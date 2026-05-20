"""f1_track_viz — track-viz operators integrated into launch_control.

Originally a standalone addon (f1_track_visualizer_addonLastLastLasttry5.py).
Now a sub-module of launch_control. All operators register via this module's
register() function, called from launch_control/operators/__init__.py.

Owns:
  • F1TrackVizProperties (scene.f1_track_viz_props PointerProperty)
  • Dep installer (isolated to modules/f1_track_viz_deps)
  • Centerline + Q racing line generation (one-time per track)
  • Per-driver styled racing lines (data-driven)
  • Path alignment (single-path manual + batch align-all)

Operator bl_idnames are unchanged from the standalone, so existing
bpy.ops.object.* calls in f1_pipeline.py auto-chain still work.

═══════════════════════════════════════════════════════════════════════════════
SESSION FAILURE LOG — STYLED-LINE PER-DRIVER DIFFERENTIATION
═══════════════════════════════════════════════════════════════════════════════
Recorded 2026-05-02. Read this BEFORE attempting another round of styled-line
algorithm changes. Four hours were spent here producing no working solution.

GOAL THE USER WANTED:
  Per-driver styled racing lines that (1) are derived from telemetry, (2) are
  anchored to Q_RACING_LINE, (3) look like real racing lines (smooth, no
  artifacts), (4) stay within the track edges with vehicle-width safety,
  (5) are VISIBLY different between drivers from any viewport distance,
  (6) are allowed to cross within corners, (7) added without breaking the
  existing addon, (8) without breaking Q-line generation, (9) strictly
  better than what was there before.

ROOT CAUSE OF THE FAILURE — DATA, NOT ALGORITHM:
  The per-corner JSON style params produced by f1_style_extract.py have
  insufficient cross-driver spread to produce visibly different smooth
  displacements from Q. Concretely, on the Miami 2025 set:
    - apex_phase per corner: snaps to ±1 across nearly all drivers (no
      shape-direction differentiation)
    - apex_tightness per corner: spreads only ~5-15% across drivers
    - vu_shape, entry_width, exit_width, smoothness, straight_bias: flat
      zero or flat 1.0 across all drivers (5 of 8 channels are dead inputs)
  With only ~10% spread on a single channel (apex_tightness), no smooth
  Q-anchored offset model can produce visible differentiation while staying
  on-track. The bottleneck is upstream extraction, not the styled-line
  algorithm.

ALGORITHMS ATTEMPTED THIS SESSION AND WHY EACH FAILED:

  GLOBAL (_v4_compute_d_offset_global, original code, kept as fallback):
    Uses lap-wide apex_tightness aggregate (8% spread) to scale a single
    kappa_norm(s) shape derived from Q's geometry. All drivers' lines are
    SCALED COPIES of the same shape. User feedback: "lines are not different
    to each other".

  APEX_WARP (_v4_compute_d_offset_apex_warp, added then deprecated):
    Per-corner dipole — positive gaussian at A, negative at A_new = A +
    apex_phase × shift × L. Encodes apex shift as shape difference. FATAL
    PROPERTY: dipole crosses zero between A and A_new, so the offset's
    mean across the lap is ~0. Drivers ride Q together everywhere except
    at corner peaks. Diagnostic showed mean=0.014m between drivers — invisible.
    No amount of magnitude amplification fixes this; 3× zero is still zero.

  PER_CORNER (_v4_compute_d_offset, pre-existing dead code, briefly enabled):
    Per-corner single-pole gaussian with WIDE sigma (2.5 × L). Tails overlap
    onto straights → continuous across-lap differentiation. PROBLEM: function
    has no per-station headroom clip, only a fraction-of-width global clip.
    On tracks where Q hugs one kerb on a connecting straight, the wide
    gaussian tail pushed cars OFF-TRACK. User feedback: "PER_CORNER GAUSSIAN
    IS THE FUCKING WORST SOLUTION, THE LINES ARE GOING OUT OF TRACK".

  HYBRID (_v4_compute_d_offset_hybrid, current APEX_WARP dispatcher target):
    Sum of (A) wide-sigma single-pole baseline (PER_CORNER's continuity) +
    (B) narrow dipole (APEX_WARP's apex shape) + per-station headroom clip
    (APEX_WARP's safety) + cross-driver amplification (upstream in operator).
    Diagnostic showed styled-line spread max=2.4m mean=0.15m — mathematically
    100× APEX_WARP-only and "genuinely different" by the threshold. User
    feedback: "ITS NOT AT ALL DIFFERENT, THEY ARE FUCKING OVERLAPPING".
    Either the visual perception threshold for differentiated racing lines is
    much higher than these numbers, or the user is judging against a mental
    model the diagnostic doesn't capture, or the alignment chain is washing
    out the difference. Was not resolved.

WHAT IS NOW IN THE FILE THAT WASN'T BEFORE THIS SESSION:
  • _v4_compute_d_offset_apex_warp (~150 lines, dipole-only — UNUSED, only
    reachable by direct call)
  • _v4_compute_d_offset_hybrid (~150 lines, current APEX_WARP target)
  • F1_OT_ApplyStyleTuning operator (chains generate-styled + align-all so
    iteration doesn't require re-running Q)
  • Cross-driver per-corner apex_tightness pre-pass + per-driver amplification
    block inside F1_OT_GenerateAllStyledRacingLines.execute
  • Per-station headroom (hr_pos_m / hr_neg_m → headroom_pos_d / headroom_neg_d)
    computation in F1_OT_GenerateAllStyledRacingLines.execute
  • End-of-Apply diagnostic dump in F1_OT_ApplyStyleTuning.execute (identity
    + pairwise spread for driving paths and styled lines)
  Plus on F1TrackVizProperties:
  • style_offset_mode (Enum: APEX_WARP / PER_CORNER / GLOBAL, default APEX_WARP)
  • style_apex_warp_k_apex, style_apex_warp_max_shift_frac,
    style_apex_warp_post_smooth, style_spread_amplify (FloatProperty sliders)
  Plus a new panel in ui/f1_track_setup_panel.py:
  • PANEL_PT_F1_StyleTune (sliders + Apply button) — registered in
    ui/__init__.py classes_tuple

THE ACTUAL PATH FORWARD (DON'T REPEAT WHAT FAILED):
  Improve f1_style_extract.py first, BEFORE touching the displacement model.
  Specifically the per-corner JSON should carry, in addition to the existing
  fields, telemetry-anchored station indices that vary meaningfully across
  drivers:
    - vmin_station_offset:     where the speed minimum sits relative to Q's
                               apex (in arc-length stations or meters)
    - brake_release_station:   where the driver came off the brakes
    - throttle_on_station:     where the driver got back on power
    - peak_lateral_g:          peak |lateral G| in the corner
  These vary 30-100% across F1 drivers in real telemetry — enough signal
  for a smooth displacement model to produce visibly different lines without
  cross-driver amplification gymnastics.

  Once those fields exist in the JSON, the HYBRID's baseline magnitude can
  be driven by (1 - peak_lateral_g_normalized) instead of (1 - apex_tightness),
  and the dipole's A_new can be set from vmin_station_offset directly. The
  algorithm doesn't need to change; the inputs do.

  If you must change the algorithm itself before fixing extraction, the
  honest answer is that NO Q-anchored displacement model will satisfy the
  user's spec on the current data. Consider instead a fundamentally different
  approach: per-corner local QP solve with each driver's apex constraint
  shifted by their telemetry-derived apex location (vmin), giving each driver
  their own min-curvature line through that corner. More expensive but breaks
  out of the "scaled-copies-of-Q" trap entirely.
═══════════════════════════════════════════════════════════════════════════════
"""
import bpy
import os
import sys
import site
import subprocess
import tempfile
import csv
import math
import importlib.util
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import (
    StringProperty, EnumProperty, FloatProperty,
    BoolProperty, IntProperty, PointerProperty
)


# ═══════════════════════════════════════════════════════════════════════════════
# DEPENDENCY MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

def get_modules_path():
    # Isolated dependencies dir for this addon. Living under modules/ but in
    # our own subfolder lets us install/upgrade/clean without colliding with
    # other addons' deps (or leftover stale wheels from earlier failed runs).
    return bpy.utils.user_resource(
        "SCRIPTS", path="modules/f1_track_viz_deps", create=True
    )

def append_modules_to_sys_path(modules_path):
    # Insert at the FRONT so our isolated wheels shadow any stale copies
    # that earlier install attempts left in <user>/modules/.
    if modules_path in sys.path:
        sys.path.remove(modules_path)
    sys.path.insert(0, modules_path)
    site.addsitedir(modules_path)

def check_dependencies():
    # quadprog before trajectory_planning_helpers, and pinned: tph pulls
    # quadprog as a transitive dep, and unpinned latest has no cp311
    # win_amd64 wheel — pip would fall back to a source build that fails
    # against Blender's header-less Python. Pinning >=0.1.12 forces a
    # version with a published wheel.
    required = {
        "fastf1": "fastf1",
        "pandas": "pandas",
        "scipy":  "scipy",
        "quadprog": "quadprog>=0.1.12",
        "trajectory_planning_helpers": "trajectory-planning-helpers",
    }
    missing = []
    for module_name, pip_name in required.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(pip_name)
    return missing

def install_package_to_blender(package, modules_path):
    # --only-binary + --prefer-binary so pip refuses source builds —
    # Blender's bundled Python ships without development headers, so any
    # C extension that has to compile from source will fail.
    # --upgrade is still needed: without it pip skips existing package
    # dirs and we end up with old code paired with new dist-info metadata.
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "--upgrade", "--target", modules_path,
            "--only-binary=:all:", "--prefer-binary",
            package
        ])
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install {package}: {e}")
        return False

def dependencies_available():
    return len(check_dependencies()) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# NUMPY UTILITY FUNCTIONS (used by centerline, racing line, alignment)
# ═══════════════════════════════════════════════════════════════════════════════

def _resample_equidistant(coords, n):
    import numpy as np
    from scipy.interpolate import interp1d

    mask = np.ones(len(coords), dtype=bool)
    for i in range(1, len(coords)):
        if np.linalg.norm(coords[i] - coords[i - 1]) < 1e-10:
            mask[i] = False
    coords = coords[mask]

    if len(coords) < 4:
        raise ValueError(f"Too few unique points ({len(coords)}) for resampling")

    closed = np.vstack((coords, coords[0]))
    diffs = closed[1:] - closed[:-1]
    dists = np.linalg.norm(diffs, axis=1)
    cum = np.concatenate(([0], np.cumsum(dists)))
    total = cum[-1]

    if total < 1e-10:
        raise ValueError("Path has zero total length")

    targets = np.linspace(0, total, n, endpoint=False)

    m = len(coords)
    ext_coords = np.vstack((coords, coords, coords))
    ext_cum = np.concatenate((cum[:-1] - total, cum[:-1], cum[:-1] + total))

    fx = interp1d(ext_cum, ext_coords[:, 0], kind='cubic')
    fy = interp1d(ext_cum, ext_coords[:, 1], kind='cubic')

    out = np.zeros((n, 2))
    out[:, 0] = fx(targets)
    out[:, 1] = fy(targets)
    return out


def _resample_equidistant_3d(coords, n):
    import numpy as np
    from scipy.interpolate import interp1d

    mask = np.ones(len(coords), dtype=bool)
    for i in range(1, len(coords)):
        if np.linalg.norm(coords[i] - coords[i - 1]) < 1e-10:
            mask[i] = False
    coords = coords[mask]

    if len(coords) < 4:
        raise ValueError(f"Too few unique points ({len(coords)}) for resampling")

    closed = np.vstack((coords, coords[0]))
    diffs = closed[1:] - closed[:-1]
    dists = np.linalg.norm(diffs, axis=1)
    cum = np.concatenate(([0], np.cumsum(dists)))
    total = cum[-1]

    if total < 1e-10:
        raise ValueError("Path has zero total length")

    targets = np.linspace(0, total, n, endpoint=False)

    m = len(coords)
    ext_coords = np.vstack((coords, coords, coords))
    ext_cum = np.concatenate((cum[:-1] - total, cum[:-1], cum[:-1] + total))

    interps = []
    for axis in range(3):
        interps.append(interp1d(ext_cum, ext_coords[:, axis], kind='cubic'))

    out = np.zeros((n, 3))
    for axis in range(3):
        out[:, axis] = interps[axis](targets)
    return out


def _kabsch_alignment(P, Q):
    import numpy as np

    P = np.asarray(P, dtype=float)
    Q = np.asarray(Q, dtype=float)
    assert P.shape == Q.shape

    centroid_P = P.mean(axis=0)
    centroid_Q = Q.mean(axis=0)

    Pc = P - centroid_P
    Qc = Q - centroid_Q

    H = Pc.T @ Qc
    U, S, Vt = np.linalg.svd(H)

    R = Vt.T @ U.T
    if np.linalg.det(R) < 0:
        Vt[-1, :] *= -1
        R = Vt.T @ U.T

    t = centroid_Q - R @ centroid_P
    P_aligned = (R @ P.T).T + t
    return R, t, P_aligned


# ═══════════════════════════════════════════════════════════════════════════════
# STYLE LAYER — corner detection + parametric α_style builder
# ═══════════════════════════════════════════════════════════════════════════════

def _detect_corners_on_centerline(coords, kappa_hi_frac=0.25, kappa_lo_frac=0.08, min_corner_len=6):
    """
    Segment a closed 2D centerline into corners with hysteresis on |κ|.

    Returns (corners, corner_id, phase, kappa_sign):
        corners     list of dicts {entry, apex, exit, kappa_sign}
        corner_id   (n,) int  — corner index per station, -1 on straights
        phase       (n,) float — [0,1] along corner (0=entry, 1=exit), 0 on straights
        kappa_sign  (n,) float — +1 inside left corner, -1 inside right corner, 0 straight
    """
    import numpy as np
    from scipy.ndimage import gaussian_filter1d

    n = len(coords)

    tang = np.zeros((n, 2))
    for i in range(n):
        d = coords[(i + 3) % n] - coords[(i - 3) % n]
        nm = np.linalg.norm(d)
        tang[i] = d / nm if nm > 1e-8 else np.array([1.0, 0.0])

    kappa = np.zeros(n)
    for i in range(n):
        t1 = tang[i]
        t2 = tang[(i + 1) % n]
        cross = t1[0] * t2[1] - t1[1] * t2[0]
        dot = float(np.clip(np.dot(t1, t2), -1.0, 1.0))
        kappa[i] = math.copysign(math.acos(dot), cross)

    kappa_s = gaussian_filter1d(np.tile(kappa, 3), sigma=5.0)[n:2 * n]
    kappa_abs = np.abs(kappa_s)
    kappa_max = float(kappa_abs.max())
    if kappa_max < 1e-6:
        return [], np.full(n, -1, dtype=int), np.zeros(n), np.zeros(n)

    kappa_hi = kappa_hi_frac * kappa_max
    kappa_lo = kappa_lo_frac * kappa_max
    above_hi = kappa_abs > kappa_hi
    above_lo = kappa_abs > kappa_lo

    # Roll so index 0 is on a straight (simplifies cyclic corner walks)
    straights = np.where(~above_lo)[0]
    if len(straights) == 0:
        apex = int(np.argmax(kappa_abs))
        corners = [{'entry': 0, 'apex': apex, 'exit': n - 1,
                    'kappa_sign': int(math.copysign(1, kappa_s[apex]))}]
        return (corners,
                np.zeros(n, dtype=int),
                np.linspace(0.0, 1.0, n),
                np.full(n, corners[0]['kappa_sign'], dtype=float))

    roll = int(straights[0])
    above_hi_r = np.roll(above_hi, -roll)
    above_lo_r = np.roll(above_lo, -roll)
    kappa_abs_r = np.roll(kappa_abs, -roll)
    kappa_s_r = np.roll(kappa_s, -roll)

    corners = []
    i = 0
    while i < n:
        if above_hi_r[i]:
            core_start = i
            while i < n and above_hi_r[i]:
                i += 1
            core_end = i - 1

            entry = core_start
            while entry > 0 and above_lo_r[entry - 1]:
                entry -= 1
            exit_ = core_end
            while exit_ < n - 1 and above_lo_r[exit_ + 1]:
                exit_ += 1

            if exit_ - entry + 1 >= min_corner_len:
                apex_local = core_start + int(np.argmax(kappa_abs_r[core_start:core_end + 1]))
                corners.append({
                    '_entry_r': entry,
                    '_apex_r': apex_local,
                    '_exit_r': exit_,
                    'L': exit_ - entry + 1,
                    'kappa_sign': int(math.copysign(1, kappa_s_r[apex_local])),
                })
        else:
            i += 1

    # Build per-station arrays in rolled coords, then unroll
    corner_id_r = np.full(n, -1, dtype=int)
    phase_r = np.zeros(n)
    sign_arr_r = np.zeros(n)
    for ci, c in enumerate(corners):
        entry, exit_ = c['_entry_r'], c['_exit_r']
        L = exit_ - entry + 1
        for k, s in enumerate(range(entry, exit_ + 1)):
            corner_id_r[s] = ci
            phase_r[s] = k / max(L - 1, 1)
            sign_arr_r[s] = c['kappa_sign']

    corner_id = np.roll(corner_id_r, roll)
    phase = np.roll(phase_r, roll)
    sign_arr = np.roll(sign_arr_r, roll)

    for c in corners:
        c['entry'] = (c.pop('_entry_r') + roll) % n
        c['apex']  = (c.pop('_apex_r')  + roll) % n
        c['exit']  = (c.pop('_exit_r')  + roll) % n

    return corners, corner_id, phase, sign_arr


def _compute_alpha_style(corners, corner_id, phase, kappa_sign, wr_safe, wl_safe, params,
                         corner_overrides=None):
    """
    Build lateral-offset warp α_style(s) from style params.

    Convention: positive α = RIGHT (TUMFTM right-normal), negative = LEFT.
    Inside of a left corner (kappa_sign=+1) is LEFT → apex pull is negative α.

    Anti-wobble treatment:
      (A) Entry/exit anchors shift with apex_phase to prevent bump overlap.
      (B) σ adapts to corner length and shrinks near the apex to prevent
          overlap when anchors compress (e.g. late apex → exit anchor near apex).
      (C) Per-station |α_style| capped at 70% of available width before the
          hard clip, so stacked bumps cannot saturate the boundary clipper.

    corner_overrides (optional): list of per-corner dicts in lap order, each
        with apex_phase / apex_tightness / vu_shape. Used when its length
        matches len(corners) — those three params are then per-corner instead
        of lap-wide. Other params (widths, smoothness, lr_asymmetry, master)
        remain global.
    """
    import numpy as np
    from scipy.ndimage import gaussian_filter1d

    n = len(corner_id)
    alpha = np.zeros(n)

    master = float(params['master'])
    if master < 1e-6:
        return alpha

    entry_w = float(params['entry_width'])
    exit_w  = float(params['exit_width'])
    lr_asym = float(params['lr_asymmetry'])

    # Build per-corner derivations. If corner_overrides is consumable, the
    # driver's per-corner apex_phase/apex_tightness/vu_shape replace the
    # global lap-wide values for that corner. Otherwise the globals are
    # broadcast to every corner (legacy behaviour).
    Nc = len(corners)
    use_overrides = (
        isinstance(corner_overrides, list)
        and len(corner_overrides) == Nc
        and Nc > 0
    )

    g_ap = float(params['apex_phase'])
    g_at = float(params['apex_tightness'])
    g_vu = float(params['vu_shape'])

    apex_target_c  = np.zeros(Nc)
    vu_bias_c      = np.zeros(Nc)
    apex_tight_c   = np.zeros(Nc)
    entry_anchor_c = np.zeros(Nc)
    exit_anchor_c  = np.zeros(Nc)
    half_gap_min_c = np.zeros(Nc)

    for ci in range(Nc):
        if use_overrides:
            co = corner_overrides[ci] or {}
            ap = float(co.get('apex_phase',     g_ap))
            at = float(co.get('apex_tightness', g_at))
            vu = float(co.get('vu_shape',       g_vu))
        else:
            ap, at, vu = g_ap, g_at, g_vu

        ap_t = 0.5 + 0.35 * ap                                  # [0.15, 0.85]
        ea   = max(0.05, ap_t - 0.35)                           # (A) anchors follow apex
        xa   = min(0.95, ap_t + 0.35)
        hg   = max(1e-3, min(ap_t - ea, xa - ap_t))

        apex_target_c[ci]  = ap_t
        vu_bias_c[ci]      = (vu + 1.0) * 0.5                   # 0=V, 1=U
        apex_tight_c[ci]   = at
        entry_anchor_c[ci] = ea
        exit_anchor_c[ci]  = xa
        half_gap_min_c[ci] = hg

    for i in range(n):
        cid = int(corner_id[i])
        if cid < 0:
            continue

        phi = float(phase[i])
        ks = float(kappa_sign[i])
        in_dir = -ks
        out_dir = ks

        w_in  = wr_safe[i] if in_dir > 0 else wl_safe[i]
        w_out = wr_safe[i] if out_dir > 0 else wl_safe[i]
        w_sym = min(w_in, w_out)

        apex_target  = float(apex_target_c[cid])
        vu_bias      = float(vu_bias_c[cid])
        apex_tight   = float(apex_tight_c[cid])
        entry_anchor = float(entry_anchor_c[cid])
        exit_anchor  = float(exit_anchor_c[cid])
        half_gap_min = float(half_gap_min_c[cid])

        # (B) Per-corner σ: length-adaptive base, clamped so bumps don't overlap.
        L = int(corners[cid]['L'])
        L_scale = math.sqrt(max(L, 10) / 30.0)            # sqrt so extremes stay tame
        base_apex = max(0.07, min(0.15, 0.10 * L_scale))
        # V-line: narrow apex bump (sharp); U-line: broad apex bump.
        base_apex *= (0.75 + 0.50 * vu_bias)              # V:0.75× … U:1.25×
        sigma_apex = min(base_apex, 0.45 * half_gap_min)  # 2σ < half-gap
        sigma_apex = max(sigma_apex, 0.04)
        sigma_ee = max(0.05, min(0.10, 0.07 * L_scale))

        apex_mag  = apex_tight * 0.80 * w_in  * math.exp(-((phi - apex_target)  ** 2) / (2 * sigma_apex ** 2))
        entry_mag = entry_w    * 0.70 * w_sym * math.exp(-((phi - entry_anchor) ** 2) / (2 * sigma_ee   ** 2))
        exit_mag  = exit_w     * 0.70 * w_sym * math.exp(-((phi - exit_anchor)  ** 2) / (2 * sigma_ee   ** 2))

        a = in_dir * apex_mag + out_dir * entry_mag + out_dir * exit_mag
        a *= (1.0 + lr_asym * ks)
        alpha[i] = a

    # Straight bias — look AHEAD to next corner's outside direction
    straight_b = float(params['straight_bias'])
    if abs(straight_b) > 1e-6:
        next_ks = np.zeros(n)
        last = 0.0
        for i in range(2 * n - 1, -1, -1):
            idx = i % n
            if corner_id[idx] >= 0:
                last = float(kappa_sign[idx])
            next_ks[idx] = last

        for i in range(n):
            if corner_id[i] >= 0:
                continue
            out_dir = 1 if next_ks[i] >= 0 else -1
            w_o = wr_safe[i] if out_dir > 0 else wl_safe[i]
            alpha[i] += straight_b * 0.40 * w_o * out_dir

    alpha *= master

    # (C) Soft cap at 70% of available width BEFORE the hard clip runs.
    # Leaves 30% headroom for smoothness blur without triggering clip kinks.
    alpha = np.clip(alpha, -0.70 * wl_safe, 0.70 * wr_safe)

    sigma = 1.0 + 10.0 * float(params['smoothness'])
    alpha = gaussian_filter1d(np.concatenate([alpha, alpha, alpha]), sigma=sigma)[n:2 * n]

    return alpha


# ═══════════════════════════════════════════════════════════════════════════════
# PROPERTIES
# ═══════════════════════════════════════════════════════════════════════════════

class F1TrackVizProperties(PropertyGroup):
    # --- Telemetry fetch ---
    season: StringProperty(name="Season", default="2023")
    grand_prix: StringProperty(name="Grand Prix", default="Bahrain")
    session_type: EnumProperty(
        name="Session",
        items=[
            ('R', "Race", ""), ('Q', "Qualifying", ""),
            ('FP1', "FP1", ""), ('FP2', "FP2", ""), ('FP3', "FP3", ""),
        ],
        default='R'
    )
    driver_id: StringProperty(name="Driver", default="VER")
    cache_dir: StringProperty(
        name="Cache Dir",
        default=os.path.join(tempfile.gettempdir(), "fastf1_cache"),
        subtype='DIR_PATH'
    )
    csv_file_path: StringProperty(name="CSV File", default="", subtype='FILE_PATH')

    # --- Track curve creation ---
    scale_factor: FloatProperty(name="Scale", default=10.0, min=0.1, max=100.0)
    curve_type: EnumProperty(
        name="Curve Type",
        items=[('NURBS', "NURBS", ""), ('BEZIER', "Bezier", "")],
        default='NURBS'
    )
    track_thickness: FloatProperty(name="Thickness", default=0.05, min=0.01, max=1.0)
    curve_resolution: FloatProperty(name="Resolution", default=12, min=1, max=64)

    # --- Track mesh (eyedropper) ---
    track_mesh: PointerProperty(
        name="Track Mesh",
        description="Select the track road mesh object",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'MESH'
    )

    # --- Centerline ---
    centerline_iterations: IntProperty(
        name="Iterations", default=5, min=1, max=10,
        description="Number of centerline refinement iterations"
    )
    centerline_ray_step: FloatProperty(
        name="Ray Step", default=0.15, min=0.05, max=1.0,
        description="Step size for edge-detection raycasts (BU)"
    )
    centerline_max_width: FloatProperty(
        name="Max Width", default=30.0, min=5.0, max=100.0,
        description="Maximum half-width to search for track edges (BU)"
    )
    centerline_smooth_sigma: FloatProperty(
        name="Smooth Sigma", default=2.0, min=0.5, max=10.0,
        description="Gaussian sigma for centerline smoothing"
    )

    # --- Racing line constraints ---
    racing_line_inset: FloatProperty(
        name="Base Edge Inset", default=0.3, min=0.0, max=2.0,
        description="Safety inset from track edges (BU)"
    )
    racing_line_kappa_bound: FloatProperty(
        name="Base Max Curvature", default=0.5, min=0.05, max=2.0,
        description="Maximum curvature bound (rad/m)"
    )
    racing_line_veh_width: FloatProperty(
        name="Vehicle Width", default=2.0, min=0.5, max=4.0,
        description="Vehicle width in meters (F1 car ~2.0m)"
    )
    racing_line_stepsize: FloatProperty(
        name="Interp Stepsize", default=2.0, min=0.5, max=10.0,
        description="Interpolation step size in meters for final raceline"
    )

    # --- Style Layer (parametric post-warp on Q_RACING_LINE) ---
    # Designed so per-corner telemetry-driven values can later replace the global sliders.
    style_enabled: BoolProperty(
        name="Enable Style Layer", default=True,
        description="If off, Q_RACING_LINE_STYLED won't be generated"
    )
    style_master: FloatProperty(
        name="Master Strength", default=1.0, min=0.0, max=1.0,
        description="0 = identical to Q_RACING_LINE, 1 = full style effect"
    )
    style_apex_phase: FloatProperty(
        name="Apex Phase", default=0.0, min=-1.0, max=1.0,
        description="-1 early apex (tight-in, wide-out) ↔ +1 late apex (wide-in, tight-out for exit speed)"
    )
    style_apex_tightness: FloatProperty(
        name="Apex Tightness", default=0.5, min=0.0, max=1.0,
        description="0 conservative margin from inside edge ↔ 1 kerb-riding aggressive"
    )
    style_entry_width: FloatProperty(
        name="Entry Width", default=0.0, min=-1.0, max=1.0,
        description="-1 tight entry ↔ +1 wide entry"
    )
    style_exit_width: FloatProperty(
        name="Exit Width", default=0.0, min=-1.0, max=1.0,
        description="-1 tight exit ↔ +1 wide track-out"
    )
    style_vu_shape: FloatProperty(
        name="V ↔ U Shape", default=0.0, min=-1.0, max=1.0,
        description="-1 V-line (sharp apex, late-brake/early-throttle) ↔ +1 U-line (broad arc, momentum)"
    )
    style_straight_bias: FloatProperty(
        name="Straight Bias", default=0.0, min=-1.0, max=1.0,
        description="-1 toward inside of next corner ↔ +1 toward outside (setup position)"
    )
    style_smoothness: FloatProperty(
        name="Smoothness", default=0.3, min=0.0, max=1.0,
        description="Low-pass filter on α_style — higher = smoother transitions"
    )
    style_lr_asymmetry: FloatProperty(
        name="L/R Asymmetry", default=0.0, min=-1.0, max=1.0,
        description="+1 apply style only to left corners, -1 only to right, 0 symmetric"
    )
    style_offset_mode: EnumProperty(
        name="Style Offset Mode",
        description=(
            "How the per-driver d-offset profile is built. SUBTLE (default) is Q-anchored "
            "with a hard per-station headroom clip — strictly on-track, small but visible "
            "per-driver variance. APEX_WARP encodes early-vs-late apex as a shape difference "
            "(lines can cross mid-corner; can run wide on tracks with narrow connecting "
            "straights). GLOBAL is the legacy lap-wide-aggregate path (no headroom clip). "
            "PER_CORNER sums per-corner gaussians without the apex-shift dipole."
        ),
        items=[
            ('SUBTLE',     "Subtle Q-anchored (recommended)",
             "Single Q-derived κ shape, scaled per driver, with hard per-station headroom "
             "clip — strictly cannot leave the track"),
            ('APEX_WARP',  "Apex-Warp",
             "Per-corner dipole at A and A_new = A + apex_phase × 0.30 × L; "
             "drivers' lines cross naturally where their apex_phase differs"),
            ('PER_CORNER', "Per-Corner Gaussians",
             "Existing _v4_compute_d_offset — sums per-corner gaussians, no apex shift"),
            ('GLOBAL',     "Global (legacy)",
             "Existing _v4_compute_d_offset_global — single lap-wide shape, scaled per driver"),
        ],
        default='SUBTLE',
    )
    style_subtle_max_headroom_frac: FloatProperty(
        name="Subtle: Max Headroom",
        default=0.35, min=0.05, max=1.0,
        description=(
            "SUBTLE mode only. Hard per-station cap on d_offset, expressed as a fraction of "
            "the available room from Q to the safe edge (after vehicle half-width + 0.15 m "
            "margin). 0.35 = lines may use up to 35% of the way to the safe edge — strictly "
            "on-track, lines stay close to Q. Raise toward 0.7 for wider variance, lower "
            "toward 0.15 for nearly-overlapping lines. 1.0 sits right at the safe edge."
        )
    )
    style_apex_warp_k_apex: FloatProperty(
        name="Magnitude (k_apex)",
        default=0.55, min=0.0, soft_max=1.5, max=3.0,
        description=(
            "How many METERS of cross-track displacement the dipole tries to apply at full "
            "looseness. Per-station headroom and the per-corner inside_budget will still cap "
            "this — raising it just lets corners that had spare room use more of it. Safe to "
            "raise; the per-station clip prevents off-track. Default 0.55."
        )
    )
    style_apex_warp_max_shift_frac: FloatProperty(
        name="Apex Shift (frac of L)",
        default=0.30, min=0.0, max=0.50,
        description=(
            "How far the driver's apex (A_new) is allowed to slide along the corner from Q's "
            "geometric apex (A), expressed as a fraction of corner length, when apex_phase = ±1. "
            "Bigger values amplify the SHAPE difference between early-apex and late-apex drivers "
            "(stronger entry-wide / exit-tight contrast), but can encroach on adjacent straights "
            "if pushed past ~0.40. Default 0.30."
        )
    )
    style_apex_warp_post_smooth: FloatProperty(
        name="Post-Smooth (stations)",
        default=4.0, min=0.0, max=15.0,
        description=(
            "Periodic gaussian sigma for the final low-pass over the summed d_offset. Higher = "
            "smoother transitions across corner boundaries, lower = sharper apex-shift signature. "
            "Raise toward 6-8 if you see kissing/wiggles between adjacent corners on chicanes; "
            "drop toward 2-3 if the apex-shift effect feels washed out. Default 4.0."
        )
    )
    style_spread_amplify: FloatProperty(
        name="Driver Spread Amplify",
        default=3.0, min=1.0, soft_max=8.0, max=15.0,
        description=(
            "Amplifies per-driver apex_tightness deviation from the cross-driver mean by this "
            "factor. Raw telemetry typically spreads only 5-15% across drivers — the resulting "
            "5-10cm peak displacement difference is invisible at viewport distance. Amplify=3.0 "
            "spreads it ~3× while keeping the average behaviour identical to raw telemetry. "
            "Each driver's amplified value is clipped to [0,1] so it stays physically meaningful. "
            "1.0 = use raw telemetry (often invisible). Default 3.0."
        )
    )
    style_json_path: StringProperty(
        name="Style JSON", default="", subtype='FILE_PATH',
        description="Path to style params JSON exported by the F1 Race Replay Studio addon"
    )

    # --- Alignment ---
    alignment_target_curve: PointerProperty(
        name="Target Line",
        description="Pick any Q_RACING_LINE* curve in the scene (eyedropper). Used by the single-path Align/Reshape button.",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'CURVE' and obj.name.startswith("Q_RACING_LINE")
    )
    overwrite_source_path: BoolProperty(
        name="Overwrite Source Curve",
        default=True,
        description="Replace the Driving Path's own geometry with the aligned result, so any follow-path rig on that curve picks up the new shape automatically. Turn OFF if you want a preview-only align without modifying the source."
    )
    alignment_samples: IntProperty(
        name="Resample Points", default=500, min=50, max=5000,
        description="Number of equidistant points for alignment resampling"
    )
    alignment_blend: FloatProperty(
        name="Racing Line Blend", default=0.9, min=0.0, max=1.0,
        description="0.0 = Raw Driver Path (Kabsch only). 1.0 = Fully snapped to Q_RACING_LINE"
    )

    # --- Source driving path ---
    driving_path: PointerProperty(
        name="Driving Path",
        description="Select the raw telemetry driving path curve",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'CURVE'
    )


# ═══════════════════════════════════════════════════════════════════════════════
# OPERATORS
# ═══════════════════════════════════════════════════════════════════════════════

class F1_OT_InstallTrackVizDeps(Operator):
    bl_idname = "f1.install_track_viz_deps"
    bl_label = "Install Dependencies"
    bl_description = "Install fastf1, pandas, scipy"

    def execute(self, context):
        modules_path = get_modules_path()
        append_modules_to_sys_path(modules_path)
        missing = check_dependencies()
        if not missing:
            self.report({'INFO'}, "All dependencies already installed!")
            return {'FINISHED'}

        ok = 0
        for pkg in missing:
            self.report({'INFO'}, f"Installing {pkg}...")
            if install_package_to_blender(pkg, modules_path):
                ok += 1
                self.report({'INFO'}, f"Installed {pkg}")
            else:
                self.report({'ERROR'},
                    f"Failed: {pkg}. If error mentions 'Access is denied' on "
                    f"a .pyd file, close Blender and re-run install from a "
                    f"fresh session before importing the addon's panel.")

        if ok == len(missing):
            self.report({'INFO'}, "All installed! Restart Blender if needed.")
        else:
            self.report({'WARNING'}, f"{ok}/{len(missing)} installed")
        return {'FINISHED'}


class F1_OT_GenerateCenterline(Operator):
    bl_idname = "f1.generate_centerline"
    bl_label = "Generate Centerline"
    bl_description = "Generate TRACK_CENTER_FIXED purely from track mesh geometry"

    @staticmethod
    def _point_on_track(track, inv, ray_dir, x, y):
        from mathutils import Vector as Vec
        origin = Vec((x, y, 10000.0))
        hit, _, _, _ = track.ray_cast(inv @ origin, ray_dir)
        return hit

    @staticmethod
    def _find_edge_dist(track, inv, ray_dir, pt, direction, coarse_step, max_dist):
        from mathutils import Vector as Vec
        last_hit_d = 0.0
        first_miss_d = -1.0
        steps = int(max_dist / coarse_step)

        for si in range(1, steps + 1):
            d_raw = si * coarse_step
            test = pt + direction * d_raw
            origin = Vec((test[0], test[1], 10000.0))
            hit, _, _, _ = track.ray_cast(inv @ origin, ray_dir)
            if hit:
                last_hit_d = d_raw
            else:
                first_miss_d = d_raw
                break

        if first_miss_d < 0:
            return max_dist

        lo, hi = last_hit_d, first_miss_d
        for _ in range(10):
            mid = (lo + hi) * 0.5
            test = pt + direction * mid
            origin = Vec((test[0], test[1], 10000.0))
            hit, _, _, _ = track.ray_cast(inv @ origin, ray_dir)
            if hit:
                lo = mid
            else:
                hi = mid
        return lo

    @staticmethod
    def _walk_track_centerline(track, inv, ray_dir, start_xy, n_target,
                                coarse_step, max_width, step_size):
        import numpy as np
        from mathutils import Vector as Vec

        find_edge = F1_OT_GenerateCenterline._find_edge_dist
        on_track = F1_OT_GenerateCenterline._point_on_track

        pt = np.array(start_xy, dtype=float)
        best_angle = 0.0
        best_width = float('inf')

        for angle_deg in range(0, 180, 5):
            angle = math.radians(angle_deg)
            direction = np.array([math.cos(angle), math.sin(angle)])
            dl = find_edge(track, inv, ray_dir, pt, direction, coarse_step, max_width)
            dr = find_edge(track, inv, ray_dir, pt, -direction, coarse_step, max_width)
            width = dl + dr
            if 1.0 < width < best_width:
                best_width = width
                best_angle = angle

        width_dir = np.array([math.cos(best_angle), math.sin(best_angle)])
        fwd = np.array([-width_dir[1], width_dir[0]])

        dl = find_edge(track, inv, ray_dir, pt, width_dir, coarse_step, max_width)
        dr = find_edge(track, inv, ray_dir, pt, -width_dir, coarse_step, max_width)
        shift = (dl - dr) * 0.5
        pt = pt + width_dir * shift

        points = [pt.copy()]
        max_points = n_target * 3 

        for step_i in range(1, max_points):
            candidate = pt + fwd * step_size

            if not on_track(track, inv, ray_dir, candidate[0], candidate[1]):
                found = False
                for angle_offset in range(5, 91, 5):
                    for sign in [1, -1]:
                        angle = math.radians(angle_offset * sign)
                        rot_fwd = np.array([
                            fwd[0] * math.cos(angle) - fwd[1] * math.sin(angle),
                            fwd[0] * math.sin(angle) + fwd[1] * math.cos(angle)
                        ])
                        test = pt + rot_fwd * step_size
                        if on_track(track, inv, ray_dir, test[0], test[1]):
                            candidate = test
                            fwd = rot_fwd
                            found = True
                            break
                    if found:
                        break
                if not found:
                    print(f"Walk stopped at step {step_i}: can't find forward direction")
                    break

            pt = candidate
            # Find true width direction by scanning angles around fwd-perpendicular
            base_left = np.array([-fwd[1], fwd[0]])
            best_width_dir = base_left
            best_total_width = float('inf')
            for angle_deg in range(-45, 46, 5):
                angle = math.radians(angle_deg)
                test_dir = np.array([
                    base_left[0] * math.cos(angle) - base_left[1] * math.sin(angle),
                    base_left[0] * math.sin(angle) + base_left[1] * math.cos(angle)
                ])
                tdl = find_edge(track, inv, ray_dir, pt, test_dir, coarse_step, max_width)
                tdr = find_edge(track, inv, ray_dir, pt, -test_dir, coarse_step, max_width)
                total = tdl + tdr
                if 0.5 < total < best_total_width:
                    best_total_width = total
                    best_width_dir = test_dir
            dl = find_edge(track, inv, ray_dir, pt, best_width_dir, coarse_step, max_width)
            dr = find_edge(track, inv, ray_dir, pt, -best_width_dir, coarse_step, max_width)
            shift = (dl - dr) * 0.5
            pt = pt + best_width_dir * shift

            if not on_track(track, inv, ray_dir, pt[0], pt[1]):
                pt = candidate

            if len(points) >= 3:
                recent = np.array(points[-3:])
                new_fwd = pt - recent[0]
                nm = np.linalg.norm(new_fwd)
                if nm > 1e-8:
                    new_fwd = new_fwd / nm
                    fwd = 0.4 * new_fwd + 0.6 * fwd
                    nm = np.linalg.norm(fwd)
                    if nm > 1e-8:
                        fwd = fwd / nm

            points.append(pt.copy())

            if step_i > n_target // 2:
                dist_to_start = np.linalg.norm(pt - points[0])
                if dist_to_start < step_size * 2.0:
                    print(f"Loop closed at step {step_i}")
                    break

        return np.array(points)

    def execute(self, context):
        if not dependencies_available():
            self.report({'ERROR'}, "Install dependencies first")
            return {'CANCELLED'}

        import numpy as np
        from scipy.interpolate import interp1d
        from scipy.ndimage import gaussian_filter1d, median_filter
        from mathutils import Vector

        props = context.scene.f1_track_viz_props
        track = props.track_mesh

        if not track:
            self.report({'ERROR'}, "Select a Track Mesh (eyedropper)")
            return {'CANCELLED'}
        if track.type != 'MESH':
            self.report({'ERROR'}, "Track Mesh must be a mesh object")
            return {'CANCELLED'}

        inv = track.matrix_world.inverted()
        ray_dir = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()

        coarse_step = props.centerline_ray_step
        max_width = props.centerline_max_width
        iterations = props.centerline_iterations
        sigma = props.centerline_smooth_sigma

        bb = [track.matrix_world @ Vector(c) for c in track.bound_box]
        min_x = min(v.x for v in bb)
        max_x = max(v.x for v in bb)
        min_y = min(v.y for v in bb)
        max_y = max(v.y for v in bb)

        start_xy = None
        scan_res = 50
        for ix in range(scan_res):
            for iy in range(scan_res):
                sx = min_x + (max_x - min_x) * (ix + 0.5) / scan_res
                sy = min_y + (max_y - min_y) * (iy + 0.5) / scan_res
                if self._point_on_track(track, inv, ray_dir, sx, sy):
                    start_xy = (sx, sy)
                    break
            if start_xy:
                break

        if not start_xy:
            self.report({'ERROR'}, "Could not find a point on the track mesh. Check mesh normals.")
            return {'CANCELLED'}

        pt0 = np.array(start_xy)
        test_width = 0.0
        for angle_deg in range(0, 180, 10):
            angle = math.radians(angle_deg)
            d = np.array([math.cos(angle), math.sin(angle)])
            dl = self._find_edge_dist(track, inv, ray_dir, pt0, d, coarse_step, max_width)
            dr = self._find_edge_dist(track, inv, ray_dir, pt0, -d, coarse_step, max_width)
            w = dl + dr
            if 1.0 < w < max_width * 1.5:
                test_width = max(test_width, w)

        step_size = max(0.5, test_width * 0.3)
        n_target = 800

        raw_centerline = self._walk_track_centerline(
            track, inv, ray_dir, start_xy, n_target,
            coarse_step, max_width, step_size
        )

        if len(raw_centerline) < 20:
            self.report({'ERROR'}, f"Walk produced only {len(raw_centerline)} points. Track mesh may have issues.")
            return {'CANCELLED'}

        n = min(len(raw_centerline), 1000)
        coords = _resample_equidistant(raw_centerline, n)

        for iteration in range(iterations):
            tangents_fixed = np.zeros((n, 2))
            for i in range(n):
                diff = coords[(i + 3) % n] - coords[(i - 3) % n]
                nm = np.linalg.norm(diff)
                tangents_fixed[i] = diff / nm if nm > 1e-8 else [1, 0]

            curv_mag = np.zeros(n)
            for i in range(n):
                t1 = tangents_fixed[i]
                t2 = tangents_fixed[(i + 1) % n]
                dot = np.clip(np.dot(t1, t2), -1, 1)
                curv_mag[i] = math.acos(dot)

            curv_mag_smooth = gaussian_filter1d(np.concatenate([curv_mag] * 3), sigma=5)[n:2*n]
            curv_max = np.max(curv_mag_smooth)

            tangents = np.zeros((n, 2))
            for i in range(n):
                c_norm = curv_mag_smooth[i] / curv_max if curv_max > 1e-8 else 0.0
                win = max(1, int(5 - 4 * c_norm))
                diff = coords[(i + win) % n] - coords[(i - win) % n]
                nm = np.linalg.norm(diff)
                tangents[i] = diff / nm if nm > 1e-8 else [1, 0]

            arr_dl = np.zeros(n)
            arr_dr = np.zeros(n)
            for i in range(n):
                pt = coords[i]
                left = np.array([-tangents[i][1], tangents[i][0]])
                arr_dl[i] = self._find_edge_dist(track, inv, ray_dir, pt, left, coarse_step, max_width)
                arr_dr[i] = self._find_edge_dist(track, inv, ray_dir, pt, -left, coarse_step, max_width)

            widths = arr_dl + arr_dr
            med_w = np.median(widths)
            valid_mask = (
                (widths > med_w * 0.4) &
                (widths < med_w * 1.6) &
                (arr_dl < max_width - 1.0) &
                (arr_dr < max_width - 1.0)
            )

            if not np.all(valid_mask):
                valid_idx = np.where(valid_mask)[0]
                if len(valid_idx) < 4:
                    continue

                ext_idx = np.concatenate([valid_idx - n, valid_idx, valid_idx + n])
                ext_dl = np.tile(arr_dl[valid_idx], 3)
                ext_dr = np.tile(arr_dr[valid_idx], 3)

                f_dl = interp1d(ext_idx, ext_dl, kind='linear')
                f_dr = interp1d(ext_idx, ext_dr, kind='linear')

                arr_dl = f_dl(np.arange(n))
                arr_dr = f_dr(np.arange(n))

            arr_dl = median_filter(arr_dl, size=7)
            arr_dr = median_filter(arr_dr, size=7)

            new_coords = np.zeros((n, 2))
            for i in range(n):
                pt = coords[i]
                left = np.array([-tangents[i][1], tangents[i][0]])
                shift = (arr_dl[i] - arr_dr[i]) * 0.5
                new_coords[i] = pt + left * shift

            for i in range(n):
                if not self._point_on_track(track, inv, ray_dir, new_coords[i, 0], new_coords[i, 1]):
                    old_pt = coords[i]
                    lo_t, hi_t = 0.0, 1.0
                    for _ in range(10):
                        mid_t = (lo_t + hi_t) * 0.5
                        test_pt = old_pt + mid_t * (new_coords[i] - old_pt)
                        if self._point_on_track(track, inv, ray_dir, test_pt[0], test_pt[1]):
                            lo_t = mid_t
                        else:
                            hi_t = mid_t
                    new_coords[i] = old_pt + lo_t * (new_coords[i] - old_pt)

            coords = _resample_equidistant(new_coords, n)

            t_new = np.zeros((n, 2))
            for i in range(n):
                diff = coords[(i + 2) % n] - coords[(i - 2) % n]
                nm = np.linalg.norm(diff)
                t_new[i] = diff / nm if nm > 1e-8 else [1, 0]

            curv_new = np.zeros(n)
            for i in range(n):
                dot = np.clip(np.dot(t_new[i], t_new[(i + 1) % n]), -1, 1)
                curv_new[i] = math.acos(dot)

            curv_new_smooth = gaussian_filter1d(np.concatenate([curv_new] * 3), sigma=3)[n:2*n]
            curv_new_max = np.max(curv_new_smooth)

            min_sigma = max(0.5, sigma * 0.4)
            sx = gaussian_filter1d(np.concatenate([coords[:, 0]] * 3), sigma=min_sigma)[n:2*n]
            sy = gaussian_filter1d(np.concatenate([coords[:, 1]] * 3), sigma=min_sigma)[n:2*n]

            for i in range(n):
                blend = curv_new_smooth[i] / curv_new_max if curv_new_max > 1e-8 else 0.0
                keep = 0.2 + 0.6 * blend
                coords[i, 0] = coords[i, 0] * keep + sx[i] * (1.0 - keep)
                coords[i, 1] = coords[i, 1] * keep + sy[i] * (1.0 - keep)

            for i in range(n):
                if not self._point_on_track(track, inv, ray_dir, coords[i, 0], coords[i, 1]):
                    for radius in range(1, min(20, n // 2)):
                        for nbr in [(i - radius) % n, (i + radius) % n]:
                            if self._point_on_track(track, inv, ray_dir, coords[nbr, 0], coords[nbr, 1]):
                                lo_t, hi_t = 0.0, 1.0
                                for _ in range(10):
                                    mid_t = (lo_t + hi_t) * 0.5
                                    test = coords[i] * (1 - mid_t) + coords[nbr] * mid_t
                                    if self._point_on_track(track, inv, ray_dir, test[0], test[1]):
                                        hi_t = mid_t
                                    else:
                                        lo_t = mid_t
                                coords[i] = coords[i] * (1 - hi_t) + coords[nbr] * hi_t
                                break
                        else:
                            continue
                        break

        name = "TRACK_CENTER_FIXED"
        for d in [bpy.data.objects, bpy.data.curves]:
            if name in d:
                d.remove(d[name], do_unlink=True)

        curve_data = bpy.data.curves.new(name, 'CURVE')
        curve_data.dimensions = '3D'
        sp = curve_data.splines.new('POLY')
        sp.points.add(n - 1)
        for i in range(n):
            sp.points[i].co = (coords[i, 0], coords[i, 1], 0, 1)
        sp.use_cyclic_u = True

        cl_obj = bpy.data.objects.new(name, curve_data)
        bpy.context.collection.objects.link(cl_obj)

        self.report({'INFO'}, f"TRACK_CENTER_FIXED created: {n} pts")
        return {'FINISHED'}


class F1_OT_GenerateRacingLine(Operator):
    bl_idname = "f1.generate_racing_line"
    bl_label = "Generate Racing Line"
    bl_description = (
        "Q_RACING_LINE via IQP — sparse-solve replacement for tph.opt_min_curv, "
        "scipy-1.17 safe, ~10s total"
    )

    @staticmethod
    def _opt_min_curv_sparse(reftrack, normvectors, A, kappa_bound, w_veh):
        """
        Exact reimplementation of tph.opt_min_curv (Heilmeier et al. 2019)
        with np.linalg.inv replaced by scipy sparse solve.
        
        A is the (4n x 4n) square spline system matrix from tph.calc_splines.
        It is ~99.9% zeros (banded structure), so sparse solve is ~9x faster
        than dense inv on n=738 tracks.
        """
        import numpy as np
        import quadprog
        from scipy.sparse import csc_matrix
        from scipy.sparse.linalg import spsolve

        no_points  = reftrack.shape[0]
        no_splines = no_points  # closed track

        # ── Extraction matrices (same as tph source) ──────────────────
        A_ex_b = np.zeros((no_points, no_splines * 4), dtype=float)
        for i in range(no_splines):
            A_ex_b[i, i * 4 + 1] = 1.0

        A_ex_c = np.zeros((no_points, no_splines * 4), dtype=float)
        for i in range(no_splines):
            A_ex_c[i, i * 4 + 2] = 2.0

        # ── SPARSE solve instead of dense inv ─────────────────────────
        # Original: A_inv = np.linalg.inv(A);  T_c = A_ex_c @ A_inv
        # Equivalent: T_c.T = solve(A.T, A_ex_c.T)
        A_sp = csc_matrix(A)
        T_c  = spsolve(A_sp.T, A_ex_c.T).T   # (n, 4n)
        T_b  = spsolve(A_sp.T, A_ex_b.T).T   # (n, 4n)

        # ── M_x, M_y (normal vectors in spline coeff space) ──────────
        M_x = np.zeros((no_splines * 4, no_points))
        M_y = np.zeros((no_splines * 4, no_points))
        for i in range(no_splines):
            j = i * 4
            if i < no_points - 1:
                M_x[j,     i    ] = normvectors[i,   0]
                M_x[j + 1, i + 1] = normvectors[i+1, 0]
                M_y[j,     i    ] = normvectors[i,   1]
                M_y[j + 1, i + 1] = normvectors[i+1, 1]
            else:
                M_x[j,     i] = normvectors[i, 0]
                M_x[j + 1, 0] = normvectors[0, 0]
                M_y[j,     i] = normvectors[i, 1]
                M_y[j + 1, 0] = normvectors[0, 1]

        # ── q_x, q_y (reference coordinates in spline coeff space) ───
        q_x = np.zeros((no_splines * 4, 1))
        q_y = np.zeros((no_splines * 4, 1))
        for i in range(no_splines):
            j = i * 4
            nxt = (i + 1) % no_points
            q_x[j, 0] = reftrack[i,   0];  q_x[j+1, 0] = reftrack[nxt, 0]
            q_y[j, 0] = reftrack[i,   1];  q_y[j+1, 0] = reftrack[nxt, 1]

        # ── Curvature denominator terms ───────────────────────────────
        x_prime = np.eye(no_points) * (T_b @ q_x)
        y_prime = np.eye(no_points) * (T_b @ q_y)
        x_prime_sq      = x_prime ** 2
        y_prime_sq      = y_prime ** 2
        x_prime_y_prime = -2.0 * (x_prime @ y_prime)

        curv_den  = (x_prime_sq + y_prime_sq) ** 1.5
        curv_part = np.divide(1.0, curv_den,
                              out=np.zeros_like(curv_den), where=curv_den != 0)
        curv_part_sq = curv_part ** 2

        P_xx = curv_part_sq @ y_prime_sq
        P_yy = curv_part_sq @ x_prime_sq
        P_xy = curv_part_sq @ x_prime_y_prime

        # ── H and f (QP cost matrices) ────────────────────────────────
        T_nx = T_c @ M_x   # (n, n)
        T_ny = T_c @ M_y   # (n, n)

        H_x  = T_nx.T @ (P_xx @ T_nx)
        H_xy = T_ny.T @ (P_xy @ T_nx)
        H_y  = T_ny.T @ (P_yy @ T_ny)
        H    = H_x + H_xy + H_y
        H    = (H + H.T) * 0.5  # enforce symmetry

        f_x  = 2.0 * (q_x.T @ T_c.T @ P_xx @ T_nx)
        f_xy = (q_x.T @ T_c.T @ P_xy @ T_ny
               + q_y.T @ T_c.T @ P_xy @ T_nx)
        f_y  = 2.0 * (q_y.T @ T_c.T @ P_yy @ T_ny)
        f    = np.squeeze(f_x + f_xy + f_y)

        # ── Kappa constraints ─────────────────────────────────────────
        Q_x = curv_part @ y_prime
        Q_y = curv_part @ x_prime
        E_kappa   = Q_y @ T_ny - Q_x @ T_nx
        k_kappa_ref = (Q_y @ (T_c @ q_y)) - (Q_x @ (T_c @ q_x))
        con_ge    = np.ones((no_points, 1)) * kappa_bound - k_kappa_ref
        con_le    = -(np.ones((no_points, 1)) * (-kappa_bound) - k_kappa_ref)
        con_stack = np.concatenate([con_ge, con_le]).ravel()

        # ── Track boundary constraints ────────────────────────────────
        half_veh     = w_veh / 2.0
        dev_max_right = reftrack[:, 2] - half_veh
        dev_max_left  = reftrack[:, 3] - half_veh

        # Clamp to avoid infeasible problem
        dev_max_right = np.maximum(dev_max_right, 0.05)
        dev_max_left  = np.maximum(dev_max_left,  0.05)

        G = np.vstack([np.eye(no_points), -np.eye(no_points), E_kappa, -E_kappa])
        h = np.concatenate([dev_max_right, dev_max_left, con_stack])

        # ── Solve: quadprog.solve_qp(H, -f, -G.T, -h) ───────────────
        H += np.eye(H.shape[0]) * 1e-8   # small regularization
        try:
            alpha = quadprog.solve_qp(H, -f, -G.T, -h, 0)[0]
        except Exception as e:
            raise RuntimeError(f"quadprog: {e}")

        # ── Curvature error (cheap version — no scipy.spatial) ────────
        q_x_sol = q_x + M_x @ np.expand_dims(alpha, 1)
        q_y_sol = q_y + M_y @ np.expand_dims(alpha, 1)
        x_p_sol = np.eye(no_points) * (T_b @ q_x_sol)
        y_p_sol = np.eye(no_points) * (T_b @ q_y_sol)
        x_pp    = np.squeeze(T_c @ q_x + T_nx @ np.expand_dims(alpha, 1))
        y_pp    = np.squeeze(T_c @ q_y + T_ny @ np.expand_dims(alpha, 1))

        curv_orig = np.zeros(no_points)
        curv_sol  = np.zeros(no_points)
        for i in range(no_points):
            denom_o = (x_prime[i,i]**2 + y_prime[i,i]**2) ** 1.5
            denom_s = (x_p_sol[i,i]**2 + y_p_sol[i,i]**2) ** 1.5
            if denom_o > 1e-12:
                curv_orig[i] = (x_prime[i,i]*y_pp[i] - y_prime[i,i]*x_pp[i]) / denom_o
            if denom_s > 1e-12:
                curv_sol[i]  = (x_p_sol[i,i]*y_pp[i] - y_p_sol[i,i]*x_pp[i]) / denom_s

        curv_error_max = float(np.max(np.abs(curv_sol - curv_orig)))
        return alpha, curv_error_max

    def execute(self, context):
        if not dependencies_available():
            self.report({'ERROR'}, "Install dependencies first")
            return {'CANCELLED'}

        import numpy as np
        from mathutils import Vector
        from scipy.interpolate import splprep, splev
        from scipy.ndimage import gaussian_filter1d, median_filter
        import time

        t_total = time.perf_counter()
        props   = context.scene.f1_track_viz_props
        track   = props.track_mesh

        cl_obj = bpy.data.objects.get("TRACK_CENTER_FIXED")
        if not cl_obj:
            self.report({'ERROR'}, "TRACK_CENTER_FIXED not found.")
            return {'CANCELLED'}
        if not track:
            self.report({'ERROR'}, "Select a Track Mesh")
            return {'CANCELLED'}

        try:
            import trajectory_planning_helpers as tph
            import quadprog
        except ImportError as e:
            self.report({'ERROR'}, f"Missing package: {e}")
            return {'CANCELLED'}

        print("\n" + "="*60)
        print("  [Racing Line] SPARSE IQP (scipy-1.17 safe)")
        print("="*60)

        # ── [1/7] Extract centerline ───────────────────────────────────
        t0 = time.perf_counter()
        sp = cl_obj.data.splines[0]
        n  = len(sp.points)
        cl = np.zeros((n, 2))
        for i in range(n):
            co = cl_obj.matrix_world @ Vector(sp.points[i].co[:3])
            cl[i] = [co.x, co.y]
        seg_lens  = np.linalg.norm(np.diff(np.vstack([cl, cl[0]]), axis=0), axis=1)
        print(f"  [1/7] Centerline: {n} pts, length={seg_lens.sum():.1f} BU "
              f"({time.perf_counter()-t0:.3f}s)")

        # ── [2/7] Roll seam to flattest point ─────────────────────────
        tang = np.zeros((n, 2))
        for i in range(n):
            d = cl[(i+3)%n] - cl[(i-3)%n]
            nm = np.linalg.norm(d)
            tang[i] = d/nm if nm > 1e-8 else [1, 0]
        curv_pre = np.array([math.acos(np.clip(np.dot(tang[i], tang[(i+1)%n]), -1, 1))
                             for i in range(n)])
        seam = int(np.argmin(curv_pre))
        cl = np.roll(cl, -seam, axis=0)
        print(f"  [2/7] Seam rolled by {seam}")

        # ── [3/7] Raycast widths ───────────────────────────────────────
        tang2 = np.zeros((n, 2))
        for i in range(n):
            d = cl[(i+3)%n] - cl[(i-3)%n]
            nm = np.linalg.norm(d)
            tang2[i] = d/nm if nm > 1e-8 else [1, 0]
        normals_raw = np.column_stack([-tang2[:, 1], tang2[:, 0]])

        t0  = time.perf_counter()
        inv = track.matrix_world.inverted()
        ray_dir = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()
        INSET   = props.racing_line_inset
        w_tr_right = np.zeros(n)
        w_tr_left  = np.zeros(n)

        print(f"  [3/7] Raycasting {n} pts...")
        for i in range(n):
            pt   = cl[i]
            bn   = normals_raw[i]
            best_total = float('inf')
            best_dir   = bn

            for ad in range(-45, 46, 5):
                a = math.radians(ad)
                td = np.array([bn[0]*math.cos(a) - bn[1]*math.sin(a),
                               bn[0]*math.sin(a) + bn[1]*math.cos(a)])
                tdl = 10.0
                for s in range(1, 67):
                    d = s*0.15
                    h2, *_ = track.ray_cast(inv @ Vector((*(pt+td*d), 10000.)), ray_dir)
                    if not h2: tdl = d-0.15; break
                tdr = 10.0
                for s in range(1, 67):
                    d = s*0.15
                    h2, *_ = track.ray_cast(inv @ Vector((*(pt-td*d), 10000.)), ray_dir)
                    if not h2: tdr = d-0.15; break
                tot = tdl+tdr
                if 0.5 < tot < best_total and tdl < 9.5 and tdr < 9.5:
                    best_total = tot; best_dir = td

            dl = 30.0
            for s in range(1, 200):
                d = s*0.15
                h2, *_ = track.ray_cast(inv @ Vector((*(pt+best_dir*d), 10000.)), ray_dir)
                if not h2: dl = d-0.15; break
            dr = 30.0
            for s in range(1, 200):
                d = s*0.15
                h2, *_ = track.ray_cast(inv @ Vector((*(pt-best_dir*d), 10000.)), ray_dir)
                if not h2: dr = d-0.15; break

            w_tr_right[i] = max(dr - INSET, 0.01)
            w_tr_left[i]  = max(dl - INSET, 0.01)

        w_tr_right = median_filter(np.tile(w_tr_right, 3), size=9)[n:2*n]
        w_tr_left  = median_filter(np.tile(w_tr_left,  3), size=9)[n:2*n]
        w_veh    = props.racing_line_veh_width
        kappa_bound = props.racing_line_kappa_bound
        min_hw   = w_veh/2.0 + 0.5
        wr_safe  = gaussian_filter1d(np.tile(np.maximum(w_tr_right, min_hw), 3), sigma=3)[n:2*n]
        wl_safe  = gaussian_filter1d(np.tile(np.maximum(w_tr_left,  min_hw), 3), sigma=3)[n:2*n]
        print(f"  [3/7] right=[{wr_safe.min():.2f},{wr_safe.max():.2f}] "
              f"left=[{wl_safe.min():.2f},{wl_safe.max():.2f}] ({time.perf_counter()-t0:.1f}s)")

        # ── [4/7] Strong centerline smoothing ─────────────────────────
        t0 = time.perf_counter()
        try:
            cl_cl = np.vstack([cl, cl[0]])
            el    = np.linalg.norm(np.diff(cl_cl, axis=0), axis=1)
            cum   = np.concatenate([[0], np.cumsum(el)])
            u_n   = cum / cum[-1]
            s_val = max(20.0, n * 0.3)
            tck_s, _ = splprep([cl_cl[:, 0], cl_cl[:, 1]], u=u_n, k=3, s=s_val, per=1)
            cl_qp = np.array(splev(u_n[:-1], tck_s)).T
            dev   = np.linalg.norm(cl_qp - cl, axis=1)
            print(f"  [4/7] Smoothed s={s_val:.0f}: dev mean={dev.mean():.3f} "
                  f"max={dev.max():.3f} BU ({time.perf_counter()-t0:.3f}s)")
        except Exception as e:
            print(f"  [4/7] Smoothing failed: {e}")
            cl_qp = cl.copy()
        n_qp = len(cl_qp)

        # ── [5/7] IQP loop — sparse direct solve ──────────────────────
        t0      = time.perf_counter()
        cur_ref = cl_qp.copy()
        cur_wr  = wr_safe.copy()
        cur_wl  = wl_safe.copy()

        n_iters_max   = 5
        alpha_tol     = 0.10
        safety_margin = 0.15

        print(f"  [5/7] IQP sparse (up to {n_iters_max} iters)...")
        converged = False

        for it in range(n_iters_max):
            t_it = time.perf_counter()

            refpath = np.vstack([cur_ref, cur_ref[0]])
            try:
                coeffs_x, coeffs_y, A_mat, _ = tph.calc_splines.calc_splines(
                    path=refpath, use_dist_scaling=True
                )
            except Exception as e:
                print(f"  iter {it}: calc_splines FAILED: {e}")
                break

            ind_s = np.arange(len(coeffs_x))
            t_s   = np.zeros(len(coeffs_x))
            try:
                psi, kappa = tph.calc_head_curv_an.calc_head_curv_an(
                    coeffs_x=coeffs_x, coeffs_y=coeffs_y,
                    ind_spls=ind_s, t_spls=t_s,
                    calc_curv=True, calc_dcurv=False
                )[:2]
            except Exception as e:
                print(f"  iter {it}: calc_head_curv_an FAILED: {e}")
                break

            normvec = tph.calc_normal_vectors.calc_normal_vectors(psi=psi)

            # Psi seam check
            psi_diff = np.mod(np.diff(np.concatenate([psi, [psi[0]+2*math.pi]])) + math.pi,
                              2*math.pi) - math.pi
            if np.max(np.abs(psi_diff)) > 0.4:
                bad = int(np.argmax(np.abs(psi_diff)))
                print(f"        iter {it}: psi jump {psi_diff[bad]:.3f}rad "
                      f"at station {bad}")

            reftrack_it = np.column_stack([cur_ref, cur_wr, cur_wl])

            try:
                alpha_it, curv_err = self._opt_min_curv_sparse(
                    reftrack_it, normvec, A_mat, kappa_bound, w_veh
                )
            except Exception as e:
                print(f"        iter {it}: QP FAILED: {e}")
                if it == 0:
                    self.report({'ERROR'}, f"QP failed: {e}")
                    return {'CANCELLED'}
                break

            alpha_it = np.clip(alpha_it,
                               -cur_wl + w_veh/2.0 + safety_margin,
                                cur_wr - w_veh/2.0 - safety_margin)

            grad = np.abs(np.diff(np.concatenate([alpha_it, [alpha_it[0]]])))
            print(f"        iter {it}: max|α|={np.max(np.abs(alpha_it)):.3f} "
                  f"mean|α|={np.mean(np.abs(alpha_it)):.3f} "
                  f"max|Δα|={grad.max():.3f} "
                  f"curv_err={curv_err:.4f} "
                  f"({time.perf_counter()-t_it:.2f}s)")

            cur_ref = cur_ref + normvec * alpha_it[:, None]
            cur_wr  = np.maximum(cur_wr - alpha_it, w_veh/2.0 + safety_margin)
            cur_wl  = np.maximum(cur_wl + alpha_it, w_veh/2.0 + safety_margin)

            if np.max(np.abs(alpha_it)) < alpha_tol and it >= 1:
                print(f"  [5/7] Converged at iter {it} ✓")
                converged = True
                break

        print(f"  [5/7] IQP done: {time.perf_counter()-t0:.1f}s converged={converged}")

        # ── [6/7] Final interpolation to user stepsize ─────────────────
        t0 = time.perf_counter()
        stepsize  = props.racing_line_stepsize
        rl_closed = np.vstack([cur_ref, cur_ref[0]])
        arc       = np.concatenate([[0],
                    np.cumsum(np.linalg.norm(np.diff(rl_closed, axis=0), axis=1))])
        total_len = arc[-1]
        n_out     = max(10, int(total_len / stepsize))

        # Light smoothing (s>0) removes residual kinks from IQP reference points
        # without destroying the optimised geometry
        s_out = max(1.0, len(rl_closed) * 0.005)
        try:
            tck, _ = splprep([rl_closed[:, 0], rl_closed[:, 1]],
                             u=arc, s=s_out, per=True)
        except Exception:
            tck, _ = splprep([rl_closed[:, 0], rl_closed[:, 1]],
                             u=arc, s=0, per=True)
        u_new    = np.linspace(0, total_len, n_out, endpoint=False)
        rx, ry   = splev(u_new, tck)
        raceline = np.column_stack([rx, ry])
        print(f"  [6/7] {n_out} pts @ {stepsize}m ({time.perf_counter()-t0:.3f}s)")

        # ── [7/7] Containment check ────────────────────────────────────
        from scipy.spatial import cKDTree
        tree = cKDTree(cl_qp)
        _, nidx = tree.query(raceline, k=1)
        off = 0; worst = 0.0
        for i in range(n_out):
            s = nidx[i]
            d = cl_qp[(s+3)%n_qp] - cl_qp[(s-3)%n_qp]
            nm = np.linalg.norm(d)
            if nm < 1e-8: continue
            nv = np.array([d[1], -d[0]]) / nm  # RIGHT
            offset = np.dot(raceline[i] - cl_qp[s], nv)
            if offset > wr_safe[s] or offset < -wl_safe[s]:
                off += 1
                worst = max(worst, max(offset - wr_safe[s], -wl_safe[s] - offset))
        if off:
            print(f"  [7/7] {off}/{n_out} pts off-track (worst={worst:.2f} BU)")
        else:
            print(f"  [7/7] All {n_out} pts within bounds ✓")

        # ── Write to Blender ───────────────────────────────────────────
        name = "Q_RACING_LINE"
        for d in [bpy.data.objects, bpy.data.curves]:
            if name in d: d.remove(d[name], do_unlink=True)

        cd  = bpy.data.curves.new(name, 'CURVE')
        cd.dimensions = '3D'
        sp2 = cd.splines.new('POLY')
        sp2.points.add(n_out - 1)
        for i in range(n_out):
            sp2.points[i].co = (raceline[i, 0], raceline[i, 1], 0.0, 1.0)
        sp2.use_cyclic_u = True

        obj = bpy.data.objects.new(name, cd)
        bpy.context.collection.objects.link(obj)

        # Stash smoothed centerline and half-widths for the style-layer operator.
        # Avoids re-raycasting (~10-30s) on every slider change.
        obj["_cl_qp_x"]          = cl_qp[:, 0].tolist()
        obj["_cl_qp_y"]          = cl_qp[:, 1].tolist()
        obj["_wr_safe"]          = wr_safe.tolist()
        obj["_wl_safe"]          = wl_safe.tolist()
        obj["_has_style_cache"]  = 1

        t_done = time.perf_counter() - t_total
        print("="*60)
        print(f"  DONE: {n_out} pts, {total_len:.0f}m, {t_done:.1f}s total")
        print("="*60 + "\n")
        self.report({'INFO'},
            f"Q_RACING_LINE: {n_out} pts, {total_len:.0f}m ({t_done:.1f}s)")
        return {'FINISHED'}


# ─── STYLED LINE V2 ─────────────────────────────────────────────────────────
# Detects corners directly on Q_RACING_LINE (not centerline), parameterizes
# phase along arc length, warps and clips in a single basis (raceline normals),
# uses smoothed normals to kill tangent-noise zigzag at corners. Centerline
# is used ONLY as a width lookup table.

def _v2_detect_corners_arclen(coords, kappa_hi_frac=0.25, kappa_lo_frac=0.08, min_len=6):
    """Hysteresis κ-corner detection on a closed 2D curve, with phase
    parameterized by ARC LENGTH within each corner (not station count)."""
    import numpy as np
    from scipy.ndimage import gaussian_filter1d

    n = len(coords)

    tang = np.zeros((n, 2))
    for i in range(n):
        d = coords[(i + 3) % n] - coords[(i - 3) % n]
        nm = np.linalg.norm(d)
        tang[i] = d / nm if nm > 1e-8 else np.array([1.0, 0.0])

    kappa = np.zeros(n)
    for i in range(n):
        t1, t2 = tang[i], tang[(i + 1) % n]
        cross = t1[0] * t2[1] - t1[1] * t2[0]
        dot = float(np.clip(np.dot(t1, t2), -1.0, 1.0))
        kappa[i] = math.copysign(math.acos(dot), cross)

    kappa_s = gaussian_filter1d(np.tile(kappa, 3), sigma=5.0)[n:2 * n]
    kappa_abs = np.abs(kappa_s)
    kmax = float(kappa_abs.max())
    if kmax < 1e-6:
        return [], np.full(n, -1, dtype=int), np.zeros(n), np.zeros(n)

    above_hi = kappa_abs > kappa_hi_frac * kmax
    above_lo = kappa_abs > kappa_lo_frac * kmax

    straights = np.where(~above_lo)[0]
    if len(straights) == 0:
        apex = int(np.argmax(kappa_abs))
        ks = int(math.copysign(1, kappa_s[apex]))
        return ([{'entry': 0, 'apex': apex, 'exit': n - 1, 'L': n,
                  'kappa_sign': ks}],
                np.zeros(n, dtype=int),
                np.linspace(0.0, 1.0, n),
                np.full(n, ks, dtype=float))

    roll = int(straights[0])
    above_hi_r = np.roll(above_hi, -roll)
    above_lo_r = np.roll(above_lo, -roll)
    kappa_abs_r = np.roll(kappa_abs, -roll)
    kappa_s_r = np.roll(kappa_s, -roll)
    coords_r = np.roll(coords, -roll, axis=0)

    seg = np.linalg.norm(np.diff(np.vstack([coords_r, coords_r[0]]), axis=0), axis=1)
    arc_r = np.concatenate([[0.0], np.cumsum(seg)])

    corners = []
    i = 0
    while i < n:
        if above_hi_r[i]:
            core_start = i
            while i < n and above_hi_r[i]:
                i += 1
            core_end = i - 1
            entry = core_start
            while entry > 0 and above_lo_r[entry - 1]:
                entry -= 1
            exit_ = core_end
            while exit_ < n - 1 and above_lo_r[exit_ + 1]:
                exit_ += 1
            L = exit_ - entry + 1
            if L >= min_len:
                apex_local = core_start + int(np.argmax(kappa_abs_r[core_start:core_end + 1]))
                corners.append({
                    '_entry_r': entry,
                    '_apex_r': apex_local,
                    '_exit_r': exit_,
                    'L': L,
                    'kappa_sign': int(math.copysign(1, kappa_s_r[apex_local])),
                })
        else:
            i += 1

    corner_id_r = np.full(n, -1, dtype=int)
    phase_r = np.zeros(n)
    sign_arr_r = np.zeros(n)
    for ci, c in enumerate(corners):
        entry, exit_ = c['_entry_r'], c['_exit_r']
        arc0 = arc_r[entry]
        arc1 = arc_r[exit_ + 1]
        denom = max(arc1 - arc0, 1e-6)
        for s in range(entry, exit_ + 1):
            corner_id_r[s] = ci
            phase_r[s] = (arc_r[s] - arc0) / denom
            sign_arr_r[s] = c['kappa_sign']

    corner_id = np.roll(corner_id_r, roll)
    phase = np.roll(phase_r, roll)
    kappa_sign = np.roll(sign_arr_r, roll)
    for c in corners:
        c['entry'] = (c.pop('_entry_r') + roll) % n
        c['apex']  = (c.pop('_apex_r')  + roll) % n
        c['exit']  = (c.pop('_exit_r')  + roll) % n

    return corners, corner_id, phase, kappa_sign


def _v2_periodic_smooth_xy(coords, sigma=1.5):
    """Light periodic gaussian on a closed XY curve. Sigma kept small so
    real corner geometry isn't flattened."""
    import numpy as np
    from scipy.ndimage import gaussian_filter1d
    n = len(coords)
    sx = gaussian_filter1d(np.tile(coords[:, 0], 3), sigma=sigma)[n:2 * n]
    sy = gaussian_filter1d(np.tile(coords[:, 1], 3), sigma=sigma)[n:2 * n]
    return np.column_stack([sx, sy])


def _v3_find_hifi_path(driver_tag, props):
    """Locate the per-driver baked telemetry path JSON. Tries in order:
       1. <style_json_path>/../../temp_data/{driver}_{N}_hifi_path.json
       2. <blend_dir>/F1_Pipeline_Assets/temp_data/...
       3. <blend_dir>/temp_data/...
    Returns the absolute path string, or None if nothing found."""
    import os, glob
    cands = []
    style_json = str(getattr(props, 'style_json_path', '') or '').strip()
    if style_json:
        style_dir = os.path.dirname(os.path.abspath(style_json))
        cands.append(os.path.join(os.path.dirname(style_dir), 'temp_data'))
    try:
        blend_dir = bpy.path.abspath('//')
    except Exception:
        blend_dir = ''
    if blend_dir:
        cands.append(os.path.join(blend_dir, 'F1_Pipeline_Assets', 'temp_data'))
        cands.append(os.path.join(blend_dir, 'temp_data'))

    for d in cands:
        if not d or not os.path.isdir(d):
            continue
        c0 = os.path.join(d, f"{driver_tag}_0_hifi_path.json")
        if os.path.isfile(c0):
            return c0
        c1 = os.path.join(d, f"{driver_tag}_hifi_path.json")
        if os.path.isfile(c1):
            return c1
        matches = glob.glob(os.path.join(d, f"{driver_tag}_*_hifi_path.json"))
        if matches:
            return sorted(matches)[0]
    return None


def _v3_load_hifi_xy(path):
    """Read hifi_path JSON → (N, 2) XY numpy array. Returns None on parse error."""
    import json
    import numpy as np
    try:
        with open(path, 'r', encoding='utf-8') as fp:
            data = json.load(fp)
        pts = data.get('points') or []
        if len(pts) < 50:
            return None
        xs = np.array([float(p.get('x', 0.0)) for p in pts], dtype=float)
        ys = np.array([float(p.get('y', 0.0)) for p in pts], dtype=float)
        return np.column_stack([xs, ys])
    except Exception:
        return None


def _v3_lap_fractions(corners, coords):
    """For each corner, return apex's lap fraction (arc-length to apex / total lap
    arc-length, in [0, 1)). Coord-frame independent."""
    import numpy as np
    n = len(coords)
    d = np.diff(np.vstack([coords, coords[0:1]]), axis=0)
    seg = np.linalg.norm(d, axis=1)
    total = float(seg.sum())
    if total < 1e-6:
        return np.zeros(len(corners))
    cumarc = np.concatenate([[0.0], np.cumsum(seg)])
    return np.array([cumarc[int(c['apex'])] / total for c in corners])


def _v3_match_corners_lap_fraction(q_corners, q_coords, sai_corners, sai_coords,
                                   max_diff=0.06):
    """Greedy one-to-one match by lap-fraction position of each apex. Q's coord
    frame and SAI's coord frame can differ — only relative arc-length within each
    path matters. Picks a global rotation offset that maximises matched pairs,
    then assigns greedily. Returns list of length len(q_corners) with matched SAI
    index or None for unmatched."""
    import numpy as np
    Nq = len(q_corners)
    Ns = len(sai_corners) if sai_corners else 0
    if Nq == 0 or Ns == 0:
        return [None] * Nq

    qf = _v3_lap_fractions(q_corners, q_coords)
    sf = _v3_lap_fractions(sai_corners, sai_coords)

    def _circ(a, b):
        d = abs(float(a) - float(b))
        return min(d, 1.0 - d)

    # Search a small set of global offsets (Q lap-fraction may start at a
    # different physical track position than SAI lap-fraction). Pick the offset
    # that maximises matched pairs under max_diff, ties broken by total error.
    best = None
    for off in np.linspace(0.0, 1.0, 41, endpoint=False):
        sf_shift = (sf + off) % 1.0
        used_s = set()
        n_match = 0
        total_err = 0.0
        for qi in range(Nq):
            best_sj = None
            best_d = max_diff + 1.0
            for sj in range(Ns):
                if sj in used_s:
                    continue
                d = _circ(qf[qi], sf_shift[sj])
                if d < best_d:
                    best_d = d
                    best_sj = sj
            if best_sj is not None and best_d <= max_diff:
                used_s.add(best_sj)
                n_match += 1
                total_err += best_d
        if best is None or n_match > best[0] or (n_match == best[0] and total_err < best[1]):
            best = (n_match, total_err, off)

    off = best[2] if best is not None else 0.0
    sf_shift = (sf + off) % 1.0

    pairs = []
    for qi in range(Nq):
        for sj in range(Ns):
            pairs.append((_circ(qf[qi], sf_shift[sj]), qi, sj))
    pairs.sort(key=lambda t: t[0])
    matched = [None] * Nq
    q_taken = set()
    s_taken = set()
    for d, qi, sj in pairs:
        if d > max_diff:
            break
        if qi in q_taken or sj in s_taken:
            continue
        matched[qi] = sj
        q_taken.add(qi)
        s_taken.add(sj)
    return matched


def _find_style_params_dir(props):
    """Locate the project's style_params/ directory. Tries:
       1. Sibling of props.style_json_path (most reliable when user has loaded one)
       2. <blend_dir>/F1_Pipeline_Assets/style_params/
       3. <blend_dir>/style_params/
    Returns absolute path, or None."""
    import os
    cands = []
    style_json = str(getattr(props, 'style_json_path', '') or '').strip()
    if style_json:
        cands.append(os.path.dirname(bpy.path.abspath(style_json)))
    try:
        blend_dir = bpy.path.abspath('//')
    except Exception:
        blend_dir = ''
    if blend_dir:
        cands.append(os.path.join(blend_dir, 'F1_Pipeline_Assets', 'style_params'))
        cands.append(os.path.join(blend_dir, 'style_params'))
    for c in cands:
        if c and os.path.isdir(c):
            return c
    return None


def _q_right_normals(raceline):
    """Per-station right-normals for Q (chord-based), used for projecting the
    driver's lateral offset and for re-applying it as displacement."""
    import numpy as np
    n_r = len(raceline)
    rn = np.zeros((n_r, 2))
    for i in range(n_r):
        d = raceline[(i + 3) % n_r] - raceline[(i - 3) % n_r]
        nm = np.linalg.norm(d)
        if nm < 1e-8:
            rn[i] = np.array([0.0, -1.0])
        else:
            t = d / nm
            rn[i] = np.array([t[1], -t[0]])
    return rn


def _extract_offset_profile(raceline, q_corners, right_normals, driver_path_xy,
                            smooth_sigma=3.0, taper_frac=0.15, max_clip=2.5):
    """Returns a per-station signed lateral offset profile (n_r,) extracted from
    the driver's path: closest-point projection onto Q's right-normals, masked
    to corner stations only, cosine-tapered at corner boundaries, lightly
    smoothed, and hard-clipped to ±max_clip metres. NOT scaled by master and
    NOT applied to coords yet — pure signal extraction."""
    import numpy as np
    from scipy.spatial import cKDTree
    from scipy.ndimage import gaussian_filter1d

    n_r = len(raceline)
    if driver_path_xy is None or len(driver_path_xy) < 50:
        return np.zeros(n_r)

    tree = cKDTree(driver_path_xy)
    _, nn = tree.query(raceline)
    raw = np.einsum('ij,ij->i', driver_path_xy[nn] - raceline, right_normals)
    raw = np.clip(raw, -max_clip, max_clip)

    out = np.zeros(n_r)
    for c in q_corners:
        idx = _v3_corner_indices(c, n_r)
        L = len(idx)
        if L < 4:
            continue
        taper_len = max(2, int(L * taper_frac))
        taper = np.ones(L)
        for k in range(taper_len):
            phase = k / max(taper_len - 1, 1)
            w = 0.5 * (1.0 - np.cos(np.pi * phase))
            taper[k] = w
            taper[L - 1 - k] = w
        out[idx] = raw[idx] * taper

    if smooth_sigma > 0.0:
        out = gaussian_filter1d(np.tile(out, 3), sigma=smooth_sigma)[n_r:2 * n_r]

    in_corner = np.zeros(n_r, dtype=bool)
    for c in q_corners:
        idx = _v3_corner_indices(c, n_r)
        in_corner[idx] = True
    out[~in_corner] = 0.0
    return out


def _styled_line_from_driver_path(raceline, q_corners, driver_path_xy, master,
                                   smooth_sigma=3.0, taper_frac=0.15, max_offset_clip=5.0,
                                   driver_tag=""):
    """Build the styled racing line by extracting the driver's actual lateral
    offset from Q (using their hifi-path / driving_path curve) and applying it
    as a deformation to Q.

    Process:
      1. For each Q station, compute Q's right-normal from a 7-point chord.
      2. cKDTree-find the closest point on the driver's path to each Q point.
      3. Project the (driver_pt - Q_pt) vector onto Q's right-normal → signed
         lateral offset per station, in metres.
      4. Mask: stations not inside any detected corner → offset = 0 (straights
         keep the line exactly on Q).
      5. Cosine-taper the first/last `taper_frac` of each corner so offset goes
         smoothly 0 → raw → 0 across the corner.
      6. Light gaussian smooth (sigma ≈ 3 stations, periodic) to remove
         telemetry sampling noise.
      7. Re-mask after smoothing as a paranoia guard against small bleed.
      8. Hard-clip per-station |offset| to max_offset_clip metres.
      9. Output: styled = Q + (offset × master) × Q_right_normal.

    Driver-style identity comes from the SHAPE of the offset profile within each
    corner, which is unique to each driver's actual driving. Q's straights are
    untouched. No JSON params — the data from FastF1 (the driving path itself)
    IS the parameter."""
    import numpy as np
    from scipy.spatial import cKDTree
    from scipy.ndimage import gaussian_filter1d

    n_r = len(raceline)
    if driver_path_xy is None or len(driver_path_xy) < 50:
        return raceline.copy(), 0, len(q_corners)

    right_normals = np.zeros((n_r, 2))
    for i in range(n_r):
        d = raceline[(i + 3) % n_r] - raceline[(i - 3) % n_r]
        nm = np.linalg.norm(d)
        if nm < 1e-8:
            right_normals[i] = np.array([0.0, -1.0])
        else:
            t = d / nm
            right_normals[i] = np.array([t[1], -t[0]])

    tree = cKDTree(driver_path_xy)
    _, nn = tree.query(raceline)
    delta = driver_path_xy[nn] - raceline                     # (n, 2)
    raw_offsets = np.einsum('ij,ij->i', delta, right_normals) # (n,)
    raw_offsets = np.clip(raw_offsets, -max_offset_clip, max_offset_clip)

    in_corner = np.zeros(n_r, dtype=bool)
    for c in q_corners:
        idx = _v3_corner_indices(c, n_r)
        in_corner[idx] = True

    final_offsets = np.zeros(n_r)
    for c in q_corners:
        idx = _v3_corner_indices(c, n_r)
        L = len(idx)
        if L < 4:
            continue
        taper_len = max(2, int(L * taper_frac))
        taper = np.ones(L)
        for k in range(taper_len):
            phase = k / max(taper_len - 1, 1)
            w = 0.5 * (1.0 - np.cos(np.pi * phase))
            taper[k] = w
            taper[L - 1 - k] = w
        final_offsets[idx] = raw_offsets[idx] * taper

    if smooth_sigma > 0.0:
        final_offsets = gaussian_filter1d(
            np.tile(final_offsets, 3), sigma=smooth_sigma,
        )[n_r:2 * n_r]

    # Re-mask hard zero outside corners (smoothing can bleed a few stations).
    final_offsets[~in_corner] = 0.0

    final_offsets *= float(master)

    # Per-corner peak-magnitude debug.
    if driver_tag:
        print(f"[STYLE-OFFSET] {driver_tag}: per-corner peak |offset| (m):", flush=True)
        for ci, c in enumerate(q_corners):
            idx = _v3_corner_indices(c, n_r)
            seg = final_offsets[idx]
            if len(seg) > 0:
                peak = float(np.abs(seg).max())
                signed_at_apex = float(final_offsets[int(c['apex'])])
                print(
                    f"  c{ci:02d} L={c['L']:3d} ks={c['kappa_sign']:+d} "
                    f"peak={peak:+.2f}m  apex_offset={signed_at_apex:+.2f}m",
                    flush=True,
                )
        max_d = float(np.abs(final_offsets).max())
        print(f"[STYLE-OFFSET] {driver_tag}: max |offset| over lap = {max_d:.2f} m", flush=True)

    styled = raceline + final_offsets[:, None] * right_normals
    return styled, n_r, len(q_corners)


def _styled_line_for_driver_legacy(raceline, q_corners, outside_budget,
                            json_corners, json_params, sai_xy, master,
                            max_drift=2.0, max_loose=0.6):
    """[Legacy — replaced by _styled_line_from_driver_path] Periodic cubic spline
    through anchor points derived from the 8-param JSON. Kept here in case the
    JSON-based fallback is needed."""
    import numpy as np
    from scipy.interpolate import CubicSpline
    n_r = len(raceline)

    # 1. Match Q's corners to SAI's per-corner JSON entries via lap-fraction.
    per_corner_data = [None] * len(q_corners)
    if sai_xy is not None and json_corners:
        sai_corners_det, _, _, _ = _v2_detect_corners_arclen(sai_xy)
        if sai_corners_det:
            matched = _v3_match_corners_lap_fraction(
                q_corners, raceline, sai_corners_det, sai_xy, max_diff=0.06,
            )
            for qi, sj in enumerate(matched):
                if sj is not None and 0 <= sj < len(json_corners):
                    per_corner_data[qi] = json_corners[sj]

    g_ap = float(json_params.get('apex_phase', 0.0))
    g_at = float(json_params.get('apex_tightness', 0.5))

    # 2. Per-station cumulative arc length and lap-fraction.
    d = np.diff(np.vstack([raceline, raceline[0:1]]), axis=0)
    seg_len = np.linalg.norm(d, axis=1)
    total_arc = float(seg_len.sum())
    if total_arc < 1e-6:
        return raceline.copy(), 0, len(q_corners)
    cum = np.concatenate([[0.0], np.cumsum(seg_len)])[:-1]      # (n_r,)
    arc_frac = cum / total_arc                                    # in [0, 1)

    # 3. Build anchor list (arc_frac, dev_x, dev_y).
    arcs = []
    dxs = []
    dys = []

    n_corners = len(q_corners)
    for ci, c in enumerate(q_corners):
        data = per_corner_data[ci]
        if data is not None:
            ap = float(data.get('apex_phase', g_ap))
            at = float(data.get('apex_tightness', g_at))
        else:
            ap, at = g_ap, g_at

        ap_eff = ap * master
        at_eff = 0.5 + (at - 0.5) * master

        drift_mag = abs(ap_eff) * float(max_drift)
        drift_mag += max(0.0, 0.5 - at_eff) * float(max_loose)
        budget = float(outside_budget.get(ci, 100.0))
        drift_mag = min(drift_mag, budget)

        apex_idx = int(c['apex'])
        p_back = max(0, apex_idx - 3)
        p_fwd = min(n_r - 1, apex_idx + 3)
        chord = raceline[p_fwd] - raceline[p_back]
        cn = float(np.linalg.norm(chord))
        if cn < 1e-6:
            continue
        chord /= cn
        right_normal = np.array([chord[1], -chord[0]])
        outside_dir = +float(c['kappa_sign']) * right_normal

        arcs.append(float(arc_frac[int(c['entry'])])); dxs.append(0.0); dys.append(0.0)
        arcs.append(float(arc_frac[apex_idx]));        dxs.append(drift_mag * outside_dir[0]); dys.append(drift_mag * outside_dir[1])
        arcs.append(float(arc_frac[int(c['exit'])]));  dxs.append(0.0); dys.append(0.0)

    # 4. Mid-straight rest anchors (zero deviation).
    for ci in range(n_corners):
        c1 = q_corners[ci]
        c2 = q_corners[(ci + 1) % n_corners]
        a_exit = float(arc_frac[int(c1['exit'])])
        a_entry = float(arc_frac[int(c2['entry'])])
        if a_entry > a_exit:
            mid = 0.5 * (a_exit + a_entry)
        else:
            mid = (0.5 * (a_exit + a_entry + 1.0)) % 1.0
        arcs.append(mid); dxs.append(0.0); dys.append(0.0)

    # 5. Sort, deduplicate, wrap for periodic.
    arr = sorted(zip(arcs, dxs, dys), key=lambda t: t[0])
    out_arcs, out_dxs, out_dys = [], [], []
    for a, x, y in arr:
        if out_arcs and abs(a - out_arcs[-1]) < 1e-6:
            continue
        out_arcs.append(a)
        out_dxs.append(x)
        out_dys.append(y)
    out_arcs.append(out_arcs[0] + 1.0)
    out_dxs.append(out_dxs[0])
    out_dys.append(out_dys[0])

    if len(out_arcs) < 4:
        return raceline.copy(), sum(1 for d in per_corner_data if d is not None), n_corners

    # 6. Periodic cubic splines for x and y deviation components.
    spl_x = CubicSpline(out_arcs, out_dxs, bc_type='periodic')
    spl_y = CubicSpline(out_arcs, out_dys, bc_type='periodic')

    dev_x = spl_x(arc_frac)
    dev_y = spl_y(arc_frac)

    styled = raceline.copy()
    styled[:, 0] += dev_x
    styled[:, 1] += dev_y

    # Debug — corner positions, anchor count, max deviation.
    print("[STYLE-CUBIC] corners (entry/apex/exit station, apex lap-frac, kappa_sign):", flush=True)
    for ci, c in enumerate(q_corners):
        print(
            f"  c{ci:02d}  entry={c['entry']:4d}  apex={c['apex']:4d}  exit={c['exit']:4d}  "
            f"apex_frac={arc_frac[int(c['apex'])]*100:.1f}%  ks={c['kappa_sign']:+d}",
            flush=True,
        )
    max_dev_total = float(np.linalg.norm(np.column_stack([dev_x, dev_y]), axis=1).max())
    print(f"[STYLE-CUBIC] {len(out_arcs)-1} anchors used | max styled-vs-Q deviation = {max_dev_total:.2f} m", flush=True)

    n_matched = sum(1 for d in per_corner_data if d is not None)
    return styled, n_matched, n_corners


def _curve_world_xy(obj):
    """Read a curve object's spline points in world XY (handles BEZIER + POLY/NURBS)."""
    import numpy as np
    from mathutils import Vector
    if obj is None or obj.type != 'CURVE' or not obj.data.splines:
        return None
    sp = obj.data.splines[0]
    if sp.type == 'BEZIER':
        pts = [obj.matrix_world @ bp.co for bp in sp.bezier_points]
    else:
        pts = [obj.matrix_world @ Vector(pt.co[:3]) for pt in sp.points]
    if len(pts) < 4:
        return None
    return np.array([[float(p.x), float(p.y)] for p in pts], dtype=float)


def _resolve_driving_path_obj(driver_code, scene):
    """Find the driving_path_* curve in scene that corresponds to this driver code.
    Three-step: (1) custom-property tag '_f1_driver_code' on the curve (universal,
    set at registration time by f1_pipeline._register_car), (2) direct substring
    name match, (3) trail-name back-lookup. Returns Object or None."""
    du = driver_code.upper()
    driving_paths = [
        o for o in scene.objects
        if o.type == 'CURVE' and o.name.startswith("driving_path_")
    ]
    # 1. Tag-based — works regardless of how the rig template was named.
    for p in driving_paths:
        tag = p.get("_f1_driver_code")
        if tag is not None and str(tag).upper().strip() == du:
            return p
    # 2. Direct name substring (legacy fallback for scenes without the tag).
    for p in driving_paths:
        if du in p.name.upper():
            return p
    # 3. Indirect via trail name substring.
    trails = [
        o for o in scene.objects
        if o.type == 'CURVE' and o.name.startswith("LC_Trail_")
    ]
    for t in trails:
        if du not in t.name.upper():
            continue
        suffix = t.name
        for prefix in ("LC_Trail_car_rig_", "LC_Trail_"):
            if suffix.startswith(prefix):
                suffix = suffix[len(prefix):]
                break
        parts = suffix.split("_")
        for i in range(len(parts), 0, -1):
            cand_name = "driving_path_" + "_".join(parts[:i])
            obj = scene.objects.get(cand_name)
            if obj is not None and obj.type == 'CURVE':
                return obj
    return None


def _v3_corner_indices(c, n):
    """Inclusive index array entry..exit, wrap-aware."""
    import numpy as np
    entry, exit_ = c['entry'], c['exit']
    if exit_ >= entry:
        return np.arange(entry, exit_ + 1)
    return np.concatenate([np.arange(entry, n), np.arange(0, exit_ + 1)])


def _v3_apex_local_index(c, n, L):
    """Where the κ-peak sits within the corner's local index range [0..L-1]."""
    import numpy as np
    entry, exit_ = int(c['entry']), int(c['exit'])
    apex_abs = int(c['apex'])
    if exit_ >= entry:
        A = apex_abs - entry
    else:
        A = (apex_abs - entry) % n
    return int(np.clip(A, 1, L - 2))


def _v3_asymmetric_bell(L, peak_phase, sharpness=1.0):
    """Smooth bump shape across L stations with peak at peak_phase ∈ (0, 1).
    Value AND slope are exactly zero at both endpoints — this is critical for
    a kink-free transition from the corner into the surrounding straight. The
    peak is placed via a power warp on a cosine bell, which keeps the function
    smooth everywhere (no piecewise discontinuity at the peak)."""
    import numpy as np
    if L < 4:
        return np.zeros(L)
    pp = float(np.clip(peak_phase, 0.05, 0.95))
    if abs(math.log(pp)) < 1e-3:
        power = 1.0
    else:
        power = math.log(0.5) / math.log(pp)
    phase = np.arange(L, dtype=float) / float(L - 1)
    warped = phase ** power
    bell = 0.5 * (1.0 - np.cos(2.0 * np.pi * warped))
    if sharpness != 1.0:
        bell = bell ** float(sharpness)
    return bell


def _v3_reshape_corner(coords, c, ap_phase, tight, vu,
                       inside_budget_at_apex=None,
                       max_inset=1.5, max_shift_frac=0.20,
                       _dbg=False, _dbg_tag=""):
    """Apply a smooth, bounded INSIDE bump to one corner. THIS IS THE
    'no-bumps' VERSION the user accepted earlier in the session.
       • Bump direction: -kappa_sign × right_normal (toward the apex inside).
       • Bump shape: gaussian centered at A_new = A_0 + apex_phase × max_shift × L,
         anchored to zero at corner entry/exit via endpoint subtraction.
       • Width controlled by vu_shape (V narrow, U broad).
       • Magnitude: tight × max_inset (NOT |ap_phase| × big-multiplier).
       • Track-clipped against the INSIDE budget at apex — this naturally
         clamps most apexes to ~0 because Q's min-curvature line already hugs
         the inside kerb. So most corners barely move from Q. That IS the
         'no bumps' look the user said worked."""
    import numpy as np

    n = len(coords)
    idx = _v3_corner_indices(c, n)
    L = len(idx)
    if L < 4:
        return idx, coords[idx].copy()

    seg = coords[idx].copy()
    A_0 = _v3_apex_local_index(c, n, L)

    iA = A_0
    p_back = max(0, iA - 3)
    p_fwd = min(L - 1, iA + 3)
    chord = seg[p_fwd] - seg[p_back]
    cn = float(np.linalg.norm(chord))
    if cn < 1e-6:
        return idx, seg
    chord /= cn
    right_normal = np.array([chord[1], -chord[0]])
    inside_dir = -float(c['kappa_sign']) * right_normal

    shift = float(ap_phase) * float(max_shift_frac) * float(L)
    A_new = float(np.clip(A_0 + shift, 1.0, L - 2.0))

    sigma_bump = float(L) * (0.10 + 0.075 * (float(vu) + 1.0))
    sigma_bump = max(sigma_bump, 1.5)

    i_arr = np.arange(L, dtype=float)
    w = np.exp(-((i_arr - A_new) ** 2) / (2.0 * sigma_bump ** 2))
    w_endpoint = float(max(w[0], w[-1]))
    w = np.maximum(0.0, w - w_endpoint) / max(1.0 - w_endpoint, 1e-6)

    inset_req = float(tight) * float(max_inset)
    if inside_budget_at_apex is not None:
        budget_clip = float(max(0.0, inside_budget_at_apex))
        inset = min(inset_req, budget_clip)
        clipped_by_track = inset < inset_req - 1e-4
    else:
        inset = inset_req
        clipped_by_track = False

    new_seg = seg + (w * inset)[:, None] * inside_dir[None, :]

    if _dbg:
        max_dev = float(np.linalg.norm(new_seg - seg, axis=1).max())
        clip_tag = " *TRACK-CLIP*" if clipped_by_track else ""
        print(
            f"[V3-DBG]   {_dbg_tag} L={L} A_0={A_0} A_new={A_new:.1f} ap={ap_phase:+.3f} "
            f"tight={tight:.3f} vu={vu:+.3f} inset_req={inset_req:.2f}m inset={inset:.2f}m{clip_tag} "
            f"sigma_bump={sigma_bump:.1f} max_dev={max_dev:.3f}m",
            flush=True,
        )

    return idx, new_seg


def _v4_compute_q_normals_width_and_d(raceline, wr_safe_cl, wl_safe_cl, nn, off_raceline):
    """Per-Q-station: chord-based right-normal (smooth by Q's smoothness),
    total track width (left-to-right kerbs at this station), and Q's
    cross-track coordinate d ∈ [0, 1] (0 = left kerb, 1 = right kerb).

    Q is ALWAYS the guide: the styled line will be Q + a lateral offset along
    Q's own smooth right-normal. Centerline normals are NOT used for direction
    (they jump non-monotonically when consecutive Q stations map to far-apart
    centerline indices at corners — that produces the 'crippled paper' artifact).
    Centerline data is used only for the scalar track widths and Q's signed
    offset from centerline, which fix the MAGNITUDE of the displacement."""
    import numpy as np
    n_r = len(raceline)
    q_right_normal = np.zeros((n_r, 2))
    for i in range(n_r):
        dvec = raceline[(i + 3) % n_r] - raceline[(i - 3) % n_r]
        nm = np.linalg.norm(dvec)
        if nm < 1e-8:
            q_right_normal[i] = np.array([0.0, -1.0])
        else:
            t = dvec / nm
            q_right_normal[i] = np.array([t[1], -t[0]])
    wr_q = wr_safe_cl[nn]
    wl_q = wl_safe_cl[nn]
    width = wr_q + wl_q
    width = np.where(width > 1e-6, width, 1.0)
    d_q = np.clip((off_raceline + wl_q) / width, 0.0, 1.0)
    return q_right_normal, width, d_q


def _v4_compute_d_offset_hybrid(corners, per_corner_data, n_r,
                                q_width, master,
                                g_ap=0.0, g_at=0.5, g_vu=0.0, g_lr=0.0,
                                k_baseline=0.15,
                                k_dipole_m=0.40,
                                max_shift_frac=0.30,
                                base_sigma_frac_dipole=0.25,
                                sigma_baseline_mult=2.5,
                                sigma_baseline_cap=30.0,
                                sigma_min_stations=4.0,
                                post_smooth_sigma=3.0,
                                global_clip=0.22,
                                headroom_pos_d=None, headroom_neg_d=None,
                                dbg_tag=""):
    """HYBRID per-driver d-offset profile — continuous across the lap PLUS
    within-corner apex-shift shape, per-station-clipped to never go off-track.

    Two summed contributions per corner:

    (A) BASELINE single-pole gaussian centered at A (Q's apex), signed +ks
        (the OUTSIDE direction of that corner, in d-units), magnitude
        (1 − apex_tightness) × k_baseline × master. The sigma is WIDE
        (sigma_baseline_mult × L, capped at sigma_baseline_cap), so the
        gaussian's tails reach onto adjacent straights and overlap with
        neighbour-corner contributions. Net effect: a loose driver sits
        consistently to the OUTSIDE of Q across the whole lap, not just
        at the corner peaks. This is what gives visible across-lap
        differentiation.

    (B) DIPOLE on top: narrow gaussian pair, signed +ks at A and −ks at
        A_new = A + apex_phase × max_shift_frac × L, magnitude
        (1 − apex_tightness) × k_dipole_m (in METERS, converted to d at
        A_new's local width). Sigma is narrow (base_sigma_frac_dipole × L)
        so the dipole only reshapes WITHIN the corner. Two drivers with
        opposite apex_phase produce opposite-signed dipoles → their styled
        lines cross between A and A_new (the geometric signature of an
        early-vs-late apex pair). Math derivation matches the standalone
        apex_warp dipole sign that was fixed earlier:
            contrib_dipole(s) = ks * mag_dipole_d * (G(s; A) − G(s; A_new))

    Final pipeline: sum baseline + dipole across all corners, periodic
    low-pass smooth, global clip in d-units, and a per-station headroom
    clip in METERS that enforces (kerb − vehicle_half − safety) at every
    station independently. The per-station clip is the safety guarantee
    that distinguishes this from PER_CORNER mode, which has no such clip
    and goes off-track when the wide-baseline tail meets a tight straight.

    Cross-driver amplification of apex_tightness happens UPSTREAM in the
    operator (before per_corner_data reaches this function), so per-driver
    baseline magnitudes are visibly different.

    Constraint roll-call:
      #1 telemetry-driven         : per-corner at + ap from JSON.       ✓
      #2 Q-anchored               : built FROM Q's apex/normals/widths. ✓
      #3 looks like racing line   : smooth gaussians + post-smooth.     ✓
      #4 stays on track           : per-station headroom clip in m.     ✓
      #5 not too conservative     : wide baseline + amp = visible.      ✓
      #6 crossings within corner  : dipole flips sign at A_new.         ✓
      #7 additive                 : new function, doesn't replace.      ✓
      #8 don't break Q            : Q untouched.                        ✓
      #9 better than what was     : combines best of all 3 prior modes. ✓
    """
    import numpy as np
    from scipy.ndimage import gaussian_filter1d

    n = int(n_r)
    if n < 8 or not corners:
        return np.zeros(n)

    d_off = np.zeros(n)
    i_arr = np.arange(n, dtype=float)

    if dbg_tag:
        print(f"[V4-HYBRID] {dbg_tag}: per-corner contributions:", flush=True)

    for ci, c in enumerate(corners):
        d_co = per_corner_data[ci] if ci < len(per_corner_data) else None
        if d_co is not None:
            try:
                ap = float(d_co.get('apex_phase',     g_ap))
                at = float(d_co.get('apex_tightness', g_at))
                vu = float(d_co.get('vu_shape',       g_vu))
            except Exception:
                ap, at, vu = g_ap, g_at, g_vu
        else:
            ap, at, vu = g_ap, g_at, g_vu

        L  = int(c['L'])
        ks = int(c['kappa_sign'])
        A  = int(c['apex'])

        ap_c = float(np.clip(ap, -1.0, 1.0))
        at_c = float(np.clip(at,  0.0, 1.0))
        vu_c = float(np.clip(vu, -1.0, 1.0))

        looseness = 1.0 - at_c

        # ─── (A) BASELINE: wide single-pole, OUTWARD direction ────────────
        # In d-coordinates, +d = toward right kerb. For a LEFT turn (ks=+1)
        # the outside is RIGHT (+d), and a loose driver pushes outward,
        # i.e. magnitude has sign +ks. Same construction as
        # _v4_compute_d_offset (PER_CORNER) so the across-lap continuity
        # property is identical.
        sigma_baseline = max(2.0, min(float(sigma_baseline_cap),
                                      float(L) * float(sigma_baseline_mult) * (1.0 + 0.30 * vu_c)))
        mag_baseline = (
            float(ks) * float(master) * float(k_baseline)
            * looseness * (1.0 + float(g_lr) * float(ks))
        )
        d_circ = ((i_arr - float(A) + n * 0.5) % n) - n * 0.5
        bump_baseline = np.exp(-(d_circ ** 2) / (2.0 * sigma_baseline ** 2))
        contrib_baseline = mag_baseline * bump_baseline

        # ─── (B) DIPOLE on top: narrow within-corner shape, encodes ap ────
        # contrib(s) = ks * mag_dipole_d * (G_old(s) − G_new(s))
        # where G_old peaks at A (Q's apex) and G_new peaks at A_new.
        # Sign derivation (verified): for ks=+1 left turn, late apex (ap>0,
        # A_new>A): at A → +ks·mag (+d = outside, driver staying wide); at
        # A_new → −ks·mag (−d = inside, driver pivoting here). Two drivers
        # with opposite ap produce opposite-signed dipoles → mid-corner
        # crossing.
        shift_stations = ap_c * float(max_shift_frac) * float(L)
        A_new = (float(A) + shift_stations) % float(n)
        A_new_int = int(round(A_new)) % n
        sigma_dipole = max(float(sigma_min_stations),
                           float(base_sigma_frac_dipole) * float(L) * (1.0 + 0.30 * vu_c))
        mag_dipole_m = (
            looseness * float(k_dipole_m) * float(master)
            * (1.0 + float(g_lr) * float(ks))
        )
        w_at_apex = float(q_width[A_new_int])
        if w_at_apex > 1e-6:
            mag_dipole_d = mag_dipole_m / w_at_apex
            d_to_new = ((i_arr - A_new + n * 0.5) % n) - n * 0.5
            d_to_old = ((i_arr - float(A) + n * 0.5) % n) - n * 0.5
            bump_new = np.exp(-(d_to_new ** 2) / (2.0 * sigma_dipole ** 2))
            bump_old = np.exp(-(d_to_old ** 2) / (2.0 * sigma_dipole ** 2))
            contrib_dipole = float(mag_dipole_d) * float(ks) * (bump_old - bump_new)
        else:
            contrib_dipole = np.zeros(n)

        d_off = d_off + contrib_baseline + contrib_dipole

        if dbg_tag:
            peak_b = float(np.abs(contrib_baseline).max())
            peak_d = float(np.abs(np.asarray(contrib_dipole)).max())
            print(
                f"  c{ci:02d} L={L:3d} ks={ks:+d} ap={ap_c:+.2f} at={at_c:.2f} | "
                f"baseline mag={mag_baseline:+.3f} sigma={sigma_baseline:.1f} peak={peak_b:.3f} | "
                f"dipole A_new={A_new_int} mag_m={mag_dipole_m:.2f} peak={peak_d:.3f}",
                flush=True,
            )

    # Periodic low-pass: kills inter-corner discontinuities at the seam,
    # sigma deliberately small so the dipole's within-corner structure
    # survives.
    if post_smooth_sigma > 0.0:
        d_off = gaussian_filter1d(np.tile(d_off, 3), sigma=float(post_smooth_sigma))[n:2 * n]

    # Global clip — last-resort ceiling on |d_off| as a fraction of width.
    # Only fires for pathological sums (several adjacent corners all biased
    # the same way after amplification).
    d_off = np.clip(d_off, -float(global_clip), +float(global_clip))

    # PER-STATION HEADROOM CLIP — the on-track guarantee. Same code/contract
    # as in _v4_compute_d_offset_apex_warp.
    if headroom_pos_d is not None and headroom_neg_d is not None:
        hp = np.asarray(headroom_pos_d, dtype=float)
        hn = np.asarray(headroom_neg_d, dtype=float)
        if hp.shape[0] == n and hn.shape[0] == n:
            n_clipped_pos = int(np.sum(d_off > hp))
            n_clipped_neg = int(np.sum(d_off < -hn))
            d_off = np.minimum(d_off,  hp)
            d_off = np.maximum(d_off, -hn)
            if dbg_tag and (n_clipped_pos + n_clipped_neg) > 0:
                print(
                    f"[V4-HYBRID] {dbg_tag}: per-station clip "
                    f"saved {n_clipped_pos}+{n_clipped_neg} stations from off-track",
                    flush=True,
                )

    if dbg_tag:
        print(
            f"[V4-HYBRID] {dbg_tag}: d_off peak={float(np.abs(d_off).max()):.3f} "
            f"mean|·|={float(np.abs(d_off).mean()):.3f}",
            flush=True,
        )

    return d_off


def _v4_compute_d_offset_apex_warp(corners, per_corner_data, n_r,
                                   q_width, inside_budget, master,
                                   g_ap=0.0, g_at=0.5, g_vu=0.0, g_lr=0.0,
                                   k_apex=0.55,
                                   max_shift_frac=0.30, base_sigma_frac=0.25,
                                   sigma_min_stations=4.0,
                                   post_smooth_sigma=4.0, global_clip=0.20,
                                   headroom_pos_d=None, headroom_neg_d=None,
                                   dbg_tag=""):
    """Per-corner APEX-WARP d-offset profile.

    For each corner, contribute a SIGNED DIPOLE to the lap-wide d-offset:

        d_off(s) += mag * ks * [ G(s; A_new, sigma) - G(s; A, sigma) ]

    where:
        A         = corner's geometric apex station (where Q's |kappa| peaks)
        A_new     = A + apex_phase * max_shift_frac * L          (driver's
                    desired apex along arc-length; +ap = late, -ap = early)
        sigma     = base_sigma_frac * L * (1 + 0.3 * vu_shape)   (V/U
                    sharpness modulates the dipole's spatial extent)
        mag (m)   = (1 - apex_tightness) * k_apex * master * (1 + g_lr * ks)
                    then clipped against inside_budget[ci]
        mag (d)   = mag (m) / q_width[A_new_int]                 (convert to
                    cross-track-coordinate fraction so it composes with d_q)
        G(s; c, s)= exp(-circ_dist(s, c)^2 / (2 sigma^2))         (periodic
                    gaussian; circular distance keeps it well-defined across
                    the seam)

    The dipole shape is the key:
      • Negative bump at A pulls the line OUTWARD relative to Q's apex
        (Q's min-curvature line hugs the inside at A; the negative pole says
        'this driver doesn't pivot here').
      • Positive bump at A_new pulls the line INWARD relative to Q at A_new
        (this driver pivots there instead).
      • Together they encode 'shifted apex' as a SHAPE difference, not a
        sideways translation. Two drivers with opposite apex_phase produce
        opposite-signed dipoles → their lines cross between A and A_new,
        which is exactly what early-vs-late apex pairs do in real telemetry.

    A driver with apex_phase ≈ 0 collapses A_new onto A — the two gaussians
    cancel — so they ride Q. A driver with apex_tightness ≈ 1 has zero
    magnitude — they ride Q. These are the correct null behaviours.

    Returns d_off : np.ndarray (n_r,)  in the same units as
    `_v4_compute_d_offset_global` so `_v4_assemble_styled` is unchanged.
    """
    import numpy as np
    from scipy.ndimage import gaussian_filter1d

    n = int(n_r)
    if n < 8 or not corners:
        return np.zeros(n)

    d_off = np.zeros(n)
    i_arr = np.arange(n, dtype=float)

    if dbg_tag:
        print(f"[V4-APEXWARP] {dbg_tag}: per-corner contributions:", flush=True)

    for ci, c in enumerate(corners):
        d_co = per_corner_data[ci] if ci < len(per_corner_data) else None
        if d_co is not None:
            try:
                ap = float(d_co.get('apex_phase',     g_ap))
                at = float(d_co.get('apex_tightness', g_at))
                vu = float(d_co.get('vu_shape',       g_vu))
            except Exception:
                ap, at, vu = g_ap, g_at, g_vu
        else:
            ap, at, vu = g_ap, g_at, g_vu

        L  = int(c['L'])
        ks = int(c['kappa_sign'])
        A  = int(c['apex'])

        ap_c = float(np.clip(ap, -1.0, 1.0))
        at_c = float(np.clip(at,  0.0, 1.0))
        vu_c = float(np.clip(vu, -1.0, 1.0))

        shift_stations = ap_c * float(max_shift_frac) * float(L)
        A_new = (float(A) + shift_stations) % float(n)
        A_new_int = int(round(A_new)) % n

        sigma = max(float(sigma_min_stations),
                    float(base_sigma_frac) * float(L) * (1.0 + 0.30 * vu_c))

        looseness = 1.0 - at_c
        mag_m = looseness * float(k_apex) * float(master) * (1.0 + float(g_lr) * float(ks))
        # inside_budget is in METERS (from operator), q_width is in METERS.
        # Clamp magnitude (in meters) so the styled line cannot punch past the
        # inside kerb at the driver's intended apex point.
        budget_m = float(inside_budget.get(ci, 0.0))
        if budget_m <= 0.0:
            # No inside room (Q already on the kerb here) — skip cleanly.
            if dbg_tag:
                print(f"  c{ci:02d} L={L:3d} ks={ks:+d} ap={ap_c:+.2f} at={at_c:.2f} "
                      f"budget=0 (skipped)", flush=True)
            continue
        if abs(mag_m) > budget_m:
            mag_m = math.copysign(budget_m, mag_m)

        # Convert meters → d-fraction at the displacement station. q_width is
        # in meters; d_offset is in [0, 1] cross-track coords summed onto d_q.
        w_at_apex = float(q_width[A_new_int])
        if w_at_apex <= 1e-6:
            continue
        mag_d = mag_m / w_at_apex

        # Periodic circular distance so the gaussian doesn't blow up across
        # the seam (lap is closed).
        d_to_new = ((i_arr - A_new + n * 0.5) % n) - n * 0.5
        d_to_old = ((i_arr - float(A) + n * 0.5) % n) - n * 0.5
        bump_new = np.exp(-(d_to_new ** 2) / (2.0 * sigma * sigma))
        bump_old = np.exp(-(d_to_old ** 2) / (2.0 * sigma * sigma))

        # Dipole sign — derivation, careful:
        #
        #   For a LEFT turn (ks=+1), INSIDE = LEFT = -d, OUTSIDE = RIGHT = +d.
        #   A late-apex driver (apex_phase > 0, A_new > A) should be:
        #     • at A:     OUTSIDE relative to Q (Q is at the inside kerb here;
        #                 the driver is staying wide). Want +d for left turn.
        #     • at A_new: INSIDE relative to Q (the driver pivots here, while
        #                 Q has already moved off the inside kerb). Want -d
        #                 for left turn.
        #
        #   So at A     → contrib must be +ks·mag_d
        #      at A_new → contrib must be -ks·mag_d
        #
        #   Using gaussians G_old=peak at A, G_new=peak at A_new:
        #      contrib(s) = ks * mag_d * (G_old(s) − G_new(s))
        #
        # Symmetric case for RIGHT turn (ks=-1): the math comes out correct
        # by the same construction. Early apex (ap < 0, A_new < A) flips the
        # roles of A and A_new automatically because the gaussians swap which
        # side they peak on.
        contrib = float(mag_d) * float(ks) * (bump_old - bump_new)
        d_off = d_off + contrib

        if dbg_tag:
            print(
                f"  c{ci:02d} L={L:3d} ks={ks:+d} ap={ap_c:+.2f} at={at_c:.2f} vu={vu_c:+.2f} "
                f"A={A:4d} A_new={A_new_int:4d} sigma={sigma:.1f} "
                f"mag_m={mag_m:+.2f} budget_m={budget_m:.2f} "
                f"peak_contrib={float(np.abs(contrib).max()):.3f}",
                flush=True,
            )

    # Periodic low-pass — smooths inter-corner contributions across the seam.
    # Sigma deliberately small (default 4 stations) so we don't blur the
    # within-corner dipole structure.
    if post_smooth_sigma > 0.0:
        d_off = gaussian_filter1d(np.tile(d_off, 3), sigma=float(post_smooth_sigma))[n:2 * n]

    # Final global clip — last line of defence against pathological sums (e.g.
    # several adjacent corners all biased the same way). Same role as in
    # _v4_compute_d_offset / _v4_compute_d_offset_global.
    d_off = np.clip(d_off, -float(global_clip), +float(global_clip))

    # PER-STATION SAFETY CLIP (the critical one). The per-corner inside_budget
    # only enforces clearance AT the apex of each corner. Dipole tails extend
    # beyond corner boundaries — onto straights — where the available headroom
    # is determined by the centerline-to-kerb distances at THAT station, not at
    # the apex. Without this clip, raising k_apex pushes straight-segment
    # stations outside the vehicle-width safety margin and the cars crash. This
    # clip enforces the constraint that EVERY station's styled position stays
    # within (kerb − vehicle_half − safety) on both sides. Headroom arrays are
    # computed in the operator from the same wr_safe / wl_safe / off_raceline
    # data already used to build inside_budget, so this is just extending the
    # existing safety contract from "at apex only" to "every station".
    if headroom_pos_d is not None and headroom_neg_d is not None:
        hp = np.asarray(headroom_pos_d, dtype=float)
        hn = np.asarray(headroom_neg_d, dtype=float)
        if hp.shape[0] == n and hn.shape[0] == n:
            n_clipped_pos = int(np.sum(d_off > hp))
            n_clipped_neg = int(np.sum(d_off < -hn))
            d_off = np.minimum(d_off,  hp)
            d_off = np.maximum(d_off, -hn)
            if dbg_tag and (n_clipped_pos + n_clipped_neg) > 0:
                print(
                    f"[V4-APEXWARP] {dbg_tag}: per-station clip "
                    f"saved {n_clipped_pos}+{n_clipped_neg} stations from going off-track",
                    flush=True,
                )

    if dbg_tag:
        print(
            f"[V4-APEXWARP] {dbg_tag}: d_off peak={float(np.abs(d_off).max()):.3f} "
            f"mean|·|={float(np.abs(d_off).mean()):.3f}",
            flush=True,
        )

    return d_off


def _v4_compute_d_offset_global(raceline, n_r, master,
                                g_ap=0.0, g_at=0.5, g_vu=0.0,
                                k_global=0.45, kappa_smooth_sigma=22.0,
                                phase_shift_max=18.0, global_clip=0.16,
                                dbg_tag=""):
    """SMOOTH GLOBAL d-offset derived from Q's signed curvature and the driver's
    LAP-WIDE style aggregates only. No per-corner data is consulted.

    Why this shape: every driver's line is `magnitude × kappa_norm(s)` where
    kappa_norm(s) is a single low-passed periodic function of arc-length. All
    drivers therefore have the SAME profile shape, just scaled by per-driver
    looseness (1 − g_at). A looser driver is *consistently* further from Q
    across the whole lap — the lines never cross, never produce
    convergence-then-divergence 'kissing' bumps, never have a corner-chunk
    pulled while the surrounding straight stays on Q.

    apex_phase shifts the kappa profile in arc-length by phase_shift_max × g_ap
    stations, so two drivers with similar tightness but different apex_phase
    have their offsets timed slightly differently — small per-driver shape
    variation without breaking the consistent-ordering property."""
    import numpy as np
    from scipy.ndimage import gaussian_filter1d
    n = int(n_r)
    if n < 8:
        return np.zeros(n)

    # Tangents and signed curvature, periodic, chord-based.
    tangents = np.zeros((n, 2))
    for i in range(n):
        dvec = raceline[(i + 5) % n] - raceline[(i - 5) % n]
        nm = float(np.linalg.norm(dvec))
        if nm > 1e-8:
            tangents[i] = dvec / nm
        else:
            tangents[i] = np.array([1.0, 0.0])
    kappa = np.zeros(n)
    for i in range(n):
        t1 = tangents[(i - 1) % n]
        t2 = tangents[(i + 1) % n]
        cross = float(t1[0] * t2[1] - t1[1] * t2[0])
        dot = float(np.clip(t1[0] * t2[0] + t1[1] * t2[1], -1.0, 1.0))
        kappa[i] = math.copysign(math.acos(dot), cross)

    # Periodic low-pass — kills high-frequency curvature wiggles.
    kappa = gaussian_filter1d(np.tile(kappa, 3), sigma=float(kappa_smooth_sigma))[n:2 * n]

    # Normalise to [-1, +1] using lap-wide max.
    k_max = float(np.abs(kappa).max())
    if k_max < 1e-9:
        return np.zeros(n)
    kappa_norm = kappa / k_max

    # Apex-phase shift (small arc-length roll for inter-driver variety).
    if abs(g_ap) > 1e-6 and phase_shift_max > 0:
        shift_int = int(round(float(g_ap) * float(phase_shift_max)))
        if shift_int != 0:
            kappa_norm = np.roll(kappa_norm, shift_int)

    looseness = 1.0 - max(0.0, min(1.0, float(g_at)))
    magnitude = float(k_global) * looseness * float(master)

    d_off = magnitude * kappa_norm
    d_off = np.clip(d_off, -float(global_clip), +float(global_clip))

    if dbg_tag:
        print(
            f"[V4-OFFSET-GLOBAL] {dbg_tag}: g_at={g_at:.3f} g_ap={g_ap:+.3f} "
            f"looseness={looseness:.3f} mag={magnitude:+.3f} "
            f"d_off peak={float(np.abs(d_off).max()):.3f} mean|.|={float(np.abs(d_off).mean()):.3f}",
            flush=True,
        )

    return d_off


def _v4_compute_d_offset_subtle(raceline, n_r, master,
                                g_ap=0.0, g_at=0.5, g_vu=0.0,
                                headroom_pos_d=None, headroom_neg_d=None,
                                max_headroom_frac=0.35,
                                k_global=0.55, kappa_smooth_sigma=22.0,
                                phase_shift_max=18.0,
                                dbg_tag=""):
    """SUBTLE per-driver d-offset — Q-anchored, strictly on-track, small but
    visible variance per the user's revised spec ("a bit of driver's style,
    can't be too different than Q, never goes off track").

    Shape philosophy is identical to `_v4_compute_d_offset_global`: one
    κ-derived periodic profile shared across drivers, scaled per driver by
    looseness = (1 − apex_tightness), with a small per-driver phase roll from
    apex_phase. Drivers therefore have the SAME shape, scaled and shifted.
    No per-corner gaussians, no apex-warp dipoles — both of those have failure
    modes (off-track tails, mean-zero displacement) documented in the file
    header session log.

    The on-track guarantee is HARD per-station clipping against the cached
    safe headroom. `headroom_pos_d` / `headroom_neg_d` are passed in d-units
    (fraction of track width) by the operator and represent the available
    room to the right / left kerb at each station after subtracting the
    vehicle half-width and a 0.15 m safety margin. We cap d_offset to
    `max_headroom_frac` of those values so the line cannot use the full
    headroom — at default 0.35 the styled line uses up to 35% of the way
    from Q to the safe edge in either direction. Lower = closer to Q,
    higher = visibly wider variance (1.0 still on-track but right at the
    safe edge, not recommended)."""
    import numpy as np
    from scipy.ndimage import gaussian_filter1d
    n = int(n_r)
    if n < 8:
        return np.zeros(n)

    tangents = np.zeros((n, 2))
    for i in range(n):
        dvec = raceline[(i + 5) % n] - raceline[(i - 5) % n]
        nm = float(np.linalg.norm(dvec))
        tangents[i] = dvec / nm if nm > 1e-8 else np.array([1.0, 0.0])
    kappa = np.zeros(n)
    for i in range(n):
        t1 = tangents[(i - 1) % n]
        t2 = tangents[(i + 1) % n]
        cross = float(t1[0] * t2[1] - t1[1] * t2[0])
        dot = float(np.clip(t1[0] * t2[0] + t1[1] * t2[1], -1.0, 1.0))
        kappa[i] = math.copysign(math.acos(dot), cross)
    kappa = gaussian_filter1d(np.tile(kappa, 3), sigma=float(kappa_smooth_sigma))[n:2 * n]

    k_max = float(np.abs(kappa).max())
    if k_max < 1e-9:
        return np.zeros(n)
    kappa_norm = kappa / k_max

    if abs(g_ap) > 1e-6 and phase_shift_max > 0:
        shift_int = int(round(float(g_ap) * float(phase_shift_max)))
        if shift_int != 0:
            kappa_norm = np.roll(kappa_norm, shift_int)

    looseness = 1.0 - max(0.0, min(1.0, float(g_at)))
    magnitude = float(k_global) * looseness * float(master)
    d_off = magnitude * kappa_norm

    f = max(0.0, min(1.0, float(max_headroom_frac)))
    if headroom_pos_d is not None and headroom_neg_d is not None:
        cap_pos = np.asarray(headroom_pos_d, dtype=float) * f
        cap_neg = np.asarray(headroom_neg_d, dtype=float) * f
        d_off = np.minimum(d_off, cap_pos)
        d_off = np.maximum(d_off, -cap_neg)

    if dbg_tag:
        print(
            f"[V4-OFFSET-SUBTLE] {dbg_tag}: g_at={g_at:.3f} g_ap={g_ap:+.3f} "
            f"looseness={looseness:.3f} mag={magnitude:+.3f} "
            f"max_hr_frac={f:.2f} d_off peak={float(np.abs(d_off).max()):.3f} "
            f"mean|.|={float(np.abs(d_off).mean()):.3f}",
            flush=True,
        )

    return d_off


def _v4_compute_d_offset(corners, per_corner_data, n_r, master,
                         g_ap=0.0, g_at=0.5, g_vu=0.0,
                         k_loose=0.35, sigma_mult=1.0, sigma_cap=25.0,
                         max_shift_frac=0.20,
                         post_smooth_sigma=6.0, global_clip=0.18,
                         dbg_tag=""):
    """Smooth periodic cross-track d-offset across the WHOLE lap, summed from
    wide per-corner gaussians and then low-pass filtered.

    Per-corner magnitude is k_loose × (1 − apex_tightness) signed by kappa_sign.
    Corners where the driver's apex_tightness ≈ 1 contribute *nothing* — those
    corners genuinely show 'driver hugs the kerb' so the styled line should
    track Q there. Corners with looser tightness drift toward middle of track.

    Adjacent corners have opposite kappa_signs (left/right alternation) — wide
    sigma (2.5 × corner_length) ensures their tails OVERLAP rather than meeting
    in a sharp ±±± alternating pattern. A final periodic gaussian smooth kills
    any residual high-frequency wiggle from the discrete-corner contributions."""
    import numpy as np
    from scipy.ndimage import gaussian_filter1d
    d_off = np.zeros(n_r)

    if dbg_tag:
        print(f"[V4-OFFSET] {dbg_tag}: per-corner contributions:", flush=True)

    for ci, c in enumerate(corners):
        d_co = per_corner_data[ci] if ci < len(per_corner_data) else None
        if d_co is not None:
            try:
                ap = float(d_co.get('apex_phase', g_ap))
                at = float(d_co.get('apex_tightness', g_at))
                vu = float(d_co.get('vu_shape', g_vu))
            except Exception:
                ap, at, vu = g_ap, g_at, g_vu
        else:
            ap, at, vu = g_ap, g_at, g_vu

        L = int(c['L'])
        ks = int(c['kappa_sign'])
        apex_idx_abs = int(c['apex'])

        shift = float(ap) * float(max_shift_frac) * float(L)
        center = (apex_idx_abs + shift) % n_r

        vu_clip = float(np.clip(vu, -1.0, 1.0))
        sigma_raw = float(L) * float(sigma_mult) * (1.0 + 0.3 * vu_clip)
        # Cap sigma so a single long corner doesn't wrap its gaussian half-way
        # round the lap (which produces the 'huge deviation at lap start' artefact
        # when the last corner's tail bleeds across the seam at station 0).
        sigma = max(2.0, min(float(sigma_cap), sigma_raw))

        looseness = 1.0 - max(0.0, min(1.0, float(at)))
        magnitude = float(ks) * float(master) * float(k_loose) * looseness
        if abs(magnitude) < 1e-6:
            if dbg_tag:
                print(f"  c{ci:02d} L={L:3d} ks={ks:+d} at={at:.2f} mag=0 (skipped)", flush=True)
            continue

        i_arr = np.arange(n_r, dtype=float)
        d_circ = (i_arr - center + n_r * 0.5) % n_r - n_r * 0.5
        bump = np.exp(-(d_circ ** 2) / (2.0 * sigma * sigma))
        d_off = d_off + magnitude * bump

        if dbg_tag:
            print(
                f"  c{ci:02d} L={L:3d} ks={ks:+d} ap={ap:+.2f} at={at:.2f} vu={vu:+.2f} "
                f"shift={shift:+.1f} sigma={sigma:.1f} mag={magnitude:+.3f}",
                flush=True,
            )

    # Final low-pass: kills any residual high-frequency wiggle from the discrete
    # corner placements. Periodic via tile-then-slice (lap is a closed loop).
    if post_smooth_sigma > 0.0:
        d_off = gaussian_filter1d(np.tile(d_off, 3), sigma=float(post_smooth_sigma))[n_r:2 * n_r]

    # Global clip — last line of defence against runaway sum stacks.
    d_off = np.clip(d_off, -float(global_clip), +float(global_clip))
    return d_off


def _v4_assemble_styled(raceline, q_right_normal, width, d_q, d_offset):
    """styled[i] = Q[i] + (d_driver[i] − d_q[i]) × width[i] × q_right_normal[i]

    Round-trips Q exactly when d_offset = 0 everywhere. Displacement direction
    is Q's own smooth chord-based normal — adjacent stations have continuous
    direction even when centerline-nn indices jump. Magnitude is bounded by
    width × |d_offset| (clipped d_offset is small, so well within track)."""
    import numpy as np
    d_driver = np.clip(d_q + d_offset, 0.0, 1.0)
    delta_d = d_driver - d_q
    displacement = (delta_d * width)[:, None] * q_right_normal
    styled = raceline + displacement
    return styled, d_driver


class F1_OT_GenerateAllStyledRacingLines(Operator):
    bl_idname = "f1.generate_all_styled_racing_lines"
    bl_label = "Generate Styled Racing Lines"
    bl_description = (
        "Auto-discover every per-driver style JSON under "
        "<project>/F1_Pipeline_Assets/style_params/ that matches the currently "
        "loaded JSON's grand_prix + season (or all of them if none is loaded), "
        "and create one Q_RACING_LINE_STYLED_{driver} curve per driver. "
        "Pulls each driver's hifi-path JSON for lap-fraction corner matching."
    )

    def execute(self, context):
        if not dependencies_available():
            self.report({'ERROR'}, "Install dependencies first")
            return {'CANCELLED'}

        import numpy as np
        from mathutils import Vector
        from scipy.spatial import cKDTree as _cKDTree
        import json as _json
        import os, glob

        props = context.scene.f1_track_viz_props
        if not props.style_enabled:
            self.report({'INFO'}, "Style layer disabled")
            return {'CANCELLED'}

        q_obj = bpy.data.objects.get("Q_RACING_LINE")
        if not q_obj:
            self.report({'ERROR'}, "Q_RACING_LINE not found — run 'Generate Racing Line' first")
            return {'CANCELLED'}
        if "_has_style_cache" not in q_obj:
            self.report({'ERROR'}, "Style cache missing on Q_RACING_LINE — regenerate it first")
            return {'CANCELLED'}

        sp_q = q_obj.data.splines[0]
        n_r = len(sp_q.points)
        raceline = np.zeros((n_r, 2))
        # Capture Q Z separately so the styled curves can follow track elevation
        # instead of sitting at z=0 (which made them float above the track).
        raceline_z = np.zeros(n_r)
        for i in range(n_r):
            co = q_obj.matrix_world @ Vector(sp_q.points[i].co[:3])
            raceline[i] = [co.x, co.y]
            raceline_z[i] = co.z

        corners_r, _, _, _ = _v2_detect_corners_arclen(raceline)
        if not corners_r:
            self.report({'WARNING'}, "No corners detected on Q_RACING_LINE")
            return {'CANCELLED'}

        cl_qp = np.column_stack([
            np.array(q_obj["_cl_qp_x"], dtype=float),
            np.array(q_obj["_cl_qp_y"], dtype=float),
        ])
        wr_safe_cl = np.array(q_obj["_wr_safe"], dtype=float)
        wl_safe_cl = np.array(q_obj["_wl_safe"], dtype=float)
        n_cl = len(cl_qp)
        nv_cl_all = np.zeros((n_cl, 2))
        for s in range(n_cl):
            d = cl_qp[(s + 3) % n_cl] - cl_qp[(s - 3) % n_cl]
            nm = np.linalg.norm(d)
            if nm < 1e-8:
                nv_cl_all[s] = np.array([0.0, -1.0])
            else:
                t = d / nm
                nv_cl_all[s] = np.array([t[1], -t[0]])
        nn = _cKDTree(cl_qp).query(raceline)[1]
        nv_cl_r = nv_cl_all[nn]
        off_raceline = np.einsum('ij,ij->i', raceline - cl_qp[nn], nv_cl_r)
        veh_half = float(props.racing_line_veh_width) * 0.5
        safety = 0.15
        inside_budget = {}
        for ci, c in enumerate(corners_r):
            a = int(c['apex'])
            if c['kappa_sign'] < 0:
                # right turn → inside is RIGHT
                b = float(wr_safe_cl[nn[a]] - off_raceline[a] - veh_half - safety)
            else:
                # left turn → inside is LEFT
                b = float(wl_safe_cl[nn[a]] + off_raceline[a] - veh_half - safety)
            inside_budget[ci] = max(0.0, b)

        master = float(props.style_master)

        # V4 cross-track cache: Q's own smooth right-normal, total track width
        # per Q station, and Q's d ∈ [0, 1]. Q is the guide — styled line is
        # Q + lateral offset along Q's normal. Built from existing centerline
        # data, no external file.
        q_right_normal, q_width, d_q_per_station = _v4_compute_q_normals_width_and_d(
            raceline, wr_safe_cl, wl_safe_cl, nn, off_raceline,
        )

        # PER-STATION headroom (in METERS) for the apex-warp clip. Mirrors the
        # inside_budget calc above but for EVERY station, in BOTH directions —
        # because the apex-warp dipole has tails that extend onto straights
        # where Q's apex-only inside_budget doesn't apply. +d direction is
        # toward the right kerb (per _v4_compute_q_normals_width_and_d's d
        # convention), so:
        #   hr_pos_m = available meters moving toward RIGHT kerb
        #   hr_neg_m = available meters moving toward LEFT kerb
        # Convert to d-units (fraction of track width) for use inside the
        # apex-warp function, which works in d.
        # styled_wall_clearance_m: extra meters of clearance between the car
        # edge and the safe-edge wall, applied ONLY to styled lines (not Q).
        # Stops the styled-line clip from letting cars graze the wall.
        styled_wall_clearance_m = 1.0
        hr_pos_m = np.maximum(0.0, wr_safe_cl[nn] - off_raceline - veh_half - safety - styled_wall_clearance_m)
        hr_neg_m = np.maximum(0.0, wl_safe_cl[nn] + off_raceline - veh_half - safety - styled_wall_clearance_m)
        _w_safe = np.maximum(q_width, 1e-6)
        headroom_pos_d = hr_pos_m / _w_safe
        headroom_neg_d = hr_neg_m / _w_safe

        style_dir = _find_style_params_dir(props)
        if not style_dir:
            self.report({'ERROR'},
                "style_params/ folder not found — set Style JSON path or place "
                "the .blend in <project_root>/F1_Pipeline_Assets/...")
            return {'CANCELLED'}

        json_files = sorted(glob.glob(os.path.join(style_dir, "*.json")))
        if not json_files:
            self.report({'ERROR'}, f"No style JSONs in {style_dir}")
            return {'CANCELLED'}

        # Filter by GP+year if a JSON is currently loaded (to avoid making lines
        # for drivers from a different track sitting in the same folder).
        filter_gp = None
        filter_yr = None
        if props.style_json_path:
            try:
                with open(bpy.path.abspath(props.style_json_path), 'r', encoding='utf-8') as fp:
                    p = _json.load(fp)
                src = p.get('source', {})
                filter_gp = str(src.get('grand_prix', '')).strip().lower() or None
                filter_yr = str(src.get('season', '')).strip() or None
            except Exception:
                pass

        print("\n========== STYLED RACING LINES — BATCH ==========", flush=True)
        print(f"[BATCH] style_dir={style_dir}", flush=True)
        print(f"[BATCH] {len(json_files)} JSON(s) | filter_gp={filter_gp!r} filter_yr={filter_yr!r}", flush=True)
        print(f"[BATCH] Q corners={len(corners_r)} | master={master:.3f}", flush=True)

        # ─── PRE-PASS: cross-driver per-corner mean apex_tightness ──────────
        # The raw per-corner apex_tightness values extracted from telemetry only
        # spread ~5-15% across drivers (e.g. NOR=0.51 vs SAI=0.42 at one corner).
        # Run that through the (1 − apex_tightness) magnitude formula and you
        # get peak per-corner displacement differences of ~5-10cm between
        # drivers — invisible from any normal viewport distance, even though
        # the algorithm is doing exactly what it's supposed to.
        #
        # The fix: amplify each driver's deviation FROM the cross-driver mean
        # by a user-controlled factor (style_spread_amplify, default 3.0). This
        # keeps the AVERAGE behaviour identical to raw telemetry but spreads
        # the per-driver signature so it's actually visible. NOR really IS
        # tighter than SAI at this corner — we're just making that visible
        # instead of hiding it inside numerical noise. Not manufactured
        # physics; principled signal amplification.
        #
        # Pre-pass walks all matched-filter JSONs once to build per-corner
        # mean. Main loop then amplifies per-driver values before passing them
        # to apex_warp.
        cross_driver_means_at = {}  # corner_index → mean apex_tightness
        spread_amp = float(getattr(props, 'style_spread_amplify', 3.0))
        if spread_amp > 1.0001:
            _per_corner_at_lists = {}
            for jf in json_files:
                try:
                    with open(jf, 'r', encoding='utf-8') as fp:
                        _p = _json.load(fp)
                except Exception:
                    continue
                _src = _p.get('source', {})
                _gp = str(_src.get('grand_prix', '')).strip().lower()
                _yr = str(_src.get('season', '')).strip()
                if filter_gp and _gp != filter_gp:
                    continue
                if filter_yr and _yr != filter_yr:
                    continue
                for _ci, _c in enumerate(_p.get('corners') or []):
                    try:
                        _at = float(_c.get('apex_tightness', 0.5))
                    except Exception:
                        continue
                    _per_corner_at_lists.setdefault(_ci, []).append(_at)
            for _ci, _vals in _per_corner_at_lists.items():
                if _vals:
                    cross_driver_means_at[_ci] = sum(_vals) / len(_vals)
            if cross_driver_means_at:
                print(
                    f"[BATCH] Cross-driver amplify={spread_amp:.2f}× active over "
                    f"{len(cross_driver_means_at)} corners "
                    f"({len(_per_corner_at_lists.get(0, []))} drivers in pre-pass)",
                    flush=True,
                )

        # ─── PRE-PASS for SUBTLE: lap-wide cross-driver mean apex_tightness ──
        # SUBTLE mode reads a single lap-wide g_at per driver (not per-corner),
        # so the per-corner mean above doesn't help it separate drivers. Build
        # a parallel mean over the lap-wide style_params.apex_tightness so the
        # main loop can amplify each driver's deviation from the lap-wide
        # cross-driver mean — same formula as the per-corner pre-pass, just
        # applied to the lap-wide aggregate.
        cross_driver_mean_g_at = None
        if spread_amp > 1.0001 and getattr(props, 'style_offset_mode', 'SUBTLE') == 'SUBTLE':
            _g_at_list = []
            for jf in json_files:
                try:
                    with open(jf, 'r', encoding='utf-8') as fp:
                        _p = _json.load(fp)
                except Exception:
                    continue
                _src = _p.get('source', {})
                _gp = str(_src.get('grand_prix', '')).strip().lower()
                _yr = str(_src.get('season', '')).strip()
                if filter_gp and _gp != filter_gp:
                    continue
                if filter_yr and _yr != filter_yr:
                    continue
                try:
                    _g_at_list.append(float((_p.get('style_params') or {}).get('apex_tightness', 0.5)))
                except Exception:
                    pass
            if _g_at_list:
                cross_driver_mean_g_at = sum(_g_at_list) / len(_g_at_list)
                print(
                    f"[BATCH] SUBTLE lap-wide amplify={spread_amp:.2f}× active "
                    f"({len(_g_at_list)} drivers, mean g_at={cross_driver_mean_g_at:.3f}, "
                    f"raw min/max={min(_g_at_list):.3f}/{max(_g_at_list):.3f})",
                    flush=True,
                )

        # ─── V4: cross-track-coordinate styled line ─────────────────────────
        # styled = left_kerb × (1 − d) + right_kerb × d
        # where d = clip(Q's d + per-driver d_offset(s), 0, 1). The d_offset
        # is a SINGLE smooth periodic function summed from wide per-corner
        # gaussians — adjacent corners overlap onto straights, so the whole
        # lap drifts continuously per-driver instead of having corner chunks
        # pulled while straights stay pinned to Q.
        written = []
        skipped = []
        for jf in json_files:
            try:
                with open(jf, 'r', encoding='utf-8') as fp:
                    payload = _json.load(fp)
            except Exception:
                skipped.append(f"{os.path.basename(jf)}: parse")
                continue

            src = payload.get('source', {})
            driver = str(src.get('driver', '')).strip()
            gp = str(src.get('grand_prix', '')).strip().lower()
            yr = str(src.get('season', '')).strip()
            if not driver:
                skipped.append(f"{os.path.basename(jf)}: no driver")
                continue
            if filter_gp and gp != filter_gp:
                continue
            if filter_yr and yr != filter_yr:
                continue

            json_params  = payload.get('style_params', {}) or {}
            json_corners = payload.get('corners') or []

            # Lap-fraction match: detect SAI's corners on its hifi-path, pair
            # by arc-length position with Q's corners.
            hifi_file = _v3_find_hifi_path(driver, props)
            sai_xy = _v3_load_hifi_xy(hifi_file) if hifi_file else None
            per_corner_data = [None] * len(corners_r)
            if sai_xy is not None and json_corners:
                sai_corners_det, _, _, _ = _v2_detect_corners_arclen(sai_xy)
                if sai_corners_det:
                    matched = _v3_match_corners_lap_fraction(
                        corners_r, raceline, sai_corners_det, sai_xy, max_diff=0.06,
                    )
                    for qi, sj in enumerate(matched):
                        if sj is not None and 0 <= sj < len(json_corners):
                            per_corner_data[qi] = json_corners[sj]
            n_match = sum(1 for d in per_corner_data if d is not None)

            # Positional fallback. If hifi-based matching produced 0 hits but
            # the JSON HAS per-corner data, pair Q's corners to the JSON's
            # corners by index. This is geometrically imperfect (Q's corner
            # detection might find a different count than the JSON's, and
            # corner ordering depends on where the lap starts) but it ensures
            # per-driver data REACHES the algorithm. Without this fallback,
            # any driver whose hifi path is missing or whose corners don't
            # align by lap-fraction silently degrades to lap-wide aggregates,
            # which differ by ~8% across drivers and produce visually
            # identical styled lines. Beats that.
            if n_match == 0 and json_corners:
                n_assigned = 0
                for ci in range(min(len(corners_r), len(json_corners))):
                    per_corner_data[ci] = json_corners[ci]
                    n_assigned += 1
                if n_assigned > 0:
                    print(
                        f"[BATCH] {driver}: hifi-match returned 0 — using "
                        f"POSITIONAL fallback ({n_assigned}/{len(corners_r)} "
                        f"corners by index, JSON has {len(json_corners)})",
                        flush=True,
                    )
                    n_match = n_assigned

            # Cross-driver amplification of per-corner apex_tightness (see
            # pre-pass docstring above). For each populated per-corner entry,
            # replace its apex_tightness with:
            #     mean + (driver_at − mean) × spread_amp
            # then clip to [0, 1] so the value remains physically meaningful
            # (looseness = 1 − at must stay in [0, 1]). When spread_amp = 1.0
            # this is a no-op and per-corner data passes through untouched.
            if spread_amp > 1.0001 and cross_driver_means_at:
                _at_log_before = []
                _at_log_after = []
                for _ci, _entry in enumerate(per_corner_data):
                    if _entry is None or 'apex_tightness' not in _entry:
                        continue
                    _mean = cross_driver_means_at.get(_ci)
                    if _mean is None:
                        continue
                    try:
                        _at_raw = float(_entry['apex_tightness'])
                    except Exception:
                        continue
                    _at_amp = _mean + (_at_raw - _mean) * spread_amp
                    _at_amp = max(0.0, min(1.0, _at_amp))
                    # Don't mutate the shared payload dict — copy first.
                    _new = dict(_entry)
                    _new['apex_tightness'] = _at_amp
                    per_corner_data[_ci] = _new
                    _at_log_before.append(_at_raw)
                    _at_log_after.append(_at_amp)
                if _at_log_before:
                    _import_np = np  # already imported at op start
                    _b = _import_np.array(_at_log_before)
                    _a = _import_np.array(_at_log_after)
                    print(
                        f"[BATCH] {driver}: amplified apex_tightness "
                        f"raw mean={float(_b.mean()):.3f} std={float(_b.std()):.3f} → "
                        f"amp mean={float(_a.mean()):.3f} std={float(_a.std()):.3f} "
                        f"(min/max raw={float(_b.min()):.3f}/{float(_b.max()):.3f}, "
                        f"amp={float(_a.min()):.3f}/{float(_a.max()):.3f})",
                        flush=True,
                    )

            g_ap = float(json_params.get('apex_phase', 0.0))
            g_at = float(json_params.get('apex_tightness', 0.5))
            g_vu = float(json_params.get('vu_shape', 0.0))
            g_lr = float(json_params.get('lr_asymmetry', 0.0))

            mode = getattr(props, 'style_offset_mode', 'SUBTLE')

            # SUBTLE lap-wide amplification: spread the narrow per-driver g_at
            # distribution around its cross-driver mean so drivers visibly
            # separate even when raw telemetry only varies ~5-15%. Same
            # formula as the per-corner amplification block above; applied
            # only in SUBTLE mode because the other modes use g_at indirectly
            # (per-corner) and have their own amplification path.
            if mode == 'SUBTLE' and cross_driver_mean_g_at is not None:
                _g_at_amp = cross_driver_mean_g_at + (g_at - cross_driver_mean_g_at) * spread_amp
                _g_at_amp = max(0.05, min(0.95, _g_at_amp))
                if abs(_g_at_amp - g_at) > 1e-4:
                    print(f"[BATCH] {driver}: SUBTLE g_at {g_at:.3f} → {_g_at_amp:.3f} "
                          f"(amp={spread_amp:.2f}×, mean={cross_driver_mean_g_at:.3f})",
                          flush=True)
                g_at = _g_at_amp

            if mode == 'SUBTLE':
                d_off = _v4_compute_d_offset_subtle(
                    raceline, n_r, master,
                    g_ap=g_ap, g_at=g_at, g_vu=g_vu,
                    headroom_pos_d=headroom_pos_d,
                    headroom_neg_d=headroom_neg_d,
                    max_headroom_frac=float(getattr(props, 'style_subtle_max_headroom_frac', 0.35)),
                    dbg_tag=driver,
                )
            elif mode == 'GLOBAL':
                d_off = _v4_compute_d_offset_global(
                    raceline, n_r, master,
                    g_ap=g_ap, g_at=g_at, g_vu=g_vu,
                    dbg_tag=driver,
                )
            elif mode == 'PER_CORNER':
                d_off = _v4_compute_d_offset(
                    corners_r, per_corner_data, n_r, master,
                    g_ap=g_ap, g_at=g_at, g_vu=g_vu,
                    dbg_tag=driver,
                )
            else:  # APEX_WARP (default) — now routes to HYBRID synthesis.
                # The dropdown label is preserved for backward compatibility
                # with existing scenes; the underlying algorithm has been
                # upgraded to the hybrid model that combines the wide single-
                # pole baseline (continuous across-lap differentiation) with
                # the apex-shift dipole (within-corner shape + crossings),
                # with the same per-station headroom clip enforcing on-track
                # safety. The previous apex-warp-only implementation is still
                # in the file (_v4_compute_d_offset_apex_warp) and reachable
                # by direct call, just not from this dispatcher.
                #
                # Slider mapping into the hybrid:
                #   k_apex       → k_baseline (controls the across-lap
                #                  magnitude — the BIG signal)
                #   max_shift_frac → max_shift_frac (controls how far the
                #                    dipole's apex shift goes)
                #   post_smooth   → post_smooth_sigma
                # Other hybrid params (k_dipole_m, sigma_baseline_mult,
                # sigma_baseline_cap, global_clip) use the function defaults
                # tuned to satisfy the constraints simultaneously.
                # Slider value is in the original meters scale (default 0.55);
                # convert to hybrid's d-unit baseline by the ratio (target d
                # default 0.15) / (slider meters default 0.55) so the slider
                # default produces hybrid default behaviour, and slider moves
                # scale proportionally.
                _slider_k = float(getattr(props, 'style_apex_warp_k_apex', 0.55))
                d_off = _v4_compute_d_offset_hybrid(
                    corners_r, per_corner_data, n_r,
                    q_width, master,
                    g_ap=g_ap, g_at=g_at, g_vu=g_vu, g_lr=g_lr,
                    k_baseline=_slider_k * (0.15 / 0.55),
                    max_shift_frac=float(getattr(props, 'style_apex_warp_max_shift_frac', 0.30)),
                    post_smooth_sigma=float(getattr(props, 'style_apex_warp_post_smooth', 3.0)),
                    headroom_pos_d=headroom_pos_d,
                    headroom_neg_d=headroom_neg_d,
                    dbg_tag=driver,
                )
            styled, d_driver = _v4_assemble_styled(
                raceline, q_right_normal, q_width, d_q_per_station, d_off,
            )

            curve_name = f"Q_RACING_LINE_STYLED_{driver}"
            for d in [bpy.data.objects, bpy.data.curves]:
                if curve_name in d:
                    d.remove(d[curve_name], do_unlink=True)
            cd = bpy.data.curves.new(curve_name, 'CURVE')
            cd.dimensions = '3D'
            sp_s = cd.splines.new('POLY')
            sp_s.points.add(n_r - 1)
            for i in range(n_r):
                sp_s.points[i].co = (styled[i, 0], styled[i, 1], float(raceline_z[i]), 1.0)
            sp_s.use_cyclic_u = True
            obj_s = bpy.data.objects.new(curve_name, cd)
            bpy.context.collection.objects.link(obj_s)

            delta_total = float(np.linalg.norm(styled - raceline, axis=1).max())
            d_off_peak = float(np.abs(d_off).max())
            d_off_mean_abs = float(np.abs(d_off).mean())
            print(
                f"[BATCH] {driver}: {n_match}/{len(corners_r)} per-corner JSON matched | "
                f"d_off peak={d_off_peak:.3f} mean|·|={d_off_mean_abs:.3f} | "
                f"max_delta={delta_total:.2f}m | wrote {curve_name}",
                flush=True,
            )
            written.append(driver)

        print(f"[BATCH] Done: {len(written)} written, {len(skipped)} skipped", flush=True)
        print("========== BATCH END ==========\n", flush=True)

        if written:
            self.report({'INFO'}, f"Generated {len(written)} styled racing lines: {', '.join(written)}")
            return {'FINISHED'}
        self.report({'WARNING'}, f"Generated 0; skipped {len(skipped)}: {'; '.join(skipped)[:160]}")
        return {'CANCELLED'}


class F1_OT_LoadStyleFromJson(Operator):
    bl_idname = "f1.load_style_from_json"
    bl_label = "Load Style from JSON"
    bl_description = "Read style params JSON (from F1 Race Replay Studio addon) and populate the sliders"

    def execute(self, context):
        import json
        props = context.scene.f1_track_viz_props

        path = bpy.path.abspath(props.style_json_path) if props.style_json_path else ""
        if not path or not os.path.isfile(path):
            self.report({'ERROR'}, "Set Style JSON to a valid file path")
            return {'CANCELLED'}

        try:
            with open(path, "r", encoding="utf-8") as fp:
                payload = json.load(fp)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to parse JSON: {e}")
            return {'CANCELLED'}

        sp = payload.get("style_params")
        if not isinstance(sp, dict):
            self.report({'ERROR'}, "JSON missing 'style_params' object")
            return {'CANCELLED'}

        mapping = {
            "apex_phase":     "style_apex_phase",
            "apex_tightness": "style_apex_tightness",
            "entry_width":    "style_entry_width",
            "exit_width":     "style_exit_width",
            "vu_shape":       "style_vu_shape",
            "straight_bias":  "style_straight_bias",
            "smoothness":     "style_smoothness",
            "lr_asymmetry":   "style_lr_asymmetry",
        }
        loaded = []
        for json_key, prop_name in mapping.items():
            if json_key in sp:
                try:
                    setattr(props, prop_name, float(sp[json_key]))
                    loaded.append(json_key)
                except Exception:
                    pass

        src = payload.get("source", {})
        driver = str(src.get("driver", "")).strip() or "DRIVER"
        context.scene["_style_driver"] = driver

        corners_in = payload.get("corners")
        if isinstance(corners_in, list) and corners_in:
            context.scene["_style_corners"] = json.dumps(corners_in)
            corner_msg = f", {len(corners_in)} per-corner entries"
        else:
            if "_style_corners" in context.scene:
                del context.scene["_style_corners"]
            corner_msg = " (no per-corner data — JSON v1)"

        tag = f"{driver}/{src.get('grand_prix','?')}/{src.get('season','?')}"
        self.report({'INFO'}, f"Loaded {len(loaded)}/8 params from {tag}{corner_msg}")
        return {'FINISHED'}


class F1_OT_AlignPathToRacingLine(Operator):
    bl_idname = "f1.align_path_to_racing_line"
    bl_label = "Align / Reshape Path"
    bl_description = "Kabsch-align the Driving Path to Q_RACING_LINE or Q_RACING_LINE_STYLED (optionally overwrite source geometry)"

    def execute(self, context):
        if not dependencies_available():
            self.report({'ERROR'}, "Install dependencies first")
            return {'CANCELLED'}

        import numpy as np
        from mathutils import Vector

        props = context.scene.f1_track_viz_props
        path = props.driving_path
        q_obj = props.alignment_target_curve
        target_name = q_obj.name if q_obj else "(none)"

        if not path:
            self.report({'ERROR'}, "Select a Driving Path")
            return {'CANCELLED'}
        if not q_obj:
            self.report({'ERROR'}, "Pick a Target Line via the eyedropper")
            return {'CANCELLED'}

        N = props.alignment_samples
        blend_ratio = props.alignment_blend

        spline_p = path.data.splines[0]
        if spline_p.type == 'BEZIER':
            n_p = len(spline_p.bezier_points)
            P_raw = np.zeros((n_p, 3))
            for i, bp in enumerate(spline_p.bezier_points):
                co = path.matrix_world @ bp.co
                P_raw[i] = [co.x, co.y, co.z]
        else:
            n_p = len(spline_p.points)
            P_raw = np.zeros((n_p, 3))
            for i, pt in enumerate(spline_p.points):
                co = path.matrix_world @ Vector(pt.co[:3])
                P_raw[i] = [co.x, co.y, co.z]

        spline_q = q_obj.data.splines[0]
        n_q = len(spline_q.points)
        Q_raw = np.zeros((n_q, 3))
        for i, pt in enumerate(spline_q.points):
            co = q_obj.matrix_world @ Vector(pt.co[:3])
            Q_raw[i] = [co.x, co.y, co.z]

        P_resampled = _resample_equidistant_3d(P_raw, N)
        Q_resampled = _resample_equidistant_3d(Q_raw, N)

        # Try BOTH cyclic directions of P during the search. F1 telemetry from
        # FastF1 and Q_RACING_LINE (derived from the .blend's centerline) are
        # not guaranteed to traverse the lap in the same direction. If they're
        # opposite, no rotation R can make ‖R·P[i] − Q[i]‖² small for every i,
        # and Kabsch picks a wildly wrong R — the path looks "flipped" /
        # off-track. Searching reversed P too lets us find the correct R.
        # We apply the resulting R to the FORWARD P_raw so the car still drives
        # in telemetry order — only the SEARCH uses the reversed array.
        P_resampled_rev = P_resampled[::-1].copy()
        candidates = (("forward", P_resampled), ("reversed", P_resampled_rev))

        test_shifts = min(N, 100)
        shift_step = max(1, N // test_shifts)
        best_rms = float('inf')
        best_shift = 0
        best_dir = "forward"

        for dir_label, P_try in candidates:
            for s in range(0, N, shift_step):
                Q_shifted = np.roll(Q_resampled, -s, axis=0)
                _, _, P_al = _kabsch_alignment(P_try, Q_shifted)
                rms = np.sqrt(((P_al - Q_shifted) ** 2).mean())
                if rms < best_rms:
                    best_rms = rms
                    best_shift = s
                    best_dir = dir_label

        # Refine within the winning direction only.
        P_winner = P_resampled if best_dir == "forward" else P_resampled_rev
        for s in range(max(0, best_shift - shift_step), min(N, best_shift + shift_step + 1)):
            Q_shifted = np.roll(Q_resampled, -s, axis=0)
            _, _, P_al = _kabsch_alignment(P_winner, Q_shifted)
            rms = np.sqrt(((P_al - Q_shifted) ** 2).mean())
            if rms < best_rms:
                best_rms = rms
                best_shift = s

        print(f"[ALIGN] best fit: dir={best_dir}, shift={best_shift}, "
              f"rms={best_rms:.2f}m", flush=True)

        Q_final = np.roll(Q_resampled, -best_shift, axis=0)
        # Use the WINNING direction's resampled P for the final Kabsch so
        # R is the rotation that actually minimised the search RMS. We still
        # apply R to the FORWARD P_raw below (preserves car drive direction);
        # rotating a closed polygon doesn't change its set of points, only
        # the index correspondence — which is what we wanted reversal to
        # change in the first place.
        P_winner_kabsch = P_resampled if best_dir == "forward" else P_resampled_rev
        R, t, _ = _kabsch_alignment(P_winner_kabsch, Q_final)

        P_full_aligned = (R @ P_raw.T).T + t

        if blend_ratio > 0.0:
            M = len(P_full_aligned)
            K_len = len(Q_raw)
            shift_ratio = best_shift / N
            
            A = Q_raw
            B = np.roll(Q_raw, -1, axis=0)
            AB = B - A
            AB_len_sq = np.sum(AB**2, axis=1)
            AB_len_sq[AB_len_sq < 1e-12] = 1e-12
            
            P_projected = np.zeros((M, 3))
            window = max(20, int(K_len * 0.15)) 
            
            for i in range(M):
                pt = P_full_aligned[i]
                # Index correspondence between P_raw[i] and Q_raw[expected_k]
                # depends on the direction the search picked. Forward:
                # expected_k ≈ (i/M + shift_ratio) · K_len. Reversed: P[i]
                # was paired with Q[N-1-i] in the search, so the mapping
                # flips: expected_k ≈ (1 - i/M + shift_ratio) · K_len.
                if best_dir == "forward":
                    expected_k = int(((i / M) + shift_ratio) * K_len) % K_len
                else:
                    expected_k = int(((1.0 - i / M) + shift_ratio) * K_len) % K_len
                idx = np.arange(expected_k - window, expected_k + window + 1) % K_len
                
                A_win = A[idx]
                AB_win = AB[idx]
                len_sq_win = AB_len_sq[idx]
                
                AP = pt - A_win
                dot_val = np.sum(AP * AB_win, axis=1)
                t_param = np.clip(dot_val / len_sq_win, 0.0, 1.0)
                
                proj = A_win + t_param[:, np.newaxis] * AB_win
                dists_sq = np.sum((pt - proj)**2, axis=1)
                best = np.argmin(dists_sq)
                P_projected[i] = proj[best]
            
            P_out = P_full_aligned * (1.0 - blend_ratio) + P_projected * blend_ratio
        else:
            P_out = P_full_aligned.copy()

        # Z-snap to track surface: the entire alignment chain (telemetry hifi
        # paths, Q_RACING_LINE, styled lines) is built at Z=0 because telemetry
        # JSONs carry no elevation and Q_RACING_LINE is written flat. Without
        # this snap the aligned path floats on the ground plane while the
        # track .blend has 3D elevation — what the user calls "rubber band
        # suspended around the track". We raycast each output point's XY
        # downward onto the track mesh; on a miss we keep current Z.
        track_obj = props.track_mesh if props.track_mesh else None
        if track_obj is None:
            track_obj = bpy.data.objects.get("Track")
        if track_obj is not None and track_obj.type == 'MESH':
            inv_tw = track_obj.matrix_world.inverted()
            dir_local = (inv_tw.to_3x3() @ Vector((0.0, 0.0, -1.0)))
            dlen = dir_local.length
            if dlen > 1e-9:
                dir_local = dir_local / dlen
            z_high = 10000.0
            n_hit = 0
            for i in range(len(P_out)):
                origin_world = Vector((float(P_out[i, 0]), float(P_out[i, 1]), z_high))
                origin_local = inv_tw @ origin_world
                hit, loc_local, _, _ = track_obj.ray_cast(origin_local, dir_local)
                if hit:
                    loc_world = track_obj.matrix_world @ loc_local
                    P_out[i, 2] = loc_world.z
                    n_hit += 1
            print(f"[ALIGN] Z-snap to '{track_obj.name}': "
                  f"{n_hit}/{len(P_out)} pts hit", flush=True)
        else:
            print("[ALIGN] Z-snap skipped: no track mesh "
                  "(set f1_track_viz_props.track_mesh or have a 'Track' object)",
                  flush=True)

        label = "ALIGNED_PATH_BLENDED"

        # Always clear any stale preview curve from previous runs so the scene
        # stays clean regardless of which mode we end up in.
        for d in [bpy.data.objects, bpy.data.curves]:
            if label in d:
                d.remove(d[label], do_unlink=True)

        # Preview mode: create ALIGNED_PATH_BLENDED as a separate curve.
        # Skipped when overwriting the source in place — that'd leave a
        # redundant second curve in the scene.
        if not props.overwrite_source_path:
            curve_data = bpy.data.curves.new(label, 'CURVE')
            curve_data.dimensions = '3D'
            sp_out = curve_data.splines.new('POLY')
            sp_out.points.add(len(P_out) - 1)
            for i in range(len(P_out)):
                sp_out.points[i].co = (P_out[i, 0], P_out[i, 1], P_out[i, 2], 1)
            sp_out.use_cyclic_u = True
            aligned_obj = bpy.data.objects.new(label, curve_data)
            bpy.context.collection.objects.link(aligned_obj)

        # Optional: overwrite the source curve's geometry in place, so any
        # follow-path rig targeting that curve automatically picks up the new shape.
        # Only spline points are touched — curve/object custom properties,
        # constraints, modifiers, drivers, and animation data are untouched.
        # Preserves original spline type (BEZIER / NURBS / POLY) so the rig's
        # expectations aren't broken.
        if props.overwrite_source_path:
            src_curve = path.data
            if src_curve.splines:
                orig_type = src_curve.splines[0].type
                orig_cyclic = bool(src_curve.splines[0].use_cyclic_u)
                orig_resolution = int(getattr(src_curve.splines[0], 'resolution_u', 12))
                orig_order = int(getattr(src_curve.splines[0], 'order_u', 4))
                orig_endpoint = bool(getattr(src_curve.splines[0], 'use_endpoint_u', True))
            else:
                orig_type, orig_cyclic = 'POLY', True
                orig_resolution, orig_order, orig_endpoint = 12, 4, True

            src_curve.splines.clear()
            new_sp = src_curve.splines.new(orig_type)
            inv = path.matrix_world.inverted()

            if orig_type == 'BEZIER':
                new_sp.bezier_points.add(len(P_out) - 1)
                for i in range(len(P_out)):
                    world_co = Vector((P_out[i, 0], P_out[i, 1], P_out[i, 2]))
                    local = inv @ world_co
                    bp = new_sp.bezier_points[i]
                    bp.co = (local.x, local.y, local.z)
                    bp.handle_left_type = 'AUTO'
                    bp.handle_right_type = 'AUTO'
            else:
                new_sp.points.add(len(P_out) - 1)
                for i in range(len(P_out)):
                    world_co = Vector((P_out[i, 0], P_out[i, 1], P_out[i, 2]))
                    local = inv @ world_co
                    new_sp.points[i].co = (local.x, local.y, local.z, 1)
                if orig_type == 'NURBS':
                    new_sp.order_u = orig_order
                    new_sp.resolution_u = orig_resolution
                    new_sp.use_endpoint_u = orig_endpoint

            new_sp.use_cyclic_u = orig_cyclic

        if props.overwrite_source_path:
            self.report({'INFO'},
                f"Reshaped '{path.name}' in place ({len(P_out)} pts, "
                f"target={target_name}, blend={blend_ratio:.2f})")
        else:
            self.report({'INFO'},
                f"{label} (preview-only, {len(P_out)} pts, "
                f"target={target_name}, blend={blend_ratio:.2f})")
        return {'FINISHED'}


class F1_OT_AlignAllDriverPaths(Operator):
    bl_idname = "f1.align_all_driver_paths"
    bl_label = "Align All Driver Paths"
    bl_description = (
        "For every Q_RACING_LINE_STYLED_{driver} in the scene, find the matching "
        "F1_Path_*{driver}* curve and Kabsch-align it. Uses the same alignment_blend "
        "/ alignment_samples / overwrite_source_path settings as the single-path button."
    )

    def execute(self, context):
        scene = context.scene
        props = scene.f1_track_viz_props

        styled_lines = [
            o for o in scene.objects
            if o.type == 'CURVE' and o.name.startswith("Q_RACING_LINE_STYLED_")
            and o.name not in ("Q_RACING_LINE_STYLED",)
        ]
        if not styled_lines:
            self.report({'ERROR'},
                "No Q_RACING_LINE_STYLED_{driver} curves in scene — run 'Generate Styled Racing Lines' first")
            return {'CANCELLED'}

        # Driving paths: ONLY curves named driving_path_* (those are the rig-followed
        # curves that the launch_control pipeline creates; LC_Trail_* are mesh trails
        # and not what the cars follow).
        driving_paths = [
            o for o in scene.objects
            if o.type == 'CURVE' and o.name.startswith("driving_path_")
        ]
        # Trails are kept as a SECONDARY index: their names always carry the rig
        # suffix (incl. driver code), which lets us back-map a driver to a
        # team-only-named driving_path (e.g. driving_path_Mclaren ← Norris).
        trails = [
            o for o in scene.objects
            if o.type == 'CURVE' and o.name.startswith("LC_Trail_")
        ]

        print("\n========== ALIGN ALL — DEBUG ==========", flush=True)
        print(f"[ALIGN] styled lines in scene: {[o.name for o in styled_lines]}", flush=True)
        print(f"[ALIGN] driving paths in scene: {[o.name for o in driving_paths]}", flush=True)
        print(f"[ALIGN] trails in scene       : {[o.name for o in trails]}", flush=True)

        if not driving_paths:
            print("[ALIGN] *** no driving_path_* curves found ***", flush=True)
            print("========== ALIGN ALL — END ==========\n", flush=True)
            self.report({'ERROR'},
                "No driving_path_* curves in scene")
            return {'CANCELLED'}

        def _resolve_driving_path(driver_code):
            du = driver_code.upper()
            # 0. Tag-based (universal — set on the curve at car registration
            #    time in f1_pipeline._register_car). Works regardless of how
            #    the rig template is named.
            for p in driving_paths:
                tag = p.get("_f1_driver_code")
                if tag is not None and str(tag).upper().strip() == du:
                    return p, "tag(_f1_driver_code)"
            # 1. Direct: driving_path whose name itself carries the driver code.
            for p in driving_paths:
                if du in p.name.upper():
                    return p, "direct-name"
            # 2. Indirect via trail: find a trail with driver code, extract its
            #    rig suffix, then look up driving_path_<suffix> or progressively
            #    shorter prefixes of the suffix.
            for t in trails:
                if du not in t.name.upper():
                    continue
                suffix = t.name
                for prefix in ("LC_Trail_car_rig_", "LC_Trail_"):
                    if suffix.startswith(prefix):
                        suffix = suffix[len(prefix):]
                        break
                parts = suffix.split("_")
                for i in range(len(parts), 0, -1):
                    candidate_name = "driving_path_" + "_".join(parts[:i])
                    p = scene.objects.get(candidate_name)
                    if p is not None and p.type == 'CURVE' and p in driving_paths:
                        return p, f"trail→suffix({'_'.join(parts[:i])})"
            return None, None

        old_path = props.driving_path
        old_target = props.alignment_target_curve
        aligned, skipped = [], []
        for line in styled_lines:
            driver = line.name.rsplit("_", 1)[-1]
            cand, how = _resolve_driving_path(driver)
            if cand is None:
                skipped.append(f"{driver}: no driving_path_*{driver}* found (direct or via trail)")
                print(f"[ALIGN] {driver}: NO MATCH", flush=True)
                continue
            try:
                props.driving_path = cand
                props.alignment_target_curve = line
                bpy.ops.f1.align_path_to_racing_line()
                aligned.append(f"{cand.name} → {line.name}")
                print(f"[ALIGN] {driver} ({how}): {cand.name} → {line.name} OK", flush=True)
            except Exception as e:
                skipped.append(f"{driver}: {e}")
                print(f"[ALIGN] {driver}: FAILED — {e}", flush=True)

        props.driving_path = old_path
        props.alignment_target_curve = old_target

        # Refresh trails so they re-bake from the modified driving paths
        # (launch_control's trail meshes reference the path geometry; without
        # this, trails stay on the old shape).
        try:
            bpy.ops.f1.refresh_trails()
            print("[ALIGN] f1.refresh_trails() OK — trails re-synced from updated paths", flush=True)
        except Exception as e:
            print(f"[ALIGN] f1.refresh_trails() skipped: {e}", flush=True)

        print(f"[ALIGN] Done: {len(aligned)} aligned, {len(skipped)} skipped", flush=True)
        print("========== ALIGN ALL — END ==========\n", flush=True)

        if aligned:
            msg = f"Aligned {len(aligned)} path(s)"
            if skipped:
                msg += f", skipped {len(skipped)}: {'; '.join(skipped)[:120]}"
            self.report({'INFO'}, msg)
            return {'FINISHED'}
        self.report({'WARNING'}, f"Aligned 0; skipped {len(skipped)}: {'; '.join(skipped)[:160]}")
        return {'CANCELLED'}


class F1_OT_ApplyStyleTuning(Operator):
    """One-click iterative tuning. Re-runs styled-line generation with the
    CURRENT slider values, then re-aligns every driving_path_<driver> onto
    the freshly rebuilt Q_RACING_LINE_STYLED_<driver> so the rigs that
    follow those driving paths actually move. Does NOT regenerate
    Q_RACING_LINE or the centerline (those are one-time-per-track and
    expensive to rebuild)."""

    bl_idname = "f1.apply_style_tuning"
    bl_label = "Apply Style Changes"
    bl_description = (
        "Rebuild styled lines from current slider values, then re-align all "
        "driver paths so the cars actually follow the new shapes. Does NOT "
        "regenerate Q_RACING_LINE or centerline. Fast — typically a few "
        "seconds for 4 drivers."
    )

    def execute(self, context):
        # Step 1 — rebuild the per-driver Q_RACING_LINE_STYLED_<driver> curves
        # from the JSONs and the current slider values. This is the call that
        # picks up new k_apex / max_shift_frac / post_smooth from props.
        try:
            r1 = bpy.ops.f1.generate_all_styled_racing_lines()
        except Exception as e:
            self.report({'ERROR'}, f"Styled-line generation failed: {e}")
            return {'CANCELLED'}
        if 'CANCELLED' in r1:
            self.report(
                {'WARNING'},
                "Styled-line generation cancelled — alignment skipped. "
                "Check console for the per-driver reason.",
            )
            return {'CANCELLED'}

        # Step 2 — re-align each driving_path_<driver> onto its NEW styled
        # line. Without this the rigs keep following the OLD path geometry
        # and the new style is invisible in the animation. align_all_driver_
        # paths internally calls f1.refresh_trails too, so trail meshes
        # also update.
        try:
            r2 = bpy.ops.f1.align_all_driver_paths()
        except Exception as e:
            self.report(
                {'WARNING'},
                f"Styled lines updated but alignment failed: {e}. "
                "Cars are still on old paths.",
            )
            return {'FINISHED'}
        if 'CANCELLED' in r2:
            self.report(
                {'WARNING'},
                "Styled lines updated; alignment cancelled (likely no "
                "driving_path_* curves matched). Cars are still on old paths.",
            )
            return {'FINISHED'}

        # ─── DIAGNOSTIC DUMP ────────────────────────────────────────────────
        # Stop guessing why driver paths look identical. Print:
        #   • Every driving_path_* curve: id, _f1_driver_code tag, first vertex
        #     in world coordinates. Same id = same Python object = the loop
        #     overwrote one curve twice (root cause A).
        #   • Pairwise max-distance between corresponding-station vertices on
        #     each pair of driving paths. < 10 cm means the styled lines
        #     themselves are too similar (root cause B). > 50 cm means the
        #     lines are genuinely differentiated.
        #   • Same dump for Q_RACING_LINE_STYLED_*.
        # User pastes this to chat — root cause then becomes obvious.
        try:
            import numpy as _np
            from mathutils import Vector as _Vec

            scene = context.scene
            print("\n========== APPLY DIAGNOSTIC — IDENTITY + SPREAD ==========", flush=True)

            def _vert0(curve_obj):
                """First spline point in world coordinates."""
                if not curve_obj or not curve_obj.data or not curve_obj.data.splines:
                    return None
                sp = curve_obj.data.splines[0]
                if sp.type == 'BEZIER' and sp.bezier_points:
                    co = curve_obj.matrix_world @ sp.bezier_points[0].co
                elif sp.points:
                    co = curve_obj.matrix_world @ _Vec(sp.points[0].co[:3])
                else:
                    return None
                return (round(co.x, 3), round(co.y, 3), round(co.z, 3))

            def _all_verts(curve_obj):
                """All spline points as (N,3) numpy array in world coordinates."""
                if not curve_obj or not curve_obj.data or not curve_obj.data.splines:
                    return None
                sp = curve_obj.data.splines[0]
                if sp.type == 'BEZIER':
                    pts = [curve_obj.matrix_world @ bp.co for bp in sp.bezier_points]
                else:
                    pts = [curve_obj.matrix_world @ _Vec(p.co[:3]) for p in sp.points]
                if not pts:
                    return None
                return _np.array([(p.x, p.y, p.z) for p in pts])

            dpaths = sorted(
                [o for o in scene.objects if o.type == 'CURVE' and o.name.startswith("driving_path_")],
                key=lambda o: o.name,
            )
            print(f"\n[DIAG] driving_path_* curves: {len(dpaths)}", flush=True)
            for o in dpaths:
                tag = o.get("_f1_driver_code", "<no tag>")
                print(f"  {o.name:40s}  id={id(o):>14d}  tag={tag!s:6s}  first_vert={_vert0(o)}", flush=True)

            # Identity check: any two paths sharing the same Python id?
            ids_seen = {}
            for o in dpaths:
                ids_seen.setdefault(id(o), []).append(o.name)
            dupes = [v for v in ids_seen.values() if len(v) > 1]
            if dupes:
                print(f"  *** WARNING: same Python object referenced by multiple names: {dupes}", flush=True)
            else:
                print(f"  → all {len(dpaths)} are distinct Python objects (cause A ruled out)", flush=True)

            # Pairwise spread between driving paths.
            print(f"\n[DIAG] pairwise driving-path spread (max vertex distance):", flush=True)
            arrs = [(o.name, _all_verts(o)) for o in dpaths]
            arrs = [(n, a) for n, a in arrs if a is not None]
            for i in range(len(arrs)):
                for j in range(i + 1, len(arrs)):
                    n1, a1 = arrs[i]
                    n2, a2 = arrs[j]
                    if a1.shape == a2.shape:
                        d = _np.linalg.norm(a1 - a2, axis=1)
                        print(f"  {n1} ↔ {n2}: max={d.max():.3f}m  mean={d.mean():.3f}m  median={float(_np.median(d)):.3f}m", flush=True)
                    else:
                        print(f"  {n1} ({a1.shape[0]} pts) vs {n2} ({a2.shape[0]} pts): different vert counts, skipped", flush=True)

            # Same for styled lines — tells us if the TARGETS themselves differ.
            slines = sorted(
                [o for o in scene.objects
                 if o.type == 'CURVE'
                 and o.name.startswith("Q_RACING_LINE_STYLED_")
                 and o.name != "Q_RACING_LINE_STYLED"],
                key=lambda o: o.name,
            )
            print(f"\n[DIAG] Q_RACING_LINE_STYLED_* curves: {len(slines)}", flush=True)
            for o in slines:
                print(f"  {o.name:40s}  id={id(o):>14d}  first_vert={_vert0(o)}", flush=True)

            print(f"\n[DIAG] pairwise STYLED-line spread (max vertex distance):", flush=True)
            sarrs = [(o.name, _all_verts(o)) for o in slines]
            sarrs = [(n, a) for n, a in sarrs if a is not None]
            for i in range(len(sarrs)):
                for j in range(i + 1, len(sarrs)):
                    n1, a1 = sarrs[i]
                    n2, a2 = sarrs[j]
                    if a1.shape == a2.shape:
                        d = _np.linalg.norm(a1 - a2, axis=1)
                        verdict = ("genuinely different" if d.max() > 0.50
                                   else "tiny — algorithm output too tame" if d.max() > 0.05
                                   else "essentially identical — algorithm produced no spread")
                        print(f"  {n1} ↔ {n2}: max={d.max():.3f}m  mean={d.mean():.3f}m  → {verdict}", flush=True)
                    else:
                        print(f"  {n1} ({a1.shape[0]} pts) vs {n2} ({a2.shape[0]} pts): different vert counts, skipped", flush=True)

            print("========== END DIAGNOSTIC ==========\n", flush=True)
        except Exception as _diag_err:
            print(f"[DIAG] failed: {_diag_err}", flush=True)

        self.report({'INFO'}, "Styled lines + driving paths updated — see console for diagnostic")
        return {'FINISHED'}


# ═══════════════════════════════════════════════════════════════════════════════
# UI PANEL
# ═══════════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRATION
# ═══════════════════════════════════════════════════════════════════════════════

classes = (
    F1TrackVizProperties,
    F1_OT_InstallTrackVizDeps,
    F1_OT_GenerateCenterline,
    F1_OT_GenerateRacingLine,
    F1_OT_GenerateAllStyledRacingLines,
    F1_OT_LoadStyleFromJson,
    F1_OT_AlignPathToRacingLine,
    F1_OT_AlignAllDriverPaths,
    F1_OT_ApplyStyleTuning,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.f1_track_viz_props = bpy.props.PointerProperty(type=F1TrackVizProperties)
    modules_path = get_modules_path()
    append_modules_to_sys_path(modules_path)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.f1_track_viz_props

if __name__ == "__main__":
    register()
