# Stream log — us122-qcew — 2026-08-25

## Claim

- **Stream id:** `us122-qcew`
- **Leaf files I will create/edit:** `docs/research/bls-qcew-validation.md`
- **Spine files I expect to need:** none (read-only research stream)

## Intent

Validate BLS QCEW as a slow-moving economic-context feature: quarterly employment,
establishments, wages by industry at county/MSA geography. Verdict must be one of:
register/reject/defer, backed by evidence on publication lag, revisions, suppression,
NAICS/geography versioning, recent MSA-delivery changes, and incremental explanatory
value against LODES and BFS in walk-forward context.

## Decisions

- <appended as found>

## Findings (2026-08-25)

**Verdict: DEFER (conditional register-later).** Source/distribution excellent
(keyless public-domain CSV slices at `data.bls.gov/cew/data/api/<yr>/<qtr>/area/<code>.csv`,
confirmed live), but QCEW is the coarsest (county/MSA), most-lagged (~2 quarters), and
most version-fragile signal in the wave, and its employment axis is redundant with LODES
(same UI-wage-record universe). Register only after LODES/BFS land and only for the
axes they lack (quarterly metro wages + establishment counts), keyed with
`naics_version` + `area_version` + disclosure masks.

Evidence (BLS docs via Wayback since www.bls.gov 403s to this env; empirical probes via
live data.bls.gov):
- Lag: newest quarter = **2025 Q4**; 2026 Q1 → HTTP 404 (verified live).
- MSA codes are **C-prefixed** 5-char (`C3538` New Orleans-Metairie; `C4726` Virginia
  Beach-Chesapeake-Norfolk); bare `35380` 404s. County FIPS 5-char.
- **2023 OMB MSA delineation** effective 2024 Q1 (history NOT re-tabulated): `C3538`
  2024 Q1 shows **−17.5% employment, −21.7% establishments** year-over-year — an admin
  artifact, not economic (verified live). Norfolk-area MSA renamed. Prefer county→aggregate
  over C-coded MSA series; never stitch MSA across the 2024 Q1 seam.
- Suppression: `disclosure_code='N'` + `empl=0` placeholder; **St. Bernard (22087) 2023
  Q1 = 734/968 rows (~76%) suppressed** at county×industry detail (verified live). Treat
  suppressed as NaN, never zero; restrict NAICS detail to large counties / 2–3-digit cuts.
- NAICS 2022 in force from 2022 Q1 (next ≈2027); 3-yr establishment classification
  re-verification back-loaded to Q1. BLS: "QCEW data are not designed as a time series"
  (admin discontinuities at Q1: 2008, 2011, 2014).
- Whole-area outage risk: Colorado industry+substate suspended Nov 2024→Feb 2025 (UI
  modernization). QCEW moved to a single data release at 2024 Q4.
- Revision: Q1 published 5×→finalized ~Sept next year; establishments ±~1%, employment/
  wages ±~0.1% initial→final.
- Access to LODES (lehd.ces.census.gov) and BFS (census.gov/econ/bfs) confirmed HTTP 200.

**Two-metro validation anchor:** New Orleans (C3538; 22071/22051/22087) + Norfolk/Hampton
Roads (C4726; 51710/51810/51550).

**Blockers / unverified:** (1) BLS terms-of-use page not reachable (terms inferred from
public-domain U.S. gov data + keyless endpoints); (2) exact live page language not
confirmed (Wayback copies only); (3) LODES/BFS validation docs (us101/us102) not written
at time of writing → those comparisons are provisional.

## Current step

Dispatched 2026-08-25 as part of the 5-stream validation wave.

## Next step

Produce `docs/research/bls-qcew-validation.md` with the validation verdict.
