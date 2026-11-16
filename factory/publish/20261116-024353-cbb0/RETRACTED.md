# Retracted (kept as evidence)

Run `20261116-024353-cbb0` passed every gate and was queued, but review found that its caption says
"this anticlockwise 7-corner circuit". The 7 is the number of *calibration* corners in the predicted
targets; Interlagos has 15 turns. The claims gate only checked numbers with two or more digits, so
the single digit got through. The hook "0.973s off the pole" was also ambiguous: it is the gap to the
**2025** pole.

Fix (same day): the claims gate now checks every number (`formulytics/gates.py`, `_NUM`); this caption
is a regression test (`tests/test_factory.py::test_claims_supported`); and `get_verified_facts` now
tells the packager what each number means. Re-gated with the new code, this post fails
`claims_supported`. It is not distributed.
