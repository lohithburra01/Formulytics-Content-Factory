"""SPIKE v4: Austin hairpin - dense wake sheets (like PteraSoftware's own wake plot), numba Biot-Savart.

v3 problem: one wake row per video frame (~1.1 m apart) -> sparse, no visible roll-up/curls.
v4: a wake row is shed every substep (SUBSTEPS per frame, ~0.15-0.25 m apart), all rows move under the induced
velocity of the whole vortex lattice + ground image every substep. Lattice = ring-vortex equivalent:
streamwise legs (dGamma across span), spanwise shed legs (change of circulation in time), bound vortex at 1/4 chord.
PteraSoftware gives the strip circulations once per frame. Biot-Savart runs in numba on all CPU cores.
"""
import subprocess
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numba as nb
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from hairpin_trails import FPS, WINDOW_S, RHO, WINGS, lap_data, g, op, pr, ps

OUT = Path(__file__).parent / "out_v4"
TRAIL_S = 1.0
SUBSTEPS = 6
N_SPAN = 6                        # panels per half wing -> 13 strip boundaries per wing
RC0, NU_T = 0.04, 0.004           # vortex core: start radius m, growth m^2/s (assumption)
ZOOM = 7.0                        # half width of view, m


def wing_geom(name, x, half, chord, z, pitch):
    xs = lambda y: g.wing_cross_section.WingCrossSection(
        airfoil=g.airfoil.Airfoil(name="NACA0012"), num_spanwise_panels=N_SPAN if y == 0 else None, chord=chord,
        Lp_Wcsp_Lpp=(0.0, y, 0.0), control_surface_symmetry_type="symmetric", spanwise_spacing="cosine" if y == 0 else None)
    return g.wing.Wing(wing_cross_sections=[xs(0), xs(half)], name=name, Ler_Gs_Cgs=(-x, 0.0, z), angles_Gs_to_Wn_ixyz=(0.0, pitch, 0.0),
                       symmetric=True, symmetryNormal_G=(0.0, 1.0, 0.0), symmetryPoint_G_Cg=(0.0, 0.0, 0.0),
                       num_chordwise_panels=5, chordwise_spacing="uniform")


def wing_sheet(V):
    """-> per wing: (downforce N, boundary y +left (nb,), strip circulation (nb-1,))"""
    plane = g.airplane.Airplane(wings=[wing_geom(*w) for w in WINGS], name="car")
    opp = op.OperatingPoint(vCg__E=V, alpha=0.0, CgP1_E_Eo=(0.0, 0.0, -1e-3),
                            surfaceNormal_E=(0.0, 0.0, 1.0), surfacePoint_E_Eo=(0.0, 0.0, 0.0))
    sp = pr.SteadyProblem(airplanes=[plane], operating_point=opp)
    ps.steady_ring_vortex_lattice_method.SteadyRingVortexLatticeMethodSolver(steady_problem=sp).run()
    out = []
    for w in sp.airplanes[0].wings:
        pan = np.asarray(w.panels)
        fz = np.array([[p.forces_W[2] for p in row] for row in pan])
        yL = np.array([p.Flpp_G_Cg[1] for p in pan[0]]); yR = np.array([p.Frpp_G_Cg[1] for p in pan[0]])
        o = np.argsort(yL); yL, yR, fz = yL[o], yR[o], fz[:, o]
        gam = fz.sum(0) / (RHO * V * np.abs(yR - yL))
        out.append((fz.sum(), -np.r_[yL, yR[-1]], gam))     # geometry y +right -> +left
    return out


@nb.njit(parallel=True, fastmath=True, cache=True)
def induce(pts, A, B, G, rc):
    n, m = pts.shape[0], A.shape[0]
    out = np.zeros((n, 3))
    for i in nb.prange(n):
        ux = uy = uz = 0.0
        px, py, pz = pts[i, 0], pts[i, 1], pts[i, 2]
        for j in range(m):
            r1x, r1y, r1z = px - A[j, 0], py - A[j, 1], pz - A[j, 2]
            r2x, r2y, r2z = px - B[j, 0], py - B[j, 1], pz - B[j, 2]
            r0x, r0y, r0z = B[j, 0] - A[j, 0], B[j, 1] - A[j, 1], B[j, 2] - A[j, 2]
            cx, cy, cz = r1y * r2z - r1z * r2y, r1z * r2x - r1x * r2z, r1x * r2y - r1y * r2x
            n1 = np.sqrt(r1x * r1x + r1y * r1y + r1z * r1z) + 1e-12
            n2 = np.sqrt(r2x * r2x + r2y * r2y + r2z * r2z) + 1e-12
            l2 = r0x * r0x + r0y * r0y + r0z * r0z
            den = cx * cx + cy * cy + cz * cz + rc[j] * rc[j] * l2
            if den < 1e-14:
                continue
            dot = r0x * (r1x / n1 - r2x / n2) + r0y * (r1y / n1 - r2y / n2) + r0z * (r1z / n1 - r2z / n2)
            k = G[j] / (4.0 * np.pi) * dot / den
            ux += k * cx; uy += k * cy; uz += k * cz
        out[i, 0], out[i, 1], out[i, 2] = ux, uy, uz
    return out


def core(age):
    return np.sqrt(RC0 ** 2 + 4 * 1.2564 * NU_T * age)


def main():
    OUT.mkdir(exist_ok=True)
    P, k, v, t, hdg = lap_data()
    ic = int(np.argmax(np.abs(k)))
    pose = lambda ts: (np.interp(ts, t, P[:, 0]), np.interp(ts, t, P[:, 1]), np.interp(ts, t, hdg), np.interp(ts, t, v))
    t_frames = np.arange(t[ic] + WINDOW_S[0] - TRAIL_S, t[ic] + WINDOW_S[1], 1 / FPS)
    dts = 1 / (FPS * SUBSTEPS)
    nw = len(WINGS)
    nodes = [np.zeros((0, 0, 3)) for _ in range(nw)]   # per wing: (rows, nb, 3), oldest first
    birth = [np.zeros(0) for _ in range(nw)]
    cg = [np.zeros((0, 0)) for _ in range(nw)]         # strip circulation of each row (rows, nb-1)
    log, tt, zcheck = [], {"ptera": 0.0, "wake": 0.0, "draw": 0.0}, []
    for f, tf in enumerate(t_frames):
        t0 = time.time(); sheet = wing_sheet(float(pose(tf)[3])); tt["ptera"] += time.time() - t0
        t0 = time.time()
        for sub in range(SUBSTEPS):
            ts = tf + sub * dts
            x0, y0, h, _ = pose(ts)
            fwd, left = np.array([np.cos(h), np.sin(h)]), np.array([-np.sin(h), np.cos(h)])
            segA, segB, segG, segR = [], [], [], []
            te_now, gam_now = [], []
            for wi, (name, x, half, chord, z, pitch) in enumerate(WINGS):
                _, yb, gam = sheet[wi]
                te = np.c_[x0 + (x - chord) * fwd[0] + yb * left[0], y0 + (x - chord) * fwd[1] + yb * left[1], np.full(len(yb), z)]
                qc = np.c_[x0 + (x - 0.25 * chord) * fwd[0] + yb * left[0], y0 + (x - 0.25 * chord) * fwd[1] + yb * left[1], np.full(len(yb), z)]
                dG = np.r_[gam[0], np.diff(gam), -gam[-1]]
                te_now.append(te); gam_now.append(gam)
                segA += [qc[1:], qc]; segB += [qc[:-1], te]; segG += [gam, dG]; segR += [np.full(len(gam), RC0), np.full(len(dG), RC0)]
                rows = nodes[wi]
                if len(rows):
                    full = np.concatenate([rows, te[None]], 0)                  # (n+1, nb, 3)
                    cfull = np.concatenate([cg[wi], gam[None]], 0)              # (n+1, nb-1)
                    ages = np.r_[ts - birth[wi], 0.0]
                    dGr = np.concatenate([np.zeros((len(rows), 1)), np.diff(cg[wi], axis=1, prepend=0, append=0)[:, 1:]], 1) if False else \
                        np.c_[cg[wi][:, :1], np.diff(cg[wi], axis=1), -cg[wi][:, -1:]]
                    # streamwise legs: older row r -> newer row r+1, strength dG of row r
                    segA.append(full[1:].reshape(-1, 3)); segB.append(full[:-1].reshape(-1, 3))
                    segG.append(dGr.reshape(-1)); segR.append(np.repeat(core(ages[:-1]), full.shape[1]))
                    # spanwise shed legs at rows 1..n: c[r-1] - c[r]
                    d = cfull[:-1] - cfull[1:]                                   # (n, nb-1)
                    segA.append(full[1:, 1:].reshape(-1, 3)); segB.append(full[1:, :-1].reshape(-1, 3))
                    segG.append(d.reshape(-1)); segR.append(np.repeat(core(ages[1:]), full.shape[1] - 1))
            A = np.concatenate(segA); B = np.concatenate(segB); G = np.concatenate(segG); R = np.concatenate(segR)
            keep = np.abs(G) > 1e-6
            A, B, G, R = A[keep], B[keep], G[keep], R[keep]
            A2 = np.r_[A, A * [1, 1, -1]]; B2 = np.r_[B, B * [1, 1, -1]]; G2 = np.r_[G, -G]; R2 = np.r_[R, R]
            sizes = [n_.shape[0] * n_.shape[1] if n_.size else 0 for n_ in nodes]
            if sum(sizes):
                pts = np.concatenate([n_.reshape(-1, 3) for n_ in nodes if n_.size])
                u = induce(pts, A2, B2, G2, R2) * dts
                o = 0
                for wi in range(nw):
                    if sizes[wi]:
                        nodes[wi] = nodes[wi] + u[o:o + sizes[wi]].reshape(nodes[wi].shape); o += sizes[wi]
                        nodes[wi][..., 2] = np.maximum(nodes[wi][..., 2], 0.02)
            for wi in range(nw):        # shed a new row at the trailing edge, drop old rows
                nodes[wi] = np.concatenate([nodes[wi], te_now[wi][None]], 0) if nodes[wi].size else te_now[wi][None]
                cg[wi] = np.concatenate([cg[wi], gam_now[wi][None]], 0) if cg[wi].size else gam_now[wi][None]
                birth[wi] = np.r_[birth[wi], ts]
                m = ts - birth[wi] <= TRAIL_S
                nodes[wi], cg[wi], birth[wi] = nodes[wi][m], cg[wi][m], birth[wi][m]
        tt["wake"] += time.time() - t0
        x0, y0, h, V = pose(tf)
        log.append((tf - t[ic], V * 3.6, sheet[0][0], sheet[1][0]))
        old = (tf - birth[0]) > 0.5
        if old.any():
            zcheck.append(nodes[0][old][..., 2].mean() - WINGS[0][4])
        if tf >= t[ic] + WINDOW_S[0]:
            t0 = time.time(); draw(f, P, (x0, y0), h, V, nodes, birth, tf, log); tt["draw"] += time.time() - t0
        if f % 30 == 0:
            print(f"frame {f}/{len(t_frames)}  wake nodes {sum(n_.shape[0] * n_.shape[1] for n_ in nodes)}  segs {len(A2)}  "
                  + "  ".join(f"{k_} {1e3 * x_ / (f + 1):.0f} ms" for k_, x_ in tt.items()), flush=True)
    n = len(t_frames)
    print("per frame: " + "  ".join(f"{k_} {1e3 * x_ / n:.0f} ms" for k_, x_ in tt.items()))
    print(f"front-wing wake older than 0.5 s sits {np.mean(zcheck) * 100:+.1f} cm vs the wing height (+ = rises, right for downforce)")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(OUT / "f_%04d.png"),
                    "-pix_fmt", "yuv420p", "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", str(OUT / "austin_hairpin_v4.mp4")], check=True)
    print("saved", OUT / "austin_hairpin_v4.mp4")


_first = [None]
CAR = np.array([[2.9, 0.0], [2.75, 0.12], [1.2, 0.2], [0.6, 0.45], [-0.6, 0.7], [-2.0, 0.6], [-2.7, 0.45],
                [-2.7, -0.45], [-2.0, -0.6], [-0.6, -0.7], [0.6, -0.45], [1.2, -0.2], [2.75, -0.12]])


def draw(f, P, c0, h, V, nodes, birth, tf, log):
    if _first[0] is None: _first[0] = f
    fig = plt.figure(figsize=(9, 10.5), facecolor="#0d0d0d")
    a = fig.add_axes([0.02, 0.24, 0.96, 0.72]); a.set_facecolor("#151515")
    px_per_m = 0.96 * 9 * 90 / (2 * ZOOM)
    a.plot(P[:, 0] - c0[0], P[:, 1] - c0[1], color="#353535", lw=12 * px_per_m * 72 / 90, solid_capstyle="round", zorder=1)
    cmaps = [plt.cm.cool, plt.cm.autumn]
    for wi, rows in enumerate(nodes):
        if not rows.size: continue
        ag = np.clip((tf - birth[wi]) / TRAIL_S, 0, 1)
        xy = rows[..., :2] - np.array(c0)
        for b in range(rows.shape[1]):               # each strip boundary = one streamline-like filament
            a.plot(xy[:, b, 0], xy[:, b, 1], color=cmaps[wi](0.5), lw=0.35, alpha=0.35, zorder=3)
        col = cmaps[wi](np.repeat(0.15 + 0.7 * ag, rows.shape[1]))
        col[:, 3] = np.repeat(np.clip(1.05 - ag, 0, 1), rows.shape[1])
        a.scatter(xy[..., 0].reshape(-1), xy[..., 1].reshape(-1), s=1.6, c=col, linewidths=0, zorder=4)
    c, s_ = np.cos(h), np.sin(h)
    a.fill(CAR[:, 0] * c - CAR[:, 1] * s_, CAR[:, 0] * s_ + CAR[:, 1] * c, color="#d01818", alpha=0.55, zorder=6)
    for name, x, half, chord, z, pitch in WINGS:
        ends = np.array([[x, half], [x, -half]])
        a.plot(ends[:, 0] * c - ends[:, 1] * s_, ends[:, 0] * s_ + ends[:, 1] * c, color="#eee", lw=2.5, zorder=7)
    a.set_xlim(-ZOOM, ZOOM); a.set_ylim(-ZOOM, ZOOM); a.set_aspect("equal"); a.set_xticks([]); a.set_yticks([])
    a.set_title(f"{V * 3.6:4.0f} km/h    front wing {log[-1][2]:5.0f} N    rear wing {log[-1][3]:5.0f} N",
                color="w", family="monospace", fontsize=12)
    lg = np.array(log)
    b = fig.add_axes([0.1, 0.04, 0.85, 0.15]); b.set_facecolor("#151515")
    b.plot(lg[:, 0], lg[:, 2], color="#3fd0ff", label="front wing"); b.plot(lg[:, 0], lg[:, 3], color="#ff9a2b", label="rear wing")
    b.set_xlim(WINDOW_S[0] - TRAIL_S, WINDOW_S[1]); b.set_ylim(0, 1500); b.tick_params(colors="w", labelsize=8)
    b.set_xlabel("seconds from apex", color="w", fontsize=8); b.set_ylabel("downforce N", color="w", fontsize=8)
    b.legend(fontsize=7, loc="upper right")
    fig.savefig(OUT / f"f_{f - _first[0]:04d}.png", dpi=90, facecolor="#0d0d0d"); plt.close(fig)


if __name__ == "__main__":
    main()
