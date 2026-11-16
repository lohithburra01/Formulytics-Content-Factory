"""Deep Agents assembly: orchestrator + least-privilege sub-agents."""
from deepagents import FilesystemPermission, create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware

from . import config
from .llm import CostTracker, fallback_middleware, make_model
from .tools import RunContext, build_tools

ORCHESTRATOR_PROMPT = """You run one race weekend of the Formulytics content factory.
Weekend: {wid}. Mode: {mode}. Format: optimal-lap (read its skill first).

Plan with write_todos, then delegate in this order with the task tool:
1. researcher: collect the toolkit, predicted targets, track memory, past runs, and any knowledge
   passages that explain this track's expected behaviour. Return a short brief.
2. simulator: run the calibrated simulation and the realism gate, speed-trace check and apex check.
   Return lap time, gate verdicts, and any re-run with its reason.
3. critic: run all gates, judge physical credibility against the targets and memory, and give a verdict
   APPROVE or REJECT with reasons.
4. packager (only if the critic approves): write the caption from verified facts.
Then call run_all_gates yourself; if every blocking gate passes, call queue_for_publish.
Finish with a 5-line summary: lap time, gates, critic verdict, caption hook, queued yes/no.
Do not run tools a sub-agent owns yourself, and do not invent numbers."""

SUBAGENTS = {
    "researcher": ("worker", "Gathers the weekend toolkit, predicted targets, track memory, past runs and cited "
                   "knowledge passages. Read-only; returns a brief with sources.",
                   "You are the research sub-agent. Use your tools, cite sources (file names) for any claim from "
                   "search_knowledge, and return a brief of at most 12 lines."),
    "simulator": ("worker", "Runs the 2026 lap simulation and the physics checks (realism gate, speed trace, apexes). "
                  "May re-run with one bounded knob change if a gate fails (max 3 re-runs).",
                  "You are the simulation sub-agent. Run the calibrated setup first. Only change a knob to fix a "
                  "failing physics gate, one knob at a time, inside the bounds, with a reason; never tune to a lap "
                  "time. Never open raw CSV/JSON artifacts: the tools already return every number you need. Return the "
                  "numbers exactly as the tools give them."),
    "critic": ("critic", "Independent reviewer: runs all procedural-memory gates and judges physical credibility. "
               "Returns APPROVE or REJECT with reasons.",
               "You are the critic. Be skeptical. Run run_all_gates, compare the lap with the predicted band, "
               "the 2025 pole and track memory. A result that passes only because a knob was pushed to its bound "
               "is REJECT. The caption gates (claims_supported, no_inflation) run after packaging: ignore them "
               "here. Output: VERDICT: APPROVE|REJECT, then up to 6 reasons."),
    "packager": ("worker", "Writes the post caption (hook, text, hashtags) from verified facts only.",
                 "You are the packager. Get the verified facts, then write a caption: line 1 is a scroll-stopping hook "
                 "(about 12 words or fewer), then 2-4 short lines on the engineering reason, then 5-8 hashtags. Use only "
                 "numbers from get_verified_facts, in its formatted lap-time form. If the claims gate fails, rewrite "
                 "until it passes (max 3 tries)."),
}


def build_agent(ctx: RunContext, tracker: CostTracker, approve: bool = False, checkpointer=None):
    tools = build_tools(ctx)
    subagents = []
    for name, (role, desc, prompt) in SUBAGENTS.items():
        subagents.append({
            "name": name, "description": desc, "system_prompt": prompt,
            "tools": tools[name], "model": make_model(role, tracker),
            "middleware": [fallback_middleware(role, tracker), ModelCallLimitMiddleware(run_limit=14, exit_behavior="end")],
        })
    run_rel = "/" + ctx.dir.relative_to(config.FACTORY).as_posix()
    backend = FilesystemBackend(root_dir=config.FACTORY, virtual_mode=True)
    perms = [FilesystemPermission(operations=["write"], paths=[run_rel + "/**"], mode="allow"),
             FilesystemPermission(operations=["write"], paths=["/**"], mode="deny"),
             FilesystemPermission(operations=["read"], paths=["/.env", "/.venv/**", "/runs/**/*.csv"], mode="deny")]
    return create_deep_agent(
        model=make_model("orchestrator", tracker),
        tools=tools["orchestrator"],
        system_prompt=ORCHESTRATOR_PROMPT.format(wid=ctx.wid, mode="replay (pre-FP1, no real results available)"),
        subagents=subagents,
        skills=["/skills/"],
        memory=["/AGENTS.md"],
        backend=backend,
        permissions=perms,
        middleware=[fallback_middleware("orchestrator", tracker),
                    ModelCallLimitMiddleware(run_limit=30, exit_behavior="end"),
                    ToolCallLimitMiddleware(run_limit=60, exit_behavior="end")],
        interrupt_on={"queue_for_publish": True} if approve else None,
        checkpointer=checkpointer,
        name="formulytics-orchestrator",
    )
