# Stream log — west-las_cruces — 2026-08-28

## Claim

- **Stream id:** west-las_cruces (US-240)
- **Leaf files created:**
  - `apps/api/src/spatial/cities/las_cruces.py` (NEW — metro bbox + 6 divisions + 9 submarkets + FEED_SPECS)
  - `apps/api/src/producers/field_maps_las_cruces.py` (NEW — PERMITS_FIELD_MAP + BUSREG_FIELD_MAP)
  - `apps/api/tests/unit/test_producers_las_cruces.py` (NEW — 42 spine-independent tests)
- **Spine files I expect to need (NOT edited by this leaf):**
  - `apps/api/src/spatial/city_registry.py` — CityId.LAS_CRUCES enum + ALIASES + REGISTRY entry
  - `apps/api/src/spatial/cities/__init__.py` — export
  - `apps/api/src/config.py` — endpoint settings
  - Dashboard METRO_META + byte-sync index.html

## Intent

Register Las Cruces, NM (~220K, Doña Ana County) as a TWO-FEED PARTIAL metro:
BuildingPermits (permits, ~82k rows, native WKID 4326 point geometry, Issued_Date watermark)
and Business_Registrations (SLA-adjacent business licenses, ~26k, LastUpdateDate watermark).
311 (Tyler Portico, no open API) and deeds (county parcel data, no sales/deeds feed) are Tier 3.

## Probe evidence (2026-08-28, live)

### City ArcGIS Server
- **Server:** `https://maps.las-cruces.org/gis/rest/services/Information_Services/MapServer`
- **Org:** `ejcbAsQEUUGWEyzb` (City of Las Cruces ArcGIS Online org)
- **Spatial reference:** WKID 4326 (native lat/lng) — no State Plane CRS issue
- **Max record count:** 1000 per layer
- **Accepts standard ArcGIS TIMESTAMP format** (not an ANSI-date host)

### Feed 1: BuildingPermits (Layer 1) — VERIFIED
- **Endpoint:** `https://maps.las-cruces.org/gis/rest/services/Information_Services/MapServer/1`
- **Platform:** ArcGIS MapServer (Feature Layer, esriGeometryPoint)
- **Row count:** 82,433 (82,428 within metro bbox)
- **Watermark:** `Issued_Date` (esriFieldTypeDate, epoch ms → ISO via ArcGISClient)
- **Watermark range:** 2016-10-03 to 2026-08-21T06:00Z (newest: 1787292000000)
- **Future-dated rows:** 0
- **Null geometries:** 0
- **Geometry:** Native WKID 4326 point, X/Y attributes are WGS84 decimals (same CRS)
- **Key columns:** Permit_Number, Permit_Type, Permit_Location, Project_Valuation, Issued_Date, Issue_Year, IssueMonthNo, OBJECTID, Zoning, X, Y
- **PII:** Owner_Name, Contractor_Name, Contractor_Business_Name — dropped at field map

### Feed 2: Business_Registrations (Layer 2) — VERIFIED
- **Endpoint:** `https://maps.las-cruces.org/gis/rest/services/Information_Services/MapServer/2`
- **Platform:** ArcGIS MapServer (Feature Layer, esriGeometryPoint)
- **Row count:** 26,508 (26,475 within metro bbox)
- **Watermark:** `LastUpdateDate` (esriFieldTypeDate, epoch ms → ISO)
- **Watermark range:** 2018-12-09 to 2026-08-21T06:00Z
- **Geometry:** Native WKID 4326 point, X/Y attributes are WGS84 decimals
- **Key columns:** RECNO, BUSINESS_NAME, DBA, RECNAME, BusCat, BusType, NAICS, CRS (parcel), RecAddress, LastUpdateDate, IssueYear, IssueMonth, STATUS, OBJECTID, X, Y
- **PII:** ContactName, Phone, Email, MailAddress — dropped at field map

### Tier 3 (unregistered)
- **311 / Service Requests:** Tyler Portico (`cityoflascrucesnm.tylerportico.com`) — no open REST API
- **Deeds / Sales:** Doña Ana County ArcGIS Server (`gis.donaana.gov`) — only Parcels/situs, no deeds/sales feed
- **CertificateOFoccupancy (L3):** Available (7,086 rows, IssueDate) but not registered

### Division evidence
Coordinate-spatial query counts from BuildingPermits layer:
- Downtown: ~19,805 | Mesilla: ~3,317 | East Mesa: ~4,001
- Sonoma Ranch: ~15,853 | Northern: ~36,532 | West Mesa: ~22,337

## Decisions

- 2026-08-28 — Claimed per leaf contract. Two feeds (permits + SLA) meet the partial-registration threshold.
- 2026-08-28 — DISCOVERY: City of Las Cruces ArcGIS Server at `maps.las-cruces.org` (NOT the dead ArcGIS Hub hint). Three live layers (BuildingPermits 82k, Business_Registrations 26k, CertificateOFoccupancy 7k). No 311 or deeds.
- 2026-08-28 — No ANSI-date host issue — `maps.las-cruces.org` accepts standard ArcGIS TIMESTAMP queries.
- 2026-08-28 — 42 tests pass, 0 ruff errors, interlock stays 24/24.

## Current step

Complete. All gates green.

## Next step

Orchestrator applies spine delta:
- `CityId.LAS_CRUCES` enum member
- `ALIASES["las_cruces"] = CityId.LAS_CRUCES`, `ALIASES["las-cruces"] = CityId.LAS_CRUCES`, `ALIASES["las cruces"] = CityId.LAS_CRUCES` (commuter-friendly)
- `ALIASES["lc"] = CityId.LAS_CRUCES` (optional shorthand)
- `REGISTRY[CityId.LAS_CRUCES]` entry with `DatasetSpec` for both feeds:
  - PERMITS: endpoint=LAS_CRUCES_PERMITS_ENDPOINT, platform=arcgis, watermark_col=Issued_Date, id_keys=[Permit_Number, OBJECTID], needs_geocode=False, geocode_context="Las Cruces, NM", max_record_count=1000, order_by="Issued_Date DESC"
  - SLA: endpoint=LAS_CRUCES_BUSREG_ENDPOINT, platform=arcgis, watermark_col=LastUpdateDate, id_keys=[RECNO, OBJECTID], needs_geocode=False, geocode_context="Las Cruces, NM", max_record_count=1000, order_by="LastUpdateDate DESC"
- No config endpoint constants needed (uses inline URLs)
- `cities/__init__.py` import
- Dashboard METRO_META "Las Cruces, NM" + snapshot/res-5 coverage + byte-synced index.html
- Leaf-naming count bump

## Outcome

**Feeds verified:** 2 (BuildingPermits + Business_Registrations)
**Total rows:** 108,941 (82,433 + 26,508)
**Watermarks:** Issued_Date=2026-08-21T06:00Z, LastUpdateDate=2026-08-21T06:00Z
**Tests:** 42 passed, 0 ruff, 0 interlock regression
**Recommendation:** REGISTER — partial (2 feeds, 3 Tier 3)

## Stash-sweep recovery note

All 3 leaf files + this stream log are UNTRACKED (no commits per leaf contract).
If a concurrent agent's `git stash -u` / `git clean` sweeps them, recover from
`git stash list` (newest stash = stash@{0}; untracked files land in stash@{0}^3)
or `git stash pop`. Files: `apps/api/src/spatial/cities/las_cruces.py`,
`apps/api/src/producers/field_maps_las_cruces.py`,
`apps/api/tests/unit/test_producers_las_cruces.py`, `.streams/west-las_cruces.md`.

## Final verification (after field-map fix)

- Removed erroneous `zipcode: ["Zoning"]` from PERMITS_FIELD_MAP (Zoning is a
  zoning code, not a ZIP — nothing on the layer carries a site ZIP).
- Deduplicated DROPPED_PII_COLUMNS.
- Re-ran: test_producers_las_cruces.py 42 passed; ruff clean on all 3 files.
- Interlock remains 24/24 (leaf-local change only).
