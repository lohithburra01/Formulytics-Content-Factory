"""Check Baku simulated speed peaks against the actual FP2 trace."""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks


ROOT = Path(__file__).resolve().parents[1]
EXPORTS = ROOT / "F1_Pipeline_Assets/exports"
REFERENCE = EXPORTS / "reference_2026_baku_fp2.csv"
DEFAULT = EXPORTS / "baku_2026_fp2_full_trace_constrained_sim.csv"


def sampled(path, x):
    frame = pd.read_csv(path, usecols=["distance", "speed"])
    station = frame.distance.to_numpy(dtype=float)
    fraction = 100 * (station - station[0]) / (station[-1] - station[0])
    return np.interp(x, fraction, frame.speed)


def check(candidate):
    x = np.linspace(0, 100, 2001)
    reference = sampled(REFERENCE, x)
    trial = sampled(candidate, x)
    ref_smooth = gaussian_filter1d(reference, 2)
    trial_smooth = gaussian_filter1d(trial, 2)
    ref_peaks, _ = find_peaks(ref_smooth, prominence=18, distance=80)
    peak_errors = []
    position_errors = []
    for i in ref_peaks:
        nearby = np.where(np.abs(x - x[i]) <= 1.5)[0]
        j = nearby[np.argmax(trial_smooth[nearby])]
        peak_errors.append(abs(trial_smooth[j] - ref_smooth[i]))
        position_errors.append(abs(x[j] - x[i]))
    late = (x >= 70) & (x <= 95)
    top_error = abs(np.max(trial_smooth[late]) - np.max(ref_smooth[late]))
    mae = np.mean(np.abs(trial - reference))
    corr = np.corrcoef(trial, reference)[0, 1]
    print(f"peaks {len(ref_peaks)}; worst peak speed error {max(peak_errors):.2f} km/h; "
          f"worst peak position error {max(position_errors):.2f} lap-%")
    print(f"late top-speed error {top_error:.2f} km/h; full-trace MAE {mae:.2f} km/h; r {corr:.4f}")
    assert len(ref_peaks) == 8
    assert max(peak_errors) <= 7.0
    assert max(position_errors) <= 1.0
    assert top_error <= 5.0
    assert mae <= 5.0
    assert corr >= 0.99


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", nargs="?", type=Path, default=DEFAULT)
    check(parser.parse_args().candidate)
