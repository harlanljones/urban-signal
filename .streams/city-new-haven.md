# Stream log — city-new-haven — 2026-08-30

## Claim

- **Stream id:** `city-new-haven`
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/new_haven.py` (new)
  - `apps/api/src/producers/field_maps_new_haven.py` (new)
  - `apps/api/tests/unit/test_producers_new_haven.py` (new)
  - `.streams/city-new-haven.md` (this file)
- **Spine files I expect to need:** `config.py`, `city_registry.py`,
  `cities/__init__.py`, `serving/dashboard.py` (METRO_META + byte-synced
  `apps/dashboard/public/index.html`), `apps/product/public/facts.json`
  (+ `apps/product/cities/*.json`), `tests/unit/test_city_leaf_naming.py`
  (leaf-count pin). **None touched by this leaf.**

## Intent

Build the New Haven, CT leaf for US-419 as a leaf-local module set that the
spine copies into REGISTRY in a later hold. New Haven is a TWO-FEED metro on
Connecticut's statewide Socrata portal (`data.ct.gov`): SLA (State Licenses
and Credentials, `ngch-56tr`) and DEEDS (Real Estate Conveyance Tax /
property sales, `5mzw-sjtu`) — the same statewide feeds Hartford already
carries, filtered to New Haven. Both are address-only (SLA has no native
coords; DEEDS carries a `geo_coordinates` Point the shared deeds producer
does not yet read), so both declare `needs_geocode=True`.

## Decisions

- 2026-08-30 — SLA id_keys `["credentialid"]` (verified unique: 47,001
  rows = 47,001 distinct `credentialid`). Watermark `recordrefreshedon` has
  **0 nulls** (max 2026-08-30, min 2004-04-23) — no `IS NOT NULL` guard
  needed (unlike Buffalo). Daily refresh cadence (distinct refresh values
  run 2026-08-30, -29, -28, …).
- 2026-08-30 — DEEDS `serialnumber` is **NOT row-unique** within
  `town='New Haven'`: 25,907 distinct vs 25,909 rows. The two collisions are
  `serialnumber` 10321 and 10412, each appearing in BOTH `listyear` 2001 and
  2010 for entirely different parcels — the sequence resets/reuses across
  assessment years (22 distinct `listyear` values). **Composite id_keys
  `["serialnumber", "listyear"]`**.
- 2026-08-30 — DEEDS `daterecorded` has **0 nulls** (watermark clean).
  `geo_coordinates` present on 8,421/25,909 rows (32.5%); 17,488 null. The
  shared `deeds_acris_producer` nested-loc fallback reads
  `the_geom`/`point`/`location`/`georeference`/`shape`/`mappable_latitude_and_longitude`
  but NOT `geo_coordinates`, so even the 32.5% native points are dropped
  today — `needs_geocode=True` (address fallback) is correct. **Spine TODO:
  add `geo_coordinates` to that fallback list so native coords are used
  first.**
- 2026-08-30 — SLA `type` (INDIVIDUAL/BUSINESS/CORPORATION), `active`
  (0/1), `statusreason`, `credentialnumber` exist on the wire but are NOT
  field-map candidates. `businessname` is present only on BUSINESS/
  CORPORATION rows; `name` carries the holder on INDIVIDUAL rows, so
  `premises_name`/`dba` both read `["businessname", "name"]`.
- 2026-08-30 — DEEDS `doc_type` maps `propertytype` (property
  classification: "Residential"/"Condo"/"Single Family"), NOT a deed
  instrument type — there is no deed-type column on this feed. `document_amount`
  maps `saleamount` (the `assessedvalue` column is underscore-free
  `assessedvalue`, so it does not shadow the `assessed_value` chain term and
  `saleamount` wins).

## Current step

Writing leaf files + tests; then running the three gate commands.

## Next step

Run `pytest tests/unit/test_producers_new_haven.py -q`, `pytest -m interlock -q`,
`pytest -k new_haven -q`; report SPINE DELTA.
