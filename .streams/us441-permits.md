# Stream log — us441-permits — 2026-09-13

## Claim

- **Stream id:** us441-permits
- **Leaf files created/edited:**
  - `apps/api/src/features/permit_taxonomy.py` (new — unified permit-type enum + per-jurisdiction normalizer)
  - `apps/api/tests/unit/test_permit_taxonomy.py` (new)
  - `apps/api/src/features/bay_area_permit_momentum.py` (new — permit_velocity_60_180, capex_density_decayed @ 60d half-life, residential_unit_delta, per-hex aggregator)
  - `apps/api/tests/unit/test_bay_area_permit_momentum.py` (new)
  - `apps/api/src/spatial/geocoder.py` (extend — cache hit/miss counters + hit-rate logging on `Geocoder.geocode`/`geocode_many`)
  - `apps/api/tests/unit/test_geocoder_cache_metrics.py` (new)
  - `apps/api/src/schemas/models.py` (extend — add `PermitEvent.normalized_permit_type`; not spine-listed)
  - `apps/api/src/schemas/avro/permit_event.avsc` (extend — mirror the new optional field; not spine-listed)
- **Spine files touched:**
  - `apps/api/src/producers/dob_permits_producer.py` — one small additive block: call
    `normalize_permit_type()` after `job_type` is resolved and set the result on
    the constructed `PermitEvent`. No control-flow changes, no other spine file
    touched (see "Decisions" below for why the originally-planned
    `city_registry.py` / `config.py` edits were dropped).

## Intent

US-441: multi-jurisdiction Bay Area building-permit ingest with geocoded H3
res-9 point join, unified permit-type taxonomy, and three derived per-hex
momentum features (permit_velocity_60_180, capex_density_decayed @
configurable half-life default 60d, residential_unit_delta).

## Decisions

- **2026-09-13 — Exhaustive live-endpoint verification, revised down from the
  initial plan.** Originally planned to register Santa Clara County (new) and
  extend Oakland with a `permits` feed to hit "4 jurisdictions incl. >=1
  county". Live-probed every ticket-specified source before writing any
  registration:
  - **Oakland** (`352t-2pt2`): does not resolve. The *existing* `oakland.py`
    module already documents (US-223) a full catalog enumeration — 313
    datasets probed 2026-08-28, zero permit hits — and explicitly states
    "do not register ... any permits/SLA/deeds feed — none exist". Adding a
    permits feed here would contradict a prior agent's confirmed finding
    baked into the codebase.
  - **Santa Clara County** (`sccgov.data.socrata.com`): enumerated the full
    ~90-dataset catalog via Socrata's catalog API. No building-permits
    dataset exists; the only permit-adjacent hits are Environmental Health
    "Plan Check"/food-facility trackers (`awpi-tuz7`, `skd7-7ix3`), not
    building permits.
  - **Alameda County** (`data.acgov.org`, ArcGIS Hub): enumerated the full
    145-item catalog via the Hub's own search API. Zero permit/building
    datasets (parcels, assessor rolls, crime, districts — no permits).
  - **Contra Costa County** (`gis.cccounty.us`): enumerated the ArcGIS REST
    services root — all folders visible (`Assessor`, `PublicWorks`, `EHSD`,
    `ConFire`, etc.); no `DCD`/building/permits folder or service exists.
  - **Marin County**: `opendata.marincounty.org` / `gis.marincounty.org` do
    not resolve at all (connection failure).
  - **San Mateo County** (`data.smcgov.org`, Socrata): enumerated the full
    88-dataset catalog. No permits dataset (parks, transit, zoning,
    boundaries — no permits).

  Given the repo's own precedent (Oakland's explicit refusal to register a
  confirmed-nonexistent feed) and that a "best-effort unverified endpoint" is
  only defensible when there's a *plausible* URL to construct (e.g.
  Harrisburg's ArcGIS FeatureServer guess following a real naming
  convention) — not when the entire real catalog was enumerated and
  confirmed absent — **no new city/county registration was added**, and
  Oakland's permits feed was **not** added. This means the `city_registry.py`
  (`CityId.SANTA_CLARA_COUNTY`) and `config.py`
  (`socrata_oakland_permits_endpoint` /
  `socrata_santa_clara_county_permits_endpoint`) spine edits originally
  planned are **dropped** — there is no real endpoint to declare.
  Documented exhaustively in PR_DESCRIPTION.md as a known AC gap with a
  concrete follow-up recommendation (human-sourced county permits API, e.g.
  direct county IT/GIS outreach or an Accela data-feed subscription — these
  systems are frequently not exposed as public bulk APIs at the county
  level, unlike city building departments).
- `permit_velocity_60_180`, `capex_density_decayed`, `residential_unit_delta`
  are implemented as a new standalone leaf module
  (`bay_area_permit_momentum.py`) rather than by editing the shared national
  `features/pipeline.py` — that pipeline already computes a differently
  defined `permit_velocity`/`capex_density_decayed` (180d half-life) consumed
  by LIMS/`EnrichedH3Feature` across every registered city; changing its
  formula would silently alter every city's existing score. The new module
  reuses `TimeDecayedCapExCalculator` (parameterized half-life) so the decay
  math itself is not duplicated.
- Added `PermitEvent.normalized_permit_type` (optional, default `None`, both
  Pydantic model and Avro schema) and wired `normalize_permit_type()` into
  `DOBPermitsProducer.parse_socrata_row` so every permit — SF, San Jose, and
  every other already-registered permit-emitting city — gets the unified
  taxonomy value at ingest time, not just as an unused standalone module.
- Geocoder cache-hit-rate: added `prometheus_client.Counter` metrics plus a
  periodic `logger.info` summary (every 100 lookups) and a
  `Geocoder.cache_hit_rate()` accessor; wired into both `geocode()` and
  `geocode_many()` (batch-backend path counts once per address; the
  no-batch-backend fallback delegates to `geocode()`, which records its own
  lookup, to avoid double-counting).

## Current step

**DONE.** All leaf work + the one small spine edit implemented, tested, and
verified. `pytest -m interlock` green. Full `scripts/verify_cicd_preflight.py`
green (all 6 gates: interlock, dashboard↔product cross-ref, facts:check,
product lint, dashboard export byte-sync, ruff check). `PR_DESCRIPTION.md`
written at repo root (replacing a stale leftover from the already-merged
US-437 PR that was still sitting in the tree). No regressions vs. clean
baseline (verified via `git stash`/`git stash pop` A/B comparison on the 16
pre-existing full-suite failures).

## Next step

None — implementation complete. Left uncommitted for the human/dispatcher to
review and commit, per the no-commit/no-push/no-PR rule. Left this stream log
file uncommitted as well, per instructions.
