# Stream log — west-nampa — 2026-08-28

## Claim

- **Stream id:** west-nampa
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/nampa.py`
  - `apps/api/src/producers/field_maps_nampa.py`
  - `apps/api/tests/unit/test_producers_nampa.py`
- **Spine files I expect to need:** NONE (leaf-only)

## Intent

Register Nampa, ID as a partial metro area. Nampa is a small city (~200K pop) with no
public REST feeds for permits (Tyler EnerGov SaaS — no public API), 311, SLA, or deeds.
The viable feeds are ROW road closures (street-cut/right-of-way permits) and
subdivision plat approvals hosted on the city's AGOL org (`nampa.maps.arcgis.com`,
org id `w6PtsxFChhUvYfXN`). All data is in Idaho State Plane West (102670/2243, feet)
— ArcGISClient handles the outSR=4326 lift. One feed registered as `permits` (road
closure permits through the DOBPermitsProducer field-map path). Final/Preliminary
Plats documented as available but not registered (no street address column for
geocode supplement).

## Decisions

- 2026-08-28 — Claimed stream. Probed cityofnampa.us → CivicPlus site, no embedded
  ArcGIS Hub. Probed `nampa.maps.arcgis.com` (AGOL org, id `w6PtsxFChhUvYfXN`, 216 items).
  Found `gisdata-nampa.hub.arcgis.com` (Hub, skeleton — no dataset API). Found
  `https://nampa.maps.arcgis.com/sharing/rest/search?q=orgid%3A%22w6PtsxFChhUvYfXN%22`
  for full item enumeration.

- 2026-08-28 — Probed CityInformation_Public MapServer
  (`utility.arcgis.com/usrsvcs/servers/2cb0c34984644eb19ebeb3f8a17b7dc9/rest/services/Public/CityInformation_Public/MapServer`).
  Layers of interest: Code Enforcement (38 — static zone polygons, not a feed),
  Address Points (35 — static reference), Canyon County Parcels (36 — 105K rows,
  Instrument null, not a deeds feed), Final Plats (41 — 53 rows, APPDATE watermark),
  Preliminary Plats (42 — 80 rows, APPDATE watermark).

- 2026-08-28 — Probed PublicRoadClosures FeatureServer
  (`utility.arcgis.com/usrsvcs/servers/7751a4c516434f1d947c67cd78a4d968/rest/services/Public/PublicRoadClosures/FeatureServer`).
  Layers: ROW_Road_Closure (3 — 76 rows, polyline, CreationDate watermark, street,
  type_, subtype_, description, Status, identifier, permitcontractor, starttime, endtime),
  ROW_Road_Detour (1 — 86 rows, polyline), ROW_Road_Closure_pt (2 — 13 rows, point),
  ROW_Flagging (0 — 1 row), ROW_Road_Closure_plgn (4 — 1 row). All in Idaho State
  Plane West (102670/2243, feet). Newest CreationDate: 1787857841000 (Aug 27, 2026).

- 2026-08-28 — Probed AGOL org for permits/311/SLA/deeds: 0 results for "permit",
  "311", "license", "deed", "inspection", "complaint", "request". Tyler EnerGov
  (nampaid-energovpub.tylerhost.net) is the permit system — no public REST API.
  Canyon County Parcels layer has null Instrument field — not a deeds feed.
  Canyon County GIS server probed: no public AGOL org found.

- 2026-08-28 — Decision: one-feed partial metro. ROW_Road_Closure registered as
  `permits` feed type (road closure/right-of-way permits through DOBPermitsProducer
  field-map path). This is the only viable feed with geometry and dates. The
  street_cut producer is hardcoded to Chicago/NYC Socrata columns and does not
  read field maps — registering as street_cut would produce no viable events.
  Final Plats and Preliminary Plats documented as available but not registered
  (no street address column for geocode supplement).

## Current step

DONE — all leaf files built and verified.

## Next step

Spine: register CityId.NAMPA + aliases + REGISTRY entry + METRO_META + dashboard byte-sync per city-registration rule. See Spine delta below for recommended member values.

## Outcome

### Feeds verified

| Feed | Layer | Platform | Rows | Watermark | Cols | Geometry | Status |
|------|-------|----------|------|-----------|------|----------|--------|
| ROW Road Closures | PublicRoadClosures/3 | arcgis | 76 | CreationDate=1787857841000 (Aug 27 2026) | street, type_, subtype_, description, Status, identifier, permitcontractor, starttime, endtime, CreationDate, EditDate, GlobalID | Polyline → centroid (outSR=4326) | REGISTERED as permits |
| ROW Road Detours | PublicRoadClosures/1 | arcgis | 86 | CreationDate | street, description, starttime, endtime, Status, identifier | Polyline → centroid | Available (not registered) |
| Final Plats (Active) | CityInformation_Public/41 | arcgis | 53 | APPDATE=1780534800000 (Jun 2026) | PROJID, DEVNAME, PSTATUS, PCATEGORY, APPDATE | Polygon → centroid | Available (not registered) |
| Preliminary Plats (Active) | CityInformation_Public/42 | arcgis | 80 | APPDATE | PROJID, DEVNAME, PSTATUS, PCATEGORY, APPDATE | Polygon → centroid | Available (not registered) |

### Rejected feeds

- **Permits**: Tyler EnerGov SaaS (nampaid-energovpub.tylerhost.net), no public REST API
- **311/Service Requests**: None found in AGOL org or city website
- **SLA/Business Licenses**: None found in AGOL org
- **Deeds**: Canyon County Parcels layer has null Instrument
- **Code Enforcement**: Static zone polygon (cezone field only)
- **Trash Collection**: Static schedule polygon
- **Storymaps Crashes**: Empty/no fields

### Confirmed mixed-CRS trap

All layers use Idaho State Plane West (102670/2243, feet). ArcGISClient requests
outSR=4326, so the geometry lift produces WGS84 lat/lng. The attribute columns
are in State Plane feet — the field map never maps them as latitude/longitude.

### Spine delta

Expected CityId member: `NAMPA = "nampa"` (to be added to city_registry.py:771).
Expected aliases: `"nampa": CityId.NAMPA, "nampa_id": CityId.NAMPA, "nampa-id": CityId.NAMPA, "nampa id": CityId.NAMPA`.
Expected registration: one `permits` feed with ROW_Road_Closure endpoint, platform=arcgis,
watermark_col=CreationDate, id_keys=["identifier","OBJECTID"], topic=raw.municipal.permits,
producer_key=permits, needs_geocode=False (native geometry from centroid), field_map=field_maps_nampa.
Metro bbox: Nampa city limits (approx 43.50-43.67, -116.66-116.46).
Divisions: Downtown, West Nampa, South Nampa, East Nampa, North Nampa, and the
University/College of Western Idaho corridor, plus Old Nampa/Opportunity Zone evidence
from the city's own GIS district layers.

### Verification results (2026-08-28)

- `pytest tests/unit/test_producers_nampa.py -q`: **30 passed**
- `pytest -k nampa -q`: **32 passed**
- `pytest -m interlock -q`: **24 passed** (leaf-naming count pin stable)
- `ruff check` on the three leaf files: **All checks passed**

### Recommended Linear comment

> Nampa, ID (US-243): PROBED — one-feed partial metro, leaf built. ROW road
> closures (`PublicRoadClosures/FeatureServer/3`) registered as `permits`
> (~76 rows, polyline geometry, CreationDate watermark, newest 2026-08-27).
> Building permits are Tyler EnerGov SaaS (no public REST API); 311/SLA/
> deeds absent (Canyon County Parcels layer has null Instrument). Final/
> Preliminary Plats available but unregistered (no address column). All
> layers in Idaho State Plane West (2243 feet) — outSR=4326 geometry lift
> only. Recommend: spine hold to register `CityId.NAMPA` + aliases +
> REGISTRY entry + dashboard byte-sync per city-registration rule.