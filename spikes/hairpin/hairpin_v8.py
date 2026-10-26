"""SPIKE v8: v7 (smoothed line, car-frame streamlines) + 2026-ish wings + fixed colours + wake cross-sections.

Changes vs v7:
- wings_v8: cambered inverted sections tuned to ClA front 0.92 / rear 0.74 m^2 (assumed 2026 level); front-wing outer
  0.35 m per side lifted 0.15 m. Lifting the tips weakens the ground-image push that collapsed the two front tip
  vortices inward within 0.1 s (-> close pair -> wake rose ~2 m/s; see NOW.md).
- Wake is shed from the real panel geometry (trailing-edge and quarter-chord points incl. pitch, camber, raised tips),
  not from a flat line at the wing's nominal height.
- Colour: diverging (slower blue / grey = car speed / faster red), range frozen from the first drawn frame.
- No x10 inset; two slices across the car (1 m behind each wing) show the tip vortices as swirls:
  in-plane induced flow (lines) over streamwise vorticity (colour).
"""
import subprocess
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap, Normalize
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import hairpin_v4 as v4
import hairpin_v6 as v6
import hairpin_v7 as v7
import wings_v8 as W
from hairpin_trails import FPS, WINDOW_S, RHO, g, op, pr, ps

W.install(v4)
OUT = Path(__file__).parent / "out_v8"
SLICE_BEHIND = 1.0                         # m behind each wing's trailing edge
DIV = LinearSegmentedColormap.from_list("div", ["#2b5fa8", "#9a9a9a", "#c0392b"])
_state = {"first": None, "norm": None, "wnorm": None}


def wing_sheet(V):
    """-> per wing: (downforce N, quarter-chord pts (nb,3), trailing-edge pts (nb,3), strip circulation (nb-1,))
    points in CAR axes: x forward of car centre, y left, z up; boundaries ordered left -> right (as v4: sets the
    sign of every vortex leg)."""
    plane = g.airplane.Airplane(wings=[v4.wing_geom(*w) for w in v4.WINGS], name="car")
    opp = op.OperatingPoint(vCg__E=V, alpha=0.0, CgP1_E_Eo=(0.0, 0.0, -1e-3),
                            surfaceNormal_E=(0.0, 0.0, 1.0), surfacePoint_E_Eo=(0.0, 0.0, 0.0))
    sp = pr.SteadyProblem(airplanes=[plane], operating_point=opp)
    ps.steady_ring_vortex_lattice_method.SteadyRingVortexLatticeMethodSolver(steady_problem=sp).run()
    car = lambda q: np.c_[-q[:, 0], -q[:, 1], q[:, 2]]          # geometry axes (x aft, y right) -> car axes
    out = []
    for w in sp.airplanes[0].wings:
        pan = np.asarray(w.panels)
        o = np.argsort([p.Flpp_G_Cg[1] for p in pan[0]])        # geometry y ascending = car left -> right
        pan = pan[:, o]
        fz = np.array([[p.forces_W[2] for p in row] for row in pan])
        le = car(np.array([p.Flpp_G_Cg for p in pan[0]] + [pan[0, -1].Frpp_G_Cg]))
        te = car(np.array([p.Blpp_G_Cg for p in pan[-1]] + [pan[-1, -1].Brpp_G_Cg]))
        gam = fz.sum(0) / (RHO * V * np.abs(np.diff(le[:, 1])))
        out.append((fz.sum(), 0.75 * le + 0.25 * te, te, gam))
    return out


def main():
    OUT.mkdir(exist_ok=True)
    P, k, v, t, hdg = v7.smooth_lap_data()
    ic = int(np.argmax(np.abs(k)))
    pose = lambda ts: (np.interp(ts, t, P[:, 0]), np.interp(ts, t, P[:, 1]), np.interp(ts, t, hdg), np.interp(ts, t, v))
    t_frames = np.arange(t[ic] + WINDOW_S[0] - v4.TRAIL_S, t[ic] + WINDOW_S[1], 1 / FPS)
    dts = 1 / (FPS * v4.SUBSTEPS)
    nw = len(v4.WINGS)
    nodes, birth, cg = [np.zeros((0, 0, 3))] * nw, [np.zeros(0)] * nw, [np.zeros((0, 0))] * nw
    log, tt, tips = [], {"ptera": 0.0, "wake": 0.0, "draw": 0.0}, []
    for f, tf in enumerate(t_frames):
        t0 = time.time(); sheet = wing_sheet(float(pose(tf)[3])); tt["ptera"] += time.time() - t0
        t0 = time.time()
        for sub in range(v4.SUBSTEPS):
            ts = tf - (v4.SUBSTEPS - 1 - sub) * dts                    # substeps end exactly at the frame time
            x0, y0, h, _ = pose(ts)
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
                    segA.append(full[1:].reshape(-1, 3)); segB.append(full[:-1].reshape(-1, 3))     # streamwise legs
                    segG.append(dGr.reshape(-1)); segR.append(np.repeat(v4.core(ages[:-1]), full.shape[1]))
                    d = cfull[:-1] - cfull[1:]                                                       # spanwise shed legs
                    segA.append(full[1:, 1:].reshape(-1, 3)); segB.append(full[1:, :-1].reshape(-1, 3))
                    segG.append(d.reshape(-1)); segR.append(np.repeat(v4.core(ages[1:]), full.shape[1] - 1))
            A, B, G, R = (np.concatenate(s) for s in (segA, segB, segG, segR))
            keep = np.abs(G) > 1e-6
            A, B, G, R = A[keep], B[keep], G[keep], R[keep]
            A2, B2, G2, R2 = np.r_[A, A * [1, 1, -1]], np.r_[B, B * [1, 1, -1]], np.r_[G, -G], np.r_[R, R]   # + ground image
            sizes = [n_.shape[0] * n_.shape[1] if n_.size else 0 for n_ in nodes]
            if sum(sizes):
                u = v4.induce(np.concatenate([n_.reshape(-1, 3) for n_ in nodes if n_.size]), A2, B2, G2, R2) * dts
                o = 0
                for wi in range(nw):
                    if sizes[wi]:
                        nodes[wi] = nodes[wi] + u[o:o + sizes[wi]].reshape(nodes[wi].shape); o += sizes[wi]
                        nodes[wi][..., 2] = np.maximum(nodes[wi][..., 2], 0.02)
            for wi in range(nw):        # shed a new row at the trailing edge, drop rows older than TRAIL_S
                nodes[wi] = np.concatenate([nodes[wi], te_now[wi][None]], 0) if nodes[wi].size else te_now[wi][None]
                cg[wi] = np.concatenate([cg[wi], sheet[wi][3][None]], 0) if cg[wi].size else sheet[wi][3][None]
                birth[wi] = np.r_[birth[wi], ts]
                m = ts - birth[wi] <= v4.TRAIL_S
                nodes[wi], cg[wi], birth[wi] = nodes[wi][m], cg[wi][m], birth[wi][m]
        tt["wake"] += time.time() - t0
        x0, y0, h, V = pose(tf)
        log.append((tf - t[ic], V * 3.6, sheet[0][0], sheet[1][0]))
        age = tf - birth[0]
        i5 = np.argmin(np.abs(age - 0.5))
        if abs(age[i5] - 0.5) < 0.02:   # front tips at 0.5 s: rise above shed height, spacing
            r = nodes[0][i5]; tips.append((r[[0, -1], 2].mean() - sheet[0][2][[0, -1], 2].mean(), np.linalg.norm(r[-1, :2] - r[0, :2])))
        if tf >= t[ic] + WINDOW_S[0]:
            w = (pose(tf + 0.5 * dts)[2] - pose(tf - 0.5 * dts)[2]) / dts
            t0 = time.time(); draw(f, P, (x0, y0), h, V, w, sheet, (A2, B2, G2, R2), log); tt["draw"] += time.time() - t0
        if f % 30 == 0:
            print(f"frame {f}/{len(t_frames)}  " + "  ".join(f"{k_} {1e3 * x_ / (f + 1):.0f} ms" for k_, x_ in tt.items()), flush=True)
    n = len(t_frames)
    print("per frame: " + "  ".join(f"{k_} {1e3 * x_ / n:.0f} ms" for k_, x_ in tt.items()))
    tips = np.array(tips)
    print(f"front tip vortices at age 0.5 s: rise {100 * tips[:, 0].mean():+.0f} cm (max {100 * tips[:, 0].max():+.0f}), "
          f"spacing {tips[:, 1].mean():.2f} m (min {tips[:, 1].min():.2f}; shed at 1.90 m)")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(OUT / "f_%04d.png"),
                    "-pix_fmt", "yuv420p", "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", str(OUT / "austin_hairpin_v8.mp4")], check=True)
    print("saved", OUT / "austin_hairpin_v8.mp4")


def seeds(c0, h, sheet):
    """Rake ahead of each wing (two heights, following the wing's own height across the span) + rings round each tip."""
    c, s_ = np.cos(h), np.sin(h)
    world = lambda q: np.c_[c0[0] + q[:, 0] * c - q[:, 1] * s_, c0[1] + q[:, 0] * s_ + q[:, 1] * c, q[:, 2]]
    pts = []
    for wi, (_, qc, te, _) in enumerate(sheet):
        ys = np.linspace(qc[-1, 1] - 0.2, qc[0, 1] + 0.2, 13)
        zs = np.interp(ys, qc[::-1, 1], te[::-1, 2])
        for dz in (-0.05, 0.05):
            pts.append(np.c_[np.full(13, qc[0, 0] + 0.6), ys, np.maximum(zs + dz, 0.03)])
        for tip in (te[0], te[-1]):
            for r in ((0.05, 0.09, 0.14) if wi == 0 else (0.06, 0.12)):
                a = np.linspace(0, 2 * np.pi, 8, endpoint=False)
                pts.append(np.c_[np.full(8, tip[0] - 0.05), tip[1] + r * np.cos(a), np.maximum(tip[2] + r * np.sin(a), 0.03)])
    return world(np.concatenate(pts))


def slice_flow(c0, h, xs, lat, z, segs):
    """Induced flow on a plane across the car at car-axis x = xs: lateral & vertical velocity, streamwise vorticity."""
    c, s_ = np.cos(h), np.sin(h)
    Y, Z = np.meshgrid(lat, z)
    pts = np.c_[c0[0] + xs * c - Y.ravel() * s_, c0[1] + xs * s_ + Y.ravel() * c, Z.ravel()]
    u = v4.induce(pts, *segs)
    vy = (-u[:, 0] * s_ + u[:, 1] * c).reshape(Y.shape)      # car-left component
    vz = u[:, 2].reshape(Y.shape)
    om = np.gradient(vz, lat, axis=1) - np.gradient(vy, z, axis=0)
    return Y, Z, vy, vz, om


def draw(f, P, c0, h, V, w, sheet, segs, log):
    if _state["first"] is None: _state["first"] = f
    A2, B2, G2, R2 = segs
    c, s_ = np.cos(h), np.sin(h)
    lines = v6.trace(seeds(c0, h, sheet), A2, B2, G2, R2, c0[0], c0[1], V, c, s_, w, v6.DS, int(v6.LENGTH / v6.DS))
    col = lines[..., 3] / V                                    # air speed relative to the car / car speed
    if _state["norm"] is None:                                 # frozen once -> no colour flicker between frames
        d = max(np.percentile(np.abs(col - 1), 98), 0.01)
        _state["norm"] = Normalize(1 - d, 1 + d)
    fig = plt.figure(figsize=(11, 13.5))
    gs = fig.add_gridspec(3, 2, height_ratios=[3.0, 1.0, 0.8], hspace=0.32, wspace=0.12)
    a = fig.add_subplot(gs[0, :]); b = fig.add_subplot(gs[2, :])
    sl = [fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1])]
    a.plot(P[:, 0] - c0[0], P[:, 1] - c0[1], color="#efefef", lw=12 * (0.8 * 11 * 100 / (2 * v6.ZOOM)) * 72 / 100 * 0.62,
           solid_capstyle="round", zorder=0)
    a.plot(P[:, 0] - c0[0], P[:, 1] - c0[1], color="#c8c8c8", lw=0.8, ls="--", zorder=1)
    xy = lines[..., :2] - np.array(c0)
    along = -(xy[..., 0] * c + xy[..., 1] * s_)
    for ax_, X, Y in ((a, xy[..., 0], xy[..., 1]), (b, along, lines[..., 2])):
        sg = np.stack([np.stack([X[:, :-1], Y[:, :-1]], -1), np.stack([X[:, 1:], Y[:, 1:]], -1)], 2).reshape(-1, 2, 2)
        lc = LineCollection(sg, array=col[:, :-1].ravel(), cmap=DIV, norm=_state["norm"], lw=0.9, zorder=3)
        ax_.add_collection(lc)
    car = v4.CAR
    a.plot(np.r_[car[:, 0], car[:1, 0]] * c - np.r_[car[:, 1], car[:1, 1]] * s_,
           np.r_[car[:, 0], car[:1, 0]] * s_ + np.r_[car[:, 1], car[:1, 1]] * c, color="#222", lw=0.8, zorder=4)
    for _, qc, te, _ in sheet:                                  # wing planform (leading edge from quarter chord)
        le = (qc - 0.25 * te) / 0.75
        q = np.r_[le, te[::-1], le[:1]]
        a.fill(q[:, 0] * c - q[:, 1] * s_, q[:, 0] * s_ + q[:, 1] * c, color="#222", zorder=5)
        b.plot(-np.r_[le[len(le) // 2, 0], te[len(te) // 2, 0]], [le[len(le) // 2, 2], te[len(te) // 2, 2]], color="#222", lw=3, zorder=5)
    for xs_ in (sheet[0][2][0, 0] - SLICE_BEHIND, sheet[1][2][0, 0] - SLICE_BEHIND):   # slice positions
        e = np.array([[xs_, 1.6], [xs_, -1.6]])
        a.plot(e[:, 0] * c - e[:, 1] * s_, e[:, 0] * s_ + e[:, 1] * c, color="#888", lw=0.8, ls=":", zorder=2)
    a.set_xlim(-v6.ZOOM, v6.ZOOM); a.set_ylim(-v6.ZOOM, v6.ZOOM); a.set_aspect("equal")
    a.set_title(f"Streamlines, top view (north up)   {V * 3.6:.0f} km/h   yaw rate {np.degrees(w):.0f} deg/s   "
                f"front wing {log[-1][2]:.0f} N   rear wing {log[-1][3]:.0f} N", fontsize=10)
    fig.colorbar(lc, ax=a, shrink=0.6, pad=0.01, label="air speed relative to car / car speed")
    lat, zz = np.linspace(-1.6, 1.6, 81), np.linspace(0.0, 1.4, 36)
    for ax_, wi, name in ((sl[0], 0, "front"), (sl[1], 1, "rear")):
        Y, Z, vy, vz, om = slice_flow(c0, h, sheet[wi][2][0, 0] - SLICE_BEHIND, lat, zz, segs)
        if _state["wnorm"] is None and wi == 0:
            _state["wnorm"] = Normalize(-np.percentile(np.abs(om), 99.5), np.percentile(np.abs(om), 99.5))
        pm = ax_.pcolormesh(Y, Z, om, cmap=DIV, norm=_state["wnorm"], shading="gouraud", zorder=1)
        ax_.streamplot(lat, zz, vy, vz, color="#333", linewidth=0.5, density=1.3, arrowsize=0.6, zorder=2)
        ax_.axhline(0, color="k", lw=2)
        ax_.set_xlim(1.6, -1.6); ax_.set_ylim(0, 1.4); ax_.set_aspect("equal")    # looking forward from behind: left on the left
        ax_.set_title(f"slice {SLICE_BEHIND:.0f} m behind {name} wing, looking forward", fontsize=9)
        ax_.tick_params(labelsize=7); ax_.set_xlabel("m, + = car left", fontsize=7)
    fig.colorbar(pm, ax=sl, shrink=0.8, pad=0.01, label="swirl (streamwise vorticity, 1/s)")
    b.axhline(0, color="k", lw=2); b.text(-3.8, 0.04, "ground", fontsize=8)
    b.set_xlim(-4, 12); b.set_ylim(-0.1, 2.0); b.set_aspect("equal")
    b.set_title("Side view (distance behind the car, height above ground)", fontsize=10); b.set_xlabel("m behind car centre")
    fig.savefig(OUT / f"f_{f - _state['first']:04d}.png", dpi=100); plt.close(fig)


if __name__ == "__main__":
    main()
