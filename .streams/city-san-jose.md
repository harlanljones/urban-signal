# Stream log — city-san-jose — 2026-08-26

Registration stream for US-147: "Register San Jose, CA — PERMITS + 311 (geocoding caveats)".

## Claim

- **Stream id:** city-san-jose
- **Implemented files:**
  - `apps/api/src/spatial/cities/san_jose.py` (spatial: metro bbox, division bboxes, submarkets, divisions, geocode field-map constants)
  - `apps/api/src/producers/field_maps_san_jose.py` (exports `FIELD_MAP`; imports from `san_jose.py`)
  - `apps/api/tests/unit/test_producers_san_jose.py` (fixtures + assertions; exercises geocoding caveats; passes WITHOUT spine registration)
- **Spine files I expect to need (do NOT edit now — documented as deltas in step 5):**
  - `apps/api/src/spatial/city_registry.py` (CityId.SAN_JOSE, REGISTRY entry, PERMITS+311 DatasetSpec, ALIASES)
  - `apps/api/src/spatial/cities/__init__.py` (import san_jose exports)
  - `apps/api/src/producers/field_maps.py` (optional central entry — currently maps live inline in spec.extra; documented)
  - `apps/api/src/config.py` (socrata_san_jose_permits_endpoint / socrata_san_jose_311_endpoint)
  - `apps/api/src/serving/dashboard.py` METRO_META + `apps/dashboard/public/index.html` byte sync

## Intent

Add San Jose, CA as a TWO-FEED city (PERMITS + 311) registered on the City's
CKAN datastore. Permits are address-only via `gx_location` and use ADR-0004
geocoding; 311 is annual/current-year with native coordinates but no address
column and roughly 49% `0,0` rows, which the parser drops before H3 indexing.

## Decisions

- San Jose open-data platform: **CKAN datastore** (`data.sanjoseca.gov`).
  PERMITS = `045b3678-e923-4002-b696-300955bc6d06`; 311 2026 =
  `d886727c-60f1-4be7-9a30-f6806375b1a3`.
- Geocoding caveats handled:
  1. Permits have no coordinates; `gx_location` is passed to the ADR-0004
     geocoder and `ASSESSORS_PARCEL_NUMBER` is retained as the APN.
  2. 311 `Latitude`/`Longitude` are native decimal degrees, but `0,0` rows are
     rejected before H3 assignment because the annual source has no address
     fallback.
  3. Permit `ISSUEDATE` is M/D/YYYY text; typed watermark state plus CKAN SQL
     `to_timestamp` comparison prevents lexical date ordering errors.

## Current step

Registration complete. San Jose focused tests pass; the interlock gate and
dashboard static-copy check are being rerun after export.

## Next step

Keep the 2026 annual 311 resource mapping current when the City publishes the
next year's CKAN resource; no open San Jose licenses or deeds feed was found.
