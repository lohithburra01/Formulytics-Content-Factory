"""MCP server: exposes the deterministic toolkit to any MCP client (Claude Desktop, Cursor,
another agent). Scoped on purpose: read + simulate + check only. Publishing, rendering and
caption writing stay inside the gated harness.

    python -m formulytics.mcp_server            # stdio
"""
import json
import tempfile

from fastmcp import FastMCP

from . import config, engine, gates, memory, rag

mcp = FastMCP("formulytics-toolkit")


@mcp.tool
def list_weekends() -> list[str]:
    """Weekends with a configured toolkit."""
    return sorted(p.stem for p in config.WEEKENDS.glob("*.json"))


@mcp.tool
def predicted_targets(weekend: str) -> dict:
    """Pre-FP1 targets (2025 pole, predicted 2026 band, top speed, corner minima)."""
    return engine.call("targets", weekend=weekend)


@mcp.tool
def simulate_lap(weekend: str, cda: float | None = None, cl: float | None = None) -> dict:
    """Run the 2026 lap simulation and the realism gate. Returns lap time and gate checks."""
    d = tempfile.mkdtemp(prefix="mcp_sim_", dir=config.RUNS)
    s = engine.call("sim", weekend=weekend, cda=cda, cl=cl, out_dir=d)
    if s.get("ok"):
        s["gate"] = engine.call("gate", weekend=weekend, csv=s["csv"])
        s["apex_touch"] = gates.gate_apex_touch({"sim": s, "weekend": engine.weekend(weekend)}).detail
    return s


@mcp.tool
def track_memory(query: str) -> dict:
    """What past weekends taught about a track (semantic memory graph)."""
    return memory.recall(query)


@mcp.tool
def search_knowledge(query: str) -> dict:
    """Cited passages from the research notes and calibration logs (pgvector)."""
    return rag.search(query)


@mcp.resource("formulytics://golden")
def golden() -> str:
    """Shipped predictions vs real laps."""
    return json.dumps(json.loads((config.FACTORY / "evals" / "golden.json").read_text())["rows"])


if __name__ == "__main__":
    mcp.run()
