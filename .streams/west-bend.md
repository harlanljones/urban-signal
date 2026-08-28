# Stream log — west-bend — 2026-08-28

## Claim

- **Stream id:** `west-bend`
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/bend.py`
  - `apps/api/src/producers/field_maps_bend.py`
  - `apps/api/tests/unit/test_producers_bend.py`
- **Spine files I expect to need:** NONE

## Intent

Onboard Bend, OR as a new metro area by live-verifying 4 official city ArcGIS feeds (PERMITS, SLA, COMPLAINTS_311, CRIME), then building a leaf producer (bbox, divisions, FEED_SPECS, field maps, tests) without touching spine files.

## Decisions

- 2026-08-28 — Claimed stream west-bend from US-237. Ticket body: "bendoregon.gov open data (ArcGIS)".
- 2026-08-28 — ArcGIS Hub at cityofbend.hub.arcgis.com is private (401). Public surfaces are on services5.arcgis.com (CityofBendOR org).
- 2026-08-28 — **PERMITS**: Permit_Applications_Point (FeatureServer/0, 165,354 rows, native point geometry, SR 2270 NAD83 Oregon North ft but outSR=4326 returns WGS84 deg; ApplicationDate watermark newest 2026-08-27). Also Permitting_Table (205,084 rows, Table non-spatial, address-only). Point layer is the primary feed.
- 2026-08-28 — **SLA**: License_Application_Points_(Business_Registrations) (FeatureServer/0, 5,942 rows, native point geometry, per-license snapshot; LicenseExpirationDate watermark).
- 2026-08-28 — **COMPLAINTS_311**: Code_Enforcement_Cases_Polygon_(Public) (FeatureServer/0, 17,300 rows, polygon geometry → centroid; CaseReportedDate watermark newest 2026-08-28).
- 2026-08-28 — **CRIME**: Public_Calls (Calls for Service GIS - Public) (FeatureServer/0, 451,275 rows, native point geometry, CreateDateTime watermark newest 2026-08-27T11:43; CallAddress + Neighborhood). Also Public_Cases (Case Offenses, 267,438 rows). Both have native geometry + address → ADR-0004 compliant. Public Calls is the primary crime feed.
- 2026-08-28 — DEEDS: Deschutes County has no bulk recorded-deeds/sales API. Parcel layers exist (DeschutesParcelsUGB) but are assessor reference only. Partial without deeds per ticket.
- 2026-08-28 — All four feeds use ArcGIS FeatureServer on services5.arcgis.com, maxRecordCount=2000, OBJECTID OID field.
- 2026-08-28 — All feeds have esriFieldTypeDate watermark columns that ArcGISClient converts to ISO 8601 UTC.
- 2026-08-28 — All four feeds declare needs_geocode=True (ADR-0004): address strings (Address/BusinessLocation/CallAddress) carry full street+city+zip; geometry lift is primary.

## Current step

Phase B — LEAF BUILD: DONE. All four leaf files written and verified.

## Next step

None (leaf complete). Await spine hold for CityId.BEND registration.

## Outcome

**Feeds verified (4):**
1. PERMITS — Permit_Applications_Point (165,354 rows, ApplicationDate watermark, newest 2026-08-27)
2. SLA — License_Application_Points_Business_Registrations (5,942 rows, LicenseExpirationDate watermark)
3. COMPLAINTS_311 — Code_Enforcement_Cases_Polygon_Public (17,300 rows, CaseReportedDate watermark, newest 2026-08-28)
4. CRIME — Public_Calls (451,275 rows, CreateDateTime watermark, newest 2026-08-27T11:43)

**Verification:**
- `pytest tests/unit/test_producers_bend.py -q` — 59 passed
- `pytest -k bend -q` — 53 passed
- `pytest -m interlock -q` — 24 passed (unchanged)
- `ruff check` on all three files — clean

**Spine delta:** CityId.BEND member + "bend" alias + registry entry fields + config endpoint settings. Recommended Linear comment: "4 feeds verified — permits, sla, 311, crime. All ArcGIS FeatureServer on services5.arcgis.com. Deschutes County deeds: unreachable (no bulk recorder API). Ready for spine hold."