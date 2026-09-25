"""Plot practice traces against the old and full-trace-constrained Baku sims."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
EXPORTS = ROOT / "F1_Pipeline_Assets/exports"
FILES = {
    "FP1": EXPORTS / "reference_2026_baku_fp1.csv",
    "FP2": EXPORTS / "reference_2026_baku_fp2.csv",
    "Previous sim": EXPORTS / "baku_2026_fp2_calibrated_sim_mu085_br160_tr055.csv",
    "Full-trace sim": EXPORTS / "baku_2026_fp2_full_trace_constrained_sim.csv",
}
OUT = ROOT / "cache/baku_fp_vs_full_trace_sim_speed.png"


def load(path):
    frame = pd.read_csv(path, usecols=["distance", "speed", "time_s"])
    frame = frame.sort_values("distance").drop_duplicates("distance")
    distance = frame.distance.to_numpy(dtype=float)
    fraction = 100 * (distance - distance[0]) / (distance[-1] - distance[0])
    speed = frame.speed.to_numpy(dtype=float)
    lap_s = float(frame.time_s.max() - frame.time_s.min())
    return fraction, speed, lap_s


def main():
    data = {name: load(path) for name, path in FILES.items()}
    x = np.linspace(0, 100, 2001)
    speed = {name: np.interp(x, values[0], values[1]) for name, values in data.items()}
    old_error = speed["Previous sim"] - speed["FP2"]
    new_error = speed["Full-trace sim"] - speed["FP2"]
    old_mae, new_mae = np.mean(abs(old_error)), np.mean(abs(new_error))
    old_r = np.corrcoef(speed["Previous sim"], speed["FP2"])[0, 1]
    new_r = np.corrcoef(speed["Full-trace sim"], speed["FP2"])[0, 1]

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
    fig, (ax, err) = plt.subplots(2, 1, figsize=(16, 9), sharex=True,
                                  gridspec_kw={"height_ratios": [3.1, 1.2]},
                                  constrained_layout=True)
    fig.patch.set_facecolor("#f7f9fc")
    for a in (ax, err):
        a.set_facecolor("white")
        a.grid(True, color="#dfe5ed", linewidth=0.8)
        a.spines[["top", "right"]].set_visible(False)

    ax.plot(x, speed["FP1"], color="#8997a6", lw=1.3,
            label=f"FP1 actual  {data['FP1'][2]:.3f} s")
    ax.plot(x, speed["Previous sim"], color="#ac9a90", lw=1.5,
            ls=(0, (4, 2)), alpha=0.85,
            label=f"Previous apex-only sim  {data['Previous sim'][2]:.3f} s")
    ax.plot(x, speed["FP2"], color="#0867b7", lw=2.5,
            label=f"FP2 actual  {data['FP2'][2]:.3f} s")
    ax.plot(x, speed["Full-trace sim"], color="#ef6b1c", lw=2.0,
            ls=(0, (5, 2)),
            label=f"FP2-constrained sim  {data['Full-trace sim'][2]:.3f} s")
    ax.set_ylabel("Speed (km/h)")
    ax.set_ylim(55, 370)
    ax.legend(loc="lower right", ncol=2, facecolor="white", framealpha=0.96)
    ax.set_title("Baku 2026 | practice speed and full-trace-constrained simulation",
                 loc="left", fontsize=16, fontweight="bold", pad=18)
    ax.text(0, 1.017, "The full FP2 speed curve constrains this run; it is a calibrated replay, not an independent prediction.",
            transform=ax.transAxes, color="#506274", fontsize=10)

    err.axhline(0, color="#28394a", lw=1)
    err.plot(x, old_error, color="#ac9a90", lw=1.45, ls=(0, (4, 2)),
             label=f"Previous vs FP2: MAE {old_mae:.1f} km/h, r {old_r:.3f}")
    err.plot(x, new_error, color="#ef6b1c", lw=1.8,
             label=f"New vs FP2: MAE {new_mae:.1f} km/h, r {new_r:.4f}")
    err.set_ylabel("Sim − FP2 (km/h)")
    err.set_xlabel("Lap distance (%)")
    err.set_xlim(0, 100)
    err.set_xticks(np.arange(0, 101, 10))
    err.legend(loc="upper right", facecolor="white", framealpha=0.96)

    fig.savefig(OUT, dpi=170, facecolor=fig.get_facecolor())
    print(f"saved {OUT}")
    print(f"previous MAE {old_mae:.2f}, r {old_r:.4f}; new MAE {new_mae:.2f}, r {new_r:.4f}")


if __name__ == "__main__":
    main()
