"""Local MCP server over the notes store (grill D10). Started by Claude Code from .mcp.json.
Tools are thin wrappers of weekend/store.py; add_node validates with Pydantic before writing."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from mcp.server.fastmcp import FastMCP  # noqa: E402

from weekend import store  # noqa: E402

mcp = FastMCP("weekend-notes")


@mcp.tool()
def find_node(note_id: str) -> dict:
    """Return one knowledge note by id ('<layer>/<name>', e.g. 'track/singapore_2026_line_rules')."""
    n = store.find_node(note_id)
    return n if n is not None else {"error": f"no note {note_id}"}


@mcp.tool()
def neighbours(note_id: str) -> dict:
    """Notes this note links to, and notes that link to it."""
    return store.neighbours(note_id)


@mcp.tool()
def search(query: str, k: int = 5) -> list:
    """Find note values by meaning (plain words), e.g. 'wide entry before turn 9'."""
    return store.search(query, k)


@mcp.tool()
def add_node(note: dict, replace: bool = False) -> dict:
    """Write one note (id, layer, scope, links, values). Every value needs exactly one origin:
    MEASURED/COMPUTED/KNOWLEDGE need `source`; USER_DECISION needs `reason` + `decided`;
    FITTED needs `source`, `fit_target`, `fit_range`. Refuses invalid notes and same-layer clashes."""
    try:
        return {"written": store.add_node(note, replace=replace)}
    except Exception as e:  # report the validation error to the caller
        return {"error": str(e)}


if __name__ == "__main__":
    mcp.run()
