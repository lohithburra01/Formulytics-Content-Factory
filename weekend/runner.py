"""Step runner (grill D15): a LangGraph graph with NO AI inside. Each node runs one pipeline stage
(cached by its input key, so only stages whose inputs changed do work). The graph state is
checkpointed in SQLite, so a crashed run resumes at the node that failed. A value with no
source pauses the graph (interrupt) with the questions; after the answers are written as notes,
`--resume` continues from the same point.

  python -m weekend singapore 2026            # run (or continue) the whole weekend
  python -m weekend singapore 2026 --resume   # continue after answering questions
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
from typing import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from weekend import new_track, pipeline
from weekend.resolve import ROOT, Unresolved, load_notes, pack_path, resolve_pack

ORDER = ["track", "base_line", "refs", "car_and_line", "time_knob", "shape_fit", "final", "checks", "review", "video"]
APPROVED = "approved.json"   # written into the review dir by `python -m weekend.approve`
LINEAGE_DIR = os.path.join(ROOT, "weekend", "lineage")


class State(TypedDict, total=False):
    track: str
    year: int
    pack: str
    done: dict          # stage -> {"key", "dir", "result"}
    committed: str


def node_resolve(state: State) -> State:
    weekend = dict(track=state["track"], year=state["year"])
    new_track.ensure_notes(state["track"], state["year"])   # a new track writes its own notes (ticket 15)
    while True:
        try:
            pack = resolve_pack(load_notes(), weekend)
            break
        except Unresolved as e:
            interrupt({"questions": e.questions})   # pause; resumed after the answers are notes
    path = pack_path(weekend)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(pack.model_dump_json(indent=1, exclude_none=True))
    return {"pack": path, "done": {}}


def make_stage_node(name):
    def node(state: State) -> State:
        memo = {k: v for k, v in state.get("done", {}).items()}
        res = pipeline.run_stage(name, state["pack"], memo)
        done = dict(state.get("done", {})); done.update(memo); done[name] = res
        return {"done": done}
    node.__name__ = f"stage_{name}"
    return node


def node_lineage(state: State) -> State:
    """Commit the pack + a result summary (grill D11 lineage). Only these two files are committed."""
    w = f"{state['track']}_{state['year']}"
    os.makedirs(LINEAGE_DIR, exist_ok=True)
    summary = {n: dict(key=d["key"], result=d["result"]) for n, d in state["done"].items()}
    spath = os.path.join(LINEAGE_DIR, f"{w}.json")
    with open(spath, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1, sort_keys=True)
    files = [os.path.relpath(state["pack"], ROOT), os.path.relpath(spath, ROOT)]
    subprocess.run(["git", "add", "--", *files], cwd=ROOT, check=True)
    staged = subprocess.run(["git", "diff", "--cached", "--quiet", "--", *files], cwd=ROOT).returncode
    if staged == 0:
        return {"committed": "unchanged"}
    ck = summary.get("checks", {}).get("result", {})
    msg = (f"lineage: {w} run (lap {ck.get('lap_s')}, checks all_ok={ck.get('all_ok')})\n\n"
           f"Pack + stage keys/results of this run; re-running the pack reproduces it.\n\n"
           f"Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>")
    subprocess.run(["git", "commit", "-m", msg, "--", *files], cwd=ROOT, check=True)
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return {"committed": head}


def review_approved(state: State) -> bool:
    return os.path.exists(os.path.join(state["done"]["review"]["dir"], APPROVED))


def build(checkpointer):
    g = StateGraph(State)
    g.add_node("resolve", node_resolve)
    prev = "resolve"
    g.add_edge(START, "resolve")
    for name in ORDER:
        g.add_node(name, make_stage_node(name))
        if name == "video":                 # the video waits for the user's OK on the review pictures
            g.add_conditional_edges(prev, review_approved, {True: name, False: END})
        else:
            g.add_edge(prev, name)
        prev = name
    g.add_node("lineage", node_lineage)
    g.add_edge(prev, "lineage"); g.add_edge("lineage", END)
    return g.compile(checkpointer=checkpointer)


def run(track: str, year: int, resume: bool = False):
    db = os.path.join(pipeline.RUNS, "runner.sqlite")
    os.makedirs(pipeline.RUNS, exist_ok=True)
    conn = sqlite3.connect(db, check_same_thread=False)
    graph = build(SqliteSaver(conn))
    cfg = {"configurable": {"thread_id": f"{track}_{year}"}}
    snap = graph.get_state(cfg)
    if resume and snap.next:
        inp = Command(resume="answered")
    elif snap.next and not resume:
        inp = None                          # a previous run stopped mid-way: continue it
    else:
        inp = State(track=track, year=year)
    out = graph.invoke(inp, cfg)
    snap = graph.get_state(cfg)
    if snap.next:                           # paused at an interrupt
        qs = [i.value for t in snap.tasks for i in t.interrupts]
        return dict(paused=True, questions=qs)
    if "video" not in out["done"]:          # stopped for the review: user looks, then approves
        rv = out["done"]["review"]
        return dict(paused=True, review=dict(dir=rv["dir"], **rv["result"]), checks=out["done"]["checks"]["result"],
                    next=f"check line.svg + speed.svg, then: python -m weekend.approve {track} {year}")
    return dict(paused=False, committed=out.get("committed"),
                checks=out["done"]["checks"]["result"], video=out["done"]["video"]["dir"])
