# Spartanburg County, SC — probe (US-301 leaf rebuild, 2026-08-28)

Leaf `city-spartanburg` probe for the Metro Expansion — Southeast milestone.
Result: **partial registrable** — ALLOWED feeds = PERMITS + SLA, both from ONE
shared on-prem ArcGIS FeatureServer layer; COMPLAINTS_311 and DEEDS are both
NOT-viable. The existing `ArcGISClient` covers the city — no fifth client.

This probe was re-derived for a REBUILD: the prior session's leaf artifacts were
lost to a branch switch. All watermarks re-verified LIVE on 2026-08-28 before any
fixture was captured.

## Host & endpoint

County on-prem ArcGIS Server 11.5: `maps.spartanburgcounty.org`.

> **Path correction vs the confirmed probe facts.** The service root is
> **`/server/rest/services`** — the naive `/arcgis/rest/services` prefix returns
> an IIS 404 (verified). The service is `EnerGov/EnerGov_Spatial_Collections`,
> and BOTH registered feeds are layer **5** ("History Points"):

`https://maps.spartanburgcounty.org/server/rest/services/EnerGov/EnerGov_Spatial_Collections/FeatureServer/5`

Layer metadata (layer /5, "History Points"):

| Key | Value |
|---|---|
| `geometryType` | `esriGeometryPoint` |
| `objectIdField` | `OBJECTID` |
| `maxRecordCount` | 2000 |
| date fields | `ApplicationDate` (esriFieldTypeDate) |
| extent (wkid 3361) | xmin 1632334.9 / ymin 1006576.7 / xmax 1783086.6 / ymax 1224872.0 |

Native spatial ref is **WKID 3361** (SC State Plane); every query requests
`outSR=4326`, so the ArcGISClient flattens point geometry onto
`latitude`/`longitude` WGS84 keys (fresh outSR=4326 points verified on every
row). **NO address columns exist** — every row carries `SpatialType='Address'`
(a server-side geocode flag) plus a `SpatialID` GUID. Coordinates are the native
source, so `needs_geocode=False`; there is no address string for ADR-0004.

## Schema (layer /5 — identical for both feeds)

| Column | Map target | Notes |
|---|---|---|
| `OBJECTID` | `job_id`/`license_id` fallback, ordering/OID | OID field (edit counter) |
| `ModuleName` | — | the load-bearing discriminator (`PermitManagement` / `BusinessLicenseEntity` / `BusinessLicenseManagement`) |
| `CaseID` | `license_id` fallback | case GUID (unique per row); lossless SLA key |
| `CaseNumber` | `job_id` / `license_id` (primary) | permits: real number (`BLDRESDNTL-0826-22014`); SLA Management: real case number (`ZPANNUFOOD-000521-2026`); **SLA Entity: the business NAME** (`Brat &amp; Curry Co`, byte-verbatim HTML-escaped) |
| `CaseType` | `job_type` fallback / `license_type` | permit class (`Demolition (Residential)`) or license class (`Limited Liability Company`) |
| `WorkClass` | `job_type` (primary) | most specific sub-type (`Residential Demolition`, `Alteration, Remodel, Repair`) |
| `ApplicationDate` | `issuance_date` / `effective_date` | date-typed watermark, ISO after flatten |
| `ProjectID` | — | `" "` (single space) layer-wide |
| `ProjectName` | `dba`/`premises_name` candidate | always `""` layer-wide — the dba falls through to CaseNumber |
| `GISHistoryQueueID` / `SpatialType` / `SpatialID` | — | not mapped (server-side geocode plumbing) |

`where` module filters verified live via `returnDistinctValues`
(`ModuleName`): `BusinessLicenseEntity`, `BusinessLicenseManagement`,
`CodeManagement` (25,137 rows — code enforcement), `InspectionManagement`,
`PermitManagement`, `ProjectManagement`.

## Watermark (re-verified live 2026-08-28)

`ApplicationDate` (esriFieldTypeDate → epoch-ms fragment, flattened to ISO by the
client; no ADR-0005 text declaration).

| Feed | `where` | Newest `ApplicationDate` | 30d / 2026 / total |
|---|---|---|---|
| PERMITS | `ModuleName='PermitManagement'` | 2026-08-28T16:08:53Z (same-day) | 1,420 / 9,640 / 41,555 |
| SLA | `ModuleName IN ('BusinessLicenseEntity','BusinessLicenseManagement')` | 2026-07-08T11:55:00Z | 0 recent / 9 YTD / 187 (Entity 79 + Mgmt 108) |

These match the prior session's reported values (permits newest 2026-08-28T15:20
in the earlier note → now 16:08:53 same-day; SLA 2026-07-08T11:55:00Z; SLA total
187; **permits total now 41,555, not 41,550** — 5 rows landed since).

## Host quirk (spine change — do NOT edit watermarks.py in the leaf)

**`maps.spartanburgcounty.org` is an ANSI-date-literal ArcGIS host.** A bare ISO
date comparison in `where` 400s:

- `ApplicationDate >= '2026-08-01T00:00:00'` → HTTP 400 (`Unable to complete
  operation.`)
- `ApplicationDate >= date '2026-08-01'` → works (returns rows)

This requires adding `maps.spartanburgcounty.org` to `watermarks.py`
`ANSI_DATE_LITERAL_HOSTS` in the serial spine hold. Sibling southeast
registrations (savannah / bowling_green / tallahassee) add their own hosts to
the same tuple.

## Feed contract for both specs

Both platform `arcgis`, watermark_col `ApplicationDate`, `needs_geocode=False`,
native point (NO `non_spatial` — the layer has real geometry), `order_by=OBJECTID`,
`oid_field=OBJECTID`, `max_record_count=2000`. The `where` module filter is
load-bearing (both feeds share the one layer).

- **PERMITS**: `producer_key=permits`, id_keys `["CaseNumber","OBJECTID"]`,
  `where="ModuleName='PermitManagement'"`, `expected_cadence_days=1`
  (same-day live). field_map `PERMITS_FIELD_MAP`.
- **SLA**: `producer_key=sla`, id_keys `["CaseNumber","CaseID","OBJECTID"]`,
  `where="ModuleName IN ('BusinessLicenseEntity','BusinessLicenseManagement')"`,
  `expected_cadence_days=30` (**flagged for orchestrator review** — a slow
  trickle ~2-3/mo; the staleness monitor will alarm at 2×N=60d). field_map
  `SLA_FIELD_MAP`.

`SPARTANBURG_FIELD_MAP = {"permits": PERMITS_FIELD_MAP, "sla": SLA_FIELD_MAP}`.

## NOT-viable feeds (do NOT register)

- **COMPLAINTS_311** — the only citizen-request-ish module is `CodeManagement`
  (code enforcement, 25,137 rows); there is no `RequestManagement` module. Not a
  municipal CRM/311 extract.
- **DEEDS** — no recorded-deeds layer; the county publishes a ROD search portal
  only. `GIS/CAMA_Parcels` is a parcel/assessment snapshot, not property sales.

## Spatial

County-scale metro following the Miami-Dade "center, not extent" precedent: the
register carries NO jurisdiction column, so the metro bbox is the whole county
footprint and the "city" is the urban core at the center
`{34.9497, -81.9320}`. City coverage proven — 3,026 of the 2026-YTD city-bbox
permit rows land inside the City of Spartanburg footprint. The bbox is grounded
in the live `County_Line` FeatureServer/0 extent (EPSG:3361 → EPSG:4326):
lng -82.2316..-81.7104, lat 34.5771..35.2001.

```python
SPARTANBURG_METRO_BBOX = {"min_lat": 34.57, "max_lat": 35.21, "min_lng": -82.24, "max_lng": -81.69}
SPARTANBURG_CENTER = {"lat": 34.9497, "lng": -81.9320}
```

**Containment fix (self-verified):** metro `max_lng` is `-81.69`, not `-81.71`.
The raw county extent max lng is `-81.7104`, so a box capped at `-81.71` would
exclude the county's eastern edge.

Divisions (6): `DOWNTOWN_CORE`, `EAST_CITY`, `WEST_CITY`, `BLUE_RIDGE_FOOTHILLS`,
`I85_CORRIDOR`, `SOUTH_COUNTY`. Submarkets (10): Downtown Spartanburg,
Northside / Rail Yard (DOWNTOWN_CORE); Eastside / Hillcrest (EAST_CITY); Westgate
(WEST_CITY); Inman / Campobello, Landrum / Chesnee (BLUE_RIDGE_FOOTHILLS);
Greer / Reidville, Duncan / Lyman (I85_CORRIDOR); Woodruff, Roebuck
(SOUTH_COUNTY). All containment invariants self-verified (each submarket inside
its division bbox; each division bbox inside the metro bbox).

## Fixtures

4 byte-verbatim attribute-value captures from the live query, flattened to the
ISO `ApplicationDate` strings and the client-injected `longitude`/`latitude`
keys the ArcGISClient emits:

- `BRMECHANIC-0826-4236` — Mechanical (Residential) / HVAC Changeout, ApplicationDate
  2026-08-28T16:08:53Z (newest), native point (35.19298, -82.19187)
- `BRDEMOLISH-0826-0698` — Demolition (Residential) / Residential Demolition,
  ApplicationDate 2026-08-28T12:58:42Z, native point (34.78404, -82.12658)
- `BLDRESDNTL-0826-22014` — Building (Residential) / Alteration, Remodel, Repair,
  ApplicationDate 2026-08-28T11:52:09Z, native point (34.95898, -82.20824)
- `ZPANNUFOOD-000521-2026` — BusinessLicenseManagement, Mobile Food Service Vendor
  Annual Zoning Permit, ApplicationDate 2026-07-08T11:55:00Z (newest SLA),
  native point (34.91441, -82.16361)

The **`Brat &amp; Curry Co`** row (BusinessLicenseEntity, a 5th fixture in the
test) captures the HTML-escaped business name byte-verbatim (`CaseNumber` = the
entity name; `ApplicationDate` 2026-07-08T00:00:00Z). The producer does NOT
HTML-unescape, so `license_id`/`dba` carry `&amp;` verbatim.
