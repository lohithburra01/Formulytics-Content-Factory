"""Compare the corrected-SVG Baku speed simulation with 2026 practice laps."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
EXPORTS = ROOT / "F1_Pipeline_Assets" / "exports"
SOURCES = {
    "FP1": EXPORTS / "reference_2026_baku_fp1.csv",
    "FP2": EXPORTS / "reference_2026_baku_fp2.csv",
    "Original SVG sim": EXPORTS / "baku_2026_synthetic_new_svg_fixed.csv",
    "Pattern-matched sim": EXPORTS / "baku_2026_fp2_calibrated_sim_mu085_br160_tr055.csv",
}
OUTPUT = ROOT / "cache" / "baku_fp_vs_pattern_matched_sim_speed.png"


def trace(path):
    frame = pd.read_csv(path, usecols=["time_s", "distance", "speed"])
    frame = frame.replace([np.inf, -np.inf], np.nan).dropna()
    frame = frame.sort_values("distance").drop_duplicates("distance")
    distance = frame["distance"].to_numpy(dtype=float)
    speed = frame["speed"].to_numpy(dtype=float)
    time = frame["time_s"].to_numpy(dtype=float)
    progress = 100 * (distance - distance[0]) / (distance[-1] - distance[0])
    return progress, speed, float(time.max() - time.min())


def main():
    data = {label: trace(path) for label, path in SOURCES.items()}
    x = np.linspace(0, 100, 2001)
    sampled = {name: np.interp(x, values[0], values[1]) for name, values in data.items()}
    fp2 = sampled["FP2"]
    original = sampled["Original SVG sim"]
    matched = sampled["Pattern-matched sim"]
    mae_original = np.mean(np.abs(original - fp2))
    mae_matched = np.mean(np.abs(matched - fp2))
    corr_original = np.corrcoef(original, fp2)[0, 1]
    corr_matched = np.corrcoef(matched, fp2)[0, 1]

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
    fig, (ax, err) = plt.subplots(
        2, 1, figsize=(16, 9), sharex=True,
        gridspec_kw={"height_ratios": [3.1, 1.25]},
        constrained_layout=True,
    )
    fig.patch.set_facecolor("#f7f9fc")
    for axis in (ax, err):
        axis.set_facecolor("white")
        axis.grid(True, color="#dfe5ed", linewidth=0.8)
        axis.spines[["top", "right"]].set_visible(False)

    colors = {"fp1": "#929da9", "fp2": "#0867b7", "original": "#b3a397", "matched": "#ed6a20"}
    ax.plot(x, sampled["FP1"], color=colors["fp1"], lw=1.45,
            label=f"FP1 actual  {data['FP1'][2]:.3f} s")
    ax.plot(x, fp2, color=colors["fp2"], lw=2.2,
            label=f"FP2 actual  {data['FP2'][2]:.3f} s")
    ax.plot(x, original, color=colors["original"], lw=1.6, ls="--", alpha=0.85,
            label=f"Original SVG sim  {data['Original SVG sim'][2]:.3f} s")
    ax.plot(x, matched, color=colors["matched"], lw=2.15,
            label=f"Pattern-matched sim  {data['Pattern-matched sim'][2]:.3f} s")
    ax.set_ylabel("Speed (km/h)")
    ax.set_ylim(55, 370)
    ax.legend(loc="lower right", ncol=2, frameon=True, facecolor="white", framealpha=0.95)
    ax.set_title("Baku 2026 | speed trace after FP2 pattern calibration", loc="left",
                 fontsize=17, fontweight="bold", pad=16)
    ax.text(0, 1.015, "FP2 corner minima calibrated the simulation; FP1 is a visual cross-check.",
            transform=ax.transAxes, color="#506274", fontsize=10)

    err.axhline(0, color="#253647", lw=1)
    err.plot(x, original - fp2, color=colors["original"], lw=1.5, ls="--",
             label=f"Original vs FP2: MAE {mae_original:.1f} km/h, r {corr_original:.3f}")
    err.plot(x, matched - fp2, color=colors["matched"], lw=1.9,
             label=f"Matched vs FP2: MAE {mae_matched:.1f} km/h, r {corr_matched:.3f}")
    err.set_ylabel("Sim − FP2 (km/h)")
    err.set_xlabel("Lap distance (%)")
    err.set_xlim(0, 100)
    err.set_xticks(np.arange(0, 101, 10))
    err.legend(loc="upper right", frameon=True, facecolor="white", framealpha=0.95)
    fig.savefig(OUTPUT, dpi=170, facecolor=fig.get_facecolor())
    print(f"Saved {OUTPUT}")
    print(f"Original: MAE {mae_original:.2f} km/h, r {corr_original:.4f}")
    print(f"Matched:  MAE {mae_matched:.2f} km/h, r {corr_matched:.4f}")


if __name__ == "__main__":
    main()
