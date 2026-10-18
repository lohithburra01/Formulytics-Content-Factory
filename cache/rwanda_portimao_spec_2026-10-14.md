# Week of 2026-10-14: two new cars (spec draft, awaiting user OK + SVGs)

## A) Rwanda (Bugesera, ~40 km from Kigali) - "2030 V8" F1 car
News 2026-10-13: F1 10-year deal with Rwanda, first race "early 2030s" (2030 at earliest).
Layout (design only, not built): ~6 km, 17 corners, ~197 m elevation change/lap. Altitude ~1.4-1.5 km -> rho ~0.86x sea level.
FIA (Ben Sulayem, same event): V8 return targeted for 2030 (needs 4/6 manufacturers, else forced in 2031).
NOT in regulations yet. Reported:
- V8, "can't get the power with less than 2.5-2.6 L" -> 2.6-3.0 L range; Motor Sport reports 3.0 L turbo
- electric "very minimal": reported MGU-K ~100 kW (vs 350 kW in 2026)
- car ~80 kg lighter target (no rulebook figure), PU >=50 kg lighter, engine cost -50%
- fully sustainable fuel (as 2026)
Proposed sim car = 2026 chassis/aero baseline (no 2030 chassis rules published) with:
- ICE ~ 560-600 kW (assumption: ICE carries most of a ~650-700 kW total) + MGU-K 100 kW
- mass 768 - 80 = ~688 kg (assumption from the reported target)
- small battery -> little/no clipping; active aero kept? (open question for user)
- ICE power x altitude derate if naturally aspirated; turbo = mostly compensated (assume turbo)
No calibration possible: fleet-median CdA/CL (noref method A); report as a prediction with a band.

## B) Portimao - Mercedes-AMG GT3 EVO (Verstappen Racing #3, GTWC Endurance finale)
Weekend 16-18 Oct 2026; Q Fri 16 Oct 17:55 local; 3 h race Sat 17 Oct 17:00 BST.
GTWC Europe last at Portimao 2015. GT Open 2025 opened at Portimao (GT3 field) = real reference lap.
Known: 6.3 L NA V8 (team sheet), ~1285 kg base, BoP-set weight & restrictor (SRO BoP bulletin for the event needed),
no hybrid, no active aero, ABS + TC allowed, slick Pirelli.
Unknown publicly: CdA, CL -> fit to the real GT3 Portimao lap (GT Open) + Friday FP/Q as verification.
Sim-racing setup sheets = suspension/wing settings, NOT physics constants; usable only as a sanity check.
