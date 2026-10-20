# 12: Guards and lineage

**What to build:** Golden test (saved pack -> identical result) runs in pre-commit; Claude Code hook blocks deletes; each completed run commits its pack + result summary.

**Blocked by:** 09

**Status:** partial: golden replay written; pre-commit + no-delete hook not done

- [ ] pre-commit blocks a commit that changes the golden result
- [ ] rm / Remove-Item / del via Claude Code is blocked
- [ ] Run ends with a git commit of the pack

Spec: ../spec.md. Pipeline facts: ../evidence/pipeline_map_singapore.md
