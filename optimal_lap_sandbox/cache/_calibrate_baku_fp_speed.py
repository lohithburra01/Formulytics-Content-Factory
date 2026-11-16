"""Fit Baku's missing SVG corner constraints to FP2, then rerun the 2026 solver.

The replacement SVG draws the correct road topology but has only 43 cubic
segments, losing several real corner radii. This calibration uses only FP2
apex positions and speeds as targets. Acceleration, braking, energy use, and
transitions are still produced by sim_2026_lap's forward/backward solver.
FP1 is kept as an independent visual check; this is not a prediction.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import median_filter
from scipy.signal import find_peaks

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import sim_2026_lap as sim
LINE = ROOT / "F1_Pipeline_Assets/tracks/azerbaijan_grand_prix_raceline_new_svg_final.json"
FP2 = ROOT / "F1_Pipeline_Assets/exports/reference_2026_baku_fp2.csv"
mu_drive = float(os.environ.get("BAKU_MU_DRIVE", "1.0"))
mu_long = float(os.environ.get("BAKU_MU_LONG", "1.35"))
trail_min = float(os.environ.get("BAKU_TRAIL_MIN", "0.40"))
cda = float(os.environ.get("BAKU_CDA", "0.717"))
suffix = "" if mu_drive == 1.0 else f"_mu{int(round(mu_drive*100)):03d}"
if mu_long != 1.35:
    suffix += f"_br{int(round(mu_long*100)):03d}"
if trail_min != .40:
    suffix += f"_tr{int(round(trail_min*100)):03d}"
if cda != .717:
    suffix += f"_cd{int(round(cda*1000)):03d}"
OUT = ROOT / f"F1_Pipeline_Assets/exports/baku_2026_fp2_calibrated_sim{suffix}.csv"
AUDIT = ROOT / f"cache/baku_fp2_corner_calibration{suffix}.json"

sim.CDA_STRAIGHT_M2 = cda
sim.CL_CORNER_M2 = 4.45
sim.RHO = 1.2274
sim.MU_DRIVE = mu_drive
sim.MU_LONG = mu_long
sim.TRAIL_FRAC_MIN = trail_min
data = json.loads(LINE.read_text())
line = np.asarray(data["raceline"], float)
arc = np.asarray(data["arc_length"], float)
length = float(data["track_length_m"])
frac = arc / length
n = len(line)

# Match the solver's default wide-stencil curvature before correcting the
# missing SVG detail. Only its physics channel changes; the SVG road and
# rendered raceline coordinates remain unchanged.
span = 4
base = np.zeros(n)
for i in range(n):
    a, b, c = line[(i-span)%n], line[i], line[(i+span)%n]
    ab, bc, ac = b-a, c-b, c-a
    denom = np.linalg.norm(ab)*np.linalg.norm(bc)*np.linalg.norm(ac)
    base[i] = 0 if denom < 1e-9 else abs(2*(ab[0]*bc[1]-ab[1]*bc[0])/denom)
base = median_filter(base, size=5, mode="wrap")

# The simplified SVG invents a medium corner at 78% where the FP2 trace stays
# near 300 km/h. Limit only that false curvature pocket, with a smooth taper.
phantom_center = 0.781
arc_delta = np.abs(frac - phantom_center)
arc_delta = np.minimum(arc_delta, 1-arc_delta) * length
taper = np.exp(-0.5*(arc_delta/58.0)**2)
base = base*(1-taper) + np.minimum(base, 0.0084)*taper

fp = np.genfromtxt(FP2, delimiter=",", names=True)
fd = (fp["distance"]-fp["distance"][0])/(fp["distance"][-1]-fp["distance"][0])
fv = fp["speed"]
peaks, properties = find_peaks(-fv, prominence=15, distance=8)
corners = [(float(fd[i]), float(fv[i])) for i in peaks]
if len(corners) != 10:
    raise RuntimeError(f"Expected ten FP2 braking minima, found {len(corners)}")

def corner_kappa(v_kmh):
    v = v_kmh/3.6
    return sim.MU_LAT*sim.G/(v*v) + sim.MU_LAT*0.5*sim.RHO*sim.CL_CORNER_M2/sim.MASS_KG

# One local curvature basis per observed corner. The centre (not the whole
# speed trace) supplies the calibrated constraint; longitudinal behaviour
# between the corners is produced by the existing model.
basis = []
amplitudes = []
for f, speed in corners:
    delta = np.abs(frac-f)
    delta = np.minimum(delta, 1-delta)*length
    width = 22.0 if speed <= 130 else 28.0
    bump = np.exp(-0.5*(delta/width)**2)
    basis.append(bump)
    j = int(np.argmin(delta))
    amplitudes.append(corner_kappa(speed)-base[j])
basis = np.asarray(basis)
amplitudes = np.asarray(amplitudes)

def run(amplitudes):
    effective = np.maximum(base + np.einsum("i,ij->j", amplitudes, basis), 1e-5)
    v, soc, mode, p_kw, times = sim.simulate_lap(
        line, arc, np.asarray(data["kappa"]), length,
        effective_curvature=effective)
    v, times = sim.smooth_longitudinal(v, arc, length, win_s=0.45)
    v, times = sim.suppress_microhumps(v, arc, length, times)
    return effective, v, soc, mode, p_kw, times

history = []
for iteration in range(16):
    effective, v, soc, mode, p_kw, times = run(amplitudes)
    observed = []
    for f, target in corners:
        delta = np.abs(frac-f)
        delta = np.minimum(delta, 1-delta)
        observed.append(float(np.min(v[delta < .0035])*3.6))
    error = np.asarray(observed)-np.asarray([x[1] for x in corners])
    history.append(dict(iteration=iteration, lap_s=float(times[-1]),
                        corner_error_kmh=np.round(error,1).tolist()))
    print(f"[fit] iteration={iteration} lap={times[-1]:.3f}s "
          f"corner MAE={np.mean(abs(error)):.1f} km/h "
          f"worst={np.max(abs(error)):.1f}", flush=True)
    if iteration == 15:
        break
    # κ−κ_aero scales approximately as 1/v². Damped updates preserve smooth
    # corner transitions and allow the model to account for braking limits.
    for j, ((f,target), speed) in enumerate(zip(corners, observed)):
        current_peak = base[int(np.argmin(abs(frac-f)))] + amplitudes[j]
        aero_floor = sim.MU_LAT*0.5*sim.RHO*sim.CL_CORNER_M2/sim.MASS_KG
        desired_peak = aero_floor + (current_peak-aero_floor)*(speed/target)**2
        amplitudes[j] = np.clip(amplitudes[j] + .7*(desired_peak-current_peak), -.08, .12)

sim.write_csv(str(OUT), v, soc, mode, p_kw, times, arc, length, fps=30)
audit = dict(method="FP2 apex-constrained effective curvature; longitudinal solver unchanged",
             svg=str(ROOT / "RaceCircuitGillesBaku.svg"),
             source=str(FP2), corners=[dict(fraction=f, target_kmh=s,
                                           amplitude_per_m=float(a))
                                       for (f,s),a in zip(corners, amplitudes)],
             phantom_center_frac=phantom_center, history=history,
             final_lap_s=float(times[-1]))
AUDIT.write_text(json.dumps(audit, indent=2))
print(f"wrote {OUT}")
