"""SPIKE v6: v4 physics, drawn as STREAMLINES (no dots).

Streamlines of the air velocity relative to the car (car frame, which rotates with the yaw rate):
    u_rel(p) = u_induced(p)  -  (V * forward  +  yaw_rate x (p - car))
u_induced = Biot-Savart of the whole wing + wake vortex lattice (+ ground image), the same field that moves the wake.
Seeds: a rake ahead of each wing across the span (two heights) + rings round each wing tip.
Lines near a tip wrap round the tip vortex (corkscrew); in the corner all lines curve with the turning car frame.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import numba as nb
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import hairpin_v4 as v4

v4.OUT = Path(__file__).parent / "out_v6"
ZOOM = 6.0
DS, LENGTH = 0.04, 11.0        # streamline step and length (m)
_first = [None]


@nb.njit(fastmath=True, cache=True)
def vel(qx, qy, qz, A, B, G, rc, cx, cy, V, fx, fy, w):
    ux = uy = uz = 0.0
    for j in range(A.shape[0]):
        r1x, r1y, r1z = qx - A[j, 0], qy - A[j, 1], qz - A[j, 2]
        r2x, r2y, r2z = qx - B[j, 0], qy - B[j, 1], qz - B[j, 2]
        r0x, r0y, r0z = B[j, 0] - A[j, 0], B[j, 1] - A[j, 1], B[j, 2] - A[j, 2]
        c1, c2, c3 = r1y * r2z - r1z * r2y, r1z * r2x - r1x * r2z, r1x * r2y - r1y * r2x
        n1 = np.sqrt(r1x * r1x + r1y * r1y + r1z * r1z) + 1e-12
        n2 = np.sqrt(r2x * r2x + r2y * r2y + r2z * r2z) + 1e-12
        den = c1 * c1 + c2 * c2 + c3 * c3 + rc[j] * rc[j] * (r0x * r0x + r0y * r0y + r0z * r0z)
        if den < 1e-14:
            continue
        kk = G[j] / (4.0 * np.pi) * (r0x * (r1x / n1 - r2x / n2) + r0y * (r1y / n1 - r2y / n2) + r0z * (r1z / n1 - r2z / n2)) / den
        ux += kk * c1; uy += kk * c2; uz += kk * c3
    ux -= V * fx - w * (qy - cy)          # minus the car-frame velocity V*fwd + w x (q - car)
    uy -= V * fy + w * (qx - cx)
    return ux, uy, uz


@nb.njit(parallel=True, fastmath=True, cache=True)
def trace(seeds, A, B, G, rc, cx, cy, V, fx, fy, w, ds, nsteps):
    n = seeds.shape[0]
    out = np.zeros((n, nsteps + 1, 4))           # x, y, z, |u_rel|
    for i in nb.prange(n):
        px, py, pz = seeds[i, 0], seeds[i, 1], seeds[i, 2]
        for k in range(nsteps + 1):
            ux, uy, uz = vel(px, py, pz, A, B, G, rc, cx, cy, V, fx, fy, w)
            sp = np.sqrt(ux * ux + uy * uy + uz * uz) + 1e-12
            out[i, k, 0], out[i, k, 1], out[i, k, 2], out[i, k, 3] = px, py, pz, sp
            mx, my, mz = px + 0.5 * ds * ux / sp, py + 0.5 * ds * uy / sp, pz + 0.5 * ds * uz / sp
            ux, uy, uz = vel(mx, my, mz, A, B, G, rc, cx, cy, V, fx, fy, w)
            sp = np.sqrt(ux * ux + uy * uy + uz * uz) + 1e-12
            px, py, pz = px + ds * ux / sp, py + ds * uy / sp, max(pz + ds * uz / sp, 0.01)
    return out


def seeds_for(c0, h):
    c, s_ = np.cos(h), np.sin(h)
    fwd, left = np.array([c, s_]), np.array([-s_, c])
    pts = []
    for name, x, half, chord, z, pitch in v4.WINGS:
        for y in np.linspace(-half - 0.2, half + 0.2, 13):           # rake ahead of the wing
            for dz in (-0.05, 0.05):
                xy = np.array(c0) + (x + 0.5) * fwd + y * left
                pts.append([xy[0], xy[1], max(z + dz, 0.03)])
        for sd in (+1, -1):                                         # ring round each tip, just behind the trailing edge
            tip = np.array(c0) + (x - chord - 0.05) * fwd + sd * half * left
            for a, r in [(a_, r_) for r_ in ((0.05, 0.09, 0.14) if name == "front" else (0.09,)) for a_ in np.linspace(0, 2 * np.pi, 8, endpoint=False)]:
                xy = tip + r * np.cos(a) * left
                pts.append([xy[0], xy[1], max(z + r * np.sin(a), 0.03)])
    return np.array(pts)


def draw(f, P, c0, h, V, nodes, birth, tf, log):
    if _first[0] is None: _first[0] = f
    A2, B2, G2, R2, w = v4.LAST
    c, s_ = np.cos(h), np.sin(h)
    lines = trace(seeds_for(c0, h), A2, B2, G2, R2, c0[0], c0[1], V, c, s_, w, DS, int(LENGTH / DS))
    fig, (a, b) = plt.subplots(2, 1, figsize=(10, 12.5), gridspec_kw={"height_ratios": [3.2, 1]})
    a.plot(P[:, 0] - c0[0], P[:, 1] - c0[1], color="#e9e9e9", lw=12 * (0.8 * 10 * 100 / (2 * ZOOM)) * 72 / 100, solid_capstyle="round", zorder=0)
    a.plot(P[:, 0] - c0[0], P[:, 1] - c0[1], color="#bbbbbb", lw=0.8, ls="--", zorder=1)
    xy = lines[..., :2] - np.array(c0)
    along = -(xy[..., 0] * c + xy[..., 1] * s_)
    col = lines[..., 3] / V                                         # speed relative to the car / car speed
    for ax_, X, Y in ((a, xy[..., 0], xy[..., 1]), (b, along, lines[..., 2])):
        segs = np.stack([np.stack([X[:, :-1], Y[:, :-1]], -1), np.stack([X[:, 1:], Y[:, 1:]], -1)], 2).reshape(-1, 2, 2)
        lc = LineCollection(segs, array=col[:, :-1].ravel(), cmap="viridis", norm=plt.Normalize(0.85, 1.15), lw=0.9, zorder=3)
        ax_.add_collection(lc)
    car = v4.CAR
    a.plot(np.r_[car[:, 0], car[:1, 0]] * c - np.r_[car[:, 1], car[:1, 1]] * s_,
           np.r_[car[:, 0], car[:1, 0]] * s_ + np.r_[car[:, 1], car[:1, 1]] * c, color="k", lw=0.8, zorder=4)
    for name, x, half, chord, z, pitch in v4.WINGS:
        xs, ys = np.meshgrid(np.linspace(x - chord, x, 6), np.linspace(-half, half, 13))
        a.scatter(xs * c - ys * s_, xs * s_ + ys * c, s=5, c="red", zorder=5)
        b.plot(-np.array([x - chord, x]), [z, z], color="red", lw=3, zorder=5)
    a.set_xlim(-ZOOM, ZOOM); a.set_ylim(-ZOOM, ZOOM); a.set_aspect("equal")
    # close-up of the left front-wing tip, in car axes (x back from the tip, y across), same data
    name, x, half, chord, z, pitch = v4.WINGS[0]
    tip = np.array(c0) + (x - chord) * np.array([c, s_]) + half * np.array([-s_, c])
    rel = lines[..., :2] - tip
    bx = -(rel[..., 0] * c + rel[..., 1] * s_); by = -rel[..., 0] * s_ + rel[..., 1] * c
    ins = a.inset_axes([0.02, 0.02, 0.55, 0.3])
    m = (np.abs(by) < 0.4).any(1) & (bx > -0.3).any(1)
    for X, Y, C in zip(bx[m], by[m], col[m]):
        ins.plot(X, Y, lw=0.8, color=plt.cm.viridis(np.clip((C.mean() - 0.85) / 0.3, 0, 1)))
    ins.set_xlim(-0.3, 4.0); ins.set_ylim(-0.4, 0.4); ins.set_aspect("equal")
    ins.set_title("CLOSE-UP x10: left front-wing tip, from above (m)", fontsize=7); ins.tick_params(labelsize=6)
    a.set_title(f"STREAMLINES, TOP VIEW (north up)  {V * 3.6:.0f} km/h   front wing {log[-1][2]:.0f} N   rear wing {log[-1][3]:.0f} N")
    b.axhline(0, color="k", lw=2); b.text(-3.8, 0.04, "ground", fontsize=8)
    b.set_xlim(-4, 12); b.set_ylim(-0.1, 2.0); b.set_aspect("equal")
    b.set_title("SIDE VIEW (distance behind the car, height above ground)"); b.set_xlabel("m behind car centre")
    fig.colorbar(lc, ax=[a, b], shrink=0.4, pad=0.01, label="air speed relative to car / car speed")
    fig.savefig(v4.OUT / f"f_{f - _first[0]:04d}.png", dpi=100); plt.close(fig)


v4.draw = draw
if __name__ == "__main__":
    v4.main()
