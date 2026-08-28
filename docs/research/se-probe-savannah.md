# Savannah / Chatham County, GA — probe (US-298 leaf, 2026-08-28)

Leaf `city-savannah` probe for the Metro Expansion — Southeast milestone. Result:
**partial registrable** — ALLOWED feed = PERMITS (Residential `/1` + Commercial `/0`
companion); 311 / SLA / DEEDS are all NOT-viable. Registered via the Chatham County
SAGIS ArcGIS server, so the existing `ArcGISClient` covers the city with no fifth
client.

This probe was re-derived for a REBUILD: the prior session's leaf artifacts were
lost to a branch switch. All watermarks re-verified LIVE on 2026-08-28 before any
fixture was captured.

## Host & endpoint

`https://pub.sagis.org/arcgis/rest/services/Savannah/BuildingPermit_FC/FeatureServer`

- `/1` = **Residential** building permits (registered as the PERMITS dataset).
- `/0` = **Commercial** building permits (spine-level companion
  `companion_endpoints["commercial_building_permits"]` — same schema, not a new
  FeedType).

Layer metadata (both layers), fetched via the query endpoint:

| Layer | `objectIdField` | `maxRecordCount` | date fields |
|---|---|---|---|
| /1 Residential | OBJECTID | 2000 | `IssuedDate_DATE`, `FinalizedDate_DATE` |
| /0 Commercial | OBJECTID | 2000 | `IssuedDate_DATE`, `FinalizedDate_DATE` |

Native spatial ref is **WKID 2239** (GA State Plane East, US-ft); every query
requests `outSR=4326`, so the ArcGISClient flattens point geometry onto
`latitude`/`longitude` WGS84 keys. Nearly every row carries native coordinates;
ADR-0004 address geocoding is the fallback for the residual coordinate-less rows.

## Watermark (re-verified live 2026-08-28)

`IssuedDate_DATE` (esriFieldTypeDate → epoch-ms fragment, flattened to ISO by the
client; no ADR-0005 text declaration). Text mirror `IssuedDate` is `MM/DD/YYYY`
and is kept only as a secondary issuance candidate in the field map.

| Layer | Newest `IssuedDate_DATE` | 7d | 60d | total |
|---|---|---|---|---|
| /1 Residential | 2026-08-20 (`26-07908-BR`) | 0 | 294 | 1933 |
| /0 Commercial | 2026-08-21 (`26-00953-BC`) | 1 | 61 | 666 |

These match the prior session's reported values exactly (newest 2026-08-20 res /
2026-08-21 com; 7d 0/1; 60d 294/61; total 1933/666) — no drift.

`where` clauses verified live (counts above were computed with the ANSI literal):
`IssuedDate_DATE >= DATE '2026-08-21'`.

## Host quirk (spine change — do NOT edit watermarks.py in the leaf)

**`pub.sagis.org` is an ANSI-date-literal ArcGIS host.** A bare ISO date
comparison in `where` 400s:

- `IssuedDate_DATE >= '2026-08-21T00:00:00'` → HTTP 400 (Unable to complete
  operation)
- `IssuedDate_DATE >= DATE '2026-08-21'` → works (returns the row)

This requires adding `pub.sagis.org` to `watermarks.py` `ANSI_DATE_LITERAL_HOSTS`
in the serial spine hold. Sibling southeast registrations (bowling_green /
tallahassee / spartanburg) add their own hosts to the same tuple.

## Schema (identical on /1 and /0)

| Column | Map target | Notes |
|---|---|---|
| `PermitNumber` | `job_id` (primary) | e.g. `26-07908-BR` / `26-00953-BC` |
| `OBJECTID` | `job_id` (fallback), ordering/OID | OID field |
| `Address` | `address_street` | street-only (e.g. `131 KING ST`) |
| `District` | `borough`, `source_neighborhood` | planning-area name (e.g. `Godley Station`, `Woodville`, `Chatham Parkway`) |
| `PermitStatus` | `status` | `Issued` / `In Review` / `Approved` |
| `PermitType` | — | `Building Residential Permit` / `Building Commercial Permit` (not mapped) |
| `Permit_Value` | `cost` | declared job cost (float) |
| `WorkClass` | `job_type` | `New` / `Addition` / `Renovation` / `Demolition-Total` / … |
| `PIN` | `bbl` | parcel id (may contain a space, e.g. `20715 01016`) |
| `IssuedDate_DATE` | `issuance_date` (primary) | date-typed watermark, ISO after flatten |
| `IssuedDate` | `issuance_date` (fallback) | `MM/DD/YYYY` text mirror |
| `ApplicantName` | — | **PII — deliberately unmapped** |
| `Description` `ADDID2` `FinalizedDate` `FinalizedDate_DATE` | — | not mapped |

## Feed contract for the PERMITS spec

- platform `arcgis`, watermark `IssuedDate_DATE`, id_keys `["PermitNumber","OBJECTID"]`
- producer_key `permits`, expected_cadence_days `7`
- needs_geocode `True`, geocode_context `"Savannah, GA"`
- order_by `OBJECTID`, oid_field `OBJECTID`, max_record_count `2000`
- field_map `SAVANNAH_PERMITS_FIELD_MAP`
- companion_endpoints `{"commercial_building_permits": .../0}`
- registered whole (no server-side status filter); null `IssuedDate_DATE` on
  In Review / Approved rows surfaces at issuance; register retained to 2023-01
  (not rolling).

## NOT-viable feeds (do NOT register)

- **COMPLAINTS_311** — Chatham County's Oneview public-works `OneView311` trunk is
  district polygons, not case rows; the city's CivicPlus 311 is a master address
  registry; Chatham `QAlert` is reference layers. No municipal CRM extract.
- **SLA** — no license register; `STVR_NewData` is a zoning overlay + assessor
  extract (short-term-rental overlay), not a license list.
- **DEEDS** — Chatham BOA Parcel is the assessor roll (`Date_Updated` 2026-06-22,
  no grantor column); `Parcel Digest` is annual snapshots. No transfer/sales feed.

## Spatial

5 divisions / 10 submarkets; submarket coordinates pinned to LIVE outSR=4326
permit coordinates captured this session. The metro bbox is set by the annexed
western edge (New Hampstead, `-81.3505`) and the northern Godley Station
annexation (`32.1814`), and is grounded in the live layer extent
(`returnExtentOnly`, outSR=4326): lat 31.93395-32.18642, lng -81.36534 - -81.04491
— the Chatham County footprint.

```python
SAVANNAH_METRO_BBOX = {"min_lat": 31.93, "max_lat": 32.19, "min_lng": -81.37, "max_lng": -81.03}
SAVANNAH_CENTER = {"lat": 32.0767, "lng": -81.0943}
```

Divisions: `HISTORIC_CORE`, `MIDTOWN`, `WEST_SIDE`, `SOUTH_SIDE`, `WEST_CHATHAM`.
Submarkets: Landmark Historic District, Victorian District (HISTORIC_CORE); Ardsley
Park, Parkside (MIDTOWN); Woodville, Liberty City (WEST_SIDE); Oglethorpe Mall,
Chatham Parkway (SOUTH_SIDE); Godley Station, New Hampstead (WEST_CHATHAM). All
containment invariants self-verified (each submarket inside its division bbox;
each division bbox inside the metro bbox).

## Fixtures

4 captures (3 residential + 1 commercial) are byte-verbatim attribute values from
the live query, flattened to the ISO date strings and the client-injected
latitude/longitude keys the ArcGISClient emits:

- `26-07908-BR` (131 KING ST, Woodville, Demolition-Total, Issued 2026-08-20)
- `26-06373-BR` (145 ORKNEY RD, Godley Station, New, Issued 2026-08-20)
- `26-07506-BR` (4113 WALTON ST, In Review, null IssuedDate_DATE, native coords)
- `26-00953-BC` (7000 BUSINESS CENTER DR, Chatham Parkway, New, Issued 2026-08-21; /0)
