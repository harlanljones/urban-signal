# Stream log — montgomery-g4 — 2026-08-24

## Outcome (2026-08-24)

Completed as a DOCUMENTED REJECTION (the ticket's acceptable branch).

MC311 (xtyh-brr2) carries polygon attributes only — no street address, no
coordinates. Measured live over the newest 300 rows through the real
cache-first Census backend: 0/294 zip-only queries resolved any coordinate;
6 rows had no zip at all; confidence distribution of hits is EMPTY (Census
onelineaddress requires a house number, so ZIP-only input misses by design).
G5' fails at 0%, and the W2 zip-centroid workaround is refused on principle —
lowering the floor cannot help when there are no candidates to floor.

Evidence doc: docs/research/mc311-geocode-evaluation.md.
Test pin: test_producers_montgomery.py::test_mc311_rejection_rests_on_measurement.

Montgomery keeps permits + ABS licenses; MC311 exclusion now rests on
measurement instead of the original construction argument.

Gates: interlock 20 passed; full suite 672 passed / 3 skipped / 0 failed.
