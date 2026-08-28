# Southeast Probe — Biloxi, MS (US-306 leaf, stream city-biloxi)

Verdict: **NOT-VIABLE** — no live row-level feed in any of the four target
families (PERMITS / COMPLAINTS_311 / SLA / DEEDS). All candidates are either
login-walled, empty-by-design, or a different data family. Nothing was
registered; no spatial data was fabricated.

Probe date: 2026-08-28 (live, network confirmed).

## Candidate doors reviewed

The brief pointed at (a) City of Biloxi GIS, (b) Harrison County
GIS/ArcGIS Hub, (c) gulfcoast regional portals. All three were probed.

1. **City of Biloxi on-prem ArcGIS Server** — `gis.biloxi.ms.us:6443`
   (`/arcgis/rest/services`). Folders: `ComDevAMS`, `Meters4/5`,
   `Wmeters3/5`, `RSR2023/b`, `GrassCuttingSchedule`, `HydrantFlowData`,
   `ward_lines*`, `SampleWorldCities`. **All are basemap** layers (water
   utilities, hydrants, meters, zoning, buildings, addresses, contours,
   wards). No permit, 311, license, or deed record table.

2. **City of Biloxi AGOL org** (`cityofbiloxi.maps.arcgis.com`, owner
   `dbounds_cob` / hosted orgs `WJhHbwy2YfOSix5p`, `XwK5zAS8O0b6s3Tp`) —
   entertainment spots, parks, trees, 3D buildings, Go-Cup leisure
   districts, golf-cart roadways, zoo. No permits/licenses/311/deeds.

3. **Tyler TESS citizen portal** — `biloxims.tylerportico.com/tess/citizen/`.
   Angular SPA, **login-walled** ("Former Employee Access"); no public
   REST or open-data export. The city's building/business-permit system is
   Tyler (Permits/TESS), and it exposes **no public feed**.

4. **Cityworks** — `cityworks.biloxi.ms.us/Cityworks/gis/1/1193/rest/services/cw/FeatureServer`.
   Layers: 1 `Request`, 2 `WorkOrder`, 3 `Inspection`, 5 `Permit`, 11
   `WorkOrderEntity`, 23 `AssetCalculationResult`.
   - Layer 5 `Permit`: 0 rows (empty view).
   - Layer 1 `Request`: 0 rows (empty view).
   - Layer 2 `WorkOrder`: 2,337 rows, BUT these are **public-works
     maintenance work orders** ("EQUIPMENT MAINTENANCE", "TRASH PICK-UP/
     LITTER PATROL", "INSTALL METER NEW TAP", "ASPHALT REPAIR"), not
     citizen 311 requests. Native geometry is a Web-Mercator point
     view; the attributes carry state-plane `WOX/WOYCoordinate` feet. No
     citizen-requester semantics (`RequestedBy` always null on live rows).

5. **Harrison County GIS on-prem** — `geo.co.harrison.ms.us/server/rest/services`.
   Folders: `AGO`, `ALL`, `AS400`, `Beautification`, `CircuitClerk`,
   `District`, `EMA`, `External`, `Fire`, `Hosted`, `Imagery`, `Justice`,
   `Misc`, `Network`, `Print`, `SandBeach`, `Utilities`.
   - Parcel/assessment layers (`External/parcelsPublic`, `AGO/
     HarrisonCounty_ApprovedParcels`, `AS400/liveParcels` + `LandRoll`
     tables): cadastral + assessment values only. **No sale price, no
     sale/transfer date, no grantor/grantee** — assessment snapshot, not
     a deeds/transfers feed.
   - `CircuitClerk` folder → **HTTP 499 "Token Required"** (login-walled;
     Mississippi circuit clerk holds land records but the REST directory
     is not public).

6. **Harrison County AGOL org** (`HMvCOUg20YqJBIY9`, `V2PQwgZMTFfgM0Xu`,
   `POWnQ9B55SeBoOXX`) — evacuation zones, road closures, LiDAR/imagery,
   PSA map layers, school districts. No permits/licenses/311/deeds.

7. **`HarrisonCADWebService`** (services5.arcgis.com/9EzFuq4pvjRgSIO3) —
   this is **Harrison County, TEXAS** (spatial ref 102738, Texas County
   Boundaries), not Mississippi. Discarded.

8. **MS Dept of Marine Resources** (`gis.dmr.ms.gov`) — shellfish/oyster
   harvest areas, artificial reefs, tidelands, permitted leasing areas.
   Environmental/resource layers, not business/seafood licenses as a
   register, not citizen requests.

9. **Socrata national catalog** (`api.us.socrata.com`) — **zero** datasets
   match "biloxi" or "gulfport" (resultSetSize 0). No Socrata presence.

10. **ArcGIS Hub / open-data domains** — `data.biloxi.ms.us`,
    `opendata.biloxi.ms.us`, `open.gulfport-ms.gov`, `data.gulfport-ms.gov`
    all **DNS-resolve fail**. `gis.biloxi.ms.us` timed out. `co.harrison.ms.us`
    cert-name mismatch (host unreachable). No published Hub open-data portal.

## Feed-by-feed probe table

| Family | Platform | Endpoint | Watermark col + newest | 7d / 60d / total | Geo | Verdict |
|---|---|---|---|---|---|---|
| PERMITS | tyler | `biloxims.tylerportico.com/tess/citizen/` | none (login-walled) | — / — / — | none | **NOT VIABLE — login wall** |
| PERMITS | arcgis | `cityworks.../cw/FeatureServer/5` (Permit) | none; **0 rows** | 0/0/0 | no rows | **NOT VIABLE — empty** |
| COMPLAINTS_311 | arcgis | `cityworks.../cw/FeatureServer/1` (Request) | none; **0 rows** | 0/0/0 | no rows | **NOT VIABLE — empty** |
| COMPLAINTS_311 | arcgis | `cityworks.../cw/FeatureServer/2` (WorkOrder) | `InitiateDate` 2026-08-28 | 7d unknown (view bounded); 2,337 total | point geometry (Web-Merc), attribs = state-plane feet | **NOT VIABLE — maintenance work orders, not citizen 311** |
| SLA | — | no source found | — | — | — | **NOT VIABLE** (business licenses only in login-walled Tyler; no open register) |
| DEEDS | arcgis | `geo.co.harrison.ms.us/.../landroll` + parcels | none (assessment refresh only) | — | parcel polygons | **NOT VIABLE — assessment snapshot, no sale price/date/grantor** |
| DEEDS | arcgis | `CircuitClerk` folder | none | — | — | **NOT VIABLE — HTTP 499 token required** |

## Bottom line

Biloxi sits in a metropolitan area (Gulfport-Biloxi) where the city runs
its permitting on a **login-walled Tyler/TESS** portal and its work-order
layers publicly on **Cityworks**, but the public `Permit` and `Request`
layers are **empty**, and the live `WorkOrder` layer is internal public-
works maintenance (not citizen 311). Property records are an **assessment
snapshot** in Harrison County (no sale/transfer date, price, or grantor)
and the county's **Circuit Clerk** land-records directory is **token-walled**.
No Socrata presence, no ArcGIS Hub open-data portal. In no family is there
a live, queryable, watermark-bearing row-level feed.

Per the interlock rule and the dispatch brief, this stream **STOPS** with a
documented NOT-VIABLE verdict. No registration, no fabricated data, no leaf
exports.
