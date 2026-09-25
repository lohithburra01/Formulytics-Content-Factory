"""Make a 1.5 s faster Baku pace projection without changing speed shape.

The input is the validated FP2-constrained longitudinal simulation. A single
positive speed multiplier preserves every extremum and its lap position.
Times are reintegrated from distance, not scaled or shifted independently.
This is a pace projection, not another independent physics prediction.
"""

import csv
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
EXPORTS = ROOT / "F1_Pipeline_Assets/exports"
BASE = EXPORTS / "baku_2026_fp2_full_trace_constrained_sim.csv"
FP2 = EXPORTS / "reference_2026_baku_fp2.csv"
OUT = EXPORTS / "baku_2026_optimal_pace_1p5s_faster.csv"
AUDIT = ROOT / "cache/baku_2026_optimal_pace_1p5s_faster.json"
GAIN_VS_FP2_S = 1.5


def read_columns(path):
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {key: np.asarray([float(row[key]) for row in rows])
            for key in ("time_s", "distance", "speed")}


def integrate_time(distance, speed_kmh):
    speed_ms = speed_kmh / 3.6
    ds = np.diff(distance)
    if np.any(ds <= 0) or np.any(speed_ms <= 0):
        raise ValueError("Expected increasing distance and positive speed")
    dt = 2 * ds / (speed_ms[:-1] + speed_ms[1:])
    return np.concatenate([[0.0], np.cumsum(dt)])


def main():
    base = read_columns(BASE)
    reference = read_columns(FP2)
    fp2_lap_s = float(reference["time_s"][-1] - reference["time_s"][0])
    target_lap_s = fp2_lap_s - GAIN_VS_FP2_S
    base_time = integrate_time(base["distance"], base["speed"])
    factor = float(base_time[-1] / target_lap_s)
    if not 1.0 < factor < 1.03:
        raise ValueError(f"Unexpected speed multiplier {factor:.6f}")

    optimal_speed = base["speed"] * factor
    optimal_time = integrate_time(base["distance"], optimal_speed)
    assert np.array_equal(np.sign(np.diff(optimal_speed)),
                          np.sign(np.diff(base["speed"])))
    assert abs(optimal_time[-1] - target_lap_s) < 1e-8

    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time_s", "distance", "speed"])
        writer.writerows(zip(optimal_time, base["distance"], optimal_speed))

    audit = {
        "method": "uniform speed scale of FP2-constrained simulation",
        "independent_prediction": False,
        "base_source": str(BASE),
        "fp2_source": str(FP2),
        "gain_vs_fp2_s": GAIN_VS_FP2_S,
        "fp2_lap_s": fp2_lap_s,
        "base_lap_s": float(base_time[-1]),
        "target_lap_s": target_lap_s,
        "output_lap_s": float(optimal_time[-1]),
        "speed_multiplier": factor,
        "base_peak_kmh": float(base["speed"].max()),
        "output_peak_kmh": float(optimal_speed.max()),
        "extrema_positions_unchanged": True,
    }
    AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"FP2 {fp2_lap_s:.3f} s; optimal projection {optimal_time[-1]:.3f} s "
          f"({GAIN_VS_FP2_S:.3f} s faster)")
    print(f"speed multiplier {factor:.6f}; peak {optimal_speed.max():.1f} km/h; "
          "all extrema positions unchanged")


if __name__ == "__main__":
    main()
