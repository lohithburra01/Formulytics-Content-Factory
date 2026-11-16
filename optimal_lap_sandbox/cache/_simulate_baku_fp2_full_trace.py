"""Run a Baku longitudinal simulation constrained by the entire FP2 speed trace.

The replacement SVG is too sparse to infer the observed lift and peak points.
FP2 therefore supplies the speed ceiling at each station. The 2026 solver
still integrates acceleration, braking limits, drive mode, and battery state.
This is a reference-constrained fit, not an independent speed prediction.
"""

import csv
import json
import math
import sys
import types
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter1d


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Only the longitudinal part of sim_2026_lap is used. Its path optimizer imports
# these optional QP packages at module load, although no QP is called here.
try:
    import quadprog  # noqa: F401
except ImportError:
    sys.modules["quadprog"] = types.ModuleType("quadprog")
try:
    import cvxopt  # noqa: F401
except ImportError:
    cvxopt_stub = types.ModuleType("cvxopt")
    cvxopt_stub.matrix = lambda *args, **kwargs: None
    cvxopt_stub.solvers = types.SimpleNamespace(options={})
    sys.modules["cvxopt"] = cvxopt_stub

import sim_2026_lap as sim


LINE = ROOT / "F1_Pipeline_Assets/tracks/azerbaijan_grand_prix_raceline_new_svg_final.json"
FP2 = ROOT / "F1_Pipeline_Assets/exports/reference_2026_baku_fp2.csv"
OUT = ROOT / "F1_Pipeline_Assets/exports/baku_2026_fp2_full_trace_constrained_sim.csv"
AUDIT = ROOT / "cache/baku_fp2_full_trace_constrained_sim.json"


def brake_envelope_open(speed_cap, arc):
    """Backward brake limit for a flying lap with observed, unequal end speeds."""
    limit = speed_cap.copy()
    for i in range(len(limit) - 2, -1, -1):
        following = limit[i + 1]
        downforce_a = sim.downforce(following, "CORNER") / sim.MASS_KG
        brake_a = sim.MU_LONG * (sim.G + downforce_a) * sim._trail_brake_frac(following)
        drag_a = sim.drag_force(following, "CORNER") / sim.MASS_KG
        achievable = math.sqrt(following**2 + 2 * (brake_a + drag_a) * (arc[i + 1] - arc[i]))
        limit[i] = min(limit[i], achievable)
    return limit


def main():
    data = json.loads(LINE.read_text(encoding="utf-8"))
    arc = np.asarray(data["arc_length"], dtype=float)
    length = float(data["track_length_m"])
    fraction = arc / length

    with FP2.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    distance = np.asarray([float(row["distance"]) for row in rows])
    reference_speed = np.asarray([float(row["speed"]) for row in rows])
    reference_fraction = (distance - distance[0]) / (distance[-1] - distance[0])

    # ~12 m Gaussian smoothing removes telemetry quantization without shifting
    # the major peak or apex positions. The target remains in speed units.
    target_kmh = gaussian_filter1d(np.interp(fraction, reference_fraction, reference_speed), 6)
    speed_cap = target_kmh / 3.6

    # These are local calibration choices for this FP2-constrained run only.
    sim.MU_DRIVE = 1.25
    sim.MU_LONG = 1.60
    sim.TRAIL_FRAC_MIN = 0.55
    sim.CDA_STRAIGHT_M2 = 0.55
    sim.CL_CORNER_M2 = 4.45
    sim.RHO = 1.2274

    # The observed speed ceiling already encodes lateral corner slowdown.
    # Zero additional physics curvature avoids counting those turns twice.
    kappa_for_longitudinal_pass = np.zeros(len(arc))
    brake_limit = brake_envelope_open(speed_cap, arc)
    speed, soc, mode, power_kw, _ = sim.forward_pass_energy_aware(
        speed_cap, brake_limit, kappa_for_longitudinal_pass,
        arc, length, v0=float(speed_cap[0]))

    # forward_pass_energy_aware closes index 0 on the final 2 m segment. Keep
    # the measured flying-lap start speed; time integrates only the open lap.
    speed[0] = speed_cap[0]
    dt = 2 * np.diff(arc) / np.maximum(speed[:-1] + speed[1:], 1e-6)
    time_s = np.concatenate([[0.0], np.cumsum(dt)])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time_s", "distance", "speed", "mode", "soc_pct", "power_kw"])
        writer.writerows(zip(time_s, arc, speed * 3.6, mode, soc * 100, power_kw))

    error = (speed - speed_cap) * 3.6
    audit = {
        "method": "full FP2 speed ceiling plus 2026 longitudinal forward/backward limits",
        "independent_prediction": False,
        "fp2_source": str(FP2),
        "raceline_source": str(LINE),
        "smoothing_sigma_stations": 6,
        "track_length_m": length,
        "mu_drive": sim.MU_DRIVE,
        "mu_long": sim.MU_LONG,
        "trail_frac_min": sim.TRAIL_FRAC_MIN,
        "cda_straight_m2": sim.CDA_STRAIGHT_M2,
        "lap_time_s_to_last_station": float(time_s[-1]),
        "mae_to_smoothed_target_kmh": float(np.mean(np.abs(error))),
        "max_speed_kmh": float(np.max(speed) * 3.6),
    }
    AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"lap {time_s[-1]:.3f} s; speed MAE to smoothed FP2 {audit['mae_to_smoothed_target_kmh']:.2f} km/h")
    print(f"peak speed {audit['max_speed_kmh']:.1f} km/h")


if __name__ == "__main__":
    main()
