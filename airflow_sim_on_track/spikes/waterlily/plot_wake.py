"""THROWAWAY SPIKE: plot WaterLily wake slices (top view at body mid-height, side view on the centreline)."""
import sys
import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
f = sys.argv[1]
with open(f, "rb") as fh:
    nx, ny, nz, kz, jy = np.frombuffer(fh.read(20), np.int32); L = np.frombuffer(fh.read(4), np.float32)[0]
    sp = np.frombuffer(fh.read(), np.float32).reshape((nx, ny, nz), order="F")
fig, ax = plt.subplots(2, 1, figsize=(12, 9))
x = (np.arange(nx) - 1) / L; y = (np.arange(ny) - 1) / L; z = (np.arange(nz) - 1) / L
for a, data, ext, t in [(ax[0], sp[:, :, kz].T, [x[0], x[-1], y[0], y[-1]], "TOP VIEW: air speed at mid-height of the body"),
                        (ax[1], sp[:, jy, :].T, [x[0], x[-1], z[0], z[-1]], "SIDE VIEW: air speed on the centreline (ground = bottom edge, moving at U)")]:
    im = a.imshow(data, origin="lower", extent=ext, cmap="turbo", vmin=0, vmax=1.3, aspect="equal")
    a.set_title(t); a.set_xlabel("body lengths")
fig.colorbar(im, ax=ax, label="speed / free-stream speed", shrink=0.8)
fig.suptitle(f"WaterLily.jl on RTX 4060 Laptop - box with Ahmed-body proportions over moving ground, {nx*ny*nz/1e6:.1f}M cells")
fig.savefig(f.replace(".bin", ".png"), dpi=110); print("saved", f.replace(".bin", ".png"))
