# 10: Notes store, meaning search, MCP server

**What to build:** find_node / neighbours / search / add_node over the YAML notes (Pydantic-checked), local sentence-transformers search with a rebuildable cache, exposed as a local MCP server auto-started from .mcp.json.

**Blocked by:** None (can start immediately)

**Status:** superseded 2026-10-23 by ticket 13 proof run (all stages ran clean twice, identical). Old note: code done (store, search, MCP server, .mcp.json); search test pending

- [ ] add_node rejects an invalid note, writes a valid one (test)
- [ ] search finds the T8->T9 note from plain words (test)
- [ ] Claude Code lists the MCP tools after restart

Spec: ../spec.md. Pipeline facts: ../evidence/pipeline_map_singapore.md
