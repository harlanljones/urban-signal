# Stream log — us443-overture — 2026-09-13

## Claim

- **Stream id:** `us443-overture`
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/overture_client.py` (new — DuckDB remote GeoParquet reader for
    Overture buildings/places themes, bbox-filtered to the 9-county Bay Area)
  - `apps/api/src/spatial/overture_density.py` (new — per-H3-res-9 building stock + POI
    density metrics, class/category mix, building_density_weight, commercial churn)
  - `apps/api/src/spatial/overture_pipeline.py` (new — end-to-end orchestration:
    fetch/accept rows -> per-hex metrics -> dasymetric-mask export, ODbL attribution
    metadata)
  - `apps/api/src/spatial/context_source.py` (leaf, not spine — registers
    `ContextSourceId.OVERTURE_BUILDINGS` / `OVERTURE_PLACES` with ODbL attribution,
    same pattern as LODES/ZBP)
  - `apps/api/tests/unit/test_overture_client.py`,
    `test_overture_density.py`, `test_overture_pipeline.py` (new)
- **Spine files I expect to need:** none. `context_source.py` is registry-shaped like
  spine but is NOT in `docs/agents/spine-manifest.txt` — confirmed by reading the
  manifest before editing. No producer/scheduler/city_registry changes needed;
  US-438 (`acs_dasymetric.py` / `acs_dasymetric_pipeline.py`) already accepts an
  externally-supplied `buildings` sequence, so wiring Overture footprints into the
  Ticket-3 dasymetric join needs no spine edit — Overture footprint geometries are
  simply passed as the `buildings=` argument to
  `run_bay_area_acs_dasymetric_pipeline`.

## Intent

Implement US-443: query Overture Maps buildings + places GeoParquet themes for the
9-county Bay Area bbox via DuckDB remote GeoParquet, compute per-H3-res-9 building
stock metrics (count, footprint area, avg height, class mix, normalized
`building_density_weight`) and POI metrics (density, category mix, commercial churn
between releases), and make the building footprint layer consumable as the
dasymetric weighting mask already built in US-438. Prior research
(`docs/research/overture-maps-evaluation.md`, stream `signal-overture`) deferred
Overture as an *event feed* (no watermark/FeedType fit) but confirmed the DuckDB
GeoParquet access pattern, bbox pruning, ODbL license, and 60-day retention —
this stream builds the actual ingestion + metrics module as a context-source
(same shape as LODES/ZBP), not a producer.

## Decisions

- 2026-09-13 — Read `docs/agents/parallel-streams.md` and `spine-manifest.txt` first.
  Confirmed `context_source.py` is a leaf (not listed in the manifest) despite being
  a shared registry, so it can be edited without interlock. `bay_area_boundary.py`
  already exports the canonical `BAY_AREA_METRO_BBOX` (wider than the ticket's
  approximate bbox on two sides, to avoid clipping the Sonoma coast/Napa tip) —
  reusing it instead of the ticket's literal numbers.
- 2026-09-13 — Verified `duckdb` `spatial` + `httpfs` extensions load offline in this
  environment (already installed/cached), matching `tiger_client.py`'s
  `ST_AsText`/WKT pattern. Will build Overture queries the same way rather than
  parsing raw WKB.
- 2026-09-13 — Design: buildings assigned to H3 res-9 by polygon centroid (ticket
  allows centroid OR intersection; centroid is O(1) per building and matches the
  ticket's own DuckDB query pattern, which selects `geometry` directly). Note this
  tradeoff in PR_DESCRIPTION.md.
- 2026-09-13 — Commercial churn computed by GERS-ID set diff between two release's
  per-hex POI id sets (appearances minus disappearances), not a naive count delta,
  per the prior research doc's finding that naive delta over-counts matcher churn.

## Current step

Done. All four new/edited leaf files written; 24 new unit tests pass
(`test_overture_client.py`, `test_overture_density.py`,
`test_overture_pipeline.py`, plus two added assertions in
`test_context_source.py`); `pytest -m interlock` from `apps/api` passes (35
tests, unaffected — no spine touched); full `scripts/verify_cicd_preflight.py`
passes all six gates (interlock, dashboard/product cross-ref, product facts
drift, product lint, dashboard export, ruff on changed files). `PR_DESCRIPTION.md`
written at the worktree root.

## Next step

None — ticket complete, no spine work required. If promoted further: swap the
substring POI-category classifier for Overture's actual taxonomy hierarchy
(`categories.primary` + `taxonomy` reference table) once a Ticket needs
category-mix precision beyond the six coarse buckets, and consider
polygon-intersection (not just centroid) building assignment if a future
ticket needs footprint-area splitting across hex boundaries.
