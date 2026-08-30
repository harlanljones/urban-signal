# Stream log — us399-asheville-deeds — 2026-08-30

## Claim

- **Stream id:** `us399-asheville-deeds`
- **Leaf files I will create/edit:** `apps/api/src/producers/asheville_deeds_spec.py` +
  `apps/api/src/producers/field_maps_asheville_deeds.py` +
  `apps/api/tests/unit/test_asheville_deeds_spec.py` + `.streams/us399-asheville-deeds.md`
- **Spine files I expect to need:** `apps/api/src/config.py`,
  `apps/api/src/spatial/city_registry.py` (NOT edited in this phase — the
  orchestrator applies the spine delta serially)

## Intent

Register the Buncombe County (NC) property roll (ArcGIS FeatureServer, polygon,
135k parcels) as a supplemental DEEDS feed for Asheville, NC. Price is
reconstructed client-side as `Stamps × 500` (NC excise stamps: $1 per $500 or
fraction). One `DatasetSpec`-shaped plain dict in `asheville_deeds_spec.py` that
constructs via `DatasetSpec(**spec)` with zero massaging, a field map in
`field_maps_asheville_deeds.py` keyed to the `deeds` FeedType canonical keys,
and unit tests proving shape/keys/watermark/mode and the price-reconstruction
helper. Labeled honestly: roll-grade (last sale per parcel), snapshot cadence,
not an event stream. Done means tests pass, ruff is clean, and the spine has a
copy-pasteable contract.

## Decisions

- 2026-08-30 — Field names verified live: Buncombe Property layer has 53
  fields, polygon geometry, OID=objectid, maxRecordCount=2000.
  `SalePrice` is zeroed on every sampled row; `Stamps` is populated (57% of
  parcels).  `DeedDate` is YYYYMMDD text (watermark).  `Instrument` = WDT, SWD,
  ADJ etc.  `Owner` = current owner (last grantee).
- 2026-08-30 — Price reconstruction: `Stamps × 500` (NC excise stamps $1 per
  $500 or fraction).  Caveat: overstates sub-$500 sales.
- 2026-08-30 — Non-arm's-length filter: `Instrument` in {ADJ, CA, DR, GC, GV,
  PL, UX, VE} or `Reason` in {AL, ATT, BS, CO, CV, ES, FD, FT, GC, GV, LO,
  NA, OT, SP, TF, TX, VC} → exclude from price signal.
- 2026-08-30 — `party1_grantor` / `party2_grantee` both map to `Owner` (the
  current owner is the last grantee).  `document_amount` maps to `Stamps` —
  `reconstruct_price` applied client-side.

## Current step

Leaf files complete.  Tests pass (70/70).  Ruff clean.

## Next step

Spine delta: add `settings.arcgis_asheville_deeds_url` to config.py, register
`FeedType.DEEDS` on `REGISTRY[CityId.ASHEVILLE]` with `ASHEVILLE_DEEDS_SPEC`,
import field map from `field_maps_asheville_deeds.py`.