"""Phase-1 diagnosis of the Madring speed deficits vs Russell FP1 (read-only).

Per FP1 speed minimum: the sim line's driven radius exactly as v_grip sees it
(4-station stencil + 5-pt median), the FP1 GPS path radius (rigidly registered
into the SVG frame), the flat-road radius the sim's grip model needs to carry
FP1's speed, the outline centreline radius, width, and the sim-line/FP1-path
gap. Lists the long curved sections (La Monumental candidates) and renders zoom
panels. Writes only new files under cache/madring_diagnosis/.
"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
from scipy.interpolate import splev, splprep
from scipy.ndimage import gaussian_filter1d, median_filter
from scipy.signal import find_peaks
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")
import sim_2026_lap as sim
from _track_registry import rho_isa

OUT = ROOT / "cache/madring_diagnosis"
OUT.mkdir(exist_ok=True)
for name in ("diagnosis.json", "deficit_zooms.png", "curvature_lap.png"):
    if (OUT / name).exists():
        raise FileExistsError(OUT / name)


def load_json(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def stencil_kappa(pts, k):
    """simulate_lap's v_grip curvature: Menger over +-k stations."""
    a = np.roll(pts, k, axis=0)
    c = np.roll(pts, -k, axis=0)
    ab, bc, ac = pts - a, c - pts, c - a
    cross = ab[:, 0] * bc[:, 1] - ab[:, 1] * bc[:, 0]
    den = np.linalg.norm(ab, axis=1) * np.linalg.norm(bc, axis=1) * np.linalg.norm(ac, axis=1)
    return np.where(den < 1e-9, 0.0, 2.0 * cross / np.maximum(den, 1e-12))


def circ_window(f, f0, half):
    return np.abs(((f - f0 + 0.5) % 1.0) - 0.5) <= half


line = load_json("cache/madring_fp1_elevation/madring_fp1_raceline.json")
P = np.asarray(line["raceline"], float)
arc = np.asarray(line["arc_length"], float)
L = float(line["track_length_m"])
n = len(P)
frac = arc / L
outline = load_json("F1_Pipeline_Assets/tracks/madring_grand_prix_outline_provisional.json")
outer = np.asarray(outline["outer"], float)
inner = np.asarray(outline["inner"], float)
centre = 0.5 * (outer + inner)
width_c = np.linalg.norm(outer - inner, axis=1)
reg = load_json("cache/madring_fp1_elevation/validation.json")["registration"]
elev = load_json("cache/madring_fp1_elevation/madring_fp1_elevation.json")
ref = pd.read_csv(ROOT / "F1_Pipeline_Assets/exports/reference_2026_madring_fp1.csv")
pos = pd.read_csv(ROOT / "cache/madring_fp1_20260911/rus_fastest_position.csv")
base = np.load(ROOT / "cache/madring_final_calibration/altitude_baseline_stations.npz")
v_sim = base["v_ms"] * 3.6
assert len(v_sim) == n

sim._apply_car_overrides(SimpleNamespace(cda=0.8, cl=4.2, rho=rho_isa(684.0)))
print(f"car: MASS {sim.MASS_KG} G {sim.G} MU_LAT {sim.MU_LAT} CL {sim.CL_CORNER_M2} RHO {sim.RHO:.4f}")

k_sim = median_filter(stencil_kappa(P, 4), size=5, mode="wrap")
v_grip = np.array([sim.v_grip_static(k) for k in k_sim]) * 3.6


def r_req_flat(v_kmh):
    """Radius the flat-road grip model needs to carry v_kmh."""
    v = v_kmh / 3.6
    return v * v / sim.a_lat_max_banked(v, "CORNER", 0.0)


# FP1 GPS path in the SVG frame, parameterised by FP1 lap fraction
xy = pos[["X", "Y"]].to_numpy(float) / 10.0
mxy = reg["scale"] * xy @ np.asarray(reg["rotation"]) + np.asarray(reg["translation"])
pos_t = pd.to_timedelta(pos.Time).dt.total_seconds().to_numpy()
ref_d = ref.distance.to_numpy() - float(ref.distance.iloc[0])
Lref = float(ref_d[-1])
pos_f = np.interp(pos_t, ref.time_s, ref_d) / Lref
u = np.r_[pos_f, pos_f[0] + 1.0]
fine = np.linspace(pos_f[0], pos_f[0] + 1.0, 20000, endpoint=False)
fp1_k = {}
for sigma in (1.0, 2.5):
    tck, _ = splprep([np.r_[mxy[:, 0], mxy[0, 0]], np.r_[mxy[:, 1], mxy[0, 1]]],
                     u=u, per=1, s=len(u) * sigma ** 2)
    dx, dy = splev(fine, tck, der=1)
    ddx, ddy = splev(fine, tck, der=2)
    fp1_k[sigma] = (dx * ddy - dy * ddx) / np.power(dx * dx + dy * dy, 1.5)
    if sigma == 1.0:
        fx, fy = (np.asarray(c) for c in splev(fine, tck))
fine_f = fine % 1.0
order = np.argsort(fine_f)
fine_f, fx, fy = fine_f[order], fx[order], fy[order]
fp1_k = {s: k[order] for s, k in fp1_k.items()}
gap_sim_fp1, _ = cKDTree(np.column_stack([fx, fy])).query(P)

c_tree = cKDTree(centre)
k_centre_all = median_filter(stencil_kappa(centre, 4), size=5, mode="wrap")
_, ci = c_tree.query(P)
k_centre, width = k_centre_all[ci], width_c[ci]
d_fp1c, fci = c_tree.query(np.column_stack([fx, fy]))
outside_fp1 = d_fp1c - 0.5 * width_c[fci]

grid = np.linspace(0, 1, 5000, endpoint=False)
rv = np.interp(grid, ref_d / Lref, ref.speed)
sv = np.interp(grid, frac, v_sim, period=1)
minima, _ = find_peaks(-rv, prominence=15, distance=125)

z = np.asarray(elev["stations"], float)[:, 2]
zs = gaussian_filter1d(z, 8, mode="wrap")
kv = np.gradient(np.gradient(zs, arc), arc)

k_fp1_on_sim = np.interp(frac, fine_f, fp1_k[2.5], period=1)
sgn = 1.0 if np.corrcoef(k_fp1_on_sim, k_sim)[0, 1] >= 0 else -1.0
print(f"curvature sign agreement factor {sgn:+.0f}; corr(k_sim, k_fp1) "
      f"{np.corrcoef(sgn * k_fp1_on_sim, k_sim)[0, 1]:.3f}")

rows = []
for i in minima:
    f0 = float(grid[i])
    idx = np.where(circ_window(frac, f0, 0.015))[0]
    fidx = np.where(circ_window(fine_f, f0, 0.015))[0]
    j_v = idx[np.argmin(v_sim[idx])]
    j_k = idx[np.argmax(np.abs(k_sim[idx]))]
    k1 = float(np.abs(fp1_k[1.0][fidx]).max())
    k25 = float(np.abs(fp1_k[2.5][fidx]).max())
    rows.append(dict(
        frac=round(f0, 4), fp1_kmh=round(float(rv[i]), 1),
        sim_kmh=round(float(v_sim[j_v]), 1), err=round(float(v_sim[j_v] - rv[i]), 1),
        R_sim=round(1 / abs(float(k_sim[j_k])), 1),
        R_fp1_s1=round(1 / k1, 1), R_fp1_s25=round(1 / k25, 1),
        R_need=round(float(r_req_flat(rv[i])), 1),
        vgrip_Rfp1=round(sim.v_grip_static(k25) * 3.6, 1),
        R_ctr=round(float(1 / np.abs(k_centre[idx]).max()), 1),
        w_min=round(float(width[idx].min()), 1),
        gap_max=round(float(gap_sim_fp1[idx].max()), 1),
        fp1_out=round(float(outside_fp1[fidx].max()), 1),
        z=round(float(zs[j_v]), 1), kv_per_km=round(float(kv[j_v] * 1000), 2),
        sim_min_frac=round(float(frac[j_v]), 4), R_sim_frac=round(float(frac[j_k]), 4)))
table = pd.DataFrame(rows)
print("\nFP1 speed minima (R in m; R_need = flat radius the sim grip model needs for FP1's speed;")
print(" vgrip_Rfp1 = sim grip-limit speed on FP1's GPS radius; fp1_out = FP1 path beyond corridor edge, m)")
print(table.drop(columns=["sim_min_frac", "R_sim_frac"]).to_string(index=False))

# long curved sections (La Monumental candidates)
ds_st = np.diff(np.r_[arc, L])
roll0 = int(np.argmin(np.abs(k_sim)))
seq = np.roll(np.arange(n), -roll0)
sg = np.where(np.abs(k_sim[seq]) > 1 / 500, np.sign(k_sim[seq]), 0)
runs, start, ssign = [], None, 0
for t in range(n + 1):
    s = sg[t] if t < n else 0
    if start is not None and s != ssign:
        runs.append([start, t - 1, ssign])
        start = None
    if start is None and s != 0:
        start, ssign = t, s
merged = []
for r in runs:
    if merged and merged[-1][2] == r[2] and ds_st[seq[merged[-1][1] + 1:r[0]]].sum() < 15:
        merged[-1][1] = r[1]
        continue
    merged.append(r)
sections = []
for a0, a1, _ in merged:
    ids = seq[a0:a1 + 1]
    length = float(ds_st[ids].sum())
    turn = float(np.degrees(np.sum(k_sim[ids] * ds_st[ids])))
    sections.append(dict(
        start=round(float(frac[ids[0]]), 4), end=round(float(frac[ids[-1]]), 4),
        length_m=round(length, 1), turn_deg=round(turn, 1),
        R_min=round(float(1 / np.abs(k_sim[ids]).max()), 1),
        R_mean=round(length / np.radians(abs(turn)), 1) if abs(turn) > 1 else None,
        sim_min=round(float(v_sim[ids].min()), 1),
        fp1_min=round(float(np.interp(frac[ids], grid, rv, period=1).min()), 1)))
sections.sort(key=lambda d: -d["length_m"])
print("\nLongest curved sections (|k| > 1/500 m, same sign):")
print(pd.DataFrame(sections[:8]).to_string(index=False))

with (OUT / "diagnosis.json").open("x", encoding="utf-8") as stream:
    json.dump(dict(minima=rows, sections=sections, sign_factor=sgn), stream, indent=2)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

fp1_v_pos = np.interp(pos_f, ref_d / Lref, ref.speed)
worst = sorted(sorted(range(len(rows)), key=lambda r: rows[r]["err"])[:3], key=lambda r: rows[r]["frac"])
norm = plt.Normalize(70, 320)
fig, axes = plt.subplots(3, 3, figsize=(18, 15), gridspec_kw={"height_ratios": [2.2, 1, 1]})
for col, r in enumerate(worst):
    row = rows[r]
    f0 = row["frac"]
    j = int(np.argmin(np.abs(((frac - row["sim_min_frac"] + .5) % 1) - .5)))
    cx, cy = P[j]
    ax = axes[0, col]
    ax.plot(outer[:, 0], outer[:, 1], color="0.55", lw=1)
    ax.plot(inner[:, 0], inner[:, 1], color="0.55", lw=1)
    ax.plot(fx, fy, "k--", lw=0.8, label="FP1 path (spline)")
    ax.scatter(P[:, 0], P[:, 1], c=v_sim, cmap="viridis", norm=norm, s=4, label="sim line (sim speed)")
    ax.scatter(mxy[:, 0], mxy[:, 1], c=fp1_v_pos, cmap="viridis", norm=norm, s=36,
               edgecolors="k", linewidths=0.6, label="FP1 GPS (FP1 speed)")
    ax.plot(cx, cy, "rx", ms=12, mew=2, label="sim min speed")
    ax.plot(np.interp(f0, fine_f, fx), np.interp(f0, fine_f, fy), "b+", ms=14, mew=2, label="FP1 min speed")
    ax.set_xlim(cx - 220, cx + 220)
    ax.set_ylim(cy - 220, cy + 220)
    ax.set_aspect("equal")
    ax.set_title(f"{f0 * 100:.1f}% | FP1 {row['fp1_kmh']:.0f} vs sim {row['sim_kmh']:.0f} km/h\n"
                 f"R sim {row['R_sim']:.0f} | R FP1 {row['R_fp1_s25']:.0f} | R needed {row['R_need']:.0f} m",
                 fontsize=10)
    if col == 0:
        ax.legend(fontsize=7, loc="lower left")
    ws = np.where(circ_window(frac, f0, 0.05))[0]
    ws = ws[np.argsort(frac[ws])]
    wf = np.where(circ_window(fine_f, f0, 0.05))[0]
    ax = axes[1, col]
    ax.plot(frac[ws] * 100, k_sim[ws] * 1000, label="sim line (as v_grip sees it)")
    ax.plot(fine_f[wf] * 100, sgn * fp1_k[1.0][wf] * 1000, lw=0.8, label="FP1 GPS s=1")
    ax.plot(fine_f[wf] * 100, sgn * fp1_k[2.5][wf] * 1000, lw=1.2, label="FP1 GPS s=2.5")
    ax.plot(frac[ws] * 100, k_centre[ws] * 1000, lw=0.8, color="0.5", label="outline centreline")
    for lim in (1000 / row["R_need"], -1000 / row["R_need"]):
        ax.axhline(lim, color="r", ls=":", lw=1)
    ax.set_ylabel("curvature (1/km)")
    ax.grid(alpha=.3)
    if col == 0:
        ax.legend(fontsize=7)
    wg = np.where(circ_window(grid, f0, 0.05))[0]
    ax = axes[2, col]
    ax.plot(grid[wg] * 100, rv[wg], label="Russell FP1")
    ax.plot(grid[wg] * 100, sv[wg], label="sim trial 1")
    ax.plot(frac[ws] * 100, np.minimum(v_grip[ws], 340), ls=":", label="sim grip ceiling")
    ax.set_xlabel("lap %")
    ax.set_ylabel("km/h")
    ax.grid(alpha=.3)
    if col == 0:
        ax.legend(fontsize=7)
fig.tight_layout()
fig.savefig(OUT / "deficit_zooms.png", dpi=80)
plt.close(fig)

fig, axes = plt.subplots(3, 1, figsize=(16, 11), sharex=True)
axes[0].plot(frac * 100, np.abs(k_sim) * 1000, lw=1, label="sim line |k|")
axes[0].plot(fine_f * 100, np.abs(fp1_k[2.5]) * 1000, lw=1, label="FP1 GPS |k| (s=2.5)")
axes[0].plot(frac * 100, np.abs(k_centre) * 1000, lw=0.7, color="0.5", label="centreline |k|")
axes[0].set_ylim(0, 45)
axes[0].set_ylabel("|curvature| 1/km")
axes[0].legend(fontsize=8)
axes[1].plot(grid * 100, rv, label="Russell FP1 1:34.077")
axes[1].plot(grid * 100, sv, label="sim trial 1 (1:38.65)")
for row in rows:
    axes[1].annotate(f"{row['err']:+.0f}", (row["frac"] * 100, row["fp1_kmh"]),
                     textcoords="offset points", xytext=(0, -14), ha="center", fontsize=8, color="r")
axes[1].set_ylabel("km/h")
axes[1].legend(fontsize=8)
axes[2].plot(frac * 100, zs, color="#e8890c", label="height above low point (m)")
ax2 = axes[2].twinx()
ax2.plot(frac * 100, kv * 1000, color="0.4", lw=0.8, label="vertical curvature (1/km)")
axes[2].set_xlabel("lap % from FP1 timing line")
axes[2].legend(fontsize=8, loc="upper left")
ax2.legend(fontsize=8, loc="upper right")
for ax in axes:
    ax.grid(alpha=.3)
fig.tight_layout()
fig.savefig(OUT / "curvature_lap.png", dpi=80)
plt.close(fig)
print("\nwrote", OUT)
