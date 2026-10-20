# Retro evidence: F1 optimal-lap agent sessions (Jul–Oct 2026)

Gathered 2026-10-19, read-only. Scripts and raw extracts are in the same scratchpad:
`extract.py`, `tools2.py`, `sessions.txt`, `user_msgs.txt` (Claude user messages), `tools.txt` (every tool call, 300 chars),
`tools2.txt` (per-session biggest results, longest calls, render/hunt commands), `codex_user_msgs2.txt` (Codex/GPT user messages).

## 0. Coverage caveat
- Claude Code transcripts still on disk: **only 13 non-empty sessions, 2026-07-19 → 2026-10-18** (all in
  `~/.claude/projects/D--f1-hot-lap-OPTIMAL-LAP-SCRIPTS`). `~/.claude/projects/D--f1-hot-lap` holds only `memory/`, with no jsonl.
  Earlier sessions (Canada May, Monaco Jun, Spa Jul, Zandvoort Aug) are gone. A **Zandvoort Claude session survives only as a
  Codex import** (`~/.codex/sessions/2026/09/11/rollout-...32e8...jsonl`).
- The GPT agent (Codex) ran **more than one episode**: Monza takeover on 09-04, Madring on 09-11 (finished by Claude in 2f32f728),
  and **Baku on 09-24/25** (rollout `2026-09-24T18-55-43`: 15 user msgs, 517 tool calls, ~67.1M total tokens). The Codex rollouts dated
  10-01 to 10-15 contain 0 tool calls. They are imports of Claude sessions and were not counted twice.
- "Correction" = the user rejects or redoes the agent's output, or expresses frustration with it. Preference tweaks such as "try 17 zoom" are listed separately.

## 1. Per-session table
Tokens: "processed" = sum over turns of (input + cache read + cache create), which tracks cost; "out" = output tokens; "peak ctx" = largest single-turn context.

| Session | Date | Track / task | User msgs | Corrections | Tool calls | Processed | Out | Peak ctx | File |
|---|---|---|---|---|---|---|---|---|---|
| a04113db | 07-19 | not race: openclaw replay, MDs, polymarket script | 5 | 0 | 27 | 4.7M | 169k | 97k | 2.4MB |
| 6a94e59d | 07-23 | Hungary | 5 | 0 (2 zoom tweaks, 2 interrupts) | 53 | 20.8M | 351k | 210k | 1.5MB |
| (Codex import) | ~08-20 | Zandvoort (Claude) | 14 | 5 | n/a | n/a | | | |
| 2ba4d47e | 09-04 | Monza (stalled; user moved to Codex) | 4 | 1 (indirect, via Codex) | 91 | 27.6M | 326k | 226k | 1.3MB |
| Codex 09-04 | 09-04 | Monza takeover | 6 | 2 | 44 | 0.41M | | | 1.2MB |
| Codex 09-11 | 09-11 | Madring (hit usage limit) | 6 | 1 | 77 | 8.8M | | | 4.3MB |
| 2f32f728 | 09-11 | Madring (finish the Codex run) | 2 | 0 | 93 | 44.6M | 1.14M | 422k | 5.7MB |
| Codex 09-24 | 09-24/25 | **Baku (GPT, rejected)** | 15 | 10 | 517 | 67.1M | | | 26.7MB |
| d7969d10 | 09-30→10-01 | Sepang + Bahrain (+ Baku quarantine) | 13 | 3 | 141 | 74.1M | 368k | 314k | 4.8MB |
| b3187800 | 10-01 | Sepang 2017 vs 2026 | 6 | 2 | 85 | 31.0M | 203k | 229k | 6.4MB |
| b471f614 | 10-01 | Sepang 2017 (cont.) + GitHub push | 29 (≈23 typed) | 6 | 189 | 101.4M | 442k | 356k | 27.8MB |
| 81bfecf6 | 10-02 | Bahrain v2 satire (jets) | 5 | 3 | 91 | 25.6M | 211k | 200k | 10.9MB |
| 5d9c15e1 | 10-08→09 | Singapore + 2025 vs 2026 + pattern predictor | 20 | 8 | 294 | **222.3M** | 905k | 566k | 9.8MB |
| b6edf9a4 | 10-09 | 2026 car physics research (engine2) | 12 | 8 | 157 | 87.3M | 388k | 440k | 5.7MB |
| 0521040b | 10-09 | Lap comparison (Singapore SQ) | 5 | 0 | 50 | 14.8M | 171k | 168k | 2.2MB |
| bdb1a717 | 10-10 | Lap comparison script + delta v2 | 18 | 8 | 127 | 45.0M | 283k | 274k | 6.3MB |
| b4e3f234 | 10-14 | Rwanda (parked) + Portimao GT3 | 19 | 5 | 248 | 91.3M | 480k | 276k | 14.3MB |
| 34499345 | 10-18 | Agentic sandbox setup | 4 | 1 | 20 | 2.8M | 35k | 81k | 1.0MB |

Claude totals: 1,666 tool calls, of which Bash 1,223 (73%), Read 200, PowerShell 59, Write 47, WebSearch 44, Edit 26, Grep 15, Glob 2, and **Agent/subagent 0**.
About 53 corrections across 13 Claude sessions, plus about 18 in Codex sessions (Baku 10, Zandvoort import 5, Monza 2, Madring 1).

## 2. Failure patterns (count = correction messages; sessions in brackets)

### P1. Racing line wrong: misses apexes, takes the wrong side, or differs from the real line. About 15 msgs in 8 sessions. High cost, because each round triggers an optimiser re-run and a re-render.
- Codex Baku 09-25: "the racing line path is not correct and its too close to center ... never touching the apex"
- 81bfecf6 10-02: "THE CAR IS NOT TOUCHING ALL THE INSIDE APEXES PROPERLY AT CORNERS"
- 5d9c15e1 10-08 #3: "the line is not tight its not touching all the apexes"; #12: "again, in the same section, from 36th sec to 40th sec"
- d7969d10 09-30 #5 and #7 (Sepang T1): "still it looks like late inside entry for turn one"
- b3187800 #5: "no no no no no, both of them are following the same line"
- b471f614 #3, #7, #9: "t1 is where youre completely wrong"; "you have fucked up the now optimal lap line big time"
- b4e3f234 #7, #8: "why is the line looking like that?? ... what the fuck is your problem???"
- This led to memories feedback-line-apex-touch, feedback-driver-lines-real and feedback-real-trace-not-hacks, but the rule was re-violated afterwards (10-08 Singapore after 10-02 Bahrain; 10-14 Portimao).

### P2. Invented or fitted model content instead of real data or credible sources. About 15 msgs in 5 sessions. High cost: whole sessions discarded.
- b6edf9a4 10-09 #3: "engine 2 ... do not fucking use them at all ... find a fucking credible source"
- b6edf9a4 #4: "do not fucking build anything by yourself ... why the fuck did you show your creativity??"
- b6edf9a4 also #5, #6, #10, #11 ("NOT GONNA ACCEPT IT, SEARCH HARDER") and #12 ("WHAT DO YOU THINK IS THE GOAL HERE?")
- bdb1a717 10-10 #6: "this is much more fake than what we already had ... not honest"; #8: "do not nudge anything"
- 5d9c15e1 #9: "do not try to create a difference deliberately"; #10/#11: the 2025 delta is unrealistic, "retrofit the 2025 sim"
- Codex Baku #7/#9: "the acceleration and the animation is not at all accurate"; "the peaks are wrong"
- Memory feedback-real-trace-not-hacks records that the user's data suggestion was ignored ("they asked for sim-racing data; I ignored it").

### P3. Video style, zoom or title regressions, or unrequested design changes. About 13 msgs in 6 sessions. Medium cost: each costs a re-render.
- Codex Baku #5/#6: "why the fuck did you change the title"; "you have added border to text who the fuck asked you that?"
- Codex Baku #12: "where the fuck are the deployments?? deploy, regen, super clip??"
- 81bfecf6 #3: "THE VIDEO WITH THE JETS IS NOT SMOOTH ... NOT HIGHEST QUALITY"; the explanatory phrase was used literally as the title
- b471f614 #10: "the minimap is blocking the cars ... the view keeps dynamically zooming"
- b4e3f234 #12: "whats the zoom level?? how many fucking times do i tell you?" The root cause was stale "zoom 18" in NOW.md (L102/L106, inside the "read this block first" section), which contradicts memory feedback-video-zoom (28).
- Zandvoort (Codex import): zoom wrong 3 times ("It should be at least half of this value", "maybe 10")

### P4. Slowness or long blocking runs. About 7 msgs in 5 sessions. Very high cost.
- Codex 09-04: "claude is running very very insanely slow on this operation, can you take over?" (Monza 2ba4d47e)
- b471f614 #4/#5: "why is the shell still running for sooo long?"; "what the fuck is happening?? why sooo much time?"
- b4e3f234 #11: "how long does this fucking run??"
- Codex Madring 09-11: "why the fuck are you stopping??"; Codex Monza: "dude wtf youre wasting time"

### P5. Wrong file or version, or forgotten facts (navigation and memory). About 6 msgs in 3 sessions.
- bdb1a717 #13–#17: "ACTUALLY WAIT IS THIS THE DELTA ENGINE V2 THAT YOU HAVE USED?"; "DO NOT EVER USE THAT OLD V2"; "NOPE THIS IS THE OLD VERSION AGAIN". The agent took delta_engine_v2.py from the notebook cell and committed it as the user's engine (16:11). This led to hifi_delta_v2.py and the memory feedback-delta-v2-file.
- 5d9c15e1 #20: "no no no look we have just created a repo last week ... try to remember". A memory for the repo push existed only afterwards (optimal-lap-repo-push).

### P6. Claimed done or fixed without verification. 2 explicit cases.
- Zandvoort (Codex import): "Nope nothings fixed, it's still the same video no change and the new video is not created"
- Zandvoort: "Are you really sure the banking is correct? ... stuck unusually at 2 deg ... It's suspicious."

### P7. Lost objective or arguing back. 3 msgs.
- b471f614 #5: "first tell me whats the objective here? i need to know if you know."
- b6edf9a4 #12: "OKAY WHAT ARE WE DOING HERE?? WHAT DO YOU THINK IS THE GOAL HERE?"
- 34499345 #3: "dont argue with me, i just need to learn things"

### P8. Unauthorized engine and process edits (GPT). 1 episode, very high cost.
- The GPT agent edited sim_2026_lap.py, raceline_video.py, svg_to_outline.py, _track_registry.py, _autofit_2026.py and NOW.md in place, uncommitted (memory baku-gpt-quarantine).
- Codex Baku #13: "why did you change anything at all?? ... you fucked up with the design, you fucked up with the logic"
- d7969d10 09-30 #1: "do not consider the last baku optimal lap generation process, it is just utter shit by the gpt agent"
- Recovery cost: about 16 forensic calls at the start of d7969d10 (git log/show/diff, ~/.claude/file-history scans, transcript greps) before any track work.

### P9. Resume after crash, /clear or full context. 5 sessions; not corrections, but they cost re-orientation.
- b471f614 #1: "last session closed abruptly vs code crashed do you know where exactly we are?"
- bdb1a717 #1: "suddenly my laptop crashed and everything closed"
- b3187800 #1: "the other chat's context is filled up" (the user pasted the previous chat)
- d7969d10 #13: "we already filled 300k context window"
- 2f32f728: "codex agent ... usage limit reached, can you take it from here"

## 3. Navigation
Per-session counts of orientation calls (ls/find/glob, git inspect, NOW.md reads, memory reads, peeks into scripts):
- 5d9c15e1: ls/find 22, git 16, NOW.md 13, memory 9
- d7969d10: ls 20, git 12, NOW.md 8
- bdb1a717: ls 21, NOW.md 8, memory 5
- b4e3f234: ls 18, NOW.md 8, git 7, memory 6
- b471f614: ls 19, git 12, NOW.md 6
- b6edf9a4: ls 24, NOW.md 6
- 2ba4d47e: NOW.md 9, script peeks 6

Examples:
- **delta v2**: in bdb1a717 the agent took the notebook's last-cell engine as "v2" (delta_engine_v2.py, committed 16:11). From 19:31 it had to use `ls -t`, timestamps and diffs to work out which v2 was real; at 19:33 it wrote hifi_delta_v2.py from the user's paste.
- **Baku forensics**: d7969d10 opened with `git log -60`, `git show HEAD:NOW.md` (twice), `git diff --stat`, ~/.claude/file-history loops and transcript greps, to separate GPT edits from Claude edits.
- **NOW.md is 469 lines / 43 KB with 4 stacked "CURRENT STATE" headers**. Sessions read it partially (`head -c 3000/4000`, `head -150`) or in full (2ba4d47e `cat NOW.md` gave 15.8 KB). It was re-read up to 13 times per session.
- Engine files were read with sed ranges (e.g. `sed -n 860,905p raceline_video.py`, `sed -n 300,345p sim_2026_lap.py`) to find functions. There is no file map or index beyond NOW.md.

## 4. Tool economy
- **Image reads**: 160 PNG reads; the largest results are 400–670 KB each (b471f614 35 reads, e.g. sat/t7t10.png 668 KB; 5d9c15e1 26; b4e3f234 25; 81bfecf6 19 strip PNGs of 416–462 KB).
- **Renders** (raceline_video/ffmpeg command invocations): b4e3f234 44, 81bfecf6 26, d7969d10 25, 5d9c15e1 22, b471f614 11. Total about 153.
- **Sim/optimiser runs**: 5d9c15e1 63, d7969d10 59, 2ba4d47e 29, 81bfecf6 18, b6edf9a4 16.
- **Blocking polls**: 52 `until ...; sleep` loops. Many calls hit the 600 s cap (601 s in 0521040b, 5d9c15e1, b3187800, b6edf9a4, d7969d10), and 2ba4d47e had a 577 s poll loop. An AskUserQuestion in 6a94e59d waited 671 s.
- **Processed tokens**: 5d9c15e1 222M (peak ctx 566k), b471f614 101M, b4e3f234 91M, b6edf9a4 87M, d7969d10 74M; Codex Baku 67M.
- **Re-work after corrections**: Bahrain v2 had jets re-encoded and then rebuilt in-render. The Sepang 2017 line went through repeated basin/optimiser runs (445 s, 434 s, 433 s). The Portimao GT3 line had to be rebuilt as v2 (build_gt3_line 261 s / 253 s).

## 5. Guardrails in `D:\f1_hot_lap\OPTIMAL LAP SCRIPTS_sandbox`
- Test suite: **exists**: `tests/` with 7 files, 76 `def test_`, 870 lines (banking, monaco physics, outline geometry, physics sim, smoke, svg parser, transfer). Nothing runs it automatically. pytest appeared in tool calls only 8 times (d7969d10 5, 34499345 2, 2ba4d47e 1).
- Git hooks in the sandbox `.git/hooks`: only `*.sample`, none active. The parent repo `D:/f1_hot_lap/.git/hooks` has only git-lfs hooks (pre-push, post-commit, post-checkout, post-merge).
- `.pre-commit-config.yaml`: not found.
- CI (`.github/workflows`): not found in the sandbox or in D:/f1_hot_lap.
- Lint config (pyproject, setup.cfg, ruff, flake8, tox, pytest.ini): not found.
- `.claude/settings.local.json` (sandbox): permissions allowlist only, **no hooks**. The global `~/.claude/settings.json` has no `"hooks"` key.
- Check scripts:
  - `cache/_gate_2026.py` (145 lines) and `cache/_check_ontrack.py` are called at the end of make_*.bat (bahrain, bahrain_what_could_have_been, hungary, monza, sepang, singapore, spa, zandvoort, GT3 portimao), but **without `|| exit /b 1`**. They are advisory and do not block the render.
  - Manual-only scripts: `cache/_backtest_2026.py`, `_noref_backtest.py`, `_verify_outline.py`, `_verify_*`, `cache/bahrain/_apex_gaps.py`, `cache/singapore/_scan_crossings.py`.
  - The Zandvoort bit-identical regression recipe exists only as prose in memory baku-gpt-quarantine.
- The sandbox NOW.md roadmap lists "golden regression tests ⬜" and "Hooks — turn feedback memories into enforced rules" as not yet done.

## 6. Steering files
| File | Lines | Bytes |
|---|---|---|
| ~/.claude/CLAUDE.md (global) | 18 | 1,641 |
| D:\f1_hot_lap\CLAUDE.md / AGENTS.md | not found | |
| OPTIMAL LAP SCRIPTS\CLAUDE.md / AGENTS.md | not found | |
| OPTIMAL LAP SCRIPTS\NOW.md | 469 | 43,136 |
| OPTIMAL LAP SCRIPTS_sandbox\NOW.md | 36 | 2,127 |
| OPTIMAL LAP SCRIPTS_sandbox\NOW_pipeline_resume.md | present (pipeline state) | |
| memory\MEMORY.md | 31 | 6,053 |
| memory\*.md (28 files incl. index) | 654 total | |

No-ops and duplicates:
- The global CLAUDE.md says "Use a subagent for broad file/search exploration", but **0 Agent calls** appear in all 13 sessions. That instruction is a no-op.
- The session protocol appears three times: global CLAUDE.md, NOW.md L466–469 ("Session protocol reminder") and sandbox NOW.md Rules.
- "Never delete anything" appears in MEMORY.md (twice), NOW.md (2 hits), sandbox NOW.md, baku-gpt-quarantine and feedback-delta-v2-file. No permission deny rule or hook enforces it.
- **The zoom value conflicts**: NOW.md still says zoom 18/19 (L102, L106, L139) while memory feedback-video-zoom says 28 "never 18". This directly caused the b4e3f234 correction.
- NOW.md has 4 stacked "CURRENT STATE"/dated headers (L1, L21, L56, L84 "read this block first") above the original manual at L167. It is not clear which block is current.
- Three MEMORY.md index entries point to files in the D: cache rather than the memory directory.

## 7. Moments where key information was unavailable
- 2ba4d47e 09-04: OpenF1 returned "401 Live F1 session in progress. Global API access (including past sessions) is restricted", which blocked the 2025 Monza Q reference, Zandvoort Q and elevation. The same lockout recurred for Madring (memory).
- b3187800 10-01: "real 2017 Sepang telemetry doesn't exist publicly. F1's official timing archive starts in 2018 (2017 returns 403)". The user: "we only have data recorded from 2018".
- b471f614 #3: the Lewis 2017 line was visible only in video, not extractable ("sadly theres no way for us to extract anything").
- d7969d10: "No public car data covers Sepang yet"; "F1's position feed snaps every car o[nto one path]". Memory f1-position-feed-map-matched records that the feed has no usable racing lines or widths.
- b6edf9a4: "No 2026 car is in iRacing, rFactor 2 or Le Mans Ultimate, and the teams and the FIA have not published their 2026 car data."
- b4e3f234: GT3 aero numbers "Not published anywhere"; the Track Titan guide returned 403; the user: "i dont have any of that to give you". Rwanda had only an oblique render, so the track was parked.
- Madring: FP2 was "still unpublished" during the run; the absolute elevation datum was unverified.
- bdb1a717 (pasted from another assistant): "F1's servers are blocked from my sandbox".
