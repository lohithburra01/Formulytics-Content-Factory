"""Eval suite. Writes evals/results.json and evals/report.html.

    python evals/run_evals.py [--no-llm] [--langsmith]

1. scoreboard   : shipped predictions vs real laps (golden.json, OpenF1), like-for-like conditions
2. regression   : re-run every weekend spec through the engine; must reproduce the shipped lap
                  (|d| <= 0.005 s) and pass the realism gate - the CI regression check
3. memory recall: questions whose answers must come out of the semantic graph
4. retrieval    : RAG hit@4 on labelled queries + off-topic queries must be withheld
5. caption judge: LLM-as-judge (V4 Pro) scores each run's caption on a rubric
"""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from formulytics import config, engine, gates, memory  # noqa: E402

EVALS = Path(__file__).resolve().parent


def scoreboard():
    g = json.loads((EVALS / "golden.json").read_text())["rows"]
    rows = [r for r in g if r.get("ref_s")]
    pre = [r for r in rows if r["stage"].startswith("pre-FP1")]
    current = [r for r in rows if r["id"] in ("mexico_2026", "sao_paulo_2026")]  # measured-superclip method
    mae = lambda rs: round(statistics.mean(abs(r["err_s"]) for r in rs), 3) if rs else None  # noqa: E731
    return {"rows": [{k: r.get(k) for k in ("id", "stage", "sim_s", "ref_s", "ref_kind", "err_s", "err_pct")} for r in g],
            "mae_s_all": mae(rows), "mae_s_pre_fp1": mae(pre), "mae_s_current_method": mae(current),
            "n_scored": len(rows), "n_unscorable": len(g) - len(rows)}


def regression(tmp: Path):
    out = []
    for p in sorted(config.WEEKENDS.glob("*.json")):
        w = json.loads(p.read_text(encoding="utf-8"))
        s = engine.call("sim", weekend=w["id"], out_dir=str(tmp / w["id"]))
        g = engine.call("gate", weekend=w["id"], csv=s["csv"]) if s.get("ok") else {"all_pass": False}
        d = round(s["lap_s"] - w["shipped"]["sim_s"], 4) if s.get("ok") else None
        out.append({"weekend": w["id"], "shipped_s": w["shipped"]["sim_s"], "rerun_s": s.get("lap_s"),
                    "delta_s": d, "gate_pass": g["all_pass"],
                    "pass": d is not None and abs(d) <= 0.005 and g["all_pass"]})
    return {"cases": out, "pass": all(c["pass"] for c in out)}


MEMORY_QA = [  # (query, path to a node attr, expected)
    ("mexico", ("result:mexico_2026", "err_s"), 0.244),
    ("sao_paulo", ("result:sao_paulo_2026", "q_wet"), True),
    ("sao_paulo", ("setup:sao_paulo_2026", "cda"), 0.643),
    ("spa", ("weekend:spa_2026", "sim_s"), 101.91),
    ("bahrain", ("note:bahrain_2026", "text"), "no real 2026 session in OpenF1 (event cancelled or not held)"),
    ("sepang", ("result:sepang_2026", "ref_kind"), "qualifying pole (dry)"),
]


def memory_recall():
    memory.build_graph()
    res = []
    for q, (nid, attr), want in MEMORY_QA:
        got = next((n.get(attr) for n in memory.recall(q)["nodes"] if n["id"] == nid), None)
        res.append({"query": q, "fact": f"{nid}.{attr}", "want": want, "got": got, "pass": got == want})
    return {"cases": res, "accuracy": round(sum(r["pass"] for r in res) / len(res), 3)}


RETRIEVAL = [
    ("why are 2026 cars slower than 2025 and what knobs are calibrated per track", "prefp1-universal-calibration-design"),
    ("Singapore street grip factor measured on the 2025 car", "singapore_2026"),
    ("Sepang has no 2025 reference lap, how was it predicted", "sepang_2026_noref"),
    ("leave-one-out backtest results for canada catalunya austria silverstone", "backtest_report"),
    ("Monaco physics engine design", "monaco-2026-physics-engine"),
    ("the line must touch the apexes rule", "feedback_rules"),
]
OFF_TOPIC = ["best pizza recipe", "stock market forecast for next year", "who won the 2010 world cup"]


def retrieval():
    from formulytics import rag
    res = []
    for q, want in RETRIEVAL:
        r = rag.search(q, k=4)
        srcs = [p["source"] for p in r["passages"]]
        res.append({"query": q, "want": want, "hit": any(want in s for s in srcs), "top": srcs[:2]})
    off = [{"query": q, "withheld": not rag.search(q)["passages"]} for q in OFF_TOPIC]
    return {"cases": res, "hit_at_4": round(sum(r["hit"] for r in res) / len(res), 3),
            "off_topic": off, "off_topic_withheld_rate": round(sum(o["withheld"] for o in off) / len(off), 3)}


JUDGE_PROMPT = """You are judging a social-media caption for an F1 engineering page (about 50K followers).
Facts the caption may use (verified; *_s values are seconds, 70.772 s = 1:10.772): {facts}
Caption hook: {hook}
Caption text: {text}
Tags: {tags}

Score 1-5 each, strictly:
- hook: would this first line stop a motorsport fan scrolling? (5 = specific, surprising, concrete)
- accuracy: is every claim consistent with the facts? Any invented claim gives 1.
- clarity: understandable to a casual fan in one read.
- compliance: no inflated or unsupported numbers; numbers formatted as lap times where relevant.
Reply ONLY with JSON: {{"hook":n,"accuracy":n,"clarity":n,"compliance":n,"why":"<one sentence>"}}"""


def _rebuild_facts(man):
    """Older manifests did not store the facts dict: rebuild it from the result + the track targets."""
    t = engine.call("targets", weekend=man["weekend"])
    lap = man["result"]["lap_s"]
    return {"sim_lap_s": lap, "vmax_kmh": man["result"]["vmax_kmh"], "vmin_kmh": man["result"]["vmin_kmh"],
            "t2025_pole_s (real 2025 pole)": t["t2025_pole_s"], "band_lo_s": t["lap_band_s"][0],
            "band_hi_s": t["lap_band_s"][1], "slower_than_2025_s": round(lap - t["t2025_pole_s"], 3)}


def caption_judge():
    from formulytics.llm import CostTracker, make_model
    tracker = CostTracker()
    judge = make_model("judge", tracker, temperature=0)
    out = []
    for m in sorted(config.RUNS.glob("*/manifest.json")):
        man = json.loads(m.read_text())
        cap = man.get("caption")
        if not cap:
            continue
        facts = man["gates"]["results"]
        f = man.get("facts") or _rebuild_facts(man)
        msg = judge.invoke(JUDGE_PROMPT.format(facts=json.dumps(f), hook=cap["hook"], text=cap["text"], tags=cap["tags"]))
        txt = msg.content.strip().strip("`").removeprefix("json").strip()
        try:
            sc = json.loads(txt[txt.index("{"): txt.rindex("}") + 1])
        except ValueError:
            sc = {"error": txt[:200]}
        claims = next(r for r in facts if r["gate"] == "claims_supported")
        out.append({"run_id": man["run_id"], "hook": cap["hook"], "scores": sc, "claims_gate": claims["passed"]})
    keys = ("hook", "accuracy", "clarity", "compliance")
    mean = {k: round(statistics.mean(o["scores"][k] for o in out if k in o["scores"]), 2)
            for k in keys if any(k in o["scores"] for o in out)}
    return {"cases": out, "mean": mean, "judge_model": config.ROUTES["judge"][0], "judge_cost": tracker.summary()}


def runs_summary():
    ms = [json.loads(m.read_text()) for m in sorted(config.RUNS.glob("*/manifest.json"))]
    if not ms:
        return {}
    gp = [r["passed"] for m in ms for r in m["gates"]["results"]]
    return {"runs": len(ms), "published": sum(m["published"] for m in ms),
            "gate_pass_rate": round(sum(gp) / len(gp), 3),
            "mean_usd": round(statistics.mean(m["cost"]["usd"] for m in ms), 4),
            "mean_wall_s": round(statistics.mean(m["wall_s"] for m in ms), 1)}


def to_langsmith(sb):
    """Golden set -> LangSmith dataset + experiment (lap-time error evaluator)."""
    from langsmith import Client, evaluate
    c = Client()
    name = "formulytics-golden-2026"
    ds = c.read_dataset(dataset_name=name) if c.has_dataset(dataset_name=name) else c.create_dataset(name)
    if not list(c.list_examples(dataset_id=ds.id, limit=1)):
        rows = [r for r in sb["rows"] if r.get("ref_s")]
        c.create_examples(dataset_id=ds.id, inputs=[{"weekend": r["id"], "stage": r["stage"]} for r in rows],
                          outputs=[{"real_s": r["ref_s"], "ref_kind": r["ref_kind"]} for r in rows])
    shipped = {r["id"]: r["sim_s"] for r in sb["rows"]}

    def target(inputs):
        return {"sim_s": shipped[inputs["weekend"]]}

    def lap_err(outputs, reference_outputs):
        e = abs(outputs["sim_s"] - reference_outputs["real_s"])
        return {"key": "abs_err_s", "score": round(e, 3)}

    def within_half_second(outputs, reference_outputs):
        return {"key": "within_0.5s", "score": int(abs(outputs["sim_s"] - reference_outputs["real_s"]) <= 0.5)}

    r = evaluate(target, data=name, evaluators=[lap_err, within_half_second], experiment_prefix="shipped-predictions")
    return {"dataset": name, "experiment": r.experiment_name}


def html(res):
    sb = res["scoreboard"]

    def tr(cells):
        return "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"
    rows = "".join(tr([r["id"], r["stage"], r["sim_s"], r.get("ref_s") or "n/a", r.get("ref_kind") or "",
                       "" if r.get("err_s") is None else f"{r['err_s']:+.3f}"]) for r in sb["rows"])
    reg = "".join(tr([c["weekend"], c["shipped_s"], c["rerun_s"], c["delta_s"], "PASS" if c["pass"] else "FAIL"])
                  for c in res["regression"]["cases"])
    mem = "".join(tr([c["fact"], c["want"], c["got"], "PASS" if c["pass"] else "FAIL"]) for c in res["memory_recall"]["cases"])
    ret = "".join(tr([c["query"], c["want"], "hit" if c["hit"] else "miss"]) for c in res["retrieval"]["cases"])
    cj = res.get("caption_judge", {})
    cap = "".join(tr([c["run_id"], c["hook"], json.dumps(c["scores"]), c["claims_gate"]]) for c in cj.get("cases", []))
    return f"""<!doctype html><meta charset=utf-8><title>Formulytics eval report</title>
<style>body{{font:14px system-ui;margin:24px;max-width:1100px;background:#fff;color:#111}}table{{border-collapse:collapse;width:100%;margin:8px 0 24px}}
td{{border-bottom:1px solid #ddd;padding:4px 8px}}h2{{margin-top:28px}}code{{background:#f3f3f3;padding:1px 4px}}</style>
<h1>Formulytics content factory: eval report</h1><p>Generated {res['generated']}. Source: <code>factory/evals/run_evals.py</code></p>
<h2>1. Predictions vs reality (golden set)</h2><p>MAE all {sb['mae_s_all']} s, pre-FP1 {sb['mae_s_pre_fp1']} s,
current method (Mexico onward) {sb['mae_s_current_method']} s. Scored {sb['n_scored']}, unscorable {sb['n_unscorable']}.</p>
<table><tr><th>weekend<th>stage<th>sim s<th>real s<th>reference<th>err s</tr>{rows}</table>
<h2>2. Regression (engine replay)</h2><table><tr><th>weekend<th>shipped<th>re-run<th>delta<th>verdict</tr>{reg}</table>
<h2>3. Memory recall</h2><p>accuracy {res['memory_recall']['accuracy']}</p><table><tr><th>fact<th>want<th>got<th></tr>{mem}</table>
<h2>4. Retrieval</h2><p>hit@4 {res['retrieval']['hit_at_4']}, off-topic withheld {res['retrieval']['off_topic_withheld_rate']}</p>
<table><tr><th>query<th>expected source<th></tr>{ret}</table>
<h2>5. Caption judge ({cj.get('judge_model', 'not run')})</h2><p>mean {cj.get('mean')}</p>
<table><tr><th>run<th>hook<th>scores<th>claims gate</tr>{cap}</table>
<h2>Runs</h2><pre>{json.dumps(res.get('runs'), indent=1)}</pre>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--langsmith", action="store_true")
    ap.add_argument("--only", default=None, help="regression (CI)")
    a = ap.parse_args()
    tmp = config.RUNS / "_eval_tmp"
    if a.only == "regression":
        r = regression(tmp)
        print(json.dumps(r, indent=1))
        sys.exit(0 if r["pass"] else 1)
    res = {"generated": time.strftime("%Y-%m-%d %H:%M"), "scoreboard": scoreboard(), "regression": regression(tmp),
           "memory_recall": memory_recall(), "retrieval": retrieval(), "runs": runs_summary()}
    if not a.no_llm:
        res["caption_judge"] = caption_judge()
    if a.langsmith:
        res["langsmith"] = to_langsmith(res["scoreboard"])
    (EVALS / "results.json").write_text(json.dumps(res, indent=1, default=str))
    (EVALS / "report.html").write_text(html(res), encoding="utf-8")
    print(json.dumps({k: (v if k in ("runs", "langsmith") else {kk: vv for kk, vv in v.items() if kk not in ("rows", "cases")})
                      for k, v in res.items() if k != "generated"}, indent=1, default=str))


if __name__ == "__main__":
    main()
