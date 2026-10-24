"""Racing line on the user's Austin SVG only (no GPS): SVG -> 5513 m, 15 m wide (map stroke) -> mirror
(anticlockwise) -> the sim's own physics line (build_raceline) -> line.svg."""
import contextlib, io, json, os, sys, time
import numpy as np
sys.path.insert(0, os.getcwd())
import svg_to_outline as SO
from weekend import pipeline as PL, simdoor


def main():
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    svg = "runs/austin_2026/track/Austin_Formula_One_circuit (1).svg"
    t0 = time.time()
    with contextlib.redirect_stdout(io.StringIO()):
        O, I = SO.build_outline_from_svg(svg, 5513.0, 15.0, 10.0)
    O, I = np.asarray(O, float), np.asarray(I, float)
    json.dump(dict(outer=O.tolist(), inner=I.tolist()), open(os.path.join(out, "outline.json"), "w"))
    m = np.array([-1.0, 1.0])
    json.dump(dict(outer=(O * m).tolist(), inner=(I * m).tolist()), open(os.path.join(out, "sim_outline.json"), "w"))
    pack = json.load(open("weekend/packs/austin_2026.json", encoding="utf-8"))
    vals = PL.P(pack["values"]).sim_vals()
    sim = simdoor.configure(vals)
    with contextlib.redirect_stdout(io.StringIO()):
        rl, arc, kappa, L = sim.build_raceline(O * m, I * m, inset_m=0.0)
    rl = np.asarray(rl, float)[:, :2]
    json.dump(dict(raceline=(rl * m).tolist(), track_length_m=float(L)), open(os.path.join(out, "raceline.json"), "w"))
    print(f"line built in {time.time() - t0:.0f}s, length {L:.0f} m")
    R = rl * m
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(16, 16))
    for E in (O, I):
        E = np.vstack([E, E[:1]]); ax.plot(E[:, 0], E[:, 1], color="#444", lw=1.0)
    ax.plot(np.r_[R[:, 0], R[0, 0]], np.r_[R[:, 1], R[0, 1]], color="#d62728", lw=1.6, label="racing line (sim physics, on your SVG)")
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(R, axis=0), axis=1))]
    for mm in range(250, int(s[-1]), 250):
        i = int(np.argmin(np.abs(s - mm))); ax.plot(*R[i], ".", color="#1f77b4", ms=6)
        ax.annotate(str(mm), R[i], textcoords="offset points", xytext=(6, -10), fontsize=8, color="#1f77b4")
    ax.plot(*R[0], "o", color="#2ca02c", ms=10, label="line start")
    ax.set_aspect("equal"); ax.axis("off"); ax.legend(loc="upper left")
    fig.savefig(os.path.join(out, "line.svg"), format="svg", metadata={"Date": None}, bbox_inches="tight")
    fig.savefig(os.path.join(out, "line.png"), dpi=60, bbox_inches="tight")


if __name__ == "__main__":
    main()
