"""SPIKE v9: v8 + optional front-wing ENDPLATES and TYRE blockers (test whether they stop the tip-vortex collapse).

- ENDPLATES: one vertical thin plate per front-wing tip (Ptera wing rolled 90 deg, mirrored), 2 cm outboard of the
  tip (touching panels gave a singular tip strip, Gamma 85). Every surface sheds its own wake.
  Strip circulation from the Kutta-Joukowski vector form F = rho Gamma V x l (works for any orientation).
- TYRES: each tyre = a line of 3D point doublets across its width (strength per length 2 pi U R^2 = potential flow
  round a cylinder of radius R moving at U), + ground image. Moves with the car. Wake nodes that end up inside a
  tyre are put back on its surface. No tyre wake (separated flow) and no wing-tyre interaction in the wing loads.
Tyre/endplate sizes are ASSUMPTIONS (2026-ish).
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
import hairpin_v4 as v4
import hairpin_v6 as v6
import hairpin_v7 as v7
import hairpin_v8 as v8
import wings_v8 as W
from hairpin_trails import FPS, WINDOW_S, RHO, g, op, pr, ps

OUT = Path(__file__).parent / "out_v9"
ENDPLATES, TYRES, REAR = True, True, True
EP_GAP, EP_BOTTOM, EP_HEIGHT = 0.02, 0.03, 0.30          # m
# tyres: x of axle ahead of car centre, |y| of tyre centre, width, radius (m)
TYRE_SET = [(1.65, 0.80, 0.30, 0.36), (-1.75, 0.78, 0.40, 0.36)]
TYRE_PTS = 7
SHADOW_MARGIN = 0.10             # m each side of a front tyre: seeds there end at the tyre (see trace)
# vortex core 3x v4 (0.04 m, 0.004 m^2/s): thin cores let the many close wake sheets (endplates, tyres) wrinkle
# and churn differently every frame -> streamline jitter 17.6 -> 6.3 cm/frame at 0.12 m (measured, 2026-10-27)
v4.RC0, v4.NU_T = 0.12, 0.012
on_frame = None                    # hook(tf, nodes, cg, birth) for diagnostics
draw = v8.draw
v8.OUT = OUT
_tyres_now = [np.zeros((0, 3)), np.zeros((0, 3))]      # tyre doublets of the frame being drawn


def endplate():
    name, x, half, chord, z, pitch = v4.WINGS[0]
    xs = [g.wing_cross_section.WingCrossSection(
        airfoil=g.airfoil.Airfoil(name="NACA0006"), num_spanwise_panels=n, chord=chord, Lp_Wcsp_Lpp=(0.0, dy, 0.0),
        control_surface_symmetry_type="symmetric", spanwise_spacing="uniform" if n else None) for dy, n in ((0.0, 4), (EP_HEIGHT, None))]
    return g.wing.Wing(wing_cross_sections=xs, name="endplate", Ler_Gs_Cgs=(-x, half + EP_GAP, EP_BOTTOM),
                       angles_Gs_to_Wn_ixyz=(90.0, 0.0, 0.0), symmetric=True, symmetryNormal_G=(0.0, 1.0, 0.0),
                       symmetryPoint_G_Cg=(0.0, 0.0, 0.0), num_chordwise_panels=5, chordwise_spacing="uniform")


def wing_sheet(V):
    """Like v8.wing_sheet, for every surface (front, rear, endplates); Gamma from the KJ vector form."""
    wings = [v4.wing_geom(*w) for w in (v4.WINGS if REAR else v4.WINGS[:1])] + ([endplate()] if ENDPLATES else [])
    opp = op.OperatingPoint(vCg__E=V, alpha=0.0, CgP1_E_Eo=(0.0, 0.0, -1e-3),
                            surfaceNormal_E=(0.0, 0.0, 1.0), surfacePoint_E_Eo=(0.0, 0.0, 0.0))
    sp = pr.SteadyProblem(airplanes=[g.airplane.Airplane(wings=wings, name="car")], operating_point=opp)
    ps.steady_ring_vortex_lattice_method.SteadyRingVortexLatticeMethodSolver(steady_problem=sp).run()
    car = lambda q: np.c_[-q[:, 0], -q[:, 1], q[:, 2]]
    out = {}
    for w in sp.airplanes[0].wings:
        pan = np.asarray(w.panels)
        le = car(np.array([p.Flpp_G_Cg for p in pan[0]] + [pan[0, -1].Frpp_G_Cg]))
        te = car(np.array([p.Blpp_G_Cg for p in pan[-1]] + [pan[-1, -1].Brpp_G_Cg]))
        qc = 0.75 * le + 0.25 * te
        F = car(np.array([np.sum([p.forces_GP1 for p in pan[:, j]], 0) for j in range(pan.shape[1])]))
        c = np.cross([-V, 0.0, 0.0], qc[:-1] - qc[1:])              # bound leg runs qc[i+1] -> qc[i]
        gam = np.einsum("ij,ij->i", F, c) / (RHO * np.einsum("ij,ij->i", c, c))
        out[w.name] = (-F[:, 2].sum(), qc, te, gam)
    if not REAR:
        out["rear"] = (0.0,) + out["front"][1:3] + (out["front"][3] * 0,)
    order = ["front", "rear"] + [k for k in out if k not in ("front", "rear")]
    return [out[k] for k in order]


def tyre_dipoles(x0, y0, h, V):
    """World positions and moments of all tyre doublets (each tyre: a line across its width + ground image)."""
    c, s_ = np.cos(h), np.sin(h)
    U = V * np.array([c, s_, 0.0])
    Q, M = [], []
    for xa, ya, wd, R in TYRE_SET:
        for sd in (1, -1):
            for yy in np.linspace(sd * ya - wd / 2, sd * ya + wd / 2, TYRE_PTS):
                for zc in (R, -R):                                   # tyre centre + ground image
                    Q.append([x0 + xa * c - yy * s_, y0 + xa * s_ + yy * c, zc]); M.append(2 * np.pi * U * R ** 2 * wd / TYRE_PTS)
    return np.array(Q), np.array(M)


@nb.njit(fastmath=True, cache=True)
def dip(qx, qy, qz, TQ, TM):
    ux = uy = uz = 0.0
    for j in range(TQ.shape[0]):
        rx, ry, rz = qx - TQ[j, 0], qy - TQ[j, 1], qz - TQ[j, 2]
        r2 = rx * rx + ry * ry + rz * rz + 0.03 * 0.03
        pr_ = rx * TM[j, 0] + ry * TM[j, 1] + rz * TM[j, 2]
        f = 1.0 / (4.0 * np.pi * r2 ** 1.5)
        ux += f * (3.0 * pr_ * rx / r2 - TM[j, 0]); uy += f * (3.0 * pr_ * ry / r2 - TM[j, 1]); uz += f * (3.0 * pr_ * rz / r2 - TM[j, 2])
    return ux, uy, uz


@nb.njit(parallel=True, cache=True)
def dip_many(pts, TQ, TM):
    out = np.zeros_like(pts)
    for i in nb.prange(pts.shape[0]):
        out[i, 0], out[i, 1], out[i, 2] = dip(pts[i, 0], pts[i, 1], pts[i, 2], TQ, TM)
    return out


def tyre_velocity(pts, x0, y0, h, V):
    """Induced velocity of the moving tyres at world points."""
    return dip_many(pts, *tyre_dipoles(x0, y0, h, V))


@nb.njit(fastmath=True, cache=True)
def vel_t(px, py, pz, A, B, G, rc, cx, cy, V, fx, fy, w, TQ, TM):
    ux, uy, uz = v6.vel(px, py, pz, A, B, G, rc, cx, cy, V, fx, fy, w)
    tx, ty, tz = dip(px, py, pz, TQ, TM)
    return ux + tx, uy + ty, uz + tz


@nb.njit(parallel=True, fastmath=True, cache=True)
def _trace(seeds, A, B, G, rc, cx, cy, V, fx, fy, w, ds, nsteps, TQ, TM):
    """v6.trace (midpoint streamlines in the turning car frame) with the tyre doublets added."""
    n = seeds.shape[0]
    out = np.zeros((n, nsteps + 1, 4))
    for i in nb.prange(n):
        px, py, pz = seeds[i, 0], seeds[i, 1], seeds[i, 2]
        for k in range(nsteps + 1):
            ux, uy, uz = vel_t(px, py, pz, A, B, G, rc, cx, cy, V, fx, fy, w, TQ, TM)
            sp = np.sqrt(ux * ux + uy * uy + uz * uz) + 1e-12
            out[i, k, 0], out[i, k, 1], out[i, k, 2], out[i, k, 3] = px, py, pz, sp
            mx, my, mz = px + 0.5 * ds * ux / sp, py + 0.5 * ds * uy / sp, pz + 0.5 * ds * uz / sp
            ux, uy, uz = vel_t(mx, my, mz, A, B, G, rc, cx, cy, V, fx, fy, w, TQ, TM)
            sp = np.sqrt(ux * ux + uy * uy + uz * uz) + 1e-12
            px, py, pz = px + ds * ux / sp, py + ds * uy / sp, max(pz + ds * uz / sp, 0.01)
    return out


def trace(seeds, A, B, G, rc, cx, cy, V, fx, fy, w, ds, nsteps):
    """Streamlines with tyres; a line that enters a tyre stops there (else the doublet core sets the colour range)."""
    out = _trace(seeds, A, B, G, rc, cx, cy, V, fx, fy, w, ds, nsteps, *_tyres_now)
    if TYRES:
        lx = (out[..., 0] - cx) * fx + (out[..., 1] - cy) * fy
        ly = -(out[..., 0] - cx) * fy + (out[..., 1] - cy) * fx
        # lines seeded in line with a front tyre always end just ahead of it: otherwise they hit it in one frame and
        # slip past in the next, and their whole downstream part jumps (measured: 18 cm/frame vs 1.7 for the rest)
        xa, ya, wd, R = TYRE_SET[0]
        shadow = np.zeros(len(out), bool)
        for sd in (1, -1):
            shadow |= np.abs(ly[:, 0] - sd * ya) < wd / 2 + SHADOW_MARGIN
        for i in np.nonzero(shadow)[0]:
            j = np.argmax(lx[i] < xa + R + 0.03)
            if j > 0:
                out[i, j:] = out[i, j - 1]
        inside = np.zeros(lx.shape, bool)
        for xa, ya, wd, R in TYRE_SET:
            for sd in (1, -1):
                inside |= (np.abs(ly - sd * ya) < wd / 2) & (np.hypot(lx - xa, out[..., 2] - R) < R)
        hit = np.maximum.accumulate(inside, axis=1)
        last = np.where(hit.any(1), hit.argmax(1) - 1, nsteps).clip(0)
        for i in np.nonzero(hit.any(1))[0]:
            out[i, last[i] + 1:] = out[i, last[i]]
    return out


def slice_flow(c0, h, xs, lat, z, segs):
    """v8.slice_flow with the tyres' induced flow added."""
    c, s_ = np.cos(h), np.sin(h)
    Y, Z = np.meshgrid(lat, z)
    pts = np.c_[c0[0] + xs * c - Y.ravel() * s_, c0[1] + xs * s_ + Y.ravel() * c, Z.ravel()]
    u = v4.induce(pts, *segs) + dip_many(pts, *_tyres_now)
    vy = (-u[:, 0] * s_ + u[:, 1] * c).reshape(Y.shape)
    vz = u[:, 2].reshape(Y.shape)
    om = np.gradient(vz, lat, axis=1) - np.gradient(vy, z, axis=0)
    return Y, Z, vy, vz, om


def shapes(a, b, sl, c, s_, sheet):
    """Tyres and endplates in the top view, side view and slices."""
    rot = lambda q: np.c_[q[:, 0] * c - q[:, 1] * s_, q[:, 0] * s_ + q[:, 1] * c]
    if TYRES:
        for xa, ya, wd, R in TYRE_SET:
            for sd in (1, -1):
                q = rot(np.array([[xa - R, sd * ya - wd / 2], [xa + R, sd * ya - wd / 2], [xa + R, sd * ya + wd / 2], [xa - R, sd * ya + wd / 2]]))
                a.fill(q[:, 0], q[:, 1], color="#555", zorder=4.5)
            b.add_patch(plt.Circle((-xa, R), R, color="#555", zorder=4.5))
            for ax_, wi in zip(sl, (0, 1)):
                dx = sheet[wi][2][0, 0] - v8.SLICE_BEHIND - xa
                if abs(dx) < R:
                    hh = np.sqrt(R * R - dx * dx)
                    for sd in (1, -1):
                        ax_.add_patch(plt.Rectangle((sd * ya - wd / 2, R - hh), wd, 2 * hh, color="#555", zorder=3))
    if ENDPLATES:
        name, x, half, chord, z, pitch = v4.WINGS[0]
        for sd in (1, -1):
            q = rot(np.array([[x, sd * (half + EP_GAP)], [x - chord, sd * (half + EP_GAP)]]))
            a.plot(q[:, 0], q[:, 1], color="#222", lw=2, zorder=5)
        b.add_patch(plt.Rectangle((-x, EP_BOTTOM), chord, EP_HEIGHT, fill=False, ec="#222", lw=1, zorder=5))


def vortex_centres(tf, nodes, cg, birth, age_s):
    """Centres of + and - trailing vorticity of the front wing + endplates at one wake age -> (spacing, height)."""
    pos, wt = [], []
    for wi in [0] + list(range(2, len(nodes))):
        if not nodes[wi].size: continue
        age = tf - birth[wi]; i = np.argmin(np.abs(age - age_s))
        if abs(age[i] - age_s) > 0.02: continue
        cgi = cg[wi][i]
        pos.append(nodes[wi][i]); wt.append(np.r_[cgi[0], np.diff(cgi), -cgi[-1]])
    if not pos:
        return None
    pos, wt = np.concatenate(pos), np.concatenate(wt)
    cp = (pos[wt > 0] * wt[wt > 0, None]).sum(0) / wt[wt > 0].sum()
    cn = (pos[wt < 0] * -wt[wt < 0, None]).sum(0) / -wt[wt < 0].sum()
    return np.hypot(*(cp - cn)[:2]), 0.5 * (cp[2] + cn[2])


v8.EXTRA = shapes
v8._state["norm"] = v8.Normalize(0.75, 1.25)      # fixed: tyres give 0..2x car speed (potential flow), would hide the wings
v8.SLICE_BEHIND = 1.5                     # 1 m behind the front wing cuts the front tyres
v8.slice_flow = slice_flow
v8.v6 = type("v6_tyres", (), {"trace": staticmethod(trace), "DS": v6.DS, "LENGTH": v6.LENGTH, "ZOOM": v6.ZOOM})


def push_out_of_tyres(pts, x0, y0, h):
    c, s_ = np.cos(h), np.sin(h)
    for xa, ya, wd, R in TYRE_SET:
        for sd in (1, -1):
            lx = (pts[:, 0] - x0) * c + (pts[:, 1] - y0) * s_ - xa           # car axes, relative to tyre centre
            ly = -(pts[:, 0] - x0) * s_ + (pts[:, 1] - y0) * c - sd * ya
            lz = pts[:, 2] - R
            rr = np.hypot(lx, lz) + 1e-9
            m = (np.abs(ly) < wd / 2) & (rr < R)
            if m.any():
                k = R / rr[m]
                lx[m] *= k; lz[m] *= k
                pts[m, 0] = x0 + (lx[m] + xa) * c - (ly[m] + sd * ya) * s_
                pts[m, 1] = y0 + (lx[m] + xa) * s_ + (ly[m] + sd * ya) * c
                pts[m, 2] = lz[m] + R
    return pts


def main():
    OUT.mkdir(exist_ok=True)
    P, k, v, t, hdg = v7.smooth_lap_data()
    ic = int(np.argmax(np.abs(k)))
    pose = lambda ts: (np.interp(ts, t, P[:, 0]), np.interp(ts, t, P[:, 1]), np.interp(ts, t, hdg), np.interp(ts, t, v))
    t_frames = np.arange(t[ic] + WINDOW_S[0] - v4.TRAIL_S, t[ic] + WINDOW_S[1], 1 / FPS)
    dts = 1 / (FPS * v4.SUBSTEPS)
    nodes = birth = cg = None
    log, tt = [], {"ptera": 0.0, "wake": 0.0, "draw": 0.0}
    for f, tf in enumerate(t_frames):
        t0 = time.time(); sheet = wing_sheet(float(pose(tf)[3])); tt["ptera"] += time.time() - t0
        nw = len(sheet)
        if nodes is None:
            nodes, birth, cg = [np.zeros((0, 0, 3))] * nw, [np.zeros(0)] * nw, [np.zeros((0, 0))] * nw
        t0 = time.time()
        for sub in range(v4.SUBSTEPS):
            ts = tf - (v4.SUBSTEPS - 1 - sub) * dts
            x0, y0, h, Vs = pose(ts)
            world = lambda q: np.c_[x0 + q[:, 0] * np.cos(h) - q[:, 1] * np.sin(h), y0 + q[:, 0] * np.sin(h) + q[:, 1] * np.cos(h), q[:, 2]]
            segA, segB, segG, segR, te_now = [], [], [], [], []
            for wi in range(nw):
                _, qc_c, te_c, gam = sheet[wi]
                qc, te = world(qc_c), world(te_c)
                dG = np.r_[gam[0], np.diff(gam), -gam[-1]]
                te_now.append(te)
                segA += [qc[1:], qc]; segB += [qc[:-1], te]; segG += [gam, dG]
                segR += [np.full(len(gam), v4.RC0), np.full(len(dG), v4.RC0)]
                rows = nodes[wi]
                if len(rows):
                    full = np.concatenate([rows, te[None]], 0)
                    cfull = np.concatenate([cg[wi], gam[None]], 0)
                    ages = np.r_[ts - birth[wi], 0.0]
                    dGr = np.c_[cg[wi][:, :1], np.diff(cg[wi], axis=1), -cg[wi][:, -1:]]
                    segA.append(full[1:].reshape(-1, 3)); segB.append(full[:-1].reshape(-1, 3))
                    segG.append(dGr.reshape(-1)); segR.append(np.repeat(v4.core(ages[:-1]), full.shape[1]))
                    d = cfull[:-1] - cfull[1:]
                    segA.append(full[1:, 1:].reshape(-1, 3)); segB.append(full[1:, :-1].reshape(-1, 3))
                    segG.append(d.reshape(-1)); segR.append(np.repeat(v4.core(ages[1:]), full.shape[1] - 1))
            A, B, G, R = (np.concatenate(s) for s in (segA, segB, segG, segR))
            keep = np.abs(G) > 1e-6
            A, B, G, R = A[keep], B[keep], G[keep], R[keep]
            A2, B2, G2, R2 = np.r_[A, A * [1, 1, -1]], np.r_[B, B * [1, 1, -1]], np.r_[G, -G], np.r_[R, R]
            sizes = [n_.shape[0] * n_.shape[1] if n_.size else 0 for n_ in nodes]
            if sum(sizes):
                pts = np.concatenate([n_.reshape(-1, 3) for n_ in nodes if n_.size])
                u = v4.induce(pts, A2, B2, G2, R2)
                if TYRES:
                    u = u + tyre_velocity(pts, x0, y0, h, Vs)
                pts = pts + u * dts
                if TYRES:
                    pts = push_out_of_tyres(pts, x0, y0, h)
                pts[:, 2] = np.maximum(pts[:, 2], 0.02)
                o = 0
                for wi in range(nw):
                    if sizes[wi]:
                        nodes[wi] = pts[o:o + sizes[wi]].reshape(nodes[wi].shape); o += sizes[wi]
            for wi in range(nw):
                nodes[wi] = np.concatenate([nodes[wi], te_now[wi][None]], 0) if nodes[wi].size else te_now[wi][None]
                cg[wi] = np.concatenate([cg[wi], sheet[wi][3][None]], 0) if cg[wi].size else sheet[wi][3][None]
                birth[wi] = np.r_[birth[wi], ts]
                m = ts - birth[wi] <= v4.TRAIL_S
                nodes[wi], cg[wi], birth[wi] = nodes[wi][m], cg[wi][m], birth[wi][m]
        tt["wake"] += time.time() - t0
        x0, y0, h, V = pose(tf)
        log.append((tf - t[ic], V * 3.6, sheet[0][0], sheet[1][0]))
        if on_frame:
            on_frame(tf, nodes, cg, birth)
        if draw and tf >= t[ic] + WINDOW_S[0]:
            _tyres_now[:] = tyre_dipoles(x0, y0, h, V) if TYRES else [np.zeros((0, 3)), np.zeros((0, 3))]
            w = (pose(tf + 0.5 * dts)[2] - pose(tf - 0.5 * dts)[2]) / dts
            t0 = time.time(); draw(f, P, (x0, y0), h, V, w, sheet[:2], (A2, B2, G2, R2), log); tt["draw"] += time.time() - t0
        if f % 30 == 0:
            print(f"frame {f}/{len(t_frames)}  " + "  ".join(f"{k_} {1e3 * x_ / (f + 1):.0f} ms" for k_, x_ in tt.items()), flush=True)
    print("per frame: " + "  ".join(f"{k_} {1e3 * x_ / len(t_frames):.0f} ms" for k_, x_ in tt.items()))
    if draw:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(OUT / "f_%04d.png"),
                        "-pix_fmt", "yuv420p", "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", str(OUT / "austin_hairpin_v9.mp4")], check=True)


if __name__ == "__main__":
    stats = []
    on_frame = lambda tf, nodes, cg, birth: stats.append(vortex_centres(tf, nodes, cg, birth, 0.5))
    main()
    st = np.array([s_ for s_ in stats if s_ is not None])
    q = lambda x: "p10 %.2f  median %.2f  p90 %.2f" % tuple(np.percentile(x, [10, 50, 90]))
    print(f"front tip-vortex centres at age 0.5 s: spacing {q(st[:, 0])} m | height {q(st[:, 1])} m")
    print("saved", OUT / "austin_hairpin_v9.mp4")
