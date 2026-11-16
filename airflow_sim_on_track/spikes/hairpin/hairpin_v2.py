"""SPIKE v2: Austin hairpin - full wake sheets + smoke tracers, zoomed in.

Changes vs v1 (user: "not detailed, no vortices, zoom in"):
  - every spanwise strip boundary of each wing sheds a trailing vortex filament with strength dGamma
    (PteraSoftware strip circulations), so the sheet rolls up into tip vortices by itself
  - smoke tracers are released each frame around the wing tips and along the trailing edges and carried by
    the induced velocity of the whole vortex system (+ ground image) -> visible swirl / corkscrew
  - camera +-10 m
Everything else (lap data, PteraSoftware per frame, world frame, north-up camera) as v1.
"""
import subprocess
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import hairpin_trails as v1
from hairpin_trails import FPS, WINDOW_S, RHO, WINGS, RC0, NU_T, lap_data, wing_geom, g, op, pr, ps

OUT = Path(__file__).parent / "out_v2"
TRAIL_S = 1.2
SUBSTEPS = 2
N_SPAN = 6                     # panels per half wing -> 13 filaments per wing
SMOKE_RING, SMOKE_R = 10, (0.08, 0.18)   # tracers per tip per frame, ring radii (m)
SMOKE_RAKE = 8                 # tracers along each wing's trailing edge per frame


def wing_sheet(V):
    """-> per wing: downforce N, y of strip boundaries (m, car frame, +left), dGamma at each boundary."""
    v1_geom = []
    for name, x, half, chord, z, pitch in WINGS:
        w = wing_geom(name, x, half, chord, z, pitch)
        for xs in w.wing_cross_sections:
            if xs.num_spanwise_panels: xs._num_spanwise_panels = N_SPAN
        v1_geom.append(w)
    plane = g.airplane.Airplane(wings=v1_geom, name="car")
    opp = op.OperatingPoint(vCg__E=V, alpha=0.0, CgP1_E_Eo=(0.0, 0.0, -1e-3),
                            surfaceNormal_E=(0.0, 0.0, 1.0), surfacePoint_E_Eo=(0.0, 0.0, 0.0))
    sp = pr.SteadyProblem(airplanes=[plane], operating_point=opp)
    ps.steady_ring_vortex_lattice_method.SteadyRingVortexLatticeMethodSolver(steady_problem=sp).run()
    out = []
    for w in sp.airplanes[0].wings:
        pan = np.asarray(w.panels)
        fz = np.array([[p.forces_W[2] for p in row] for row in pan])
        yL = np.array([p.Flpp_G_Cg[1] for p in pan[0]]); yR = np.array([p.Frpp_G_Cg[1] for p in pan[0]])
        order = np.argsort(yL); yL, yR, fz = yL[order], yR[order], fz[:, order]
        gam = fz.sum(0) / (RHO * V * np.abs(yR - yL))
        yb = np.r_[yL, yR[-1]]
        dG = np.r_[gam[0], np.diff(gam), -gam[-1]]       # shed strength at each boundary
        out.append((fz.sum(), -yb, dG))                   # geometry y is +right -> flip to +left
    return out


def induced(pts, A, B, G, rc, chunk=400):
    out = np.zeros_like(pts)
    r0 = B - A; l0 = np.linalg.norm(r0, axis=1)
    for c0 in range(0, len(pts), chunk):
        p = pts[c0:c0 + chunk]
        r1 = p[:, None] - A[None]; r2 = p[:, None] - B[None]
        cr = np.cross(r1, r2)
        n1 = np.linalg.norm(r1, axis=2); n2 = np.linalg.norm(r2, axis=2)
        den = (cr ** 2).sum(2) + (rc[None] * l0[None]) ** 2
        dot = (r0[None] * (r1 / np.maximum(n1, 1e-9)[..., None] - r2 / np.maximum(n2, 1e-9)[..., None])).sum(2)
        out[c0:c0 + chunk] = (G[None, :, None] / (4 * np.pi) * cr / den[..., None] * dot[..., None]).sum(1)
    return out


def main():
    OUT.mkdir(exist_ok=True)
    P, k, v, t, hdg = lap_data()
    ic = int(np.argmax(np.abs(k)))
    t_frames = np.arange(t[ic] + WINDOW_S[0] - TRAIL_S, t[ic] + WINDOW_S[1], 1 / FPS)
    idx = np.searchsorted(t, t_frames)
    rng = np.random.default_rng(0)
    fil = {}            # (wing, boundary) -> list of nodes [x, y, z, dGamma, birth]
    smoke = np.zeros((0, 6))   # x, y, z, birth, wing, kind
    log, tt = [], {"ptera": 0.0, "wake": 0.0, "draw": 0.0}
    for f, (tf, i) in enumerate(zip(t_frames, idx)):
        c, s_ = np.cos(hdg[i]), np.sin(hdg[i])
        fwd, left = np.array([c, s_]), np.array([-s_, c])
        t0 = time.time(); sheet = wing_sheet(float(v[i])); tt["ptera"] += time.time() - t0
        t0 = time.time()
        te_now = {}
        for wi, (name, x, half, chord, z, pitch) in enumerate(WINGS):
            _, yb, dG = sheet[wi]
            for b, (y, d) in enumerate(zip(yb, dG)):
                te_now[(wi, b)] = (np.r_[P[i] + (x - chord) * fwd + y * left, z], d)
        # new smoke: rings round each tip + rake along each trailing edge
        new = []
        for wi, (name, x, half, chord, z, pitch) in enumerate(WINGS):
            for sd in (+1, -1):
                tip = np.r_[P[i] + (x - chord) * fwd + sd * half * left, z]
                ang = rng.uniform(0, 2 * np.pi, SMOKE_RING); rr = rng.uniform(*SMOKE_R, SMOKE_RING)
                for a_, r_ in zip(ang, rr):
                    off = r_ * np.cos(a_) * left; dz = r_ * np.sin(a_)
                    new.append([*(tip[:2] + off), max(z + dz, 0.02), tf, wi, 0])
            for y in rng.uniform(-half, half, SMOKE_RAKE):
                p = P[i] + (x - chord) * fwd + y * left
                new.append([*p, z + rng.uniform(-0.03, 0.03), tf, wi, 1])
        smoke = np.r_[smoke, np.array(new)]
        for _ in range(SUBSTEPS):
            A, B, G, R = [], [], [], []
            for key, nodes in fil.items():
                cur, d_now = te_now[key]
                chain = [n[:3] for n in nodes] + [cur]
                for j in range(len(chain) - 1):
                    A.append(chain[j + 1]); B.append(chain[j]); G.append(nodes[j][3])
                    R.append(np.sqrt(RC0 ** 2 + 4 * 1.2564 * NU_T * (tf - nodes[j][4])))
            for wi in range(len(WINGS)):     # bound vortex segments between consecutive boundaries
                _, yb, dG = sheet[wi]; gam = np.cumsum(dG)[:-1]
                for b in range(len(yb) - 1):
                    A.append(te_now[(wi, b + 1)][0]); B.append(te_now[(wi, b)][0]); G.append(gam[b]); R.append(RC0)
            A, B, G, R = map(np.asarray, (A, B, G, R))
            A2, B2 = np.r_[A, A * [1, 1, -1]], np.r_[B, B * [1, 1, -1]]
            G2, R2 = np.r_[G, -G], np.r_[R, R]
            keys = [(key, j) for key, nodes in fil.items() for j in range(len(nodes))]
            pts = np.r_[np.array([fil[key][j][:3] for key, j in keys]).reshape(-1, 3), smoke[:, :3]]
            if len(pts) and len(A2):
                u = induced(pts, A2, B2, G2, R2) / (FPS * SUBSTEPS)
                for (key, j), du in zip(keys, u[:len(keys)]):
                    fil[key][j][:3] += du; fil[key][j][2] = max(fil[key][j][2], 0.02)
                smoke[:, :3] += u[len(keys):]; smoke[:, 2] = np.maximum(smoke[:, 2], 0.01)
        for key, (cur, d) in te_now.items():
            fil.setdefault(key, []).append(np.r_[cur, d, tf])
            fil[key] = [n for n in fil[key] if tf - n[4] <= TRAIL_S]
        smoke = smoke[tf - smoke[:, 3] <= TRAIL_S]
        tt["wake"] += time.time() - t0
        log.append((tf - t[ic], v[i] * 3.6, sheet[0][0], sheet[1][0]))
        if tf >= t[ic] + WINDOW_S[0]:
            t0 = time.time(); draw(f, P, i, hdg[i], v[i], fil, smoke, tf, log); tt["draw"] += time.time() - t0
        if f % 30 == 0:
            print(f"frame {f}/{len(t_frames)}  smoke {len(smoke)}  " + "  ".join(f"{k_} {1e3 * x_ / (f + 1):.0f} ms" for k_, x_ in tt.items()), flush=True)
    n = len(t_frames)
    print("per frame: " + "  ".join(f"{k_} {1e3 * x_ / n:.0f} ms" for k_, x_ in tt.items()))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(OUT / "f_%04d.png"),
                    "-pix_fmt", "yuv420p", "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", str(OUT / "austin_hairpin_v2.mp4")], check=True)
    print("saved", OUT / "austin_hairpin_v2.mp4")


_first = [None]
CAR = np.array([[2.9, 0.0], [2.75, 0.15], [1.2, 0.25], [0.6, 0.5], [-0.6, 0.75], [-2.0, 0.7], [-2.7, 0.5],
                [-2.7, -0.5], [-2.0, -0.7], [-0.6, -0.75], [0.6, -0.5], [1.2, -0.25], [2.75, -0.15]])


def draw(f, P, i, h, V, fil, smoke, tf, log):
    if _first[0] is None: _first[0] = f
    fig = plt.figure(figsize=(9, 10.5), facecolor="#0d0d0d")
    a = fig.add_axes([0.02, 0.24, 0.96, 0.72]); a.set_facecolor("#1c1c1c")
    R = 10
    a.plot(P[:, 0] - P[i, 0], P[:, 1] - P[i, 1], color="#3a3a3a", lw=380, solid_capstyle="round", zorder=1)
    # wake sheet filaments (thin, faint) - shows roll-up
    for (wi, b), nodes in fil.items():
        nd = np.array(nodes)
        if len(nd) < 2: continue
        a.plot(nd[:, 0] - P[i, 0], nd[:, 1] - P[i, 1], color=("#2b7fff" if wi == 0 else "#ff9a2b"), lw=0.4, alpha=0.35, zorder=3)
    # smoke: colour = wing, brightness = height swing (swirl), fade with age
    if len(smoke):
        age = (tf - smoke[:, 3]) / TRAIL_S
        base = np.where(smoke[:, 4] == 0, 0, 1)
        cm = [plt.cm.cool, plt.cm.autumn]
        for wi in (0, 1):
            m = base == wi
            zz = smoke[m, 2]; zn = (zz - zz.min()) / max(np.ptp(zz), 1e-6)
            col = cm[wi](0.25 + 0.6 * zn); col[:, 3] = np.clip(1 - age[m], 0, 1) * 0.8
            a.scatter(smoke[m, 0] - P[i, 0], smoke[m, 1] - P[i, 1], s=3.5, c=col, linewidths=0, zorder=4)
    c, s_ = np.cos(h), np.sin(h)
    a.fill(CAR[:, 0] * c - CAR[:, 1] * s_, CAR[:, 0] * s_ + CAR[:, 1] * c, color="#d01818", zorder=6)
    for name, x, half, chord, z, pitch in WINGS:
        ends = np.array([[x, half], [x, -half]])
        a.plot(ends[:, 0] * c - ends[:, 1] * s_, ends[:, 0] * s_ + ends[:, 1] * c, color="#eee", lw=3, zorder=7)
    a.set_xlim(-R, R); a.set_ylim(-R, R); a.set_aspect("equal"); a.set_xticks([]); a.set_yticks([])
    a.set_title(f"{V * 3.6:4.0f} km/h    front wing {log[-1][2]:5.0f} N    rear wing {log[-1][3]:5.0f} N",
                color="w", family="monospace", fontsize=12)
    lg = np.array(log)
    b = fig.add_axes([0.1, 0.04, 0.85, 0.15]); b.set_facecolor("#151515")
    b.plot(lg[:, 0], lg[:, 2], color="#2b7fff", label="front wing"); b.plot(lg[:, 0], lg[:, 3], color="#ff9a2b", label="rear wing")
    b.set_xlim(WINDOW_S[0] - TRAIL_S, WINDOW_S[1]); b.set_ylim(0, 1500); b.tick_params(colors="w", labelsize=8)
    b.set_xlabel("seconds from apex", color="w", fontsize=8); b.set_ylabel("downforce N", color="w", fontsize=8)
    b.legend(fontsize=7, loc="upper right")
    fig.savefig(OUT / f"f_{f - _first[0]:04d}.png", dpi=90, facecolor="#0d0d0d"); plt.close(fig)


if __name__ == "__main__":
    main()
