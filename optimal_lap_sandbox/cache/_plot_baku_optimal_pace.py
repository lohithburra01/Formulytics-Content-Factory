"""Show the Baku optimal pace projection against the practice speed pattern."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
EXPORTS = ROOT / "F1_Pipeline_Assets/exports"
SOURCES = {
    "FP1": EXPORTS / "reference_2026_baku_fp1.csv",
    "FP2": EXPORTS / "reference_2026_baku_fp2.csv",
    "Matched sim": EXPORTS / "baku_2026_fp2_full_trace_constrained_sim.csv",
    "Optimal pace": EXPORTS / "baku_2026_optimal_pace_1p5s_faster.csv",
}
OUT = ROOT / "cache/baku_fp2_vs_optimal_pace_1p5s.png"


def trace(path):
    frame = pd.read_csv(path, usecols=["time_s", "distance", "speed"])
    distance = frame.distance.to_numpy(dtype=float)
    fraction = 100 * (distance - distance[0]) / (distance[-1] - distance[0])
    return fraction, frame.speed.to_numpy(dtype=float), float(frame.time_s.iloc[-1] - frame.time_s.iloc[0])


def main():
    data = {name: trace(path) for name, path in SOURCES.items()}
    x = np.linspace(0, 100, 2001)
    v = {name: np.interp(x, values[0], values[1]) for name, values in data.items()}
    gain = v["Optimal pace"] - v["Matched sim"]
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
    fig, (ax, diff) = plt.subplots(2, 1, figsize=(16, 8.5), sharex=True,
                                   gridspec_kw={"height_ratios": [3.2, 1]},
                                   constrained_layout=True)
    fig.patch.set_facecolor("#f7f9fc")
    for axis in (ax, diff):
        axis.set_facecolor("white")
        axis.grid(True, color="#dfe5ed", linewidth=0.8)
        axis.spines[["top", "right"]].set_visible(False)

    ax.plot(x, v["FP1"], color="#94a0ac", lw=1.25,
            label=f"FP1 actual  {data['FP1'][2]:.3f} s")
    ax.plot(x, v["FP2"], color="#0867b7", lw=2.0,
            label=f"FP2 actual  {data['FP2'][2]:.3f} s")
    ax.plot(x, v["Matched sim"], color="#ef6b1c", lw=1.65, ls=(0, (5, 2)),
            label=f"FP2-matched sim  {data['Matched sim'][2]:.3f} s")
    ax.plot(x, v["Optimal pace"], color="#9d2ba3", lw=2.2,
            label=f"Optimal pace projection  {data['Optimal pace'][2]:.3f} s")
    ax.set_title("Baku 2026 | same speed pattern, 1.5 seconds quicker than FP2",
                 loc="left", fontsize=17, fontweight="bold", pad=18)
    ax.text(0, 1.017, "Uniform +1.340% speed increase from the FP2-matched run; every peak and braking point stays at the same distance.",
            transform=ax.transAxes, fontsize=10, color="#506274")
    ax.set_ylabel("Speed (km/h)")
    ax.set_ylim(55, 370)
    ax.legend(loc="lower right", ncol=2, facecolor="white", framealpha=0.96)

    diff.axhline(0, color="#28394a", lw=1)
    diff.plot(x, gain, color="#9d2ba3", lw=2.0)
    diff.set_ylim(0, 6)
    diff.set_ylabel("Gain vs matched sim\n(km/h)")
    diff.set_xlabel("Lap distance (%)")
    diff.set_xlim(0, 100)
    diff.set_xticks(np.arange(0, 101, 10))
    fig.savefig(OUT, dpi=170, facecolor=fig.get_facecolor())
    print(f"saved {OUT}")
    print(f"optimal lap {data['Optimal pace'][2]:.3f} s; max gain {gain.max():.2f} km/h")


if __name__ == "__main__":
    main()
