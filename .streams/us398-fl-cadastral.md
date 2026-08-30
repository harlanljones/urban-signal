# Stream log — us398-fl-cadastral — 2026-08-30

## Claim

- **Stream id:** `us398-fl-cadastral`
- **Leaf files I will create/edit:** `apps/api/src/producers/fl_cadastral_spec.py` +
  `apps/api/src/producers/field_maps_fl_cadastral.py` +
  `apps/api/tests/unit/test_fl_cadastral_spec.py` + `.streams/us398-fl-cadastral.md`
- **Spine files I expect to need:** `apps/api/src/config.py`,
  `apps/api/src/spatial/city_registry.py` (NOT edited in this phase — the
  orchestrator applies the spine delta serially)

## Intent

Register the FL Statewide Cadastral (ArcGIS FeatureServer, polygon, assessment-
derived) as a construction-activity proxy for the eight FL metros that are
currently permits-missing or 1–2-feed: Ocala, Orlando, Lakeland, Melbourne/Palm
Bay, Port St. Lucie, Gainesville, Cape Coral, and Tallahassee (upgrade). One
`DatasetSpec`-shaped plain dict in `fl_cadastral_spec.py` that constructs via
`DatasetSpec(**spec)` with zero massaging, a field map in
`field_maps_fl_cadastral.py` keyed to the `permits` FeedType canonical keys, and
unit tests proving shape/keys/watermark/mode. County code → metro resolution
rides the existing `geography_crosswalk.city_for_county_fips`. Done means tests
pass, ruff is clean, and the spine has a copy-pasteable contract.

## Decisions

- 2026-08-30 — Field names verified live: both endpoints reachable from this
  host (ArcGIS FeatureServer metadata + sample rows).  FL cadastral has 121
  fields, polygon geometry, OID=OBJECTID, maxRecordCount=2000.  Buncombe has
  53 fields, polygon, OID=objectid, maxRecordCount=2000.
- 2026-08-30 — Wrote `FL_COUNTY_CODE_TO_FIPS` mapping (FDOR code 01–67 → 5-digit
  FIPS).  Dade/Miami-Dade is FIPS 12086 at FDOR 13, which breaks any simple
  "12 + zero-padded CO_NO" derivation — spelled out in full.
- 2026-08-30 — FL cadastral field map intentionally omits `job_type` (the
  producer's NB/DM/A1/A2 classification is not derivable from this source).
  The construction signal is `EFF_YR_BLT` within 1–3 years of `ASMNT_YR`,
  wired by the spine at the feature level.
- 2026-08-30 — Buncombe `document_amount` maps to `Stamps` (not `SalePrice`,
  which is zeroed on every row).  `reconstruct_price(stamps)` helper =
  `stamps × 500` with the small-sale caveat documented.
- 2026-08-30 — Buncombe `party1_grantor` / `party2_grantee` both map to `Owner`
  (the current owner is the last grantee in a per-parcel last-sale roll).
  `is_arms_length` helper filters on `Instrument` / `Reason` codes.

## Current step

Leaf files complete.  Tests pass (70/70).  Ruff clean.

## Next step

### FL cadastral spine delta (per metro)

For each FL metro, the orchestrator:
1. Adds `settings.arcgis_fl_cadastral_url` to config.py (the endpoint constant).
2. Registers `FeedType.PERMITS` with `fl_cadastral_spec(cono)` where `cono` is
   the metro's FDOR county code, or None for the ongoing statewide slice, and
   picks up the field map from `field_maps_fl_cadastral.py`.
3. Creates a `METRO_META` entry if the metro is new (not needed for the 8
   target metros — all are registered).
4. Resolves county → metro via `geography_crosswalk.city_for_county_fips(fips)`
   using `FL_COUNTY_CODE_TO_FIPS`.

### Asheville deeds spine delta

1. Adds `settings.arcgis_asheville_deeds_url` to config.py.
2. Registers `FeedType.DEEDS` on `REGISTRY[CityId.ASHEVILLE]` with
   `ASHEVILLE_DEEDS_SPEC`.
3. Imports `ASHEVILLE_DEEDS_FIELD_MAP` from
   `src.producers.field_maps_asheville_deeds` into city_registry.py.
4. Scheduler picks up the `deeds` producer_key automatically (no scheduler.py
   change needed outside the spine manifest).