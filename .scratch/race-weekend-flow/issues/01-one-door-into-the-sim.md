# 01: Every stage sets up the sim only from the pack

**What to build:** One shared function configures the sim (constants, street grip, sanity bands) from the pack, used by every process that imports the sim (autofit sims, optimiser workers, final sim). Every stage writes into its own run folder; nothing writes the shared cache files; no env-var reaches a stage. The existing final-sim step is ported onto it.

**Blocked by:** None (can start immediately)

**Status:** done (2026-10-20)

- [ ] Stages run in a child process with a clean environment; a stale SG_MECH / KGRIP_STENCIL in the shell has no effect (test)
- [ ] Every run writes only under its own run folder; no file under cache/ or F1_Pipeline_Assets/ changes during a run (test)
- [ ] Sim refuses to run if it has a constant the pack lacks, or the pack has one the sim lacks
- [ ] Existing Singapore final-sim golden test still byte-identical

Spec: ../spec.md. Pipeline facts: ../evidence/pipeline_map_singapore.md
