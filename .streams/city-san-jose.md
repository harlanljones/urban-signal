# Stream log — city-san-jose — 2026-08-26

Copy of `.streams/_TEMPLATE.md` per docs/agents/parallel-streams.md (phase 1 Claim).
Leaf worker for US-147: "Register San Jose, CA — PERMITS + 311 (geocoding caveats)".

## Claim

- **Stream id:** city-san-jose
- **Leaf files I will create/edit:**
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

Add San Jose, CA as a TWO-FEED city (PERMITS + 311) registered on SanGIS
(Socrata open data). The 311 feed is address-string-located for a meaningful
share of rows, so it is declared `needs_geocode` (ADR 0004); the PERMITS feed
carries native coordinates but spells them `Y_COORD`/`X_COORD` and several rows
are coordinate-less. The leaf delivers the spatial module, the per-city field
maps, and a registration-free test that exercises both the address-vs-coordinate
caveats and the geocoder's CA-context / unit-designator normalization.

## Decisions

- San Jose open-data platform: **SanGIS** (Socrata Open Data, data.sanjoseca.gov
  style). PERMITS = Building Permits; 311 = San José 311 Service Requests.
- Geocoding caveats handled:
  1. 311 coordinates ride `Y_COORD`/`X_COORD` (decimal degrees) but a large
     fraction of rows are address-only / 0.0/0.0 → producer falls through to
     the ADR-0004 geocoder via `needs_geocode`.
  2. Some rows carry *projected* garbage (abs(lat)>90 / abs(lng)>180) → the
     parser's out-of-range guard nulls them and routes to the geocoder.
  3. Addresses already end in "SAN JOSE, CA" → geocoder `_STATE_RE` sees `CA`
     and does NOT append the `geocode_context` suffix (no double context).
  4. Unit designators ("APT 4") → `normalize_address` v2 drops them in place,
     preserving the city context needed for a rooftop match.

## Current step

Leaf complete. `uv run pytest tests/unit/test_producers_san_jose.py -q` → 18 passed.
`uv run pytest -m interlock -q` → 5 failures, ALL pre-existing and unrelated
(durham: imported in cities/__init__.py + dashboard METRO_META but absent from
REGISTRY/CityId; another in-flight stream). No San Jose regression.

## Next step

Interlock phase (spine, one stream at a time): apply the registry/ALIASES/
__init__/config/dashboard deltas in step 5 of the leaf report, then re-run
`pytest -m interlock -q` to confirm only the durham failures remain (which are
owned by the durham stream, not this one).
