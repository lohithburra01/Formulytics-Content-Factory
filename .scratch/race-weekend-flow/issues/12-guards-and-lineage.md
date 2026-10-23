# 12: Guards and lineage

**What to build:** Golden test (saved pack -> identical result) runs in pre-commit; Claude Code hook blocks deletes; each completed run commits its pack + result summary.

**Blocked by:** 09

**Status:** 2 of 3 done (2026-10-23): pre-commit golden guard (core.hooksPath weekend/hooks, tested: tampered golden -> blocked) + no-delete PreToolUse hook (.claude/settings.json, tested live); lineage commit checked in ticket 13

- [ ] pre-commit blocks a commit that changes the golden result
- [ ] rm / Remove-Item / del via Claude Code is blocked
- [ ] Run ends with a git commit of the pack

Spec: ../spec.md. Pipeline facts: ../evidence/pipeline_map_singapore.md
