# MC311 Geocode Evaluation (Wave G4, US-94)

**Date:** 2026-08-24
**Verdict:** REJECTED — the address path resolves nothing; exclusion now
rests on measurement, not assumption.

## Source

`data.montgomerycountymd.gov/resource/xtyh-brr2.json` ("MC311 Service
Requests"), sampled newest 300 rows by `created DESC` on 2026-08-24.

The schema carries **no street address and no coordinates**: geographic
context is polygon-attribute only (`x_zipcode`, `x_city`, `x_state`,
`x_councildist`, `x_congdist`, `x_mdstatedist`, plus SLA bookkeeping).
Zip population in the sample was healthy (`20902`, `20854`, `20895`, …),
so this is not a data-quality miss — it is the feed's design.

## Measured result

Candidate queries were built exactly as a registration would
(`"{x_city}, {x_zipcode}"`, normalized per ADR 0004) and run through the
real cache-first Census TIGER backend:

| outcome | count | share |
|---|---|---|
| provider hit (any confidence) | **0** | **0.0%** |
| provider miss | 294 | 98.0% |
| no zip present at all | 6 | 2.0% |

Confidence distribution of hits: **empty** — there is no "confident but
wrong" tail to argue about, because Census `onelineaddress` requires a house
number and returns no match for ZIP-only input *by design*.

## Why this closes the ticket as a rejection

- G5′ (≥95% events with resolved coordinates) fails at **0%** — not marginally.
- The plan-risk W2 scenario (a zip centroid is precisely the confident-but-
  wrong coordinate) never materializes here: the measured failure mode is
  total absence of resolution, which is safer than a centroid and still
  disqualifying. Lowering the confidence floor cannot help — there are no
  candidates to floor. Registering via a static ZIP-centroid table would be
  manufacturing exactly the coordinate W2 exists to block, and is refused.
- Montgomery keeps its registered permits + ABS licenses feeds unchanged;
  MC311 remains excluded, now pinned by test rather than by the original
  construction argument alone.

## Revisit conditions

A future registration becomes evaluable only if Montgomery adds street-level
location fields (address or point geometry) to the SODA resource, or if a
parcel/address join key appears that D6-amendable scope could consume.
