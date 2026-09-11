"""Measured Madring racing line from FP1+FP2 GPS (multi-lap principal curve).

The SVG polyline's fast bends are ~25-30% too tight (cache/madring_diagnosis):
the sim loses 36-57 km/h at every 149-225 km/h bend while slow corners agree.
One FP1 lap's GPS (4 Hz, ~15 m spacing at speed) is too sparse to measure those
radii, so this pools every push lap (<= PUSH_FRAC x session best) of FP1+FP2:
samples are projected onto an evolving reference path and the smoothed mean
lateral offset updates it until converged. Also derives the timing-line origin,
per-lap speed traces on the measured distance axis, a relative elevation
profile, and a drawn-road outline anchored to the observed lateral usage.
Rigid rotation+translation into the SVG frame only (no scaling: GPS lengths
are kept true). All outputs are new files; nothing existing is modified.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.interpolate import splev, splprep
from scipy.ndimage import gaussian_filter1d, median_filter
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")
import sim_2026_lap as sim

SRC = ROOT / "cache/madring_practice_laps"
OUT = ROOT / "cache/madring_gps_line"
OUTLINE = ROOT / "F1_Pipeline_Assets/tracks/madring_grand_prix_outline_gps.json"
PUSH_FRAC = 1.02      # push lap = within 2% of its session's fastest
DS = 0.5              # working path spacing, m
SIG_S = 4.0           # along-track smoothing of the mean lateral offset, m
STATION_DS = 2.0      # output raceline spacing, m (the SVG line was ~2.0 m)
MAX_OFF = 8.0         # push-lap sample further than this from the path = outlier
ROAD_W = 12.0         # drawn width where observed usage is narrower (operator: mostly 12 m)
CAR_HALF = 1.0        # GPS is the car centre; the road edge lies beyond the car's side

OUT.mkdir(exist_ok=True)
FILES = dict(line=OUT / "madring_gps_raceline.json", elev=OUT / "madring_gps_elevation.json",
             traces=OUT / "speed_traces.npz", report=OUT / "build_report.json",
             png=OUT / "gps_line_check.png", outline=OUTLINE)
for path_ in FILES.values():
    if path_.exists():
        raise FileExistsError(path_)


def resample(path, ds):
    closed = np.vstack([path, path[:1]])
    cum = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(closed, axis=0), axis=1))]
    u = np.linspace(0.0, cum[-1], int(round(cum[-1] / ds)), endpoint=False)
    return np.column_stack([np.interp(u, cum, closed[:, 0]), np.interp(u, cum, closed[:, 1])])


def normals(path):
    tan = np.roll(path, -1, 0) - np.roll(path, 1, 0)
    tan /= np.linalg.norm(tan, axis=1, keepdims=True)
    return np.column_stack([-tan[:, 1], tan[:, 0]])  # left of travel


def project(path, pts):
    """Nearest-segment projection onto a closed polyline -> (s, signed d [+left], length)."""
    seg = np.roll(path, -1, axis=0) - path
    seglen = np.linalg.norm(seg, axis=1)
    cum = np.r_[0.0, np.cumsum(seglen)[:-1]]
    total = float(seglen.sum())
    _, near = cKDTree(path).query(pts)
    best = np.full(len(pts), np.inf)
    s_out = np.zeros(len(pts))
    d_out = np.zeros(len(pts))
    for off in (-1, 0):
        j = (near + off) % len(path)
        w = pts - path[j]
        tt = np.clip(np.einsum("ij,ij->i", w, seg[j]) / np.maximum(seglen[j] ** 2, 1e-12), 0.0, 1.0)
        r = w - tt[:, None] * seg[j]
        dist = np.linalg.norm(r, axis=1)
        side = np.sign(seg[j, 0] * r[:, 1] - seg[j, 1] * r[:, 0])
        take = dist < best
        best[take] = dist[take]
        s_out[take] = (cum[j] + tt * seglen[j])[take]
        d_out[take] = (side * dist)[take]
    return s_out % total, d_out, total


def binned_mean(s, values, total, n, sigma_m):
    """Normalized-convolution mean of samples on n uniform bins along a closed path."""
    idx = np.floor(s / total * n).astype(int) % n
    num = np.bincount(idx, weights=values, minlength=n)
    cnt = np.bincount(idx, minlength=n).astype(float)
    sig = sigma_m / (total / n)
    return (gaussian_filter1d(num, sig, mode="wrap")
            / np.maximum(gaussian_filter1d(cnt, sig, mode="wrap"), 1e-9))


def stencil_kappa(pts, k):
    """simulate_lap's v_grip curvature: Menger over +-k stations."""
    a, c = np.roll(pts, k, axis=0), np.roll(pts, -k, axis=0)
    ab, bc, ac = pts - a, c - pts, c - a
    cross = ab[:, 0] * bc[:, 1] - ab[:, 1] * bc[:, 0]
    den = np.linalg.norm(ab, axis=1) * np.linalg.norm(bc, axis=1) * np.linalg.norm(ac, axis=1)
    return np.where(den < 1e-9, 0.0, 2.0 * cross / np.maximum(den, 1e-12))


def grip_kappa(pts):
    return median_filter(stencil_kappa(pts, 4), size=5, mode="wrap")


def circ_delta(x, ref, total):
    return ((x - ref + total / 2) % total) - total / 2


# ---------------------------------------------------------------- data
def load(tag):
    frames = [pd.read_csv(SRC / f"{kind}_{tag}.{ext}") for kind, ext in
              (("pos", "csv.gz"), ("car", "csv.gz"), ("laps", "csv"))]
    for df in frames:
        df.insert(0, "session", tag)
    return frames


loaded = [load(tag) for tag in ("fp1", "fp2")]
pos = pd.concat([x[0] for x in loaded], ignore_index=True)
car = pd.concat([x[1] for x in loaded], ignore_index=True)
laps = (pd.concat([x[2] for x in loaded], ignore_index=True)
        .rename(columns={"Driver": "driver", "LapNumber": "lap"}))
laps["lap"] = laps["lap"].astype(int)
laps["accurate"] = laps["IsAccurate"].astype(str).str.lower() == "true"
laps["push"] = laps.accurate & (laps.LapTime <= PUSH_FRAC * laps.groupby("session").LapTime.transform("min"))
KEY = ["session", "driver", "lap"]
pos = pos[pos.status == "OnTrack"]
pos_g = {k: g.sort_values("t") for k, g in pos.groupby(KEY)}
car_g = {k: g.sort_values("t") for k, g in car.groupby(KEY)}
meta = laps.set_index(KEY)
usable = [k for k in meta.index if k in pos_g and k in car_g and len(pos_g[k]) >= 300]
push = [k for k in usable if bool(meta.loc[k, "push"])]
print(f"laps: timed {len(meta)}, usable {len(usable)}, push {len(push)} "
      f"(fp1 {sum(k[0] == 'fp1' for k in push)}, fp2 {sum(k[0] == 'fp2' for k in push)})", flush=True)

# ---------------------------------------------------------------- principal curve
fast = min(push, key=lambda k: meta.loc[k, "LapTime"])
xy0 = pos_g[fast][["x", "y"]].to_numpy()
xy0 = xy0[np.r_[True, np.linalg.norm(np.diff(xy0, axis=0), axis=1) > 0.05]]  # records repeat; splprep needs distinct points
chord = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(np.vstack([xy0, xy0[:1]]), axis=0), axis=1))]
tck, _ = splprep([np.r_[xy0[:, 0], xy0[0, 0]], np.r_[xy0[:, 1], xy0[0, 1]]], u=chord / chord[-1],
                 per=1, s=len(xy0) * 1.0)
path = resample(np.column_stack(splev(np.linspace(0, 1, 20000, endpoint=False), tck)), DS)
push_pts = np.vstack([pos_g[k][["x", "y"]].to_numpy() for k in push])
history = []
for it in range(20):
    s, d, total = project(path, push_pts)
    keep = np.abs(d) <= MAX_OFF
    mean_d = binned_mean(s[keep], d[keep], total, len(path), SIG_S)
    path = resample(path + mean_d[:, None] * normals(path), DS)
    history.append(dict(it=it, max_shift_m=round(float(np.abs(mean_d).max()), 4),
                        rms_offset_m=round(float(np.sqrt(np.mean(d[keep] ** 2))), 3),
                        outliers=int((~keep).sum()), length_m=round(total, 2)))
    print(history[-1], flush=True)
    if it >= 3 and history[-1]["max_shift_m"] < 0.02:
        break

# ---------------------------------------------------------------- timing line
s_start, s_end = [], []
for k in push:
    g, c = pos_g[k], car_g[k]
    t, lt = g.t.to_numpy(), float(meta.loc[k, "LapTime"])
    s_k, _, total = project(path, g[["x", "y"]].to_numpy()[[0, -1]])
    v0 = np.mean(np.interp(np.linspace(0.0, t[0], 5), c.t, c.speed)) / 3.6
    v1 = np.mean(np.interp(np.linspace(t[-1], lt, 5), c.t, c.speed)) / 3.6
    s_start.append((s_k[0] - v0 * t[0]) % total)
    s_end.append((s_k[1] + v1 * (lt - t[-1])) % total)
ends = np.r_[s_start, s_end]
dev = circ_delta(ends, ends[0], total)
s_line = float((ends[0] + np.median(dev)) % total)
sf_spread = dict(start_mad_m=float(np.median(np.abs(circ_delta(np.array(s_start), s_line, total)))),
                 end_mad_m=float(np.median(np.abs(circ_delta(np.array(s_end), s_line, total)))),
                 start_vs_end_m=float(np.median(circ_delta(np.array(s_end), s_line, total))
                                      - np.median(circ_delta(np.array(s_start), s_line, total))))
print("timing line at s =", round(s_line, 2), sf_spread, flush=True)

closed = np.vstack([path, path[:1]])
cum = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(closed, axis=0), axis=1))]
n_st = int(round(total / STATION_DS))
u = (s_line + np.arange(n_st) * total / n_st) % total
st = np.column_stack([np.interp(u, cum, closed[:, 0]), np.interp(u, cum, closed[:, 1])])
seg = np.linalg.norm(np.diff(np.vstack([st, st[:1]]), axis=0), axis=1)
arc = np.r_[0.0, np.cumsum(seg)[:-1]]
L = float(seg.sum())

# ---------------------------------------------------------------- per-lap speed traces on s
grid_s = np.arange(0.0, L, 1.0)
# Position timestamps jitter at ~4 Hz, so s(t) = speed-integrated distance
# scaled to L (smooth, monotone) plus a slow correction toward the projected
# position (absolute along-track). A lap is rejected only on a gross mismatch.
traces, trace_keys, rejected, lap_rms, dist_ratio, jitter = [], [], [], {}, [], []
for k in push:
    g, c = pos_g[k], car_g[k]
    t, lt = g.t.to_numpy(), float(meta.loc[k, "LapTime"])
    s_k, d_k, _ = project(st, g[["x", "y"]].to_numpy())
    lap_rms[k] = float(np.sqrt(np.mean(np.clip(d_k, -MAX_OFF, MAX_OFF) ** 2)))
    s_k[(t < 5.0) & (s_k > L / 2)] -= L
    s_k[(t > lt - 5.0) & (s_k < L / 2)] += L
    tc, vc = c.t.to_numpy(), c.speed.to_numpy() / 3.6
    tt, vv = np.r_[0.0, tc, lt], np.r_[vc[0], vc, vc[-1]]
    dist = np.r_[0.0, np.cumsum(0.5 * (vv[1:] + vv[:-1]) * np.diff(tt))]
    dist_ratio.append(float(dist[-1] / L))
    s_dist = dist * (L / dist[-1])
    err = s_k - np.interp(t, tt, s_dist)
    err_s = gaussian_filter1d(err, 4.0, mode="nearest")
    jitter.append(float(np.sqrt(np.mean((err - err_s) ** 2))))
    if np.abs(err_s).max() > 40.0:
        rejected.append(k)
        continue
    s_t = np.maximum.accumulate(s_dist + np.interp(tt, np.r_[0.0, t, lt], np.r_[0.0, err_s, 0.0]))
    traces.append(np.interp(grid_s, s_t, vv * 3.6))
    trace_keys.append(k)
traces = np.asarray(traces)
lap_times = np.array([float(meta.loc[k, "LapTime"]) for k in trace_keys])
top = np.argsort(lap_times)[:10]
top10 = np.median(traces[top], axis=0)
p90 = np.percentile(traces, 90, axis=0)
print(f"speed traces: {len(trace_keys)} kept, {len(rejected)} rejected | per-lap RMS offset from path "
      f"median {np.median(list(lap_rms.values())):.3f} m | speed-integrated distance / path length "
      f"median {np.median(dist_ratio):.4f} (IQR {np.percentile(dist_ratio, 25):.4f}-{np.percentile(dist_ratio, 75):.4f}) "
      f"| along-track position jitter median {np.median(jitter):.1f} m", flush=True)

# ---------------------------------------------------------------- elevation (mean of push laps)
zs_s, _, _ = project(st, push_pts)
z_pts = np.concatenate([pos_g[k].z.to_numpy() for k in push])
z_st = binned_mean(zs_s, z_pts, L, n_st, 10.0)
z_datum = float(z_st.min())
z_rel = z_st - z_datum

# ---------------------------------------------------------------- drawn road from observed usage
all_pts = np.vstack([pos_g[k][["x", "y"]].to_numpy() for k in usable])
s_all, d_all, _ = project(st, all_pts)
ok = np.abs(d_all) < 15.0
nb = int(np.ceil(L / 5.0))
q = (pd.DataFrame(dict(b=(np.floor(s_all[ok] / 5.0).astype(int) % nb), d=d_all[ok]))
     .groupby("b").d.quantile([0.02, 0.98]).unstack().reindex(range(nb))
     .interpolate(limit_direction="both"))
centres = (np.arange(nb) + 0.5) * 5.0
lo = np.interp(arc, centres, gaussian_filter1d(q[0.02].to_numpy(), 2, mode="wrap"), period=L)
hi = np.interp(arc, centres, gaussian_filter1d(q[0.98].to_numpy(), 2, mode="wrap"), period=L)
k_st = grip_kappa(st)
k_sm = gaussian_filter1d(k_st, 10 / STATION_DS, mode="wrap")
left, right = hi + CAR_HALF, lo - CAR_HALF
need = np.maximum(ROAD_W - (left - right), 0.0)
turn_l, turn_r = k_sm > 1 / 400, k_sm < -1 / 400
right = np.where(turn_l, right - need, right)                 # inside = left: widen outside
left = np.where(turn_r, left + need, left)                    # inside = right: widen outside
flat = ~(turn_l | turn_r)
left, right = np.where(flat, left + need / 2, left), np.where(flat, right - need / 2, right)
left = np.clip(gaussian_filter1d(left, 15 / STATION_DS, mode="wrap"), CAR_HALF + 0.2, 12.0)
right = np.clip(gaussian_filter1d(right, 15 / STATION_DS, mode="wrap"), -12.0, -(CAR_HALF + 0.2))

# ---------------------------------------------------------------- into the SVG frame (rigid)
reg = json.loads((ROOT / "cache/madring_fp1_elevation/validation.json").read_text(encoding="utf-8"))["registration"]
R = np.asarray(reg["rotation"])
centroid = st.mean(axis=0)
T = (reg["scale"] - 1.0) * centroid @ R + np.asarray(reg["translation"])
to_svg = lambda p: p @ R + T  # noqa: E731
st_svg = to_svg(st)
nrm = normals(st)
edge_l, edge_r = to_svg(st + left[:, None] * nrm), to_svg(st + right[:, None] * nrm)
f2000 = np.arange(2000) / 2000 * L
e_l = np.column_stack([np.interp(f2000, arc, edge_l[:, j], period=L) for j in range(2)])
e_r = np.column_stack([np.interp(f2000, arc, edge_r[:, j], period=L) for j in range(2)])
area = lambda p: 0.5 * float(np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1]))  # noqa: E731
outer, inner = (e_l, e_r) if abs(area(e_l)) > abs(area(e_r)) else (e_r, e_l)
if area(outer) < 0:                     # svg_to_outline convention: CCW loops
    outer, inner = outer[::-1].copy(), inner[::-1].copy()

from shapely.geometry import LinearRing, Point, Polygon  # noqa: E402
corridor = Polygon(outer, [inner])
checks = dict(outer_simple=LinearRing(outer).is_simple, inner_simple=LinearRing(inner).is_simple,
              outer_contains_inner=Polygon(outer).contains(Polygon(inner)), corridor_valid=corridor.is_valid,
              stations_inside=int(sum(corridor.contains(Point(p)) for p in st_svg)), stations=n_st)
print("outline checks", checks, flush=True)

# ---------------------------------------------------------------- compare with the SVG line
svg = json.loads((ROOT / "cache/madring_fp1_elevation/madring_fp1_raceline.json").read_text(encoding="utf-8"))
svg_p = np.asarray(svg["raceline"], float)
svg_f = np.asarray(svg["arc_length"], float) / float(svg["track_length_m"])
k_svg = grip_kappa(svg_p)
diag = json.loads((ROOT / "cache/madring_diagnosis/diagnosis.json").read_text(encoding="utf-8"))
gps_f = arc / L
sf_gap = float(np.linalg.norm(st_svg[0] - svg_p[0]))
cmp_rows = []
for row in diag["minima"]:
    f0 = row["frac"]
    wg = np.abs(circ_delta(gps_f, f0, 1.0)) <= 0.015
    ws = np.abs(circ_delta(svg_f, f0, 1.0)) <= 0.015
    cmp_rows.append(dict(frac=f0, fp1_kmh=row["fp1_kmh"], R_need=row["R_need"],
                         R_svg=round(float(1 / np.abs(k_svg[ws]).max()), 1),
                         R_gps=round(float(1 / np.abs(k_st[wg]).max()), 1),
                         top10_min_kmh=round(float(top10[np.abs(circ_delta(grid_s / L, f0, 1.0)) <= 0.015].min()), 1)))
cmp = pd.DataFrame(cmp_rows)
print("\nSVG vs measured radius at each FP1 minimum (R_need = radius the sim grip model needs for FP1's speed)")
print(cmp.to_string(index=False), flush=True)

# ---------------------------------------------------------------- write outputs
kappa_raw, _ = sim.kappa_ds_menger(st_svg)
src = (f"FP1+FP2 GPS principal curve: {len(push)} push laps (<= {PUSH_FRAC:.2f} x session best), "
       f"F1 official archive; rigid rotation into the SVG frame, true GPS scale")
with FILES["line"].open("x", encoding="utf-8") as fh:
    json.dump(dict(raceline=st_svg.tolist(), arc_length=arc.tolist(), kappa=kappa_raw.tolist(),
                   track_length_m=L, banking_deg=[], source=src,
                   sf_source="timing line from lap-start/lap-end GPS of every push lap"), fh)
grid2000 = np.linspace(0.0, 1.0, 2000, endpoint=False)
elev_2000 = np.interp(grid2000 * L, arc, z_rel, period=L)
with FILES["elev"].open("x", encoding="utf-8") as fh:
    json.dump(dict(track="madring", source=f"F1 official archive, 2026 Madring FP1+FP2, mean of {len(push)} push laps; Z/10",
                   altitude_reference="metres above the lap low point; absolute vertical datum unverified",
                   raw_height_min_m=float(z_st.min()), raw_height_max_m=float(z_st.max()),
                   removed_raw_datum_m=z_datum, alt_min_m=0.0, alt_max_m=round(float(z_rel.max()), 2),
                   span_m=round(float(z_rel.max()), 2), dist_frac=grid2000.round(5).tolist(),
                   elev_m=elev_2000.round(3).tolist(),
                   stations=np.column_stack([st_svg, z_rel]).round(3).tolist(),
                   sf_source="timing line from practice GPS; same origin as the 2D line"), fh)
with FILES["outline"].open("x", encoding="utf-8") as fh:
    json.dump(dict(outer=outer.tolist(), inner=inner.tolist(),
                   source=src + "; edges anchored to the 2-98% lateral usage of every timed lap, "
                                f"widened to {ROAD_W:.0f} m on the outside where usage is narrower"), fh)
np.savez_compressed(FILES["traces"], grid_s=grid_s, traces=traces, lap_times=lap_times,
                    keys=np.array(["|".join(map(str, k)) for k in trace_keys]),
                    top10=top10, p90=p90, length_m=L)
report = dict(push_laps=len(push), usable_laps=len(usable), fastest=list(map(str, fast)),
              convergence=history, length_m=L, stations=n_st, timing_line=sf_spread,
              sf_gap_to_fp1_registered_origin_m=sf_gap,
              lap_rms_offset_m=dict(median=float(np.median(list(lap_rms.values()))),
                                    p90=float(np.percentile(list(lap_rms.values()), 90))),
              session_mean_offset_m={tag: float(np.mean([np.mean(project(st, pos_g[k][["x", "y"]].to_numpy())[1])
                                                           for k in push if k[0] == tag])) for tag in ("fp1", "fp2")},
              speed_traces=dict(kept=len(trace_keys), rejected=len(rejected),
                                top10_laps=[trace_keys[i][0] + " " + trace_keys[i][1] + f" {lap_times[i]:.3f}" for i in top]),
              elevation_span_m=float(z_rel.max()), outline_checks=checks,
              road_width_m=dict(min=float((left - right).min()), median=float(np.median(left - right)),
                                max=float((left - right).max())),
              radius_vs_svg=cmp_rows)
with FILES["report"].open("x", encoding="utf-8") as fh:
    json.dump(report, fh, indent=2, default=str)

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ref = pd.read_csv(ROOT / "F1_Pipeline_Assets/exports/reference_2026_madring_fp1.csv")
rd = ref.distance.to_numpy() - float(ref.distance.iloc[0])
fig = plt.figure(figsize=(16, 16))
ax = fig.add_subplot(3, 1, 1)
ax.plot(outer[:, 0], outer[:, 1], color="0.6", lw=0.8)
ax.plot(inner[:, 0], inner[:, 1], color="0.6", lw=0.8)
ax.plot(svg_p[:, 0], svg_p[:, 1], color="tab:orange", lw=0.8, label="SVG line (FP1-registered)")
ax.plot(st_svg[:, 0], st_svg[:, 1], color="k", lw=0.8, label=f"measured line ({len(push)} push laps)")
ax.plot(*st_svg[0], "go", label="measured timing line")
ax.plot(*svg_p[0], "r^", label="FP1-registered origin")
ax.set_aspect("equal")
ax.legend(fontsize=8)
ax.set_title(f"Madring measured line | L {L:.1f} m | S/F gap to FP1 origin {sf_gap:.1f} m")
ax = fig.add_subplot(3, 1, 2)
ax.plot(svg_f * 100, np.abs(k_svg) * 1000, lw=0.8, color="tab:orange", label="SVG line |k| (v_grip view)")
ax.plot(gps_f * 100, np.abs(k_st) * 1000, lw=0.9, color="k", label="measured line |k| (v_grip view)")
for row in cmp_rows:
    ax.plot(row["frac"] * 100, 1000 / row["R_need"], "rv", ms=7)
ax.set_ylim(0, 60)
ax.set_ylabel("|curvature| 1/km  (red = max for FP1 speed)")
ax.grid(alpha=.3)
ax.legend(fontsize=8)
ax = fig.add_subplot(3, 1, 3)
ax.plot(grid_s / L * 100, p90, lw=0.8, label="push-lap p90")
ax.plot(grid_s / L * 100, top10, lw=1.0, label="top-10 laps median")
ax.plot(rd / rd[-1] * 100, ref.speed, lw=0.8, label="Russell FP1 (distance fraction)")
ax.set_xlabel("lap % from timing line")
ax.set_ylabel("km/h")
ax.grid(alpha=.3)
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(FILES["png"], dpi=75)
plt.close(fig)
print("\nwrote", OUT, "and", OUTLINE)
