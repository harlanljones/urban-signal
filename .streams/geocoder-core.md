# Stream log — geocoder-core — 2026-08-24

## Claim

- **Stream id:** `geocoder-core` (Linear US-28, claimed --assignee self)
- **Leaf files I will create/edit:** `apps/api/src/spatial/geocoder.py`,
  `apps/api/tests/unit/test_geocoder.py`,
  `apps/api/tests/unit/test_spatial_enrichment_worker.py`,
  `docs/adr/0004-address-geocoding.md`
- **Spine files I expect to need:** `apps/api/src/consumers/
spatial_enrichment_worker.py` (the single sanctioned spine touch),
  `apps/api/src/config.py` (geocoder settings block)

## Intent

Wave G1 (D6): deterministic, self-hostable, Postgres-cached,
confidence-gated address geocoding. Unblocks G2/G3/G4 (US-75/73/74/94).
Acceptance: >=95% hit on Norfolk 311 newest 500; determinism proven twice
across a cache flush; coord_source flag on enriched records; ADR 0004.

## Decisions

- 2026-08-24 — Backend-pluggable: CensusBatchBackend ships for self-host
  parity (plan's named substrate) but its public endpoint is unreachable
  from this environment (egress); NominatimBackend (self-hostable URL,
  public instance usable for verification at 1 rps) serves acceptance runs.
  The Postgres cache is THE determinism guarantee: coordinates frozen at
  first success, definitive misses also cached so replays never drift.
- 2026-08-24 — Confidence gated at READ time against the current floor so
  policy can tighten without re-hitting providers; raw cached values are
  immutable.
- 2026-08-24 — coord_source stamped on enriched records in the worker
  ("native" / backend source / absent-on-skip); persistence into feature
  tables deliberately deferred to retrain-prep (W7 boundary documented in ADR).

## Outcome (2026-08-24)

Completed. Leaf: geocoder.py (normalizer v1, PostgresGeocodeCache with frozen
misses, NominatimBackend with corroboration scoring, CensusBatchBackend for
self-host parity, cache-first Geocoder with read-time gating); worker spine
touch (address-only records geocode + coord_source stamped; native stamped;
legacy no-geocoder behavior preserved when unconfigured); config gained
geocode_confidence_floor + nominatim_base_url.

**Acceptance evidence (live):**
1. Hit rate: Norfolk 311 newest 500 rows → 493 carried a location string;
   **469/493 = 95.13%** geocoded above floor (pass 2 post-flush: 470/494 =
   95.12%).
2. Determinism: snapshot 351 cached hashes → DELETE all → re-geocode same
   rows via live provider again → **350/350 identical**, including 23
   frozen misses (327 coordinates byte-identical).
3. coord_source: pinned by worker tests ("native" / backend source / absent
   on skip).
4. ADR 0004 recorded (fills the number; HJ-114's ADR is 0005 per its ticket).

Gates: interlock 20 passed; full suite 636 passed / 3 skipped / 0 failed
(+21 tests); ruff clean on new files.
