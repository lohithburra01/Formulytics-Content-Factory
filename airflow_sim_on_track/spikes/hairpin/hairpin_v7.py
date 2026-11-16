"""SPIKE v7: v6 streamlines with a SMOOTHED racing line (fixes the jitter).

v6 jitter cause: heading came from the raw 0.5 m raceline points (zigzag ~0.6 deg per frame), and the yaw rate is a
0.01 s difference of it -> yaw rate jumped 0 <-> 1 rad/s frame to frame. The streamlines live in the turning car frame,
so the yaw_rate x r term at 11 m behind the car jumped up to 17 m/s per frame and the whole field whipped about.
v7: Gaussian-smooth the line positions (sigma 1 m, periodic) before heading/curvature/speed alignment.
Measured: yaw-rate jump per frame median 0.44 -> 0.013 rad/s; line moves at most 4 cm at the hairpin.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import hairpin_trails as tr
import hairpin_v4 as v4
import hairpin_v6  # noqa: F401  (installs the v6 streamline draw into v4)

v4.OUT = Path(__file__).parent / "out_v7"
SMOOTH_SIGMA = 1.0                 # m, Gaussian on the raceline points
_raw_lap_data = tr.lap_data


def smooth_lap_data():
    P, k, v, t, hdg = _raw_lap_data()          # P is resampled every 0.5 m, closed loop
    n = int(4 * SMOOTH_SIGMA / 0.5)
    x = np.arange(-n, n + 1) * 0.5
    ker = np.exp(-0.5 * (x / SMOOTH_SIGMA) ** 2); ker /= ker.sum()
    P = np.c_[[np.convolve(np.r_[P[-n:, i], P[:, i], P[:n, i]], ker, "valid") for i in (0, 1)]].T
    d1 = np.roll(P, -1, 0) - np.roll(P, 1, 0)
    hdg = np.unwrap(np.arctan2(d1[:, 1], d1[:, 0]))
    return P, k, v, t, hdg                     # k, v, t from the raw line: curvature was already smoothed, 4 cm shift


v4.lap_data = smooth_lap_data
if __name__ == "__main__":
    v4.main()
