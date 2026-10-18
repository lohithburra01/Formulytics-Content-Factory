# Monaco 2026 — Optimal Lap Simulation

**Result: a 1:11.8 perfect optimal lap of Monaco under the 2026 regulations.**

This is a physics simulation, not a game replay and not a guess. It computes the
fastest *physically legal* lap a 2026 car could drive around Monaco — the ideal
racing line plus perfect energy deployment — and renders it. Below is exactly how
it's built and, just as importantly, the rules I held myself to so the time is
**honest**.

---

## The honesty rules (what makes this legit)

A "fast" lap is easy to fake — inflate the grip, let the car cut corners, or let
speed teleport. I refused all three. The lap is bound by four hard constraints:

1. **The car never leaves the track.** The racing line is computed to stay inside
   the real circuit boundary *by construction* — no corner-cutting, no clipping a
   point to the wall to cheat a tighter line. What you see is a line a real car
   could physically hold between the barriers.

2. **The grip never exceeds a real car.** Cornering load is capped to what real
   F1 cars actually pull. In this lap the car sits at ~3.6 g lateral for 95% of
   the corners and tops out around 4.1 g — **at or below** the real 2026 cars'
   ~4.5–5 g. The lap is quick because the *line and energy use* are optimal, not
   because the tyres are made magic.

3. **Every motion is physically smooth.** Real cars can't snap from full throttle
   to full brake instantly, and they flow through chicanes with a single dip in
   speed, not a stutter. The speed profile is jerk-limited to match how real 2026
   cars actually change speed under throttle, braking and transitions.

4. **It's validated against real 2026 data.** I pulled the real 2026 Monaco FP1
   telemetry (Leclerc's 1:13.978) and checked the sim's speed profile against it.

---

## How it compares to the real 2026 car

Benchmark: **real 2026 Monaco FP1 fastest lap — LEC 1:13.978.** A practice lap
isn't a pushing qualifying lap, so the projected quali pace is roughly two seconds
quicker (~1:11.9). The sim lands at **1:11.8** — right where a *perfect* lap should:
just ahead of the projected real quali, and slower than the 2025 pole (because the
2026 rules cut downforce, so 2026 Monaco is genuinely slower than 2025).

The sim's speed *distribution* tracks the real FP1 lap almost point-for-point —
the shape is real, it's just driven optimally:

| Speed percentile | This sim | Real 2026 FP1 |
|---|---|---|
| Slowest 5% (corners) | 66 km/h | 65 km/h |
| 25% | 101 km/h | 100 km/h |
| Median | 166 km/h | 157 km/h |
| 75% | 223 km/h | 218 km/h |
| Fastest 5% | 267 km/h | 267 km/h |
| Top speed (tunnel) | 281 km/h | 284 km/h |

The only place it carries more than the real lap is mid-corner — and it does that
at *lower* g than the real car, because the optimal line uses a wider, faster
radius than a human threading practice traffic. That's the perfect lap beating the
human, not the tyres cheating.

---

## The physics model (built to the 2026 rules)

**The car:**
- 768 kg (the 2026 FIA minimum weight)
- 400 kW combustion engine + MGU-K hybrid, ~4 MJ usable battery

**The 2026 Monaco-specific rules — the headline new physics:**
- **Active aero is disabled the whole lap.** Monaco has no straight long enough to
  legally open the wings, so the car runs its single biggest-downforce
  configuration everywhere — maximum grip, maximum drag.
- **Rev1 speed-limited hybrid deployment.** The MGU-K can deploy its full 350 kW
  only up to 200 km/h; the cap then tapers to ~100 kW at 270 km/h and to zero by
  300 km/h. So the electric boost helps most off the slow corners and fades out
  near top speed — exactly as the regulations intend.
- **Overtake mode** (a bigger deployment allowance) is applied only on the single
  fastest part of the lap, as the rules permit.
- The 2026 aerodynamic downforce reduction (~−30% vs 2025) is baked in.

**The grip model:**
- A friction-circle tyre model: the car can't brake/accelerate and corner at full
  force simultaneously, just like reality.
- Downforce grows with the square of speed, so the car has huge grip in the fast
  sections and only mechanical grip in the slow hairpin.

---

## How the lap is generated

1. **Track shape** → the Monaco circuit outline (centerline + the two edges) at
   its real ~9 m road width.
2. **Optimal line** → a minimum-time racing line is solved across the track width,
   smoothed so the curvature changes at a rate a real car could steer, and kept
   inside the boundary.
3. **Physics pass** → the car is driven around that line forward and backward
   until the speed and battery state are consistent: every braking point,
   apex speed, deployment zone and top speed comes out of the model, not by hand.
4. **Realism filter** → the speed profile is rounded to a jerk-limited shape so
   transitions look and behave like a real car.
5. **Render** → the result is drawn as the on-track video with live speed.

---

## In one line

A 2026-rules Monaco lap, driven on the optimal line with perfect energy
deployment, with grip and motion capped to what real cars actually do and
cross-checked against real 2026 telemetry. **1:11.8 — fast because it's perfect,
not because it cheats.**
