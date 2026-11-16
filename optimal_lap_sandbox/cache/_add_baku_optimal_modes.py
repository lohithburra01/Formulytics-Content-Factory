"""Add 2026 energy-mode labels to the existing Baku optimal pace CSV."""

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
EXPORTS = ROOT / "F1_Pipeline_Assets/exports"
PACE = EXPORTS / "baku_2026_optimal_pace_1p5s_faster.csv"
BASE = EXPORTS / "baku_2026_fp2_full_trace_constrained_sim.csv"
OUT = EXPORTS / "baku_2026_optimal_pace_1p5s_faster_with_modes.csv"


def main():
    pace = pd.read_csv(PACE)
    base = pd.read_csv(BASE)
    modes = np.full(len(pace), "NORMAL", dtype=object)
    braking = base["mode"].to_numpy() == "REGEN"
    modes[braking] = "REGEN"

    # Deploy for the first seven seconds after each braking zone, while MGU-K
    # power is available. Preserve the already fixed speed and time samples.
    times = pace["time_s"].to_numpy(dtype=float)
    speed = pace["speed"].to_numpy(dtype=float)
    exit_time = times[0]
    for i in range(len(modes)):
        if braking[i]:
            continue
        if i == 0 or braking[i - 1]:
            exit_time = times[i]
        if times[i] - exit_time < 7.0 and speed[i] < 300.0:
            modes[i] = "DEPLOY"

    # The long main straight gets the three-second high-speed harvest segment
    # beginning at its maximum-speed point. It is after the peak, before the
    # next braking zone, and does not alter the velocity profile.
    peak = int(np.argmax(speed))
    superclip = ((times >= times[peak]) & (times < times[peak] + 3.0)
                 & (speed >= 0.96 * speed[peak]) & ~braking)
    modes[superclip] = "SUPERCLIP"

    pace["mode"] = modes
    pace.to_csv(OUT, index=False)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
