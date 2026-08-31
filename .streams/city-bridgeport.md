# Stream log — city-bridgeport — 2026-08-30

## Claim

- **Stream id:** `city-bridgeport`
- **Leaf files I will create:**
  - `apps/api/src/spatial/cities/bridgeport.py`
  - `apps/api/src/producers/field_maps_bridgeport.py`
  - `apps/api/tests/unit/test_producers_bridgeport.py`
  - `.streams/city-bridgeport.md` (this file)
- **Spine files I expect to need (NOT edited here):**
  - `apps/api/src/config.py` (new `socrata_ct_sla_endpoint`, `socrata_ct_deeds_endpoint`)
  - `apps/api/src/spatial/city_registry.py` (`CityId.BRIDGEPORT`, aliases, `CityRegistration`)
  - `apps/api/src/spatial/cities/__init__.py` (auto-gathers via US-429 — no manual edit)
  - `apps/api/src/serving/dashboard.py` + `apps/dashboard/public/index.html` (METRO_META)
  - `apps/api/src/export/snapshot_builder.py` (SUPPORTED_CITIES)

## Intent

Ship the Bridgeport, CT leaf for US-419: a TWO-FEED PARTIAL metro reusing the
statewide Connecticut Socrata feeds already registered for Hartford. SLA =
`data.ct.gov/resource/ngch-56tr.json` filtered `city = 'BRIDGEPORT'`; DEEDS =
`data.ct.gov/resource/5mzw-sjtu.json` filtered `town = 'Bridgeport'`. Both are
address-only (no native WGS84 lat/lng read by the shared producers), so both
declare `needs_geocode=True`. Leaf must import without a spine edit, expose the
canonical `BRIDGEPORT_*` constants + `REGISTRATION`, and pass spine-stable tests.

## Decisions

- 2026-08-30 — Live re-probed both feeds (see "Live-probe corrections" below).
  `serialnumber` is NOT row-unique within `town='Bridgeport'` (serialnumber
  `10861` appears in listyear 2010 AND 2001) → `id_keys = ["serialnumber",
  "listyear"]`; `(serialnumber, listyear)` verified unique (empty `$having` dup
  result).
- 2026-08-30 — Neither watermark is null (SLA `recordrefreshedon` 0/39955 null;
  DEEDS `daterecorded` 0/41036 null), so no `IS NOT NULL` guard needed (unlike
  Buffalo's `issdttm`).
- 2026-08-30 — DEEDS `geo_coordinates` coverage 12,574 / 41,036 = 30.6%. The
  shared deeds producer's loc fallback reads `the_geom`/`point`/`location`/
  `georeference`/`shape`/WKT but NOT `geo_coordinates`, so the leaf declares
  `needs_geocode=True` and the SPINE DELTA asks the orchestrator to add
  `geo_coordinates` to the deeds producer loc fallback.
- 2026-08-30 — Field map uses the CORRECT live CT column names (Hartford's
  inline field_map is stale): `credentialid`/`fullcredentialcode`/`credential`/
  `credentialtype`/`effectivedate`/`issuedate`/`expirationdate`/`address`/`city`/
  `zip`/`status`/`businessname`/`name`/`recordrefreshedon` for SLA;
  `serialnumber`/`listyear`/`daterecorded`/`town`/`address`/`saleamount`/
  `propertytype` for DEEDS.

## Live-probe corrections (2026-08-30)

- **SLA** `ngch-56tr`: 39,955 rows for `city='BRIDGEPORT'` (matches ticket's
  ~39,955). Watermark `recordrefreshedon` ISO datetime, 0 nulls, newest
  2026-08-30. Broad statewide credentials feed (gas dealers, repairers, etc. —
  not only hospitality), consistent with the Hartford precedent. `where` uses
  uppercase `'BRIDGEPORT'`.
- **DEEDS** `5mzw-sjtu`: 41,036 rows for `town='Bridgeport'`. `daterecorded` ISO
  datetime, 0 nulls, newest 2025-09-30 (listyear 2024 — an annual grand-list
  publication, so the watermark lags ~11 months). `serialnumber` NOT unique →
  composite id. `geo_coordinates` 30.6% coverage.

## Current step

Writing the four leaf files.

## Next step

Run the three verify commands, then report the SPINE DELTA.
