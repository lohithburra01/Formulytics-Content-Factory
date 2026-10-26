"""SPIKE: Austin hairpin, frame-by-frame wing trails.

Per frame (30 fps):
  1. lap data -> car position, heading, speed (speed = real 2026 FP1 trace, aligned to the racing line by speed shape)
  2. PteraSoftware steady ring VLM at that speed, in ground effect -> downforce per wing -> circulation (Kutta-Joukowski)
  3. new trail points at the 4 wing tips, at their positions on the track (world frame, air at rest)
  4. old trail points move only by the air they induce on each other (Biot-Savart, vortex segments + ground image)
  5. draw: camera over the car, north up
Wing geometry, ride heights and the vortex core growth are ASSUMPTIONS for this spike.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pterasoftware"))
import pterasoftware as ps
from pterasoftware import geometry as g, operating_point as op, problems as pr

TRACK = Path("D:/f1_hot_lap/OPTIMAL LAP SCRIPTS/F1_Pipeline_Assets")
RACELINE = TRACK / "tracks/united_states_grand_prix_lapcomp_raceline.json"
FP1 = TRACK / "exports/reference_2026_austin_fp1.csv"
OUT = Path(__file__).parent / "out"
FPS, WINDOW_S, TRAIL_S = 30, (-3.0, 3.0), 1.5
RHO = 1.225
# wings: name, x ahead of car centre, half span, chord, height above ground, pitch (deg, negative = downforce)
WINGS = [("front", 2.6, 0.9, 0.30, 0.08, -8.0), ("rear", -2.4, 0.5, 0.35, 0.83, -8.0)]
RC0, NU_T, SUBSTEPS = 0.06, 0.005, 4          # vortex core: start radius (m), growth (m^2/s) -> ~0.16 m after 1 s


# ---------- lap data ----------
def lap_data():
    P = np.asarray(json.load(open(RACELINE))["raceline"], float)
    seg = np.linalg.norm(np.diff(P, axis=0, append=P[:1]), axis=1)
    s = np.r_[0, np.cumsum(seg)][:-1]; L = s[-1] + seg[-1]
    ss = np.arange(0, L, 0.5)
    P = np.c_[np.interp(ss, s, P[:, 0], period=L), np.interp(ss, s, P[:, 1], period=L)]
    d1 = np.roll(P, -1, 0) - np.roll(P, 1, 0)
    d2 = (np.roll(P, -1, 0) - 2 * P + np.roll(P, 1, 0)) / 0.25
    k = (d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]) / np.maximum(np.linalg.norm(d1, axis=1) ** 3, 1e-9)
    k = np.convolve(np.r_[k[-20:], k, k[:20]], np.ones(21) / 21, "same")[20:-20]
    # real speed: FP1 v(distance fraction), shifted to best match a curvature-limited estimate of this line
    fp = pd.read_csv(FP1)
    vfp = np.interp(ss / L, fp.distance / fp.distance.iloc[-1], fp.speed / 3.6)
    vest = np.minimum(85, np.sqrt(4 * 9.81 / np.maximum(np.abs(k), 1e-6)))
    a, b = (vest - vest.mean()) / vest.std(), (vfp - vfp.mean()) / vfp.std()
    corr = np.real(np.fft.ifft(np.fft.fft(a) * np.conj(np.fft.fft(b)))) / len(a)
    shift = int(np.argmax(corr)); v = np.roll(vfp, shift)
    t = np.r_[0, np.cumsum(0.5 / v[:-1])]
    hdg = np.unwrap(np.arctan2(d1[:, 1], d1[:, 0]))
    print(f"line {L:.0f} m, FP1 aligned with corr {corr[shift]:.3f} (shift {shift * 0.5:.0f} m), lap {t[-1]:.1f} s")
    return P, k, v, t, hdg


# ---------- PteraSoftware: wing loads at one speed ----------
def wing_geom(name, x, half, chord, z, pitch):
    xs = lambda y: g.wing_cross_section.WingCrossSection(
        airfoil=g.airfoil.Airfoil(name="NACA0012"), num_spanwise_panels=10 if y == 0 else None, chord=chord,
        Lp_Wcsp_Lpp=(0.0, y, 0.0), control_surface_symmetry_type="symmetric", spanwise_spacing="cosine" if y == 0 else None)
    return g.wing.Wing(wing_cross_sections=[xs(0), xs(half)], name=name, Ler_Gs_Cgs=(-x, 0.0, z), angles_Gs_to_Wn_ixyz=(0.0, pitch, 0.0),
                       symmetric=True, symmetryNormal_G=(0.0, 1.0, 0.0), symmetryPoint_G_Cg=(0.0, 0.0, 0.0),
                       num_chordwise_panels=5, chordwise_spacing="uniform")


def wing_loads(V):
    """-> list of (downforce N, circulation m^2/s) per wing. Geometry z is height above ground (Cg on the ground plane)."""
    plane = g.airplane.Airplane(wings=[wing_geom(*w) for w in WINGS], name="car")
    opp = op.OperatingPoint(vCg__E=V, alpha=0.0, CgP1_E_Eo=(0.0, 0.0, -1e-3),
                            surfaceNormal_E=(0.0, 0.0, 1.0), surfacePoint_E_Eo=(0.0, 0.0, 0.0))
    sp = pr.SteadyProblem(airplanes=[plane], operating_point=opp)
    ps.steady_ring_vortex_lattice_method.SteadyRingVortexLatticeMethodSolver(steady_problem=sp).run()
    out = []
    for w, (_, _, half, *_r) in zip(sp.airplanes[0].wings, WINGS):
        fz = np.array([[p.forces_W[2] for p in row] for row in np.asarray(w.panels)])   # (chordwise, spanwise)
        width = np.array([np.linalg.norm(p.frontLeg_G) for p in np.asarray(w.panels)[0]])
        gamma = fz.sum(0) / (RHO * V * width)                                       # per spanwise strip
        out.append((fz.sum(), float(gamma.max())))
    return out


# ---------- vortex trails in the world frame ----------
def induced(pts, A, B, G, rc):
    """velocity at pts (N,3) from straight vortex segments A->B (M,3), circulation G (M,), core rc (M,)"""
    r1 = pts[:, None, :] - A[None]; r2 = pts[:, None, :] - B[None]; r0 = B - A
    cr = np.cross(r1, r2)
    n1 = np.linalg.norm(r1, axis=2); n2 = np.linalg.norm(r2, axis=2)
    den = (cr ** 2).sum(2) + (rc[None] * np.linalg.norm(r0, axis=1)[None]) ** 2
    dot = (r0[None] * (r1 / np.maximum(n1, 1e-9)[..., None] - r2 / np.maximum(n2, 1e-9)[..., None])).sum(2)
    return (G[None, :, None] / (4 * np.pi) * cr / den[..., None] * dot[..., None]).sum(1)


def main():
    OUT.mkdir(exist_ok=True)
    P, k, v, t, hdg = lap_data()
    ic = int(np.argmax(np.abs(k)))
    t_frames = np.arange(t[ic] + WINDOW_S[0] - TRAIL_S, t[ic] + WINDOW_S[1], 1 / FPS)
    idx = np.searchsorted(t, t_frames)

    # tips: (wing index, side +1 left / -1 right); trail = list of nodes [x, y, z, gamma, birth time]
    tips = [(wi, sd) for wi in range(len(WINGS)) for sd in (+1, -1)]
    trails = {tp: [] for tp in tips}
    log, t_ptera, t_wake = [], 0.0, 0.0
    for f, (tf, i) in enumerate(zip(t_frames, idx)):
        c, s_ = np.cos(hdg[i]), np.sin(hdg[i])
        t0 = time.time(); loads = wing_loads(float(v[i])); t_ptera += time.time() - t0
        t0 = time.time()
        # segments: every trail chain + bound vortex across each wing, and their ground images
        tip_now = {}
        for wi, sd in tips:
            name, x, half, chord, z, pitch = WINGS[wi]
            xte = x - chord   # trailing edge
            tip_now[(wi, sd)] = np.array([P[i, 0] + xte * c - sd * half * s_, P[i, 1] + xte * s_ + sd * half * c, z])
        for _sub in range(SUBSTEPS):
            A, B, G, R = [], [], [], []
            for (wi, sd), nodes in trails.items():
                chain = [n[:3] for n in nodes] + [tip_now[(wi, sd)]]
                gam = [n[3] for n in nodes] + [loads[wi][1]]
                age = [tf - n[4] for n in nodes] + [0.0]
                for j in range(len(chain) - 1):    # filament runs from the wing back into the wake; sign per side
                    A.append(chain[j + 1]); B.append(chain[j]); G.append(sd * gam[j + 1]); R.append(np.sqrt(RC0 ** 2 + 4 * 1.2564 * NU_T * age[j]))
            for wi in range(len(WINGS)):
                A.append(tip_now[(wi, -1)]); B.append(tip_now[(wi, +1)]); G.append(loads[wi][1]); R.append(RC0)
            A, B, G, R = map(np.asarray, (A, B, G, R))
            allnodes = [(tp, j) for tp, nodes in trails.items() for j in range(len(nodes))]
            if not allnodes:
                break
            Ai, Bi = A * [1, 1, -1], B * [1, 1, -1]                     # ground = mirror image, opposite sense
            A2, B2, G2, R2 = np.r_[A, Ai], np.r_[B, Bi], np.r_[G, -G], np.r_[R, R]
            pts = np.array([trails[tp][j][:3] for tp, j in allnodes])
            u = induced(pts, A2, B2, G2, R2)
            for (tp, j), du in zip(allnodes, u):
                trails[tp][j][:3] = trails[tp][j][:3] + du / (FPS * SUBSTEPS)
                trails[tp][j][2] = max(trails[tp][j][2], 0.02)
        for tp in tips:                                                  # release new points, drop old ones
            trails[tp].append(np.r_[tip_now[tp], loads[tp[0]][1], tf])
            trails[tp] = [n for n in trails[tp] if tf - n[4] <= TRAIL_S]
        t_wake += time.time() - t0
        log.append((tf - t[ic], v[i] * 3.6, loads[0][0], loads[1][0]))
        if tf >= t[ic] + WINDOW_S[0]:
            draw(f, P, i, hdg[i], v[i], trails, tips, log)
    n = len(t_frames)
    print(f"{n} frames: PteraSoftware {1e3 * t_ptera / n:.0f} ms/frame, trails {1e3 * t_wake / n:.0f} ms/frame")
    np.savetxt(OUT / "log.csv", np.array(log), delimiter=",", header="t_from_apex,kmh,front_N,rear_N", comments="")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(OUT / "f_%04d.png"),
                    "-pix_fmt", "yuv420p", "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", str(OUT / "austin_hairpin_trails.mp4")], check=True)
    print("saved", OUT / "austin_hairpin_trails.mp4")


COLS = {0: "#00d0ff", 1: "#ffb000"}
_first = [None]


def draw(f, P, i, h, V, trails, tips, log):
    if _first[0] is None: _first[0] = f
    fig = plt.figure(figsize=(9, 10), facecolor="#111")
    a = fig.add_axes([0.03, 0.27, 0.94, 0.68]); a.set_facecolor("#2a2a2a")
    a.plot(P[:, 0] - P[i, 0], P[:, 1] - P[i, 1], color="#555", lw=95, solid_capstyle="round", zorder=1)
    a.plot(P[:, 0] - P[i, 0], P[:, 1] - P[i, 1], color="#777", lw=0.7, ls="--", zorder=2)
    for tp in tips:
        nd = np.array(trails[tp])
        if len(nd) < 2: continue
        age = (log[-1][0] - (nd[:, 4] - nd[-1, 4]) * 0 - 0) if False else (nd[-1, 4] - nd[:, 4]) / TRAIL_S
        xy = nd[:, :2] - P[i]
        for j in range(len(nd) - 1):
            a.plot(xy[j:j + 2, 0], xy[j:j + 2, 1], color=COLS[tp[0]], lw=0.6 + nd[j, 3] / 4, alpha=max(0.0, 1 - age[j]), zorder=4)
    c, s_ = np.cos(h), np.sin(h)
    body = np.array([[2.9, 0], [2.6, 0.9], [2.4, 0.9], [-2.6, 0.5], [-2.7, -0.5], [2.4, -0.9], [2.6, -0.9]])
    body = np.array([[2.9, 0], [2.6, 0.9], [-2.7, 0.5], [-2.7, -0.5], [2.6, -0.9]])
    a.fill(body[:, 0] * c - body[:, 1] * s_, body[:, 0] * s_ + body[:, 1] * c, color="red", zorder=5)
    R = 30; a.set_xlim(-R, R); a.set_ylim(-R, R); a.set_aspect("equal"); a.set_xticks([]); a.set_yticks([])
    a.set_title(f"Austin hairpin   {V * 3.6:5.0f} km/h   front {log[-1][2]:5.0f} N   rear {log[-1][3]:5.0f} N",
                color="w", family="monospace")
    lg = np.array(log)
    b = fig.add_axes([0.1, 0.05, 0.85, 0.17]); b.set_facecolor("#1a1a1a")
    b.plot(lg[:, 0], lg[:, 2], color=COLS[0], label="front wing downforce")
    b.plot(lg[:, 0], lg[:, 3], color=COLS[1], label="rear wing downforce")
    b.set_xlim(WINDOW_S[0] - TRAIL_S, WINDOW_S[1]); b.set_ylim(0, 6000); b.tick_params(colors="w", labelsize=8)
    b.set_xlabel("seconds from apex", color="w", fontsize=8); b.legend(fontsize=7, loc="upper right")
    fig.savefig(OUT / f"f_{f - _first[0]:04d}.png", dpi=80, facecolor="#111"); plt.close(fig)


if __name__ == "__main__":
    main()
