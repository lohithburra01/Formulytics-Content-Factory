# Airflow sim on track

- Resume state: read `NOW.md` first; it is the source of truth for where work stands.
- Specs and tickets: `.scratch/<feature>/` per `docs/agents/issue-tracker.md`. Design/plan docs: `docs/YYYY-MM-DD-<topic>-{design,plan}.md`.
- Code in `src/`, tests in `tests/`.
- Code borrowed from `D:\f1_hot_lap\OPTIMAL LAP SCRIPTS` is copied in, never edited at the source; log each import in `docs/imports.md` (source path, source commit, what changed).
- Never delete files: move or rename instead (the PreToolUse hook blocks deletes).
- Commit on `main` after each finished step. Do not push unless asked (no remote yet).
