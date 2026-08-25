# West/Midwest unexplored metros: platform discovery and feed audit

**Date of survey: 2026-08-25.** Every host, dataset, watermark, and row below was probed live on that day. The six metros were left out of prior Socrata sweeps and Wave-2 surveys because their candidate hosts failed discovery — nothing in the earlier documentation should be read as evidence about them. "Live feed" means a newest-row read (watermark column descending) confirmed fresh data; Hub/CKAN `modified` metadata was treated as unreliable and never used as evidence.

## Method

For each metro: find the correct portal host(s); detect platform (ArcGIS Hub / CKAN / Socrata / custom); search the catalog for the four feed families (building permits, 311, business licenses, property sales/deeds); row-level verify every survivor — newest row by watermark descending, column list, geocoding fields, and a recent-window row count. Only newest-row reads count as evidence. See the per-metro entries for exact endpoints.

Where an ArcGIS Hub DCAT endpoint answers (`<host>.opendata.arcgis.com/api/search/v1/collections/dataset/items?q=…`), item IDs were resolved to FeatureServer URLs via the ArcGIS Online sharing REST API (`https://www.arcgis.com/sharing/rest/content/items/<id>/`) and layer metadata + newest rows fetched directly. Where MapServer `/sharing/rest/services?f=json` answered with non-empty service lists, those services were enumerated and filtered.

Limits: one query per family per site, so a city marked "none found" may have a feed under a name the query missed (the Kansas City lesson applies doubly across platforms). Many of these cities store transactional permit data inside Accela or Oracle Public Sector portals that expose no public bulk API.

## Correction to the survey

Two additional ArcGIS hosts were found that the previous surveys did not probe: `slcgov.maps.arcgis.com` and `city-of-boise.opendata.arcgis.com`. Boise is the only metro among the six with any registerable feed. Salt Lake City's ArcGIS Hub has 100 datasets and 48 FeatureServices, but none carry transactional building-permit records — only infrastructure inventories, planning overlays, and Survey123 forms.

## Summary

| Metro | Correct host(s) | Platform | Register | Not register |
|---|---|---|---|---|
| Boise, ID | `city-of-boise.opendata.arcgis.com` | ArcGIS Hub | **permits** (residential-only) | 311, licenses, deeds |
| Salt Lake City, UT | `slcgov.opendata.arcgis.com` | ArcGIS Hub (GIS/catalog only) | **none** | permits, 311, licenses, deeds |
| Tucson, AZ | — (private portal, no services) | none-found | **none** | all four |
| Fresno, CA | — (private hub, DNS dead) | none-found | **none** | all four |
| Albuquerque, NM | — (hub private, maps empty) | none-found | **none** | all four |
| Grand Rapids, MI | `cityofgr.opendata.arcgis.com` | ArcGIS Hub (empty catalog) | **none** | all four |

## Per-metro findings

### Boise, ID — register residential permits only

Portal: `city-of-boise.opendata.arcgis.com` (ArcGIS Hub, ~50 datasets). Services served from `services1.arcgis.com/WHM6qC35aMtyAAlN/arcgis/rest/services/`.

- **Permits — provisional register (residential only).** `Development_Tracker_Open_Data`
  resolves to `Housing_OpenData/FeatureServer` (feature layer, 26 fields).
  Watermark `IssuedDate` (`esriFieldTypeDateOnly`): newest **2026-08-14** (3 rows issued that day, matching record prefix `BLD26`). Total 10,905 rows in catalog; 901 since 2025-01; 278 since 2026-01; 54 since 2026-07; **25 in last 30 days**. Volume is modest for a metro of 240k. **Coordinates: state-plane meters (EPSG:2229)** — point geometry present but x/y values (~2,520,000 / ~700,000) require coordinate transformation to WGS84 lat/lng for H3 indexing. `Match_addr` field provides geocoded address at `PointAddress` accuracy. ResidentialType distinguishes single-family (94% of rows) from multi-family (6%). `ReceiveDate`, `FinaledDate`, `Units`, `Score` present.
  - **Endpoint:** `https://services1.arcgis.com/WHM6qC35aMtyAAlN/arcgis/rest/services/Housing_OpenData/FeatureServer/0`
  - **Watermark:** `IssuedDate` (DateOnly, arrives as `"YYYY-MM-DD"` string)
  - **Geometry type:** Point (state-plane NAD83 Idaho Zone — needs transform)
  - **Row count estimate:** ~1,428 since 2024 (provisional)

  Caveat: this covers **new residential construction only**, not commercial permits, remodels, or demolition. The Accela system behind slcgov.com likely holds transactional permits, but it is not accessible through any public API. Boise would register as a partial city, like Austin/LA/Pittsburgh.

- **311 — no feed.** `BPD_CallsForService` is a Table (no geometry), dispatch-level cadence data without location attributes. Not citizen 311. No other candidate surfaced.

- **Licenses / deeds — no feed.** Only infrastructure, parks, trails, and GIS overlay layers.

### Salt Lake City, UT — register none

Portal: `slcgov.opendata.arcgis.com` (ArcGIS Hub, 100 datasets). Also reachable as `maps.slc.gov/server/rest/services` for some MapLayers. All services serve from `services.arcgis.com/mMBpeYj0vPFotzbe/...`.

- **Permits — no feed.** 48 FeatureServices enumerated, plus 2 MapServers. They cover: infrastructure asset inventories (hydrants, light fixtures, benches, fencing, pavement), planning/land-use overlays (Zoning Layer, Future Land Use, Transit Corridors, CRA districts), utility systems (Lead & Copper, CRT interaction reports, water system), Survey123 public feedback forms, parking permit areas, parcel data, and wildlife corridors. **None carry transactional building-permit records.** SLC stores construction permitting in Accela (via slc.gov/building-inspections) which exposes no public bulk API. The DCAT also returned items titled "Grease_Removal_Devices_view", "Parking Permit Areas", and "Fire Information Survey_form" — none relevant.

  Note: `slc-gov.maps.arcgis.com` and `slcgov.maps.arcgis.com` both answered HTTP 200 with empty service lists; `data.slco.org` (Salt Lake County) did not resolve.

- **311 — no feed.** No dataset surfaced for citizen service requests.

- **Licenses / deeds — no feed.** Only parcel snapshots and tax-collection overlays. No recorded-deed stream.

### Tucson, AZ — register none

Portals probed: `tucsonazopendata.opendata.arcgis.com` (DCAT returns 401 — private org id), `tucson.maps.arcgis.com/sharing/rest/services`, `city-of-tucson---arcgis-com.maps.arcgis.com/sharing/rest/services`, `cityoftucson.maps.arcgis.com/sharing/rest/services`, `tucsonmaps.maps.arcgis.com/sharing/rest/services`, `pimacounty.maps.arcgis.com/sharing/rest/services`. All either returned 0 services or a private-error body. The county-level Pima County portal also had no public services.

No Socrata domain matched. No CKAN endpoint found. `tucsonaz.gov` main portal exists but does not link to a programmatic open-data endpoint.

- **All four families — NOT_FOUND.** Tucson's open data appears to be published on a private ArcGIS organization or a custom portal with no publicly discoverable DCAT or REST index. Confirmed absent, not unverified.

### Fresno, CA — register none

Portals probed: `fresno.opendata.arcgis.com` (DCAT returns 401 — private), `city-of-fresno-ca---mapserver---arcgis-com.maps.arcgis.com/sharing/rest/services` (HTTP 200, 0 services), `fresnocounty.maps.arcgis.com/sharing/rest/services` (200, 84 bytes = error), `cofresno.maps.arcgis.com/sharing/rest/services` (200, 0 services), `fresno.ca.maps.arcgis.com/sharing/rest/services` (200, 84 bytes). `fresno.gov` not on Socrata (domain-not-found error). No CKAN detected.

- **All four families — NOT_FOUND.** Fresno appears to use a private ArcGIS organization or an internal GISServer that does not publish services to the public sharing REST API. No DCAT catalog is accessible without authentication. Confirmed absent, not unverified.

### Albuquerque, NM — register none

Portals probed: `abqopen.opendata.arcgis.com` (DCAT returns 401 — private), `albuquerquemaps.maps.arcgis.com/sharing/rest/services` (200, 0 services), `city-of-albuquerque-nm.maps.arcgis.com/sharing/rest/services` (400 — invalid URL), `cog-rnm.maps.arcgis.com/sharing/rest/services` (200, 0 services). `nmbbb.org` (Bernalillo County Building Department) does not respond. `data.abq.org` does not resolve. `abqnm.gov` does not resolve. No Socrata, no CKAN.

- **All four families — NOT_FOUND.** Albuquerque runs ArcGIS hosts but none expose publishable services or a public DCAT catalog. The Bernalillo County assessor/record office may hold deed data, but it is not accessible through a municipal open-data API. Confirmed absent, not unverified.

### Grand Rapids, MI — register none

Portal: `cityofgr.opendata.arcgis.com` (ArcGIS Hub DCAT answers HTTP 200 but returns 0 datasets). `grand-rapids-mi---mapserver---arcgis-com.maps.arcgis.com/sharing/rest/services` (200, 0 services). `city-of-grand-rapid.maps.arcgis.com/sharing/rest/services` (200, 0 services). Kent County MapServer (`kcnt.maps.arcgis.com`) also empty. No Socrata, no CKAN.

- **All four families — NOT_FOUND.** Grand Rapids has an ArcGIS Hub that answers the DCAT probe with an empty catalog — either the catalog hasn't been populated or datasets are hidden behind authentication. MapServer endpoints return valid JSON structures with zero services. Confirmed absent, not unverified.

## Recommendation

**One metro graduates to the candidate list: Boise, ID.** Its New Residential Permits layer is live (newest IssuedDate 2026-08-14), geocoded at point level, and carries a rich schema including `RecordID`, `Units`, `ResidentialType`, `LivingUnits`, `Score`, and address match. However, two caveats apply:

1. **Volume is low.** 278 permits since 2026-01 and only 25 in the last 30 days. Boise is the smallest metro on this list (240k city population); annual permit volume of ~1,000 is thin for a signal product.
2. **State-plane coordinates.** The geometry is EPSG:2229 (NAD83 / Idaho North State Plane, meters), not WGS84 lat/lng. Converting requires a coordinate-transform step (e.g., `pyproj` or GDAL) before H3 indexing. Without geocoding, address-only fallback using `Match_addr` could work if the downstream parser handles string addresses.
3. **Residential-only coverage.** Commercial permits, remodels, and demolitions are excluded. This makes Boise a partial registration, similar to Tampa (single-family only).

The remaining five metros (Salt Lake City, Tucson, Fresno, Albuquerque, Grand Rapids) have no registerable feeds on this evidence. Their ArcGIS hubs either contain only planning/GIS overlays with no transactional data (SLC), or are private/unreachable (Tucson, Fresno, Albuquerque, Grand Rapids). These five would need a deeper investigation — potentially county-level deed sources, Accela permit-portals with scraping APIs, or new client types (e.g., a web-scraping client for portals that only render permit data in Angular SPAs) — before being considered again.
