# Stream log — us101-lodes — 2026-08-25

## Claim

- **Stream id:** `us101-lodes`
- **Leaf files I will create/edit:** `docs/research/census-lodes-validation.md`
- **Spine files I expect to need:** none (read-only research stream)

## Intent

Validate Census LEHD LODES as a slow-moving contextual spatial signal for Urban
Signal: workplace concentration, residence-to-work flows, worker/job composition.
Verdict must be one of: register/reject/defer, backed by evidence on access, terms,
geography crosswalk, release lag, volume, reproducibility, and incremental value
against existing feed-derived signals.

## Decisions

- **2026-08-25 — VERDICT: DEFER** → `docs/research/census-lodes-validation.md`.
  Data side fully proven; integration model is the blocker.
- Access/terms: public-domain federal data; anonymous `curl` download of LODES8
  per-state gz verified (no API key / auth).
- Granularity: census block (2020 blocks, 2024 TIGER) — FINER than H3 res 7–9, so
  no BFS-style granularity mismatch. Crosswalk emits block internal-point
  `blklatdd`/`blklondd` (no TIGER geometry file needed) + FIPS/cty/cbsa/place codes.
- Coverage: 2002–2023, 51 states; LA & VA fully covered. Reference period Q2
  (Apr–Jun); job = "beginning-of-quarter" stock (ref + prior quarter). Disclosure:
  "partially synthetic", CBDRB-FY21-249.
- Latency: LODES8 dir last-modified 2025-12-12; 2023 data ≈ 28-month lag. Annual
  file-drop cadence (formal calendar unverified).
- Volume (measured, 2023 JT00 S000): LA OD main 1,631,945 rows / 9.8MB gz; VA
  3,062,303 / 18.3MB. WAC LA 35,876 blk=1,895,919 jobs; VA 55,775=3,894,892. RAC
  LA 88,415=1,881,792; VA 114,163=3,924,600. Crosswalk LA 2.5MB / VA 2.9MB.
- Metro (measured): NOLA bbox 20,484 blocks → H3 res7/8/9 = 280/1,189/4,663; WAC
  7,211 blk=404,544 jobs; RAC 13,507=351,623. Norfolk bbox 4,271 → res9 1,216;
  WAC 1,488=130,869; RAC 3,028=90,578. NOLA OD rows (work/live/both in metro)
  368,511/322,254/261,696.
- Unblock path: new WORKFORCE/JOB_DENSITY signal family + bulk-file producer +
  H3-aggregate storage (spine/interlock change) + a context consumer; if they
  land, register NOLA + Norfolk first as year-over-year level context at
  division/submarket + H3 7–9, pinned to LODES8 2020-geo vintage + SHA-256.

## Current step

Dispatched 2026-08-25 as part of the 5-stream validation wave.

## Next step

Produce `docs/research/census-lodes-validation.md` with the validation verdict.
