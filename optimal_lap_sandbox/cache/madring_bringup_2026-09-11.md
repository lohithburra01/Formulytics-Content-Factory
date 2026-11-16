# Madring SVG bring-up — 2026-09-11

Status: SVG geometry accepted for continued development. The outline and lap are provisional; no calibrated prediction or video has been produced.

## Scope and user constraints

- Madring is the active track. Monza is set aside; retain all Monza work.
- User explicitly prohibits deleting anything. Preserve files and unrelated work.
- Continue the pre-session prediction workflow: this track's 2026 sessions are for later validation, unless the user changes that scope.
- No shared physics, converter, registry, calibration files, or renderer code was changed during this bring-up.

## Input and external geometry facts

- Source: `Madring_(2026).svg`, 8,779 bytes.
- SHA-256: `8793879c3406e2b74228e8706406191dc5863942ad4364c282ad7fd4954a0116`.
- Screen: one selected stroked centreline; 379 segments (2 cubic, 377 straight); 457 flattened points; 17.2 segments/turn across 22 turns. Density verdict GOOD. Mostly polyline input means count alone is not proof of surveyed accuracy.
- Length used: 5,414 m, from the [F1 circuit guide dated September 10, 2026](https://www.formula1.com/en/latest/article/circuit-guide-everything-you-need-to-know-about-the-madring.NF7Mh3iag3w9GUPlihwJA). This guide lists 22 turns. Recheck the final FIA plan before production if it provides a conflicting length or topology.
- La Monumental: 24% banking is a slope, equivalent to atan(0.24) = 13.50 degrees. Do not enter 24 as degrees. The [circuit operator's technical page](https://www.madring.com/en/circuit) gives 547.82 m for this corner, mostly 12 m widths elsewhere, and elevation landmarks of 671 m at T2 and 697 m at T7. These are design inputs, not Madring telemetry calibration targets.

## Generated artifacts and checks

- Outline: `F1_Pipeline_Assets/tracks/madring_grand_prix_outline_provisional.json`.
- Outline conversion used length 5414, assumed base width 12, minimum corner radius 9 m. Existing converter smoothing and local hairpin narrowing were retained.
- 2,000 paired stations; measured centreline 5,408.9 m (-0.094% relative to scale input); width min 9.69 / median 12.00 / max 12.00 m.
- Shapely checks: centreline, outer ring, and inner ring are simple; outer polygon contains inner polygon; resulting corridor polygon is valid.
- The legacy outline verifier's width-only pinch check passed, and the preview was visually inspected. Its check alone does not prove absence of intersections; the Shapely results above supply that evidence.
- Preview: `cache/_verify_madring_provisional.png`.
- Verified diagnostic line: `cache/madring_geometry_verified_raceline.json`; CSV: `cache/madring_geometry_verified.csv`; complete log: `cache/madring_geometry_verified.log`.
- The first interrupted run's outputs remain as `cache/madring_geometry_probe_raceline.json` and `cache/madring_geometry_probe.csv`. They match the verified outputs byte-for-byte. No files were deleted.
- On-track check and inspected preview: `cache/_ontrack_madring_provisional.png`. All 2,665 line points inside the corridor under the checker; 0 points beyond the 0.30 m tolerance, worst signed excursion -0.14 m.
- Optimized line length 5,331.70 m; minimum line radius 15.14 m. This is shorter than the input centreline because of racing-line optimization; it was not rescaled to hide the difference.

## Diagnostic lap, not a calibrated prediction

The repeated simulation completed with exit code 0. It used the current default car knobs CDA 0.80, CL 4.20, rho 1.225, existing vehicle-calibration warm-start values, and default 1 m inset. Banking and elevation were absent.

- Lap: 97.537 s (1:37.54), after longitudinal smoothing.
- Speed range: 70–312 km/h (rounded simulator output).
- Sanity: 132 superclip stations; median gain 28.3 and drop 46.5 km/h/s; all built-in sanity bounds passed.
- This validates operation of the geometry pipeline, not Madring lap-time accuracy. No historical lap gate, Madring calibration, or published lap-time claim is justified.

## Required next work

1. Compare topology, real driving direction and exact start/finish against the final event circuit plan. The converter enforces CCW; the simulator reverses to CW. Index zero is currently the automatic straight midpoint proxy (about 288 m before the first major curvature peak), not an independently confirmed timing line.
2. Resolve actual widths around narrow corners. The provisional 9.69 m minimum comes from automatic narrowing, not a surveyed Madring width.
3. Map La Monumental banking in the final S/F-referenced arc frame. Existing `banking_deg` means an EFFECTIVE model angle; do not silently treat surveyed slope as a fitted effective angle. No previous Madring lap exists to fit it from.
4. Set an evidenced altitude/air-density assumption and choose an honest new-circuit calibration method. The usual 2025-reference predictor/autofit/gate cannot be applied directly. Design documentation explicitly leaves Madring out of v1; the proposed physics-inversion fallback is not implemented.
5. Validate that method using other circuits' real 2026 evidence before producing a final lap/video. The old note that Zandvoort is the only meaningfully banked circuit is superseded for Madring.

Probe invocation must explicitly pass a confirmed nonexistent reference path, e.g. `--reference-csv cache/madring_no_reference_geometry_probe.csv`. Omitting the argument silently defaults to a Canada reference and can misplace the lap origin. The nonexistent path was checked before verification and remains intentionally absent.
