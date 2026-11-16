"""Measure the sanity check's GAIN/DROP rate statistic on ANY lap csv.

sim_2026_lap.py's assert_sanity gates the braking DROP rate median against a
deliberately TRACK-AGNOSTIC band [28,60] km/h/s. This reproduces that exact
statistic - 30 fps resample, 0.5 s window, median of |rate| over braking
samples - so a sim value can be checked against REAL traces instead of being
argued about, and so a band can be shown to be too narrow for a given circuit
rather than simply widened until a run passes.

  python cache/_drop_rate_audit.py "path.csv::label" ...

Braking mask: the `brake` channel when the csv carries a live one (OpenF1
writes 0/100), else any sample decelerating faster than 2 km/h/s. Real OpenF1
csvs sample at ~3-4 Hz, so their rates are smoothed by the resample and read
LOWER than a dense sim csv - compare real-to-real and sim-to-sim, never across.
"""
from __future__ import annotations

import csv
import sys

import numpy as np


def stats(path):
    t, v, brk = [], [], []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t.append(float(r["time_s"])); v.append(float(r["speed"]))
            try:
                brk.append(float(r.get("brake") or 0.0))
            except ValueError:
                brk.append(0.0)
    t = np.maximum.accumulate(np.asarray(t)); v = np.asarray(v); brk = np.asarray(brk)
    T = float(t[-1])
    m = max(60, int(T * 30))
    tg = np.linspace(0.0, T, m, endpoint=False)
    spd = np.interp(tg, t, v)                       # csv speed is already km/h
    step = max(1, int(0.5 * 30))
    rates = np.full(m, np.nan)
    rates[:-step] = (spd[step:] - spd[:-step]) / 0.5
    live_brake = brk.max() > 0
    if live_brake:
        idx = np.clip(np.searchsorted(t, tg, side="right") - 1, 0, len(v) - 1)
        is_brake = brk[idx] > 0
    else:
        is_brake = rates < -2.0
    drop = np.abs(rates[is_brake & (rates < -2)]); drop = drop[~np.isnan(drop)]
    gain = rates[(~is_brake) & (rates > 2) & (spd < 0.88 * spd.max())]
    gain = gain[~np.isnan(gain)]
    return dict(T=T, top=float(spd.max()), brake_src="brake ch" if live_brake else "rate<-2",
                drop_med=float(np.median(drop)) if len(drop) else float("nan"),
                drop_p90=float(np.percentile(drop, 90)) if len(drop) else float("nan"),
                gain_med=float(np.median(gain)) if len(gain) else float("nan"))


def main():
    print(f"{'label':26s} {'lap':>7s} {'top':>5s} {'drop_med':>9s} {'drop_p90':>9s} "
          f"{'gain_med':>9s}  brake-mask")
    for a in sys.argv[1:]:
        path, _, label = a.partition("::")
        try:
            s = stats(path)
        except Exception as e:                                  # noqa: BLE001
            print(f"{(label or path):26s} FAILED {type(e).__name__}: {e}"); continue
        print(f"{(label or path):26s} {s['T']:7.2f} {s['top']:5.0f} {s['drop_med']:9.1f} "
              f"{s['drop_p90']:9.1f} {s['gain_med']:9.1f}  {s['brake_src']}")


if __name__ == "__main__":
    main()
