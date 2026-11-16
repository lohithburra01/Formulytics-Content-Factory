"""Agent tools. Each one wraps a deterministic engine call or a store, logs to the audit
ledger, and writes into the run state the gates read. Tools are grouped by the sub-agent
that may use them (least privilege): the researcher cannot simulate, the simulator cannot
publish, nobody but the packager writes captions."""
import json
import time
from pathlib import Path

from langchain_core.tools import tool

from . import engine, gates, memory, rag
from .ledger import Ledger

CAR_BOUNDS = {"cda": (0.55, 0.90), "cl": (3.8, 5.6), "rho": (0.95, 1.25)}


def fmt_lap(s: float) -> str:
    m, r = divmod(s, 60)
    return f"{int(m)}:{r:06.3f}"


class RunContext:
    def __init__(self, weekend_id: str, run_dir: Path, render: bool = False):
        self.wid, self.dir, self.render = weekend_id, Path(run_dir), render
        self.dir.mkdir(parents=True, exist_ok=True)
        self.ledger = Ledger(self.dir / "ledger.jsonl")
        self.state = {"weekend": engine.weekend(weekend_id), "sim_history": []}

    def facts(self) -> dict:
        """The only numbers a caption may use (gate R7)."""
        s, t = self.state.get("sim"), self.state.get("targets")
        f = {}
        if s:
            f.update(sim_lap_s=s["lap_s"], vmax_kmh=s["vmax_kmh"], vmin_kmh=s["vmin_kmh"])
        if t:
            f.update(t2025_pole_s=t["t2025_pole_s"], band_lo_s=t["lap_band_s"][0], band_hi_s=t["lap_band_s"][1])
        if s and t:
            f["slower_than_2025_s"] = round(s["lap_s"] - t["t2025_pole_s"], 3)
        self.state["facts"] = f
        return f

    def _call(self, name, fn, **args):
        t0 = time.time()
        out = fn(**args)
        self.ledger.log("tool", tool=name, args=args, latency_s=round(time.time() - t0, 2),
                        result=out if len(json.dumps(out, default=str)) < 4000 else "<large>")
        return out


def build_tools(ctx: RunContext) -> dict:
    W = ctx.wid

    # ---------------- researcher ----------------
    @tool
    def get_weekend_toolkit() -> str:
        """The format toolkit configured for this weekend: track geometry source, direction,
        car setup knobs, render rules and the formats this track supports."""
        w = ctx.state["weekend"]
        return json.dumps({k: w[k] for k in ("id", "track_name", "direction", "formats", "sim", "render")})

    @tool
    def get_predicted_targets() -> str:
        """Pre-FP1 targets for this track: 2025 pole, predicted 2026 lap band, top speed and corner
        minimum speeds (2025 Q reference x leave-one-out-backtested 2025->2026 transfer)."""
        t = ctx._call("get_predicted_targets", engine.call, command="targets", weekend=W)
        ctx.state["targets"] = t
        return json.dumps(t)

    @tool
    def recall_track_memory(query: str) -> str:
        """Semantic memory: what the factory knows about a track/method from past weekends
        (setups, how earlier predictions scored against real qualifying). query e.g. 'mexico'."""
        return json.dumps(ctx._call("recall_track_memory", memory.recall, query=query))[:6000]

    @tool
    def past_runs() -> str:
        """Episodic memory: the last runs of this weekend (gate failures, re-runs, cost)."""
        # Replay must not leak real results: post-hoc scores vs reality are withheld from agents.
        return json.dumps([{k: v for k, v in e.items() if k != "post_hoc"} for e in memory.episodes(W)])

    @tool
    def search_knowledge(query: str) -> str:
        """Search the factory's research notes, calibration logs and regulations; returns passages
        with their source file so claims can be cited."""
        return json.dumps(ctx._call("search_knowledge", rag.search, query=query, k=4))

    # ---------------- simulator ----------------
    @tool
    def run_simulation(cda: float | None = None, cl: float | None = None, rho: float | None = None) -> str:
        """Run the 2026 lap simulation on the weekend's reviewed line. Leave knobs empty to use the
        calibrated setup; overrides must stay inside physical bounds (cda 0.55-0.90, cl 3.8-5.6,
        rho 0.95-1.25). Returns lap time, speed range and artifact paths."""
        for k, v in (("cda", cda), ("cl", cl), ("rho", rho)):
            if v is not None and not CAR_BOUNDS[k][0] <= v <= CAR_BOUNDS[k][1]:
                return json.dumps({"ok": False, "error": f"{k}={v} outside physical bounds {CAR_BOUNDS[k]}"})
        n = len(ctx.state["sim_history"])
        out = ctx._call("run_simulation", engine.call, command="sim", weekend=W, cda=cda, cl=cl, rho=rho,
                        out_dir=str(ctx.dir / f"sim_{n}"))
        if out.get("ok"):
            ctx.state["sim"] = out
            ctx.state["sim_history"].append(out)
            ctx.state.pop("gate", None)
            ctx.state.pop("trace_check", None)
        return json.dumps({k: v for k, v in out.items() if k not in ("env_knobs",)})

    @tool
    def run_realism_gate() -> str:
        """Run the engine's 2026 realism gate on the latest simulation (lap rail, predicted band,
        top speed, corner minima, acceleration/braking rates, superclip shape)."""
        if "sim" not in ctx.state:
            return json.dumps({"ok": False, "error": "run_simulation first"})
        g = ctx._call("run_realism_gate", engine.call, command="gate", weekend=W, csv=ctx.state["sim"]["csv"])
        ctx.state["gate"] = g
        return json.dumps(g)

    @tool
    def check_speed_trace() -> str:
        """Compare the simulated speed trace with the real reference trace (2025 qualifying pole
        for this track, distance-normalised)."""
        if "sim" not in ctx.state:
            return json.dumps({"ok": False, "error": "run_simulation first"})
        ref = str(engine.config.ENGINE_ROOT / ctx.state["weekend"]["sim"]["reference_csv"])
        c = ctx._call("check_speed_trace", engine.call, command="speed_corr", sim_csv=ctx.state["sim"]["csv"], real_csv=ref)
        c["reference"] = "real 2025 Q pole trace"
        ctx.state["trace_check"] = c
        return json.dumps(c)

    @tool
    def check_apexes() -> str:
        """Measure how close the line comes to the inside edge at every apex (gate R3)."""
        r = gates.gate_apex_touch(ctx.state)
        ctx.ledger.log("gate", **r.__dict__)
        return json.dumps({"passed": r.passed, "detail": r.detail, "apexes": r.evidence.get("apexes")})

    # ---------------- critic ----------------
    @tool
    def run_all_gates() -> str:
        """Run every procedural-memory gate (feedback rules R1-R8) on the current run state.
        Blocking failures prevent publishing."""
        ctx.facts()
        rep = gates.run_all(ctx.state)
        ctx.state["gates_report"] = rep
        ctx.ledger.log("gates", all_pass=rep["all_pass"], failures=rep["blocking_failures"])
        return json.dumps({"all_pass": rep["all_pass"], "blocking_failures": rep["blocking_failures"],
                           "results": [{k: r[k] for k in ("gate", "rule", "passed", "detail")} for r in rep["results"]]})

    # ---------------- packager ----------------
    @tool
    def get_verified_facts() -> str:
        """The verified numbers from this run (the ONLY numbers a caption may contain) plus
        ready-formatted lap times."""
        f = ctx.facts()
        pretty = {k: fmt_lap(v) for k, v in f.items() if k.endswith("_s") and v > 60}
        meaning = {"sim_lap_s": "our simulated optimal 2026 lap (pre-FP1)",
                   "t2025_pole_s": "the REAL 2025 qualifying pole at this track (last year, not this weekend)",
                   "slower_than_2025_s": "how much slower our 2026 lap is than the 2025 pole",
                   "band_lo_s": "fastest end of the predicted 2026 lap band", "band_hi_s": "slowest end of the band",
                   "vmax_kmh": "simulated top speed", "vmin_kmh": "simulated slowest corner speed"}
        return json.dumps({"facts": f, "meaning": meaning, "formatted": pretty,
                           "track": ctx.state["weekend"]["track_name"], "year": ctx.state["weekend"]["year"],
                           "rule": "every number in the caption must be one of these; nothing else (no corner counts, "
                                   "no years other than this season and last)"})

    @tool
    def write_caption(hook: str, text: str, tags: list[str]) -> str:
        """Write the post caption. hook = first line (scroll-stopper), text = full caption,
        tags = hashtags. Numbers must come from get_verified_facts; the claims gate checks this
        immediately and tells you which numbers are unsupported."""
        ctx.facts()
        ctx.state["caption"] = {"hook": hook, "text": text, "tags": tags}
        ctx.state["label_s"] = ctx.state["sim"]["lap_s"] if "sim" in ctx.state else None
        r = gates.gate_claims_supported(ctx.state)
        ctx.ledger.log("caption", hook=hook, claims_ok=r.passed, detail=r.detail)
        return json.dumps({"claims_gate": r.passed, "detail": r.detail})

    @tool
    def queue_for_publish() -> str:
        """Put the approved output in the publish/ queue (caption + manifest). Refused unless every
        blocking gate passes. Distribution happens outside this repo."""
        ctx.facts()
        rep = gates.run_all(ctx.state)
        ctx.state["gates_report"] = rep
        if not rep["all_pass"]:
            ctx.ledger.log("publish_refused", failures=rep["blocking_failures"])
            return json.dumps({"queued": False, "blocking_failures": rep["blocking_failures"]})
        ctx.state["queued"] = True
        ctx.ledger.log("publish_queued")
        return json.dumps({"queued": True})

    groups = {
        "researcher": [get_weekend_toolkit, get_predicted_targets, recall_track_memory, past_runs, search_knowledge],
        "simulator": [run_simulation, run_realism_gate, check_speed_trace, check_apexes],
        "critic": [run_all_gates, get_verified_facts, recall_track_memory],
        "packager": [get_verified_facts, write_caption],
        "orchestrator": [get_weekend_toolkit, run_all_gates, queue_for_publish],
    }
    return groups
