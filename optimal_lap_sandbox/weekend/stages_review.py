"""Review pictures before the video (user rule 2026-10-23): the user checks these, then approves.

  line.svg   whole track (both edges) + the racing line, corners numbered, distance marks every 250 m
  speed.svg  sim speed vs the reference lap (FP1 when it exists) + clip zones + time gap along the lap

The runner stops after this stage until `python -m weekend.approve <track> <year>` marks it approved;
the video is rendered only for an approved review (same key = same line and same lap).
"""
from __future__ import annotations

import json
import os

import numpy as np

from weekend import features as F
from weekend.pipeline import stage


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["svg.hashsalt"] = "weekend-review"     # stable element ids -> byte-identical reruns
    return plt


def _save(fig, path):
    fig.savefig(path, format="svg", metadata={"Date": None}, bbox_inches="tight")


def _report(up):
    with open(os.path.join(up["checks"], "report.json"), encoding="utf-8") as fh:
        return json.load(fh)


def _corners(up):
    return _report(up)["features"].get("corners", [])


def _lap(path):
    import pandas as pd
    return pd.read_csv(path)


def draw_line(out, outline, raceline, corners, title):
    plt = _plt()
    O, I = np.array(outline["outer"]), np.array(outline["inner"])
    R = np.array(raceline["raceline"])[:, :2]
    arc = np.array(raceline["arc_length"])
    fig, ax = plt.subplots(figsize=(16, 16))
    for E in (O, I):
        E = np.vstack([E, E[:1]])
        ax.plot(E[:, 0], E[:, 1], color="#444", lw=1.0)
    ax.plot(np.r_[R[:, 0], R[0, 0]], np.r_[R[:, 1], R[0, 1]], color="#d62728", lw=1.6, label="racing line")
    ax.plot(*R[0], "o", color="#2ca02c", ms=10, label="start / finish")
    k = max(1, len(R) // 200)
    ax.annotate("", xy=R[k], xytext=R[0], arrowprops=dict(arrowstyle="-|>", color="#2ca02c", lw=2))
    for m in range(250, int(arc[-1]), 250):                  # distance marks along the line
        i = int(np.argmin(np.abs(arc - m)))
        ax.plot(*R[i], ".", color="#1f77b4", ms=6)
        ax.annotate(f"{m}", R[i], textcoords="offset points", xytext=(6, -10), fontsize=8, color="#1f77b4")
    for c in corners:                                        # corner minima found by the checks
        i = int(np.argmin(np.abs(arc - c["s_m"])))
        ax.annotate(f"C{c['id']} {c['s_m']:.0f} m\nsim {c['sim']:.0f} / ref {c['ref']:.0f}", R[i],
                    textcoords="offset points", xytext=(10, 10), fontsize=9, fontweight="bold",
                    arrowprops=dict(arrowstyle="-", color="#888"))
    ax.set_aspect("equal"); ax.axis("off"); ax.legend(loc="upper left", bbox_to_anchor=(0, -0.02))
    ax.set_title(title)
    _save(fig, os.path.join(out, "line.svg")); plt.close(fig)


def draw_speed(out, sim, ref, corners, ref_name, title, segments=()):
    plt = _plt()
    L = float(sim.distance.iloc[-1])
    from weekend.shape_fit import warp                    # reference lined up corner to corner (as the checks)
    rd = warp(sim.distance.to_numpy(float), sim.speed, ref.distance.to_numpy(float), ref.speed)(ref.distance)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(22, 10), sharex=False, gridspec_kw=dict(height_ratios=[3, 1], hspace=0.35))
    a1.plot(rd, ref.speed, color="#1f77b4", lw=1.3, label=ref_name)
    a1.plot(sim.distance, sim.speed, color="#d62728", lw=1.3, label="sim")
    from weekend.shape_fit import clip_match                # sim side = its SUPERCLIP label, as the checks
    cm = clip_match(sim, ref, 60.0)
    zs = [(z["sim_m"][0], z["sim_m"][1], 0.0, z["sim_drop_kmh"]) for z in cm["zones"] if z["sim_m"]] + \
         [(z["sim_m"][0], z["sim_m"][1], 0.0, z["sim_drop_kmh"]) for z in cm["extra"]]
    zr = F.clip_zones(rd, ref.time_s, ref.speed, ref.throttle)
    for z in zr:
        a1.axvspan(z[0], z[1], ymin=0.92, ymax=1.0, color="#1f77b4", alpha=0.5)
    for z in zs:
        a1.axvspan(z[0], z[1], ymin=0.84, ymax=0.92, color="#d62728", alpha=0.5)
    if "mode" in sim:                                        # the sim's own SUPERCLIP label
        m = (sim["mode"] == "SUPERCLIP").to_numpy()
        a1.fill_between(sim.distance, 0, 1, where=m, transform=a1.get_xaxis_transform(), color="#ff7f0e", alpha=0.12,
                        label="sim label SUPERCLIP")
    for sg in segments:                                      # per-section shape check (user rule 2026-10-23)
        if not sg["ok"]:
            a1.axvspan(sg["start_m"], sg["end_m"], ymin=0.0, ymax=0.06, color="#d62728", alpha=0.35)
        a1.annotate(f"{sg['rmse_kmh']:.0f} km/h", ((sg["start_m"] + sg["end_m"]) / 2, 0.01),
                    xycoords=("data", "axes fraction"), ha="center", fontsize=8,
                    color="#d62728" if not sg["ok"] else "#2ca02c")
    for c in corners:
        a1.annotate(f"C{c['id']}", (c["s_m"], c["ref"]), textcoords="offset points", xytext=(0, -16),
                    ha="center", fontsize=9, fontweight="bold")
    a1.set_ylabel("speed km/h"); a1.grid(alpha=0.3); a1.set_xticks(np.arange(0, L, 250))
    a1.legend(loc="upper left", bbox_to_anchor=(0, -0.02), ncol=3,
              title=f"top bars: clip zones (speed falling at full throttle) - blue {ref_name}, red sim; "
                    f"bottom: per-section shape error vs FP1 x K (RMSE km/h), red = fails")
    g = np.linspace(0, L, 1000)
    dt = np.interp(g, sim.distance, sim.time_s) - np.interp(g, rd, ref.time_s)
    a2.plot(g, dt, color="#333"); a2.axhline(0, color="#999", lw=0.8)
    a2.set_ylabel(f"sim - {ref_name} (s)\n+ = sim behind"); a2.set_xlabel("distance (m)"); a2.grid(alpha=0.3)
    a2.set_xticks(np.arange(0, L, 250))
    a1.set_title(title)
    _save(fig, os.path.join(out, "speed.svg")); plt.close(fig)
    return [list(map(lambda x: round(x, 1), z)) for z in zr], [list(map(lambda x: round(x, 1), z)) for z in zs]


@stage("review", reads=["video.track_name", "ref.fp1_csv_file", "ref.q2025_csv_file"],
       needs=["track", "final", "refs", "checks"])
def review(p, out, up, weekend):
    with open(os.path.join(up["track"], "outline.json"), encoding="utf-8") as fh:
        outline = json.load(fh)
    with open(os.path.join(up["final"], "raceline.json"), encoding="utf-8") as fh:
        raceline = json.load(fh)
    rep = _report(up)
    corners = rep["features"].get("corners", [])
    sim = _lap(os.path.join(up["final"], "lap.csv"))
    fp1 = "ref.fp1_csv_file" in p
    ref = _lap(p.file("ref.fp1_csv_file") if fp1 else p.file("ref.q2025_csv_file"))
    ref_name = f"{weekend['year']} FP1" if fp1 else f"{weekend['year'] - 1} Q"
    title = f"{p['video.track_name']} {weekend['year']} - sim lap {sim.time_s.iloc[-1]:.3f} s"
    draw_line(out, outline, raceline, corners, title)
    zr, zs = draw_speed(out, sim, ref, corners, ref_name, title, rep.get("segments", []))
    return dict(line_svg="line.svg", speed_svg="speed.svg", ref=ref_name, clip_zones_ref=zr, clip_zones_sim=zs)
