# Results: Formulytics deployment

## Season scoreboard

Every event, the prediction is published before the cars run. Once the real session is in, it is scored against
the official result from OpenF1 ([`build_golden.py`](../factory/evals/build_golden.py)) and added here. Nothing is
removed. Dry simulations are compared only with dry laps.

| Event | Data before shipping | Predicted | Real | Reference | Error |
|---|---|---|---|---|---|
| São Paulo | none | 1:10.772 | 1:10.763 | fastest dry lap (qualifying was wet) | **+0.009 s** |
| Mexico City | none | 1:16.758 | 1:16.514 | pole | **+0.244 s** |
| Silverstone | FP1 | 1:27.970 | 1:28.111 | pole | −0.141 s |
| Monaco | FP1 | 1:11.770 | 1:12.051 | pole | −0.281 s |
| Madring | FP1, FP2 | 1:32.363 | 1:31.824 | pole | +0.539 s |
| Singapore | none | 1:33.010 | 1:31.373 | pole | +1.637 s |
| Spa | none | 1:41.910 | 1:44.361 | pole | −2.451 s |
| Sepang | none, no prior-year reference | 1:31.838 | 1:35.130 | pole | −3.292 s |
| Bahrain | none | 1:32.186 | — | event not held | — |

Misses are the input to the Learn step. The large early misses each produced a logged method change, and blind error
has fallen since. The scoreboard is the long-run measure, not any single event.

## What every run guarantees

| | On every run |
|---|---|
| **Blind** | No data from the event past its cutoff; real-world scores are hidden from the agents |
| **Gated** | Eight fail-closed gates; any failure, or any missing artifact, stops publishing |
| **Checked by a second model** | A separate critic, on its own model, approves or rejects the result |
| **Recorded** | Manifest (git SHA, models, input hashes, knobs, gate results, billed cost), append-only ledger, full trace |
| **Bounded** | Budget caps per run and in total; a run costs cents of model spend |
| **Scored** | The prediction joins the scoreboard once the event has run |
| **Learned from** | A failure that gets through becomes a regression test and a public [retraction](../factory/publish), never a deletion |

## Evaluation suite

Engine regression and gate tests run in CI on every push; the full suite runs on demand
([`run_evals.py`](../factory/evals/run_evals.py)). Current values:

| Eval | Measures | Current |
|---|---|---|
| Prediction error | Mean absolute error over all scored events, and over events since the current method | 1.07 s · 0.13 s |
| Engine regression | Shipped laps reproduced exactly by the current engine | pass |
| Retrieval | Hit rate at 4; off-topic queries withheld rather than answered | 0.83 · 3/3 |
| Memory recall | Facts recovered from the knowledge graph | 6/6 |
| Caption judge | An LLM judge scores captions for hook, accuracy, clarity and compliance | 1 to 5 per axis |
| Gate tests | A passing and a failing case for every gate, plus every past failure as a regression case | 22 pass |

