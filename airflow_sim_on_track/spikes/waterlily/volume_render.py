"""THROWAWAY SPIKE: render the saved WaterLily 3D field as volumetric 'fog' (emission-absorption ray march), top + side views.
Fog density = how much the air has been slowed (1 - speed/U), body cells masked out."""
import sys
import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
f = sys.argv[1]
with open(f, "rb") as fh:
    nx, ny, nz, kz, jy = np.frombuffer(fh.read(20), np.int32); L = np.frombuffer(fh.read(4), np.float32)[0]
    sp = np.frombuffer(fh.read(), np.float32).reshape((nx, ny, nz), order="F")
n = nx - 2
# body = same rounded box as bench_body.jl (cell coords, ghost offset 1)
X, Y, Z = np.meshgrid(np.arange(nx) - 1.5, np.arange(ny) - 1.5, np.arange(nz) - 1.5, indexing="ij")
c = np.array([1.0 * L, n / 4, 0.048 * L + 0.138 * L]); h = np.array([0.5 * L, 0.1865 * L, 0.138 * L]); r = 0.1 * L
q = np.stack([np.abs(X - c[0]), np.abs(Y - c[1]), np.abs(Z - c[2])], -1) - (h - r)
sdf = np.linalg.norm(np.maximum(q, 0), axis=-1) + np.minimum(q.max(-1), 0) - r
dens = np.clip(1.0 - sp, 0, 1) ** 1.5
dens[sdf < 1.5] = 0; dens[:, :, :3] = 0                  # no fog inside the body or in the ground cells
col = plt.cm.turbo(np.clip(sp, 0, 1.2) / 1.2)[..., :3]   # fog colour = local speed

def march(axis, k=0.06):
    d = np.moveaxis(dens, axis, -1)[..., ::-1]; cc = np.moveaxis(col, axis, -2)[..., ::-1, :]
    a = 1 - np.exp(-k * d)                                # opacity per cell
    T = np.cumprod(np.concatenate([np.ones_like(a[..., :1]), 1 - a[..., :-1]], -1), -1)
    img = (T[..., None] * a[..., None] * cc).sum(-2)
    return img + T[..., -1:] * (1 - a[..., -1:]) * 0.05   # dark background

top = march(2); side = march(1)
bodytop = (sdf.min(axis=2) < 0); bodyside = (sdf.min(axis=1) < 0)
top[bodytop] = 0.85; side[bodyside] = 0.85
fig, ax = plt.subplots(2, 1, figsize=(12, 8), facecolor="k")
ax[0].imshow(np.transpose(top, (1, 0, 2)) ** 0.8, origin="lower", extent=[0, nx / L, 0, ny / L])
ax[1].imshow(np.transpose(side, (1, 0, 2)) ** 0.8, origin="lower", extent=[0, nx / L, 0, nz / L])
for a, t in zip(ax, ["TOP VIEW - whole 3D volume, fog = slowed air", "SIDE VIEW - same volume"]):
    a.set_title(t, color="w"); a.tick_params(colors="w"); a.set_facecolor("k")
fig.suptitle("WaterLily 3D field rendered as a volume (not slices, not lines)", color="w")
out = f.replace(".bin", "_volume.png"); fig.savefig(out, dpi=110, facecolor="k"); print("saved", out)
