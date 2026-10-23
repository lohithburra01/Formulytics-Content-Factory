# 17 — Energy pattern = FP1 (spec D28)

**Status:** ready (written 2026-10-23)

## Why (Austin run 1)
FP1 clips on 4 straights (440-476 m 303->295, 1177-1233 m 284->277, 2308-2395 m 282->269, back straight 3237-3498 m
332->322). The sim deployed full power on the first three (11-21 km/h faster), emptied the battery to 6 %, and its
only SUPERCLIP (P_SUPERCLIP_NET_W 335 kW, placed by SUPERCLIP_SPEED_FRAC 0.96 of top speed) still GAINED speed.

## What
1. Check: sim clip zones vs FP1 clip zones (location overlap + speed drop) in the checks stage; mismatch = not ok.
2. Sim: clip where FP1 clips (zones from the pack/refs, not from a top-speed fraction); clip strength FITTED to
   FP1's speed drop per zone (not hand-set).
3. Grip factor (track.street_grip_k) tuned only for street circuits (card street: true); 1.0 otherwise.

## Done when
Austin rerun: every FP1 clip zone matched by a sim clip zone with a similar drop, none extra; lap judged in band.
