# Stream log — us439-lodes — 2026-09-13

## Claim

- **Stream id:** `us439-lodes`
- **Leaf files I will create/edit:**
  `apps/api/src/spatial/lodes_bay_area_pipeline.py` (new module),
  `apps/api/tests/unit/test_lodes_bay_area_pipeline.py` (new tests),
  `PR_DESCRIPTION.md` (worktree root).
- **Spine files I expect to need:** none. This mirrors US-438's
  `acs_dasymetric_pipeline.py` scope: a standalone Bay Area pipeline module +
  tests, not yet wired into snapshot/dashboard/context_source (grep confirmed
  US-438 has zero downstream references outside its own module/tests, so
  US-439 follows the same precedent).

## Intent

Implement US-439: ingest CA LODES v8 WAC + RAC (+ optional OD), filter to the
9 Bay Area FIPS counties (reuse `BAY_AREA_COUNTIES` from `acs_variables.py`),
join block-level job/resident counts to H3 res-9 hexes via crosswalk internal
points, and compute total_jobs, jobs_to_residents_ratio, CNS01-20 industry mix
fractions, and CE01-03 wage tier fractions, tagged with LODES vintage year.
Reuses `download_to_cache`/`state_xwalk_url`/`state_file_url` from
`src.export.national_builder` for fetch/cache consistency with the existing
national LODES builder.

## Decisions

- 2026-09-13 — Scope matches US-438 precedent: leaf-only, no spine edits, no
  downstream wiring (snapshot/dashboard integration left as follow-up, noted
  in PR_DESCRIPTION.md).
- 2026-09-13 — OD commute-flow aggregation (optional per ticket) scoped to
  intra-Bay-Area flows only (both work and home block resolve via the same
  Bay-Area-filtered crosswalk); commutes crossing the 9-county boundary are
  not captured. Documented as a tradeoff in PR_DESCRIPTION.md.

## Current step

Done: pipeline module + tests written, ruff clean, full `verify_cicd_preflight.py`
green (interlock gate, dashboard cross-ref, facts:check, product lint, dashboard
export, ruff), `PR_DESCRIPTION.md` written at worktree root. No spine files touched.

## Next step

Handed off — human reviews and commits. If resumed: nothing outstanding; only
follow-ups noted in `PR_DESCRIPTION.md` (Notes) are downstream wiring into
snapshot/dashboard, which is out of scope for this ticket (mirrors US-438).
