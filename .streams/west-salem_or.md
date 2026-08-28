# Stream log — west-salem_or — 2026-08-28

## Claim

- **Stream id:** west-salem_or
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/salem_or.py` (new)
  - `apps/api/src/producers/field_maps_salem_or.py` (new)
  - `apps/api/tests/unit/test_producers_salem_or.py` (new)
  - `.streams/west-salem_or.md`
- **Spine files I expect to need:** NONE (leaf-only)

## Intent

Register Salem, OR metro area with 2-3 verified municipal data feeds (permits, SLA) from the City of Salem's ArcGIS Online org (`services.arcgis.com/kIA6yS9KDGqZL7U3`). Slug: `salem_or` (disambiguated vs Salem, MA). Build leaf files only — no spine edits.

## Decisions

- 2026-08-28 — Claimed. Ticket US-226 body points to `salemoregon.opendata.arcgis.com` which is a 404 (domain not found). Live-probe found the real City of Salem, OR ArcGIS Online org at `salem.maps.arcgis.com` (org id `kIA6yS9KDGqZL7U3`), with 264 FeatureServer services. Three candidate feeds identified:
  1. **Structure_Permits** (FeatureServer/0) — 802 rows, permits, native point geometry (outSR=4326 → WGS84), watermark ISSUEDDATE (newest 2026-08-27T15:24:25+00:00, oldest 2025-09-08 — rolling ~1 year window), NEIGHBORHOOD + WARD columns. No future-date sentinels. ISO date literals work. → **REGISTER as permits**
  2. **Amanda_MultiFamily_Licenses_Data** (FeatureServer/0) — 1,111 rows, multifamily rental licenses + short-term rentals, native point geometry, watermark INDATE (newest 2026-08-26), EXPIRYDATE future-dated 2026-12-31 (annual cycle, expected for expiry — INDATE is the watermark, no sentinel issue). NEIGHBORHOOD + WARD columns. → **REGISTER as sla**
  3. **Land_Use_Applications** (FeatureServer/0) — 307 rows, land use applications, point geometry, INDATE watermark. Not registered — no matching FeedType / producer, small size, 307 rows is Tier-3 marginal.
  4. **311events** — 8 rows, all from 2017 (Tier 3 stale demo). **REJECT**.
  5. Marion County deeds — no open bulk API identified. **Tier 3**.
- 2026-08-28 — Store SR is WKID 2913 (Oregon State Plane South, feet). X/Y attribute columns are integer projected State Plane feet — never map as coordinates. Native geometry with outSR=4326 query returns proper WGS84 lat/lng.
- 2026-08-28 — All 802 permits and 1,111 SLA rows carry native geometry (0 null-geometry rows). needs_geocode=False.
- 2026-08-28 — SLA map refinement: OWNER (legal entity; person on short-term rows) is PII and dropped; COMPLEXNAME is the only dba/premises_name candidate; FOLDERNAME is the street address. Both maps declare no latitude/longitude candidates (State Plane trap).
- 2026-08-28 — 6 divisions / 9 submarkets, evidence-based on the live NEIGHBORHOOD column (Northgate 121, South Gateway 120, West Salem 66, East Lancaster 63, Sunnyslope 50, SEMCA 41, SESNA 40, SCAN 40, NOLA 39, CAN-DO 37, Highland 33, NEN 33, etc.).

## Current step

Complete — all leaf files written and verified.

## Outcome

**Feeds verified (live-probed 2026-08-28):**
- **permits** — Structure_Permits, `https://services.arcgis.com/kIA6yS9KDGqZL7U3/arcgis/rest/services/Structure_Permits/FeatureServer/0`, ArcGIS, **802 rows**, watermark `ISSUEDDATE` (newest `2026-08-27T15:24:25+00:00`), columns: OBJECTID, FOLDERRSN, GISID, FOLDERNUMBER, PROPERTYADDRESS, CREATEDDATE, ISSUEDDATE, SUBDESCRIPTION, WORKDESCRIPTION, STATUS, FOLDERDESCRIPTION, X, Y, NEIGHBORHOOD, WARD, DAYS_FROM_DATE, FOLDERREVISION, MAPDESCRIPTION, GlobalID. Native WGS84 point geometry (100% coverage). Rolling 1-yr window.
- **sla** — Amanda_MultiFamily_Licenses_Data, `.../Amanda_MultiFamily_Licenses_Data/FeatureServer/0`, ArcGIS, **1,111 rows**, watermark `INDATE` (newest `2026-08-26T11:23:33+00:00`), columns: OBJECTID, SUBTYPE, FOLDERNUMBER, FOLDERTYPE, FOLDERTYPEDESC, FINALDATE, INDATE, STATUS, STATUSDESC, FOLDERNAME, FOLDERDESC, ISSUEUSER, EXPIRYDATE, REFERENCENO, FOLDERGROUP, SUBCODE, SUBDESC, WORKCODE, WORKDESC, PRIORITY, PROPERTYRSN, FOLDERRSN, REVISION, CENTURY, YEAR, SEQUENCE, POINT_X, POINT_Y, OWNER, COMPLEXNAME, PROGRAMINSPDATE, INITINSPDATE, REINSPDATE, FINALINSPDATE, UNITS, BUILDINGS, NEIGHBORHOOD, WARD, GlobalID. Native WGS84 point geometry (100% coverage). EXPIRYDATE 2026-12-31 is annual-cycle expiry (not a sentinel; watermark is INDATE).
- **REJECTED:** 311events (8 stale 2017 rows); Land_Use_Applications (307 rows, no FeedType); Marion County deeds (no open bulk API).

**Tests:** `test_producers_salem_or.py` → 47 passed. `-k salem_or` green. `-m interlock` → 24 passed. Ruff on all 3 files → clean.

## Spine delta

- `CityId.SALEM_OR = "salem_or"` enum member + aliases (`"salem_or"`, `"salemoregon"`, `"salem oregon"`); slug is DISAMBIGUATED vs Salem, MA.
- `CityRegistration` with two DatasetSpecs (snapshot from `SALEM_FEED_SPECS` in `salem_or.py`):
  - `permits` — endpoint `SALEM_PERMITS_ENDPOINT` (`Structure_Permits/FeatureServer/0`), watermark `ISSUEDDATE`, platform arcgis, `topic_permits`, interval 300s, incremental, `needs_geocode=False`, `expected_cadence_days=1`.
  - `sla` — endpoint `SALEM_SLA_ENDPOINT` (`Amanda_MultiFamily_Licenses_Data/FeatureServer/0`), watermark `INDATE`, platform arcgis, `topic_sla`, interval 600s, incremental, `needs_geocode=False`, `expected_cadence_days=7`.
- Config: no new settings needed (uses existing `topic_permits`/`topic_sla`).
- Export `salem_or` from `cities/__init__.py`; dashboard `METRO_META` "Salem, OR" + snapshot/res-5 coverage + byte-synced index.html; bump leaf-naming count pin.
- Recommended Linear comment: "Salem, OR VERIFIED — 2 feeds (permits 802 / SLA 1,111), both 100% native geometry, daily cadence. Ticket's salemoregon.opendata.arcgis.com is 404; real door is services.arcgis.com/kIA6yS9KDGqZL7U3. Ready for spine registration."

## Next step

Orchestrator applies the spine delta (CityId.SALEM_OR, registry entries, dashboard wiring) and reviews the city on the map.
