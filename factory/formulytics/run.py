"""Run one weekend end to end.

    python -m formulytics.run --weekend sao_paulo_2026 [--approve] [--render]

Flow: agents plan/simulate/critique/package -> deterministic post-run (gates are the authority,
not the LLM) -> versioned manifest -> publish/ queue -> episodic memory -> post-hoc score vs the
golden dataset (real results are only read AFTER the agents are done).
"""
import argparse
import hashlib
import json
import subprocess
import time
import uuid

from . import config, gates, memory
from .llm import BudgetExceeded, CostTracker
from .tools import RunContext, fmt_lap


def _sha(path):
    try:
        return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]
    except OSError:
        return None


def _git_sha():
    try:
        return subprocess.run(["git", "-c", "safe.directory=*", "rev-parse", "--short", "HEAD"], cwd=config.REPO,
                              capture_output=True, text=True).stdout.strip()
    except OSError:
        return None


def post_hoc_score(ctx):
    g = json.loads((config.FACTORY / "evals" / "golden.json").read_text())
    row = next((r for r in g["rows"] if r["id"] == ctx.wid), None)
    sim = ctx.state.get("sim")
    if not row or not row.get("ref_s") or not sim:
        return None
    err = sim["lap_s"] - row["ref_s"]
    return {"real_ref_s": row["ref_s"], "ref_kind": row["ref_kind"], "sim_s": sim["lap_s"],
            "err_s": round(err, 3), "err_pct": round(100 * err / row["ref_s"], 2),
            "q_pole_s": (row["real"].get("q_pole") or {}).get("lap_s"), "q_wet": row["real"]["q_wet"]}


def run(weekend: str, approve: bool = False, render: bool = False, run_id: str | None = None) -> dict:
    from .agents import build_agent
    run_id = run_id or time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
    ctx = RunContext(weekend, config.RUNS / run_id, render=render)
    tracker = CostTracker(ledger=ctx.ledger)
    cp = None
    if approve:
        from langgraph.checkpoint.memory import InMemorySaver
        cp = InMemorySaver()
    agent = build_agent(ctx, tracker, approve=approve, checkpointer=cp)
    cfg = {"run_name": f"weekend:{weekend}", "tags": ["formulytics", weekend, "replay"],
           "metadata": {"run_id": run_id, "weekend": weekend}, "recursion_limit": 150,
           "configurable": {"thread_id": run_id}}
    t0 = time.time()
    ctx.ledger.log("run_start", weekend=weekend, approve=approve)
    final, error = None, None
    try:
        out = agent.invoke({"messages": [{"role": "user", "content": f"Produce this weekend's optimal-lap post for {weekend}."}]}, cfg)
        while approve and out.get("__interrupt__"):
            print("\n[approval] the agent wants to queue this post. Caption:\n", json.dumps(ctx.state.get("caption"), indent=1))
            ok = input("approve? [y/N] ").strip().lower() == "y"
            from langgraph.types import Command
            out = agent.invoke(Command(resume={"decisions": [{"type": "approve" if ok else "reject"}]}), cfg)
        final = out["messages"][-1].content
    except BudgetExceeded as ex:
        error = str(ex)
    except Exception as ex:  # noqa: BLE001 - record and fail closed
        error = f"{type(ex).__name__}: {ex}"
    wall = round(time.time() - t0, 1)

    # ---- deterministic post-run: gates are the authority ----
    ctx.facts()
    rep = gates.run_all(ctx.state)
    publishable = rep["all_pass"] and ctx.state.get("queued", False) and error is None
    sim = ctx.state.get("sim") or {}
    w = ctx.state["weekend"]
    manifest = {
        "run_id": run_id, "weekend": weekend, "format": "optimal_lap", "git_sha": _git_sha(),
        "models": config.ROUTES, "wall_s": wall, "cost": tracker.summary(), "error": error,
        "inputs": {k: {"path": w["sim"][k], "sha256_16": _sha(config.ENGINE_ROOT / w["sim"][k])}
                   for k in ("outline", "raceline_in", "reference_csv", "targets")},
        "car": sim.get("car"), "env_knobs": w["sim"]["env"],
        "sim_runs": [{"lap_s": s["lap_s"], "car": s["car"]} for s in ctx.state["sim_history"]],
        "result": {"lap_s": sim.get("lap_s"), "lap": fmt_lap(sim["lap_s"]) if sim else None,
                   "vmax_kmh": sim.get("vmax_kmh"), "vmin_kmh": sim.get("vmin_kmh")},
        "facts": ctx.state.get("facts"), "gates": rep, "caption": ctx.state.get("caption"), "queued_by_agent": ctx.state.get("queued", False),
        "published": publishable, "agent_summary": final,
    }
    manifest["post_hoc"] = post_hoc_score(ctx)
    (ctx.dir / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    if publishable:
        q = config.PUBLISH / run_id
        q.mkdir(parents=True, exist_ok=True)
        (q / "post.json").write_text(json.dumps({"weekend": weekend, "caption": ctx.state["caption"],
                                                 "lap": manifest["result"]["lap"], "manifest": f"runs/{run_id}/manifest.json"}, indent=1))
    memory.add_episode({"weekend": weekend, "run_id": run_id, "lap_s": sim.get("lap_s"),
                        "gates_pass": rep["all_pass"], "failures": rep["blocking_failures"],
                        "published": publishable, "usd": tracker.summary()["usd"], "post_hoc": manifest["post_hoc"],
                        "sim_reruns": max(0, len(ctx.state["sim_history"]) - 1)})
    ctx.ledger.log("run_end", published=publishable, wall_s=wall, usd=tracker.summary()["usd"])
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weekend", default="sao_paulo_2026")
    ap.add_argument("--approve", action="store_true", help="human taste approval before publish (interrupt)")
    ap.add_argument("--render", action="store_true")
    a = ap.parse_args()
    m = run(a.weekend, approve=a.approve, render=a.render)
    print(json.dumps({k: m[k] for k in ("run_id", "result", "published", "cost", "post_hoc", "error")}, indent=1, default=str))
    print("gates:", [(r["gate"], r["passed"]) for r in m["gates"]["results"]])
    print("summary:\n", m["agent_summary"])


if __name__ == "__main__":
    main()
