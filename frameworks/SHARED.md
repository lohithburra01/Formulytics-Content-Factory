# Formulytics Retention Framework: the shared core

Both parts, [Discover](DISCOVER.md) (find a format worth making) and [Produce](PRODUCE.md)
(make it every week, honestly, with a fresh touch), stand on the same five ideas. They are written
once here.

> **Agents make decisions. Tools make numbers. Gates make it honest.**

---

## 1. The dividing line: script or model?

> **If the rule can be written before seeing the input, it is a script.
> If it can only be decided after seeing the input, it needs a model.**

This line decides where every piece of work goes. Applied to one race weekend:

| Work | Can the rule be written in advance? | So it is |
|---|---|---|
| Simulate the lap from car parameters | Yes: physics | Deterministic engine |
| Pick the calibration recipe for a track type | Yes, once it is validated | Script, with bounded knobs |
| Check that the line touches the apexes | Yes: a distance threshold | Gate |
| Decide whether this weekend's result is physically credible given everything else known | No: it depends on what else is odd this weekend | Model (critic) |
| Pick this weekend's touch (weather layer, local prop, driver focus) | No: depends on this weekend's story | Model (designer) |
| Decide whether the first 3 seconds would stop a thumb | No: depends on the rendered frames | Model (vision judge), then human |
| Decide what format to make in the first place | No | Model plus human, steered ([Discover](DISCOVER.md)) |

The consequence: the agentic core of a content system is not the number-crunching, which should keep
moving into scripts. It is the small, new, judged artifact each run: the angle, the touch, the hook.
Over time, work moves down the table: a judgment made the same way three times becomes a rule,
and a rule with tests becomes a script or a gate.

## 2. Primitives

Every repo that uses these frameworks has these objects. Templates are in [`templates/`](templates).

| Primitive | What it is | Used in |
|---|---|---|
| **Source** | A data adapter plus a **capability card**: what it supports, what it cannot, how far to trust it ([template](templates/source_card.example.yaml)) | Discover writes it, Produce enforces it |
| **Toolkit** | The frozen form of a format: deterministic engine, bounded knobs, renderer, gates, review packet, `SKILL.md` | Discover freezes it, Produce runs it |
| **Format grammar** | What is **locked**, which **open slots** may change each event, and the contract of each slot ([template](templates/format.example.yaml)) | Produce |
| **Event** | One instance to run (a race weekend), with a **data cutoff** | Produce |
| **Fact** | A number produced by a tool, with provenance and an evidence grade | Both |
| **Rule** | A written observation from the owner, with an id, a kind and a checker ([template](templates/rulebook.example.yaml)) | Both |
| **Gate** | An automated pass or fail check, traced to the rule it came from | Both |
| **Variant** | A reusable touch for an open slot, with its trigger and track record ([template](templates/variant.example.yaml)) | Produce |
| **Reference** | Ground truth, sealed until the run is scored | Both |
| **Review packet** | The smallest set of artifacts a human needs to decide quickly | Both |

## 3. Evidence grades

Every finding and every number carries a grade.

| Grade | Meaning | May it be published? |
|---|---|---|
| `measured` | A tool read it from real data | Yes |
| `derived` | A deterministic engine computed it from measured inputs | Yes |
| `cited` | An external source, with a link | Yes, with attribution |
| `assumed` | A prior, an estimate, a guess | No. It may drive a run, never a claim |

## 4. Two kinds of truth, both scored

A content system makes two kinds of claims, and the world later grades both:

| Claim | Example | Scored against | When |
|---|---|---|---|
| **About the world** | "The optimal 2026 lap here is 1:10.772" | The real lap (qualifying pole or fastest dry lap) | After the event |
| **About the audience** | "Variant B will hold more viewers past 3 s than variant A" | The post's real retention (3-second hold, average watch time) | Days after posting |

The same discipline applies to both: **predict blind, ship, score, keep the misses public.**
Views are not used as the score because they depend heavily on distribution, not only on the video.

## 5. Honesty layers

Each layer exists because of a specific way an agent produces something false.

| # | Layer | Failure it prevents | Enforced by |
|---|---|---|---|
| 1 | **Number provenance** | A number no tool produced | Every number in any output must match a Fact id (`claims_supported` gate) |
| 2 | **Source limits** | Data used for what it cannot support | Capability cards, plus gates that forbid known-bad uses (`no_api_xy`) |
| 3 | **Blind runs** | Seeing the answer before predicting it | Event cutoff; references sealed; post-hoc scores hidden from agents |
| 4 | **No fitting to the target** | A knob pushed until the result looks right | Physical bounds; one knob per retry with a stated reason; critic rejects knobs at a bound |
| 5 | **Worst-segment checks** | A good average hiding one bad corner | Gates check the worst segment, not only the mean |
| 6 | **Separation of duties** | The maker grading its own work | Critic and judges are separate agents with their own models and tools |
| 7 | **Hooks are claims** | A catchy line that is not true | Hook cards and captions go through the same claims gate as numbers |
| 8 | **Touches never imply** | A creative layer that suggests something false (a rain filter on a dry simulation) | Every variant declares what it must not imply; the vision judge checks it |
| 9 | **Public misses** | Only showing wins | Every output scored, misses included; retractions kept, never deleted |

## 6. Autonomy levels

Set per toolkit, and separately for numbers and for taste.

| Level | Behaviour | Promotion |
|---|---|---|
| **L0** | Prototype. The human approves every step | The toolkit passes the freeze test |
| **L1** | The human sees the review packet and approves or rejects | *n* runs approved with no changes; for taste, judge-owner agreement above a set rate |
| **L2** | Ships alone when every gate passes with margin; escalates the rest | *n* auto-shipped runs with no retraction |
| **L3** | Fully automatic; the human gets a weekly digest | Demoted to L2 on any retraction |

Escalation triggers: a gate inside its margin band, a knob at its bound, critic and maker disagree,
the first run on a new event type, an `assumed` finding drove the run, or a new (unapproved) variant.

Discover stays at L0 or L1 by design: inventing a format is a steered collaboration, not a job to
hand off.

## 7. Prior art, and what is actually new here

Most of the parts are known. They are cited here so the claim stays narrow. Every source below was
opened and checked on 2026-11-17.

| Area | Closest prior work | What it covers | What it does not cover, relative to this system |
|---|---|---|---|
| Harness engineering | M. Hashimoto, [My AI Adoption Journey](https://mitchellh.com/writing/my-ai-adoption-journey) (2026); V. Trivedy, [The Anatomy of an Agent Harness](https://www.langchain.com/blog/the-anatomy-of-an-agent-harness) (LangChain, 2026), source of "agent = model + harness"; OpenAI, [Harness engineering](https://openai.com/index/harness-engineering/) (2026); He et al., [Harness Engineering for Language Agents (CAR)](https://www.preprints.org/manuscript/202603.1756) (preprint, 2026) | Every agent mistake becomes a harness fix; the harness as control, agency and runtime | Software engineering only; no published claims, no scoring against the world |
| Agent principles and packaging | HumanLayer, [12-Factor Agents](https://github.com/humanlayer/12-factor-agents); Anthropic, [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) (2024) and [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) (2025); [Agent Skills](https://agentskills.io) (`SKILL.md` standard, used here); LangChain [Deep Agents](https://github.com/langchain-ai/deepagents) (used here) | Small focused agents, owned context and control flow, skills loaded on demand, sub-agents | Domain gates, evidence grades |
| Explore once, then freeze | El Yadouni and Li, [TraceCompiler](https://arxiv.org/abs/2608.02680) (2026); Wang et al., [Agent Workflow Memory](https://arxiv.org/abs/2409.07429) (2024); [AgentRR](https://arxiv.org/abs/2505.17716) (2025); [SkillWeaver](https://arxiv.org/abs/2504.07079) (2025); [Voyager](https://arxiv.org/abs/2305.16291) (2023); Skyvern [code caching](https://www.skyvern.com/docs/developers/features/code-caching.md), Stagehand [caching](https://browserbase.com/blog/stagehand-caching) | Agent traces compiled into mostly deterministic workflows or tested skills; TraceCompiler separates constants from residual model decisions, close to the dividing line in section 1 | Browser and API tasks; the frozen artifact is a workflow, not a physics or render engine validated against outside references |
| Blind prediction, scored | [ForecastBench](https://arxiv.org/abs/2409.19839) (ICLR 2025); [Prophet Arena](https://arxiv.org/abs/2510.17638) (2025); [Foresight Arena](https://arxiv.org/abs/2605.00420) (2026); World Monitor's [public forecast scorecard](https://www.worldmonitor.app/blog/posts/ai-forecast-accuracy-brier-scorecard-worldmonitor/) (2026); Gneiting and Raftery, *Strictly Proper Scoring Rules* (JASA, 2007) | Live questions that cannot leak, proper scoring, never-edited records with misses public | Forecasting questions, not media claims; no evidence bound to each claim when it is published |
| Claim provenance and guardrails | [FActScore](https://arxiv.org/abs/2305.14251) (2023); [AIS](https://arxiv.org/abs/2112.12870) (2021); [ALCE](https://arxiv.org/abs/2305.14627) (2023); Wiseman et al., [RotoWire](https://arxiv.org/abs/1707.08052) (2017, sports data-to-text); [NeMo Guardrails](https://arxiv.org/abs/2310.10501); [Guardrails AI](https://github.com/guardrails-ai/guardrails) | Atomic fact checking, attribution, numbers checked against a box score, programmable output rails | Scoring after generation, not a fail-closed publish gate where every on-screen number must be a stored Fact |
| Engagement and video judges | [VQualA 2025 engagement challenge](https://arxiv.org/abs/2509.02969) (SnapUGC) and its [winning method](https://arxiv.org/abs/2508.02516); [MicroLens](https://arxiv.org/abs/2309.15379); [VideoScore](https://arxiv.org/abs/2406.15252); [V-JEPA 2](https://arxiv.org/abs/2506.09985) (Meta, 2025: frozen video encoder, ViT-g at about 1B parameters) | Population-level engagement prediction, learned video-quality judges, general video embeddings | One channel's own taste; checks on a plan before rendering |
| Personal judges | [PARL](https://arxiv.org/abs/2605.31545) (2026, per-user rubric learning); Dong et al., [Can LLM be a Personalized Judge?](https://arxiv.org/abs/2406.11657) (2024) | Judges conditioned on one person's preferences | Not tied to a production loop or scored against audience outcomes |
| Ideation agents | Sakana, [The AI Scientist](https://arxiv.org/abs/2408.06292) (2024); Google, [AI co-scientist](https://arxiv.org/abs/2502.18864) (2025); Si et al., [Can LLMs Generate Novel Research Ideas?](https://arxiv.org/abs/2409.04109) (2024); [Scideator](https://arxiv.org/abs/2409.14634) | Generating and ranking ideas, human-steered recombination, novelty checks | Ideas that must repeat every event under hard data limits; the owner's private rules as standing context |

**What is new here** is not any single part but one combination, which none of the work above covers:

> **An agent system that publishes claims about the real world to a large audience, binds every claim to
> evidence at publish time, is scored later against both what happened and how the audience responded,
> keeps its misses public, and applies the owner's own private rules before anything is rendered.**

The F1 channel is a live, scored deployment of that combination ([results](../README.md#results)).
The parts marked *designed* in each part's status table are not yet built.
