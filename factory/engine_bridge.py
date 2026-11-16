"""Engine bridge: a thin JSON CLI over the existing physics/delta/render scripts.

The engine (OPTIMAL LAP SCRIPTS/) runs on its own Python (3.10 + fastf1/scipy/etc.).
The agent harness (Python 3.11, deepagents) never imports it; it calls this file as a
subprocess and reads ONE JSON object from the last stdout line. That keeps the
deterministic toolkit isolated from the LLM layer and makes every tool call replayable.

    python engine_bridge.py <command> '<json args>'

Commands: targets, sim, gate, real_quali, speed_corr, delta, render
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ENGINE = Path(os.environ.get("ENGINE_ROOT", Path(__file__).resolve().parent.parent / "OPTIMAL LAP SCRIPTS"))
PY = sys.executable


def _weekend(wid):
    p = Path(__file__).resolve().parent / "weekends" / f"{wid}.json"
    return json.loads(p.read_text(encoding="utf-8"))


def _e(rel):
    return str(ENGINE / rel)


def _delta_engine():
    """Import the delta engine unchanged. The F1IH feed mixes timestamps with and without
    milliseconds ('2026-11-07 20:17:59'), which breaks pandas' inferred format inside
    get_trace_f1ih. Parse leniently in this process only; the engine file is not edited."""
    sys.path.insert(0, _e("LAP COMPARISON"))
    import pandas as pd
    import hifi_delta_v2 as hd
    if not getattr(pd.to_datetime, "_lenient", False):
        _orig = pd.to_datetime

        def lenient(arg, *a, **k):
            k.setdefault("format", "mixed")
            return _orig(arg, *a, **k)
        lenient._lenient = True
        hd.pd.to_datetime = lenient
    return hd


def _run(cmd, env_extra=None, timeout=1800):
    env = dict(os.environ)
    env.update(env_extra or {})
    r = subprocess.run(cmd, cwd=str(ENGINE), env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    return r.returncode, r.stdout + r.stderr


def cmd_targets(a):
    w = _weekend(a["weekend"])
    t = json.loads(Path(_e(w["sim"]["targets"])).read_text())
    return {"track": t["track"], "t2025_pole_s": t["t25_s"], "lap_band_s": t["lap_band_s"],
            "vtop_target_kmh": t["vtop_target_kmh"], "n_corners": len(t["corners"]),
            "corners": [{"s_m": c["s_m"], "v2025": c["v25_kmh"], "v2026_target": c["v26_target_kmh"]}
                        for c in t["corners"]],
            "method": "2025 Q reference x 2025->2026 transfer (LOO-backtested), no 2026 session data"}


def cmd_sim(a):
    w = _weekend(a["weekend"])
    s = w["sim"]
    car = dict(s["car"])
    car.update({k: a[k] for k in ("cda", "cl", "rho") if a.get(k) is not None})
    out = Path(a["out_dir"])
    out.mkdir(parents=True, exist_ok=True)
    csv_out, rl_out = out / "sim.csv", out / "raceline_sim_frame.json"
    cmd = [PY, _e("sim_2026_lap.py"), "--outline", _e(s["outline"]), "--raceline-out", str(rl_out),
           "--csv-out", str(csv_out), "--reference-csv", _e(s["reference_csv"]),
           "--rho", str(car["rho"]), "--cda", str(car["cda"]), "--cl", str(car["cl"])]
    if s.get("raceline_in"):
        cmd += ["--raceline-in", _e(s["raceline_in"])]
    code, log = _run(cmd, s.get("env"))
    (out / "sim.log").write_text(log, encoding="utf-8")
    m = re.search(r"\[sim\] lap: ([\d.]+)s \(bang-bang\) -> ([\d.]+)s", log)
    v = re.search(r"v=\[(\d+),(\d+)\] km/h", log)
    if code >= 2 or not m:
        return {"ok": False, "error": "sim failed", "log_tail": log[-1500:]}
    res = {"ok": True, "lap_s": float(m.group(2)), "lap_bangbang_s": float(m.group(1)),
           "vmin_kmh": int(v.group(1)) if v else None, "vmax_kmh": int(v.group(2)) if v else None,
           "car": car, "env_knobs": s.get("env", {}), "csv": str(csv_out), "raceline_sim_frame": str(rl_out)}
    if s.get("mirrored"):
        rl_real = out / "raceline.json"
        c2, l2 = _run([PY, _e("cache/_singapore_prep.py"), "unmirror", str(rl_out), str(rl_real)])
        res["raceline"] = str(rl_real) if c2 == 0 else None
    else:
        res["raceline"] = str(rl_out)
    return res


def cmd_gate(a):
    w = _weekend(a["weekend"])
    t = json.loads(Path(_e(w["sim"]["targets"])).read_text())
    code, log = _run([PY, _e("cache/_gate_2026.py"), a["csv"], str(t["t25_s"]), "--targets", _e(w["sim"]["targets"])])
    checks = [{"pass": g == "PASS", "check": d.strip()} for g, d in re.findall(r"\[(PASS|FAIL)\] (.+)", log)]
    return {"all_pass": code == 0 and checks and all(c["pass"] for c in checks), "checks": checks,
            "source": "cache/_gate_2026.py (2026 realism gate)"}


def cmd_real_quali(a):
    """Real qualifying result + pole speed trace (F1IH car data + OpenF1 laps)."""
    hd = _delta_engine()
    year, gp = a["year"], a["gp"]
    order = hd.f1ih_classification(year, gp, "Qualifying")
    pole = order[0]
    tr = hd.get_trace_f1ih(year, gp, "Qualifying", pole)
    out = Path(a["out_dir"])
    out.mkdir(parents=True, exist_ok=True)
    p = out / "real_pole_trace.csv"
    with open(p, "w", encoding="utf-8") as f:
        f.write("distance,speed\n")
        for c in tr["car"]:
            f.write(f"{c['distance']},{c['speed']}\n")
    return {"event": tr["event"], "pole_driver": pole, "pole_full_name": tr["full_name"],
            "pole_lap_s": tr["lap_time"], "top3": order[:3], "trace_csv": str(p),
            "source": "OpenF1 session_result/laps + backend.f1insightshub.com car_data"}


def cmd_speed_corr(a):
    import numpy as np
    import pandas as pd
    sim = pd.read_csv(a["sim_csv"])
    real = pd.read_csv(a["real_csv"]).dropna()
    real = real[real["distance"].diff().fillna(1) > 0]
    xs = np.linspace(0, 1, 1000)
    vs = np.interp(xs, sim["distance"] / sim["distance"].max(), sim["speed"])
    vr = np.interp(xs, real["distance"] / real["distance"].max(), real["speed"])
    return {"speed_corr": round(float(np.corrcoef(vs, vr)[0, 1]), 4),
            "top_speed_err_kmh": round(float(vs.max() - vr.max()), 1),
            "mean_abs_err_kmh": round(float(np.mean(np.abs(vs - vr))), 2),
            "note": "distance-normalised, 1000 samples; real trace is map-matched public feed"}


def cmd_delta(a):
    import numpy as np
    hd = _delta_engine()
    ref = hd.get_trace_f1ih(a["year"], a["gp"], a.get("session", "Qualifying"), a["ref"])
    tgt = hd.get_trace_f1ih(a["year"], a["gp"], a.get("session", "Qualifying"), a["tgt"])
    dist, delta = hd.calculate_delta(ref, tgt)
    ok = ~np.isnan(delta)
    i = int(np.nanargmax(np.abs(delta)))
    return {"ref": ref["driver"], "tgt": tgt["driver"], "ref_lap_s": ref["lap_time"], "tgt_lap_s": tgt["lap_time"],
            "final_delta_s": round(float(delta[ok][-1]), 3), "max_abs_delta_s": round(float(delta[i]), 3),
            "max_at_m": round(float(dist[i]), 0), "engine": "LAP COMPARISON/hifi_delta_v2.py"}


def cmd_render(a):
    w = _weekend(a["weekend"])
    r = w["render"]
    cmd = [PY, _e("raceline_video.py"), "--outline", _e(w["sim"]["outline_video"]), "--raceline", a["raceline"],
           "--telemetry-csv", a["csv"], "--track-name", w["track_name"], "--zoom", str(a.get("zoom", r["zoom"])),
           "--elevation-json", _e(w["sim"]["elevation_json"]), "--display-laptime", str(a["label_s"]),
           "--tagline", a.get("tagline", r.get("tagline", "")), "--out", a["out"]]
    code, log = _run(cmd, timeout=7200)
    return {"ok": code == 0 and Path(a["out"]).exists(), "out": a["out"], "log_tail": log[-600:]}


if __name__ == "__main__":
    fn = globals()["cmd_" + sys.argv[1]]
    args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    try:
        print(json.dumps(fn(args)))
    except Exception as ex:  # noqa: BLE001 - surface every engine failure as data, fail closed upstream
        print(json.dumps({"ok": False, "error": f"{type(ex).__name__}: {ex}"}))
