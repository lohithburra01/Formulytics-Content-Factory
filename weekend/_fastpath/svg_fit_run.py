"""Speed fit (shape_fit, unchanged method) -> final -> checks -> review on the SVG-only physics line."""
import json, os, shutil, sys, time
import numpy as np
sys.path.insert(0, os.getcwd())
import weekend.stages  # noqa: F401
from weekend import pipeline as PL, simdoor, line as LN
from weekend.stages import write_raceline, _line_prm


def run(name, out, up, pack):
    st = PL.STAGES[name]
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    res = st.fn(PL.P(PL.selected(pack["values"], st.reads)), out, up, pack["weekend"]) or {}
    json.dump(res, open(os.path.join(out, "done.json"), "w"), indent=1, sort_keys=True, default=float)
    print(f"{name} done in {time.time() - t0:.0f}s", flush=True)
    return res


def main():
    base = "runs/austin_2026/svg_line"
    pack = json.load(open("weekend/packs/austin_2026.json", encoding="utf-8"))
    P = PL.P(pack["values"])
    chk = json.load(open("runs/austin_2026/checks/95e250a604b7077e/inputs.json"))["up"]
    # track dir: SVG outline (real + sim frame), mirrored like Singapore
    json.dump(dict(mirror_x=True, source="user SVG only"), open(os.path.join(base, "done.json"), "w"))
    # base line dir: the physics line on the SVG, S/F rolled, sim frame
    bl = os.path.join(base, "base_line"); os.makedirs(bl, exist_ok=True)
    rl = np.array(json.load(open(os.path.join(base, "raceline_sf.json")))["raceline"]) * np.array([-1.0, 1.0])
    sim = simdoor.configure(P.sim_vals())
    arc, kappa, L = sim._arc_kappa_closed(rl)
    write_raceline(os.path.join(bl, "raceline.json"), rl, arc, kappa, L)
    # time_knob dir: the tuned car + zero knots (line = the physics line itself)
    tk = os.path.join(base, "time_knob"); os.makedirs(tk, exist_ok=True)
    shutil.copyfile(os.path.join(chk["time_knob"], "car.json"), os.path.join(tk, "car.json"))
    d = json.load(open(os.path.join(chk["time_knob"], "done.json"))); d["rules"] = None
    json.dump(d, open(os.path.join(tk, "done.json"), "w"), indent=1, default=float)
    K = LN.setup(os.path.join(bl, "raceline.json"), os.path.join(base, "sim_outline.json"), _line_prm(P))
    np.save(os.path.join(tk, "knots.npy"), np.zeros(K))
    up = dict(track=base, base_line=bl, refs=chk["refs"], time_knob=tk)
    sf = run("shape_fit", os.path.join(base, "shape_fit"), up, pack)
    print("shape_fit lap", sf.get("lap_s"), "k", sf.get("k"), "failing", sum(not x["ok"] for x in sf.get("sections", [])), flush=True)
    run("final", os.path.join(base, "final"), dict(track=base, base_line=bl, shape_fit=os.path.join(base, "shape_fit")), pack)
    cl = os.path.join(base, "car_and_line"); os.makedirs(cl, exist_ok=True)
    d = json.load(open(os.path.join(chk["car_and_line"], "done.json"))); d["rules"] = []
    json.dump(d, open(os.path.join(cl, "done.json"), "w"), indent=1, default=float)
    c = run("checks", os.path.join(base, "checks"), dict(refs=chk["refs"], final=os.path.join(base, "final"), car_and_line=cl,
                                                         time_knob=tk, shape_fit=os.path.join(base, "shape_fit")), pack)
    print(json.dumps({k: c[k] for k in ("lap_s", "lap_in_band", "clips_ok", "gate_ok", "corners_flagged")}, default=float))
    print("sections failing", c["segments_bad"])
    run("review", os.path.join(base, "review"), dict(track=base, final=os.path.join(base, "final"), refs=chk["refs"],
                                                     checks=os.path.join(base, "checks")), pack)


if __name__ == "__main__":
    main()
