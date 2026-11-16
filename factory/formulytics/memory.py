"""Three memory types.

- episodic : memory/episodes.jsonl - one record per weekend run (what ran, scores, cost, lessons)
- semantic : memory/track_graph.json - knowledge graph of tracks, methods, car setups and results,
             built from the weekend specs + the golden dataset; queried by recall()
- procedural: memory/procedural/feedback_rules.md -> formulytics/gates.py (rules the agent must obey)

Context compaction inside a run is Deep Agents' SummarizationMiddleware; long-term state lives here.
"""
import json
import time
from pathlib import Path

from . import config

EPISODES = config.MEMORY / "episodes.jsonl"
GRAPH = config.MEMORY / "track_graph.json"
GOLDEN = config.FACTORY / "evals" / "golden.json"


def add_episode(rec: dict):
    EPISODES.parent.mkdir(parents=True, exist_ok=True)
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **rec}
    with open(EPISODES, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, default=str) + "\n")
    return rec


def episodes(weekend: str | None = None, last: int = 5):
    if not EPISODES.exists():
        return []
    rows = [json.loads(l) for l in EPISODES.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [r for r in rows if weekend is None or r.get("weekend") == weekend][-last:]


def build_graph():
    """Nodes: track, weekend, method, setup, result. Edges carry the relation name."""
    nodes, edges = {}, []

    def node(nid, kind, **attrs):
        nodes.setdefault(nid, {"id": nid, "kind": kind}).update(attrs)
        return nid

    golden = json.loads(GOLDEN.read_text())["rows"] if GOLDEN.exists() else []
    for g in golden:
        wid = g["id"]
        track = node("track:" + wid.rsplit("_", 1)[0], "track")
        wk = node("weekend:" + wid, "weekend", stage=g["stage"], sim_s=g["sim_s"])
        edges.append((track, "held", wk))
        m = node("method:" + g["stage"], "method")
        edges.append((wk, "predicted_with", m))
        if g.get("ref_s"):
            r = node("result:" + wid, "result", real_ref_s=g["ref_s"], ref_kind=g["ref_kind"],
                     err_s=g["err_s"], err_pct=g["err_pct"], q_wet=g["real"]["q_wet"])
            edges.append((wk, "scored", r))
        else:
            edges.append((wk, "note", node("note:" + wid, "note", text=g.get("note"))))
    for p in config.WEEKENDS.glob("*.json"):
        w = json.loads(p.read_text(encoding="utf-8"))
        wk = node("weekend:" + w["id"], "weekend", direction=w["direction"], formats=w["formats"])
        su = node("setup:" + w["id"], "setup", **w["sim"]["car"], env_knobs=sorted(w["sim"]["env"]))
        edges.append((wk, "car_setup", su))
        edges.append((wk, "render_rule", node("render:" + w["id"], "render", **w["render"])))
    g = {"nodes": list(nodes.values()), "edges": [{"src": a, "rel": r, "dst": b} for a, r, b in edges]}
    GRAPH.parent.mkdir(parents=True, exist_ok=True)
    GRAPH.write_text(json.dumps(g, indent=1))
    return g


def recall(query: str, hops: int = 2) -> dict:
    """Return every node within `hops` of nodes whose id matches the query (e.g. 'mexico')."""
    g = json.loads(GRAPH.read_text()) if GRAPH.exists() else build_graph()
    by = {n["id"]: n for n in g["nodes"]}
    words = [w for w in query.lower().replace(",", " ").split() if len(w) > 2]
    seeds = {n for n in by if any(w in n.lower() for w in words + [query.lower().replace(" ", "_")])}
    seen, frontier = set(seeds), set(seeds)
    for _ in range(hops):
        nxt = set()
        for e in g["edges"]:
            if e["src"] in frontier and e["dst"] not in seen:
                nxt.add(e["dst"])
            if e["dst"] in frontier and e["src"] not in seen and not e["src"].startswith("track:"):
                nxt.add(e["src"])
        seen |= nxt
        frontier = nxt
    return {"query": query, "nodes": [by[i] for i in sorted(seen)],
            "edges": [e for e in g["edges"] if e["src"] in seen and e["dst"] in seen]}
