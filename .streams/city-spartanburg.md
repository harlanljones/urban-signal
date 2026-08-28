# Stream log — city-spartanburg — 2026-08-28

Phase-2 leaf stream for Linear US-301: Spartanburg County, SC registration
(PERMITS + SLA). Spine is serial after this stream; do not edit spine files
here. This is a REBUILD: the batch-1 leaf artifacts were lost to a branch
switch (main -> chore/restore-metros-and-columbus mid-session). Probe facts
below are re-verified LIVE before fixtures were captured.

## Claim

- **Stream id:** `city-spartanburg`
- **Leaf files I will create/edit:**
  - `.streams/city-spartanburg.md` (this file)
  - `docs/research/se-probe-spartanburg.md` (NEW)
  - `apps/api/src/spatial/cities/spartanburg.py` (NEW)
  - `apps/api/src/producers/field_maps_spartanburg.py` (NEW)
  - `apps/api/tests/unit/test_producers_spartanburg.py` (NEW)
- **Spine files I expect to need (do NOT edit in this stream):**
  - `apps/api/src/spatial/city_registry.py` (CityId.SPARTANBURG, ALIASES, REGISTRY)
  - `apps/api/src/spatial/cities/__init__.py`
  - `apps/api/src/config.py` (`arcgis_spartanburg_permits_url` / `_sla_url`)
  - `apps/api/src/producers/watermarks.py` (ANSI_DATE_LITERAL_HOSTS += maps.spartanburgcounty.org)
  - `apps/api/src/serving/dashboard.py` METRO_META + `apps/dashboard/public/index.html`

## Intent

Leaf-complete Spartanburg County (SC) on the county's on-prem ArcGIS Server
11.5 (`maps.spartanburgcounty.org`, HTTP path `/server/rest/services`, NOT
`/arcgis/rest/services` — 404 on the naive path). Two feeds register from the
SAME `EnerGov/EnerGov_Spatial_Collections/FeatureServer/5` ("History Points")
layer, separated purely by a load-bearing `where` module filter:
`ModuleName='PermitManagement'` (PERMITS) and
`ModuleName IN ('BusinessLicenseEntity','BusinessLicenseManagement')` (SLA).
Tests pass WITHOUT a registry entry.

## Decisions

- The ArcGIS service root is `https://maps.spartanburgcounty.org/server/rest/services`.
  The `/arcgis/rest/services` prefix returns an IIS 404 — the URL in the
  confirmed probe facts used `/arcgis/...`, which is wrong for this host.
  Correct URL: `https://maps.spartanburgcounty.org/server/rest/services/EnerGov/EnerGov_Spatial_Collections/FeatureServer/5`.
- Layer 5 is `History Points` (geometryType esriGeometryPoint, outSR=4326 on
  query). NO address columns — `SpatialType='Address'` on every row signals a
  server-side geocode (the `SpatialID` GUID resolves to a point). So
  `needs_geocode=False`; coordinates arrive natively via the client's geometry
  lift to `latitude`/`longitude`.
- **Host quirk (spine delta, NOT editing watermarks.py):**
  `maps.spartanburgcounty.org` is ANSI-date-literal. Verified live: plain
  `ApplicationDate >= '2026-08-01T00:00:00'` returns ArcGIS error
  `400 Unable to complete operation`, while
  `ApplicationDate >= date '2026-08-01'` works. Must be added to
  `ANSI_DATE_LITERAL_HOSTS`.
- Both feeds share the watermark column `ApplicationDate` (esriFieldTypeDate —
  epoch-ms on the wire, ISO after client flatten). No ADR-0005 text declaration.
- PERMITS producer_key `permits`, expected_cadence_days `1` (same-day live:
  newest ApplicationDate 2026-08-28T16:08:53Z). Total PermitManagement rows
  41,555; 30d 1,420; 2026-YTD 9,640.
- SLA producer_key `sla`, expected_cadence_days `30` (trickle ~2-3/mo; only
  187 rows ever). Newest union ApplicationDate 2026-07-08T11:55:00Z (0 in the
  recent window, 4 in the annual window). **Flag for orchestrator review**:
  SLA is a slow trickle by nature — 30d cadence is a judgement call the
  scheduler/probe monitors at 2×N=60d.
- COMPLAINTS_311 NOT-VIABLE (the only ~311 module is `CodeManagement` = code
  enforcement; there is no `RequestManagement` module). DEEDS NOT-VIABLE (ROD
  search portal only; `GIS/CAMA_Parcels` is a parcel snapshot, not sales).
- id_keys: labels are the story. PERMITS `["CaseNumber","OBJECTID"]`
  (CaseNumber unique per permit, e.g. `BLDRESDNTL-0826-22014`). SLA
  `["CaseNumber","CaseID","OBJECTID"]` — **note**: `BusinessLicenseEntity`
  rows carry the business NAME as `CaseNumber` (e.g. `Brat &amp; Curry Co`,
  byte-verbatim HTML-escaped), while `BusinessLicenseManagement` rows carry a
  real case number (`ZPANNUFOOD-000521-2026`). CaseNumber is not guaranteed
  unique across the union; CaseID GUID is the lossless key.
- `<` in module names: `Brat &amp; Curry Co` is the raw field value. The
  producer does NOT HTML-unescape, so `license_id` / `dba` carry `&amp;`
  verbatim. Fixture preserves it. (A front-end/consumer may decode downstream.)
- Field map job_type order `["WorkClass","CaseType"]` — WorkClass is the more
  specific "sub-type" (e.g. `Residential Demolition`, `New Single Family
  Residence`, `Alteration, Remodel, Repair`) so classification lands
  DM/A2; CaseType is the fallback. `New Single Family Residence` does NOT
  match the producer's NB keywords ("NEW CONSTRUCTION"/"NEW BUILDING") — that
  is a known producer-classification gap, documented, not worked around in the
  leaf. `issuance_date -> ["ApplicationDate"]` (the watermark; no separate
  filing-date column exists).

## Live probe (2026-08-28, all re-verified live before fixture capture)

Portal `maps.spartanburgcounty.org` (county on-prem ArcGIS Server 11.5; the Hub
is a shell — DCAT 404, City dashboard export frozen 2026-04-10). Trust live rows.

| Feed | Layer | where | Newest ApplicationDate | Recent window / total | Geo | Verdict |
|---|---|---|---|---|---|---|
| PERMITS | /5 History Points | `ModuleName='PermitManagement'` | 2026-08-28T16:08:53Z (same-day) | 30d 1,420 / 2026 9,640 / total 41,555 | native point (outSR=4326); `SpatialType='Address'`, NO address columns | LIVE, register |
| SLA | /5 History Points | `ModuleName IN ('BusinessLicenseEntity','BusinessLicenseManagement')` | 2026-07-08T11:55:00Z | 0 recent / 4 annual / total 187 (Entity 79 + Mgmt 108) | native point; `SpatialType='Address'` | LIVE, register (trickle; cadence 30) |
| COMPLAINTS_311 | /5 CodeManagement | `ModuleName='CodeManagement'` | 25,137 rows | native | **NOT-VIABLE** (code enforcement, no RequestManagement) | do not register |
| DEEDS | — | GIS/CAMA_Parcels = parcel snapshot | — | — | ROD search portal only | **NOT-VIABLE** | do not register |

Modal names verified `returnDistinctValues`: BusinessLicenseEntity,
BusinessLicenseManagement, CodeManagement, InspectionManagement,
PermitManagement, ProjectManagement. County_Line FeatureServer/0 extent
(transformed EPSG:3361 -> 4326): lng -82.2316..-81.7104, lat 34.5771..35.2001
— grounds the metro bbox.

## Spatial

County-scale metro (Miami-Dade "center, not extent" precedent): the register
carries NO jurisdiction column, so the metro bbox covers the whole county
extent and the "city" is the urban core at the center
{34.9497, -81.9320}; 3,026 of the 2026-YTD city-bbox permit rows prove the
county layer covers the city. `max_lng` was fixed -81.71 -> -81.69 (the raw
county extent max lng is -81.7104, so -81.71 would have excluded the county's
eastern edge). 6 divisions, 10 submarkets; every division bbox nests in the
metro bbox; every submarket sits in its division; containment self-verified.

METRO_BBOX: min_lat 34.57, max_lat 35.21, min_lng -82.24, max_lng -81.69.

## Files written

- `docs/research/se-probe-spartanburg.md`
- `apps/api/src/spatial/cities/spartanburg.py`
- `apps/api/src/producers/field_maps_spartanburg.py`
- `apps/api/tests/unit/test_producers_spartanburg.py`

## Tests

```
cd apps/api && .venv/bin/python -m pytest tests/unit/test_producers_spartanburg.py -q
44 passed
```

No `CityId.SPARTANBURG`. No spine edits. Geocoding mocked at
`src.spatial.geocoder.geocode_row_if_declared`; no division/borough resolution
or geocode call-count assertions. (Prior run reported 45; the rebuilt leaf lands
44 — the delta is a dropped redundant classifier assertion, no coverage lost.)

## Spine delta (do NOT apply in this stream)

Copy-paste for the serial interlock hold:

1. `CityId.SPARTANBURG = "spartanburg"` (after `TUCSON`).
2. Aliases in `_HANDWRITTEN_ALIASES`:
   `spartanburg`, `spartanburg_sc`, `spartanburg-sc`, `spartanburg sc`,
   `spartanburg county`, `spartanburg_county_sc`.
3. `city_registry.py` imports:
   - `from src.spatial.cities.spartanburg import SPARTANBURG_DIVISION_BBOXES, SPARTANBURG_DIVISIONS, SPARTANBURG_METRO_BBOX, SPARTANBURG_SUBMARKETS`
   - `from src.producers.field_maps_spartanburg import SPARTANBURG_FIELD_MAP`
4. `cities/__init__.py` export block (same four constants + `is_in_spartanburg_metro`).
5. `config.py`:
   - `arcgis_spartanburg_permits_url = "https://maps.spartanburgcounty.org/server/rest/services/EnerGov/EnerGov_Spatial_Collections/FeatureServer/5"`
   - `arcgis_spartanburg_sla_url = "https://maps.spartanburgcounty.org/server/rest/services/EnerGov/EnerGov_Spatial_Collections/FeatureServer/5"`
6. `REGISTRY[CityId.SPARTANBURG]`:
   - name `"Spartanburg County"`, state `"SC"`
   - center `{"lat": 34.9497, "lng": -81.9320}`
   - job_suffix `"spartanburg"`
   - datasets PERMITS + SLA (both arcgis, `needs_geocode=False`, `non_spatial`
     False — native point, `order_by="OBJECTID"`, `oid_field="OBJECTID"`,
     `max_record_count=2000`):
     - PERMITS: endpoint `settings.arcgis_spartanburg_permits_url`,
       watermark_col `ApplicationDate`, id_keys `["CaseNumber","OBJECTID"]`,
       `where="ModuleName='PermitManagement'"`, producer_key `permits`,
       expected_cadence_days `1`, field_map `SPARTANBURG_FIELD_MAP["permits"]`.
     - SLA: endpoint `settings.arcgis_spartanburg_sla_url`,
       watermark_col `ApplicationDate`, id_keys `["CaseNumber","CaseID","OBJECTID"]`,
       `where="ModuleName IN ('BusinessLicenseEntity','BusinessLicenseManagement')"`,
       producer_key `sla`, expected_cadence_days `30`,
       field_map `SPARTANBURG_FIELD_MAP["sla"]`.
7. `watermarks.py` `ANSI_DATE_LITERAL_HOSTS` += `"maps.spartanburgcounty.org"`.
8. `METRO_META` in `apps/api/src/serving/dashboard.py` **and** byte-synced
   `apps/dashboard/public/index.html`: `spartanburg: { name: 'Spartanburg County' }`.

## Current step

Leaf rebuilt from the confirmed probe facts (live re-verified 2026-08-28).
Fixtures captured byte-verbatim. Leaf tests **44 passed** — green, no spine edits.
All 5 leaf files written (stream log, probe doc, spartanburg.py,
field_maps_spartanburg.py, test_producers_spartanburg.py).

## Next step

Report to orchestrator. Spine hold (enum/aliases/REGISTRY/config/watermarks
ANSI host/metro-meta/index.html) must be applied serially by the orchestrator
per the SPINE DELTA block above; do NOT apply in this stream.
