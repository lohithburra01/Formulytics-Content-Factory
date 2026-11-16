# 12: Guards and lineage

**What to build:** Golden test (saved pack -> identical result) runs in pre-commit; Claude Code hook blocks deletes; each completed run commits its pack + result summary.

**Blocked by:** 09

**Status:** done (2026-10-23): pre-commit golden guard (tested blocks), no-delete hook (tested live), lineage commit 5fbb42e

- [x] pre-commit blocks a commit that changes the golden result
- [x] rm / Remove-Item / del via Claude Code is blocked
- [x] Run ends with a git commit of the pack

Spec: ../spec.md. Pipeline facts: ../evidence/pipeline_map_singapore.md
