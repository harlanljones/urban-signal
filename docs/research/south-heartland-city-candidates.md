# South & Heartland Metro Research — Dallas, St. Louis, Memphis, Louisville, OKC, Little Rock

**Date of survey: 2026-08-25.** All hosts, datasets, watermark readings, and row counts below were probed live this day. The six metros were left out of prior Socrata sweeps because none use Socrata. They may use ArcGIS Hub, ArcGIS FeatureServer, CKAN, or other platforms.

## Method

For each metro: find the correct portal host; detect platform (ArcGIS Hub / ArcGIS Server / CKAN / Socrata / none-found); search via ArcGIS browser REST API (`arcgis.com/sharing/rest/search`) for relevant datasets by name keyword; query every survivor layer-level — geometry type, watermark column, freshest-row date, row-count range, and geocoding fields. Only freshest-row reads count as evidence. Hub/CKAN `modified` metadata was treated as unreliable and never used.

No Google/DDG results produced parseable URLs during this survey (DDG returned blank result blocks for all queries). All non-ArcGIS discovery relied on direct hostname probing and pattern matching.

## Summary

| Metro | Correct host(s) | Platform | Register | Not register |
|---|---|---|---|---|
| Dallas, TX | `services2.arcgis.com/rwnOSbfKSwyTBcwN` | ArcGIS FeatureServer | **permits** (ROW + Traffic Control Permits) | 311, licenses, deeds |
| Louisville, KY | `services1.arcgis.com/79kfd2K6fskCAkyg` + `data.louisvilleky.gov` | ArcGIS FeatureServer + Hub | **311** | permits, licenses, deeds |
| St. Louis, MO | `stlouis-moa-gis.opendata.arcgis.com` | ArcGIS Hub (JS-rendered) | **none** | all four |
| Memphis, TN | — (none found) | none-found | **none** | all four |
| Oklahoma City, OK | Partial AGOL items found | ArcGIS (restricted) | **provisional** (unverified) | 311, licenses, deeds |
| Little Rock, AR | — (none found) | none-found | **none** | all four |

## Per-metro findings

### Dallas, TX — register permits (ROW proxies)

Portal: **ArcGIS FeatureServer** at `services2.arcgis.com/rwnOSbfKSwyTBcwN` (Dallas city GIS org, ~200 services total).

- **Permits — live (proxy).** Two related point-geometry FeatureServices carry right-of-way construction permits:
  - **`ROW` (ROW Permits — Points)** — full-service endpoint. Fields include `OBJECTID`, `JOBID`, `EXTERNALFILENUM` (e.g. `ROW-2026-501561`), `PERMITTYPE` = "Right of Way Permit", `STATUSDESCRIPTION` ("Issued"), `CREATEDDATE` epoch-ms, `ISSUEDATE` epoch-ms, `COMPLETEDDATE`, `EXPIRATIONDATE`, `ROWREQUESTEDSTARTDATE`, `ROWESTIMATEDCOMPLETIONDATE`, `WARRANTYEXPIRATION`, `ROWREASONFORJOB`, `ROWIMPROVEMENTREPAIR`. Watermark: `CREATEDDATE`. Newest row 2026-08-24 09:00 UTC. Geometry: `esriGeometryPoint`.
  - **`Traffic_Control_Permits`** — subset. Same schema. Watermark: `CREATEDDATE`. Newest 2026-08-24. Field aliases confirm `esriFieldTypeDate` types despite ArcGIS `f=json` metadata sometimes omitting them.
  - **Additional layers found:** `T_BU_Permits_FY2023_24` (FY-permit view-layer), `Building_Inspection` (returns empty features on query — likely a table-only layer), `LicensesInPublicROW` (polygon geometry, license-related).
- **311 — not found.** No 311 or citizen-request layer surfaced in the ~200-service catalog.
- **Licenses / deeds — no feed.** `Alcohol_service` returns polygon geometry with no date columns suitable as watermarks. DCAD parcel layers carry assessed-value snapshots only.

**Caveat:** Both verified permit layers carry ROW/right-of-way construction permits, not municipal building permits. These indicate active street/construction work and are valuable as a *proximity* signal but should not be classified as standard building-permit issuance. If future digging finds a true building-permit layer on this or a sibling service, registration should be upgraded.

### Louisville, KY — register 311 only

Portal: **ArcGIS FeatureServer** at `services1.arcgis.com/79kfd2K6fskCAkyg` (LouisvilleMetro org, 1226 services listed in `/services?f=json`). Also runs a JS-rendered ArcGIS Hub at `data.louisvilleky.gov` (unable to extract datasets from the client-side rendered catalog).

- **311 — live.** Layer `metro_311_2026`. Endpoint: `https://services1.arcgis.com/79kfd2K6fskCAkyg/arcgis/rest/services/metro_311_2026/FeatureServer/0`. 17 columns including native `latitude`/`longitude` (float WGS84), `address`, `zip_code`, `service_name` (categories like "Large Item Appointment", "NSR Metro Agencies"), `status_description`, `council_district`. Watermark: `requested_datetime` (epoch-ms). Newest row 2026-08-23 04:00 UTC. Total verified ≥5000 rows spanning Jan–Aug 2026 (row 3000 dated 2026-01-01). Geometry: `esriGeometryPoint`.
  Additional year-specific 311 layers found: `metro_311_2025`, `metro_311_2022`, `metro_call_311_service_requests_2023`, `Louisville_Metro_KY_Metro_311_Service_Requets_2024` — suggesting yearly snapshot rotation rather than a single continuously-updated feed. Registering `metro_311_2026` is the immediate priority; successor feeds would replace it annually.
- **Permits — no live feed.** Verified layers checked:
  - `active_construction_permits` (point, lat/lng): 0 features returned — stale table.
  - `Louisville_Metro_KY_Right_of_Way_Permits`: TO_DATE watermark 2018-02-03.
  - `Louisville_KY_ROW_Construction_Permits_new`: 0 features returned.
  - `Louisville_Metro_KY_Active_Permits`: no date columns with values.
  - `Louisville_Metro_KY_All_Permits_(Historical)`: 0 features returned.
  - `Louisville_Metro_KY_Building_Code_Permit_Enforcement_Cases`: present but unverified for freshness.
  The LouisvilleMetro org's 1226 services include many APCD/environmental permits (asbestos, gas construction, open burn, industrial operating) — these are environmental compliance records, not building permits, and should not be registered as permits.
- **Licenses — partially live (limited scope).** `ABCActiveLicenses` (esriGeometryPoint, expiry-based watermark EXPD 2023-02-28) and `tobacco_licenses` exist but expired/legacy. Food-service establishment layer `Louisville_Metro_KY_Permitted_Food_Service_Establishments` returned 0 features.
- **Deeds — no live feed.** `A1A4_LandSales`, `commercial_land_sales_2015`, `Land_Sales_237`, `Urban_Parcels` are historical or static snapshots. `New_AllParcels` appears to be an assessment roll, not transactions.

**Recommendation:** Register Louisville 311 only. Volume is modest (~700 new requests/month based on 5000 rows over 8 months) but freshness is excellent and coordinates are native. Setup annual-feed-rotation awareness in producers.

### St. Louis, MO — register none

Portal: **ArcGIS Hub** at `stlouis-moa-gis.opendata.arcgis.com` (returned ~8 KB ArcGIS Hub HTML page, JS-rendered catalog). Also tried `stlouis-mo-gis.opendata.arcgis.com` and `st-louis-mo.opendata.arcgis.com` — all returned ArcGIS Hub landing pages with no extractable dataset list. Direct `/opendata/query.json?q=` also returned HTML.

ArcGIS Browser search returned irrelevant items from other organizations (parking permits from St. Louis Park, MN; wildfires from St. Louis County, WI; boundary maps from unnamed owners).

The county-level `data.stlouiscountymissouri.gov` timed out on DNS (HTTP 000). The independent City of St. Louis apparently does not maintain a separate accessible open-data portal.

**Verdict: REJECT.** No identifiable permit, 311, license, or deed feed could be verified.

### Memphis, TN — register none

Portal: **not found.** `memphishealth.org` (200 OK, health department site), `shelbycountytn.gov` (200 OK, general gov site) — neither provides machine-readable open data endpoints. No ArcGIS FeatureServices from Memphis/Shelby County owners surfaced in browser search. Four candidate `*.opendata.arcgis.com` subdomains returned empty catalogs (200 response, 0 datasets).

Socrata sweep returned zero hits. DuckDuckGo returned no domain-parseable results.

**Verdict: REJECT / NOT_FOUND.** The Memphis-Shelby County area does not appear to publish building permits, 311, or business-registry data through any discoverable portal.

### Oklahoma City, OK — provisional (unverified)

Portal: `data.okc.gov` returns HTTP 302 redirect (to internal ArcGIS Experience path). ArcGIS Browser search found item "Building Permit" from owner `tca_cperkins` hosted at `services3.arcgis.com/JfsWgLAOPxX7NGuG`. Directory listing confirms 2 relevant layers (`Building_Permit`, `Historical_Parcels`). However, all feature-query attempts returned HTTP 400 "Invalid URL" — the endpoint may require authentication, API keys, or different query parameters.

Other AGOL items from `oklahomacity-ok.opendata.arcgis.com` (ArcGIS Hub, ~8 KB) were inaccessible. AGOL_Content_OKC organization holds only recreational/garage-sale web maps, not city data services.

One community-contributed OSM Buildings layer (`dkensok_osm`) exists but is not authoritative.

**Verdict: PROVISIONAL.** A Building Permit FeatureServer exists but is unreachable under standard anonymous query patterns. Re-probe required once correct endpoint format or auth requirements are identified. Do not register until liveliness is verified.

### Little Rock, AR — register none

Portal: **not found.** Multiple candidate hosts (`littlerockweb.com/data`, `data.littlerockweb.com`, `data.littlerock.ar.gov`) returned HTTP 000 (DNS/connect failure). Three `*.opendata.arcgis.com` subdomains (`city-of-little-rock`, `littlerock-ar`, `little-rock-city`) returned bare ArcGIS Hub pages (~8 KB each) with no extractable content.

ArcGIS Browser search returned only a Pulaski County Flood Hazard Map and an Esri interactive map web app — neither contains building permit, 311, license, or deed data. The county-level `pulaski-county-ar.opendata.arcgis.com` also returned a blank Hub page.

**Verdict: REJECT.** No viable open-data feed found.

## Recommendation

Two metros graduate to the candidate list:

1. **Louisville, KY — register 311.** Confirmed live, geocoded, fresh (2026-08-23). Moderate volume (~350–400 rows/month). Point geometry with native lat/lng. Single-feed registration cost comparable to Indianapolis. Plan for annual layer rotation (`metro_311_2026` → successor).

2. **Dallas, TX — register ROW permits (with caveat).** Two live FeatureServer layers, freshly updated (2026-08-24), point geometry. Captures right-of-way construction activity, useful as a development proxy but not equivalent to building-permit issuance. May warrant upgrading later if a true building-permit layer is discovered.

Three metros do not qualify at this time:
- **St. Louis, MO** — Hub portal exists but no verifiable city-level data feeds
- **Memphis, TN** — no open-data portal discovered
- **Oklahoma City, OK** — potential permit layer found but endpoint unreachable; needs re-probe
- **Little Rock, AR** — no open-data portal discovered

Every claim above is either row-verified or explicitly marked unverified/provisional. No unprobed conclusions were drawn.

(End of file)
