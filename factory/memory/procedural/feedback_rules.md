# Procedural memory: feedback rules -> gates

Early in the project the human reviewed outputs and gave feedback. Each piece of feedback
that recurred became a rule, and each rule became an automated gate in
`formulytics/gates.py`. The agent cannot publish if a blocking gate fails.

| id | feedback (paraphrased) | gate | how it is checked |
|----|------------------------|------|-------------------|
| R1 | "2026 cars are slower than 2025; match the rate-vs-speed curve, not just peak speeds" | `realism` | engine's `cache/_gate_2026.py`: lap above 2025 pole + rail, inside predicted band, top speed, corner minima, accel/brake rates, superclip shape |
| R2 | "Never use API car x/y positions; the feed is map-matched to one path" | `no_api_xy` | geometry must come from the SVG-derived outline, never a position feed |
| R3 | "The line must touch the apexes; no wide or mid-track apexes" | `apex_touch` | at >= 80% of corners the line centre comes within 1.5 m of the inside edge |
| R4 | "Use real traces, not hacks or lap-time-only fits" | `real_trace` | simulated speed trace vs the reference trace, distance-normalised corr >= 0.94 |
| R5 | "Optimal-lap videos at zoom 28" | `zoom` | zoom = 28, or a per-track exception the human set (Interlagos: 20) |
| R6 | "Don't inflate the lap time" (after Mexico landed 0.24 s from real Q) | `no_inflation` | displayed lap time = simulated lap time |
| R7 | "Only cite credible sources; no made-up numbers" | `claims_supported` | every number in the caption must exist in the run's verified facts |
| R8 | "Delta v2 is hifi_delta_v2.py, never delta_engine_v2.py" | `delta_engine` | driver comparisons must report the hifi_delta_v2 engine |

Taste-level feedback (music, hook wording, matchup choice) is not gated. It goes through
the LLM judge and the optional human approval interrupt.
