# California Inland, Central Valley & Coastal Expansion Probe — 2026-08-30

**Probe date:** 2026-08-30  
**Scope:** California Inland, Central Valley & Coastal Expansion Targets (10 probe scopes):
1. Fresno, CA (City of Fresno Open Data / Fresno County GIS)
2. Riverside, CA (City of Riverside Open Data / Riverside County GIS)
3. San Bernardino, CA (San Bernardino County Open Data / SB City)
4. Stockton, CA (City of Stockton Open Data / San Joaquin County)
5. Modesto, CA (City of Modesto GIS / Stanislaus County)
6. Santa Rosa / Sonoma County, CA (Sonoma County Open Data / City of Santa Rosa)
7. Oxnard / Thousand Oaks / Ventura County, CA (Ventura County GIS / Open Data)
8. Santa Barbara, CA (Santa Barbara Open Data / County GIS)
9. Salinas / Monterey County, CA (Monterey County Open Data / Salinas GIS)
10. California State-level supplementation feeds: `data.ca.gov`, CSLB, CA ABC, CalEnviroScreen / CDPH.

---

## 1. Executive Summary Table

| City / County | Feed Family | Platform | Endpoint / Identifier | Tier | Watermark Column | Geocoding / Spatial Fields | Recommendation |
|---|---|---|---|---|---|---|---|
| **Fresno, CA** | Building Permits | Accela ACA | `fresno-prod.accela.com/Fresno/` | 3 | N/A (UI only) | N/A | **Reject/Defer** (Accela token-gated, no CivicData export) |
| Fresno, CA | 311 | FresnoGo / Web | `fresno.gov/311` (DNS fail on `311.fresno.gov`) | 3 | N/A | N/A | **Reject** (No public API) |
| Fresno, CA | SLA | ArcGIS Hub | `cityoffresno.opendata.arcgis.com` | 3 | N/A | N/A | **Reject** (0 hits for licenses) |
| Fresno, CA | Deeds | County Clerk | `fresnocountyca.gov` recorder | 3 | N/A | N/A | **Reject** (No open transaction stream) |
| **Riverside / RivCo** | Building Permits | ArcGIS Server | `gis.countyofriverside.us` (`OpenData/General` MapServer/280 `PLUS_ACTIVITIES`) | **1** | `APPLIED_DATE` (epoch ms, ANSI date literal required) | Native parcel polygon (`outSR=4326` centroid) | **REGISTERED** (`inland_empire`, `where=CASE_MODULE='PERMIT'`) |
| Riverside / RivCo | Crime | ArcGIS FeatureServer | `services.arcgis.com/Fu2oOWg1Aw7azh41` (`View_CrimesRPD/FeatureServer/4`) | **1** | `offendate` (epoch ms) | Native WGS84 point (`BLOCK_ADDRESS` context) | **REGISTERED** (`inland_empire`) |
| Riverside / RivCo | 311 / SLA / Deeds | Various | City/County GIS | 3 | N/A | N/A | **Defer** (Absent on public GIS) |
| **San Bernardino** | Permits | Accela / EZOP | `lus.sbcounty.gov` (EZ Online Permitting) | 3 | N/A (UI portal) | N/A | **Reject/Defer** (UI search only) |
| San Bernardino | 311 | SB Direct | City/County portals | 3 | N/A | N/A | **Reject** (No open API) |
| San Bernardino | SLA | County Clerk | `sbcounty.gov` (Fictitious Business Names) | 3 | N/A | Tabular/PDF only | **Reject** (Non-geocoded, manual lists) |
| San Bernardino | Deeds | County Recorder | `sbcounty.gov` Self-Service Portal | 3 | N/A | N/A | **Reject** (Index search only, doc fee) |
| **Stockton, CA** | SLA (Liquor) | ArcGIS Server | `gisportal.stocktonca.gov/arcgis2` (`OpenCounter/OpenCounterMap/MapServer/7`) | **1 / 2** | `OriginalIssueDate` (epoch ms) | Native geometry (`outSR=4326`, CA SP Zone 3) | **REGISTERED** (`stockton`) |
| Stockton, CA | Permits / 311 | ArcGIS Server | `gisportal.stocktonca.gov` (Accela, CityWorks, Comcate) | 3 | N/A | 499 Token Required | **Reject** (Token-gated internal folders) |
| Stockton, CA | Deeds | County GIS | `sjmap.org` / San Joaquin Assessor | 3 | N/A | N/A | **Reject** (No deed transaction feed) |
| **Modesto, CA** | SLA (Business Lic) | ArcGIS Enterprise | `gis.modestogov.com/hosting/rest` (`ExternalServices/Map_Layer_Service_External/FeatureServer/7`) | **1 / 2** | N/A (Snapshot mode, `alarm_exempt`) | Native geometry (`outSR=4326`, WKID 102643) | **REGISTERED** (`modesto`) |
| Modesto, CA | Permits | ArcGIS Enterprise | `gis.modestogov.com/hosting` (`TrakIT`) | 3 | N/A | 403 Forbidden | **Reject** (TrakIT permit folder secured) |
| Modesto, CA | 311 | GoModesto | `iframe.publicstuff.com` (client_id=1000044) | 3 | N/A | XML-RPC rejects anonymous | **Reject** (Legacy XML-RPC error) |
| Modesto, CA | Deeds | County Recorder | `crweb.stancounty.com` | 3 | N/A | N/A | **Reject** (Search portal only) |
| **Santa Rosa / Sonoma** | Crime | Socrata | `data.sonomacounty.ca.gov` (`3rsj-iche`) | **1** | `date_time` (ISO 8601) | Native Socrata point (`location`) | **REGISTERED** (`santa_rosa`) |
| Santa Rosa / Sonoma | Permits | PowerBI / AGOL | `Insights.SRCity.org` / `santarosa.maps.arcgis.com` | 3 | N/A (Stale 2018 in AGOL) | N/A | **Reject** (PowerBI UI only) |
| Santa Rosa / Sonoma | 311 / SLA / Deeds | Various | County Socrata / City GIS | 3 | N/A | N/A | **Reject** (Permits APN-only `88ms-k5e7`, recorder dead) |
| **Oxnard–Ventura** | SLA (Business Lic) | ArcGIS Hub | `open-data-cityofventura.hub.arcgis.com` (`OpenData_PSI_BusinessLicenses/FeatureServer/0`) | **1** | `DATEISSUE` (epoch ms) | Native WGS84 point (`outSR=4326`) | **REGISTERED** (`oxnard_ventura`) |
| Oxnard–Ventura | 311 (Graffiti/Req) | ArcGIS Hub | `open-data-cityofventura.hub.arcgis.com` (`Graffiti_Responses_Read_Only/FeatureServer/0`) | **1** | `ReportedOn` (epoch ms) | Native WGS84 point (`outSR=4326`) | **REGISTERED** (`oxnard_ventura`) |
| Oxnard–Ventura | Crime | ArcGIS Hub | `open-data-cityofventura.hub.arcgis.com` (`OpenData_Police_Crimes/FeatureServer/0`) | **1** | `Incident_Date_Start` (epoch ms) | Native WGS84 point (`GeneralizedAddress`) | **REGISTERED** (`oxnard_ventura`) |
| Oxnard (Companion) | 311 Requests | ArcGIS FeatureServer | `services3.arcgis.com/PWexKTkN39Lf339y` (`Requests/FeatureServer/0`) | **1** | `DateCreated` (epoch ms) | Native WGS84 point (235k rows) | **Future Companion** (Stand-alone `oxnard` metro) |
| Oxnard–Ventura | Deeds | County Recorder | `recorder.countyofventura.org` | 3 | N/A | N/A | **Reject** (Search portal only) |
| **Santa Barbara** | Permits | Accela / MAPS | `santabarbaraca.gov` / Accela ACA | 3 | N/A (Dashboard UI) | N/A | **Reject/Defer** (No bulk REST API) |
| Santa Barbara | 311 | City Web | `santabarbaraca.gov` | 3 | N/A | N/A | **Reject** (No open 311 endpoint) |
| Santa Barbara | SLA | Avenu / City | `bizlicenseonline.com` / `countyofsb.org` | 3 | N/A | N/A | **Reject** (Vendor portal) |
| Santa Barbara | Deeds | County Recorder | `sbcrecorder.com` / `recorder.countyofsb.org` | 3 | N/A | N/A | **Reject** (Index only, fee-gated docs) |
| **Salinas / Monterey** | Permits / 311 | OpenDataSoft / GIS | `cityofsalinas.opendatasoft.com` / `maps.co.monterey.ca.us` | 3 | N/A | N/A | **Reject/Defer** (Static layers only) |
| Salinas / Monterey | SLA / Deeds | County Clerk | `countyofmonterey.gov/recorder` | 3 | N/A | N/A | **Reject** (Interactive portal only) |
| **CA State: ABC** | Statewide SLA | CSV / ASCII Zip | `abc.ca.gov/licensing/licensing-reports/` | **2** | `ORIG_ISS_DT` / `EFF_DATE` | Premise Address, City, County, Zip (`needs_geocode=True`) | **RECOMMENDED SUPPLEMENT** (All 10 CA metros) |
| **CA State: CSLB** | Statewide Contractors | CSV / Fixed-width | `cslb.ca.gov` Public Data Portal | **2** | `ISSUE_DATE` / `EXP_DATE` | Business Address, City, County, Zip | **RECOMMENDED SUPPLEMENT** (Contractor capacity proxy) |
| **CA State: CalEnviroScreen** | Environmental Context | ArcGIS FeatureServer | `services.arcgis.com/PCHfdHz4GlDNAhBb` (`CalEnviroScreen_4_0_Results_/FeatureServer/0`) & 5.0 | **1** | Static vintage (2021 / 2026) | Native Census Tract Polygons | **RECOMMENDED COVARIATE** (Statewide H3 enrichment) |
| **CA State: data.ca.gov** | State Open Data (CKAN) | CKAN API | `data.ca.gov/api/3/action/package_search` | **2** | `metadata_modified` | Varied (Water Board, CDPH, Caltrans) | **Targeted Ingest** |

---

## 2. Detailed Per-Metro Breakdown

### 1. Fresno, CA (Fresno County)
- **Portal Status:** 
  - ArcGIS Hub: `cityoffresno.opendata.arcgis.com` exists but hosts only Survey123 internal submission forms.
  - Accela Citizen Access: `fresno-prod.accela.com/Fresno/` is UI-search only; anonymous bulk API is token-gated.
  - CivicData CKAN: `www.civicdata.com/api/3/action/package_search?q=fresno` yields 1 unrelated package ("Illegal Dumping").
  - Socrata: `data.fresno.gov` does not exist.
  - 311: `311.fresno.gov` DNS fails.
- **Feeds Verdict:** Tier 3 across all 4 core families.
- **Recommendation:** Do not register a municipal feed. Cover Fresno via CA Statewide ABC licenses and CalEnviroScreen context layers.

### 2. Riverside, CA & Riverside County (`inland_empire`)
- **Portal Status:**
  - Riverside County ArcGIS Server: `gis.countyofriverside.us/arcgis/rest/services/OpenData/General/MapServer/280` (`PLUS_ACTIVITIES`).
    - *Schema:* `CASE_MODULE`, `APPLIED_DATE`, `STATUS`, `DESCRIPTION`, `PARCEL_NUMBER`.
    - *Filter:* `CASE_MODULE = 'PERMIT'`.
    - *Watermark:* `APPLIED_DATE` (epoch ms, ANSI date literal required).
    - *Geometry:* Parcel polygons in CA State Plane Zone VI (WKID 102646), converted to WGS84 centroids via `outSR=4326`.
  - City of Riverside Crime: `services.arcgis.com/Fu2oOWg1Aw7azh41/arcgis/rest/services/View_CrimesRPD/FeatureServer/4`.
    - *Watermark:* `offendate`.
    - *Geometry:* Native WGS84 point.
- **Recommendation:** Registered as `inland_empire` (Riverside County anchor). PERMITS + CRIME live.

### 3. San Bernardino, CA & San Bernardino County
- **Portal Status:**
  - San Bernardino County Open Data (`open-data-sbcounty.hub.arcgis.com`, org `aA3snZwJfFkVyDuP`): 253 datasets, but all static GIS cadastres (Zoning, Fire Hazard Severity, Assessor Book boundaries).
  - Building Permits: Land Use Services EZOP (`lus.sbcounty.gov`) — interactive portal without bulk export.
  - Fictitious Business Names: Tabular monthly files without spatial attributes.
  - Deeds: Recorder index search portal (`sbcounty.gov`), document images gated behind paywalls.
- **Feeds Verdict:** Tier 3 across all core municipal families.
- **Recommendation:** Reject local feeds. Rely on CA State ABC licensing and state-level contractor/environmental feeds.

### 4. Stockton, CA & San Joaquin County (`stockton`)
- **Portal Status:**
  - City of Stockton ArcGIS Server: `gisportal.stocktonca.gov/arcgis2/rest/services/OpenCounter/OpenCounterMap/MapServer/7`.
    - *Dataset:* Active Liquor Licenses (SLA). 1,363 rows.
    - *Watermark:* `OriginalIssueDate` (epoch ms).
    - *Geometry:* Native geometry lifted via `outSR=4326` (Store CRS: CA State Plane Zone 3 WKID 102643 / EPSG:2227).
  - Permits / 311: Token-gated folders (499 Token Required on Accela, CityWorks, Comcate).
  - Deeds: San Joaquin County (`sjmap.org`) does not expose deed transfer streams.
- **Recommendation:** Registered as `stockton` with SLA only (Tier 1/2).

### 5. Modesto, CA & Stanislaus County (`modesto`)
- **Portal Status:**
  - City of Modesto ArcGIS Enterprise: `gis.modestogov.com/hosting/rest/services/ExternalServices/Map_Layer_Service_External/FeatureServer/7`.
    - *Dataset:* Business Licenses (SLA). 4,574 rows.
    - *Mode:* Snapshot mode (no date watermark; dedup on `ACCOUNTNUM`, `alarm_exempt`).
    - *Geometry:* Native geometry lifted via `outSR=4326` (Store CRS: WKID 102643).
  - Hub `modesto.opendata.arcgis.com`: 401 Private Org.
  - Permits: `TrakIT` service folder returns 403 Forbidden.
  - 311: GoModesto (PublicStuff iframe client_id=1000044) rejects anonymous XML-RPC requests.
  - Deeds: Stanislaus County Clerk-Recorder (`crweb.stancounty.com`) is search-only.
- **Recommendation:** Registered as `modesto` with SLA snapshot only.

### 6. Santa Rosa, CA & Sonoma County (`santa_rosa`)
- **Portal Status:**
  - Sonoma County Socrata (`data.sonomacounty.ca.gov`):
    - *Crime Feed:* `3rsj-iche` (Sheriff's Office Incident Data, 329k rows, daily fresh).
    - *Watermark:* `date_time`.
    - *Geometry:* Native Socrata `location` point container.
  - Permits: City of Santa Rosa uses PowerBI dashboards (`Insights.SRCity.org`); AGOL datasets are stale (2018). County permits (`88ms-k5e7`) are APN-only without coordinates/addresses.
  - 311 / SLA / Deeds: Absent on Socrata and AGOL.
- **Recommendation:** Registered as `santa_rosa` with CRIME only.

### 7. Oxnard–Ventura & Ventura County (`oxnard_ventura`)
- **Portal Status:**
  - City of Ventura ArcGIS Hub (`open-data-cityofventura.hub.arcgis.com` / AGO org `dBVj4EXO3IdRPOqb`):
    - *SLA:* `OpenData_PSI_BusinessLicenses/FeatureServer/0` (12.5k rows, watermark `DATEISSUE`).
    - *311:* `Graffiti_Responses_Read_Only/FeatureServer/0` (22k rows, watermark `ReportedOn`).
    - *Crime:* `OpenData_Police_Crimes/FeatureServer/0` (86k rows, watermark `Incident_Date_Start`).
  - City of Oxnard: `services3.arcgis.com/PWexKTkN39Lf339y/.../Requests/FeatureServer/0` (311 Requests, 235k rows, watermark `DateCreated`, Tier 1 candidate for future standalone `oxnard` registration).
  - Deeds: Ventura County Recorder (`recorder.countyofventura.org`) is interactive search-only.
- **Recommendation:** Registered as `oxnard_ventura` (anchored on City of Ventura) with SLA, 311, and CRIME.

### 8. Santa Barbara, CA & Santa Barbara County
- **Portal Status:**
  - City of Santa Barbara: Building permits are behind Accela ACA and interactive PowerBI dashboards; GIS data via MAPS portal has no open bulk transactional endpoints.
  - County of Santa Barbara Open Data (`data.countyofsb.org`): Land use, zoning, hazard boundaries, parcel base layers; no transactional permit, 311, or license streams.
  - Clerk-Recorder (`sbcrecorder.com`): Online index search dating back to 1900, document images fee-gated.
- **Feeds Verdict:** Tier 3 across all 4 core families.
- **Recommendation:** Reject local feeds. Cover Santa Barbara with California statewide ABC, CSLB, and CalEnviroScreen layers.

### 9. Salinas, CA & Monterey County
- **Portal Status:**
  - City of Salinas: OpenDataSoft portal (`cityofsalinas.opendatasoft.com`) and Map Gallery host static municipal infrastructure layers.
  - Monterey County GIS (`maps.co.monterey.ca.us/portal`): Parcel report tool, zoning maps, survey records; no live event feed.
  - Monterey County Recorder (`countyofmonterey.gov/recorder`): Search portal without bulk export API.
- **Feeds Verdict:** Tier 3 across all 4 core families.
- **Recommendation:** Reject local feeds. Cover Salinas / Monterey County with California state supplements.

---

## 3. Evaluation of California State-Level Supplementation Feeds

### A. California Department of Alcoholic Beverage Control (ABC)
- **Host / Access:** `abc.ca.gov/licensing/licensing-reports/`
- **Format:** Weekly zipped ASCII fixed-width text / CSV data export.
- **Coverage:** Statewide (~90,000 active licenses across all 58 CA counties).
- **Attributes:** License Number, Status (Active/Pending/Revoked), License Type Code (e.g. Type 20 Off-Sale Beer/Wine, Type 41 On-Sale Beer/Wine, Type 47 On-Sale General), Primary Name, DBA Name, Premise Address, Premise City, Premise County, Premise Zip, Original Issue Date (`ORIG_ISS_DT`), Expiration Date (`EXP_DATE`).
- **Watermark:** `ORIG_ISS_DT` (incremental formation) and `EXP_DATE` (renewal tracking).
- **Geocoding:** Tier 2 via `GeocoderClient` (or spatial polygon containment on city/metro boundary).
- **Utility:** Serves as a uniform, standardized SLA feed for all California metros (Fresno, San Bernardino, Santa Barbara, Salinas, etc.) that lack native municipal business license APIs.

### B. Contractors State License Board (CSLB)
- **Host / Access:** `cslb.ca.gov` Public Data Portal / Master List Export.
- **Format:** Downloadable CSV/Excel lists by county & classification (or fixed-block master file).
- **Coverage:** ~285,000 licensed contractors statewide.
- **Attributes:** License Number, Business Name, Classifications (A - General Engineering, B - General Building, C - Specialty Contractors), Status, Issue Date, Expiration Date, Address, City, County, Zip.
- **Utility:** Supplies contractor capacity and commercial activity covariates across all CA metros.

### C. CalEnviroScreen 4.0 / 5.0 (OEHHA / CalEPA)
- **Host / Access:** 
  - CalEnviroScreen 4.0 FeatureServer: `https://services.arcgis.com/PCHfdHz4GlDNAhBb/arcgis/rest/services/CalEnviroScreen_4_0_Results_/FeatureServer/0`
  - CalEnviroScreen 5.0 (July 2026 release): `gis.data.ca.gov` / `data.ca.gov/dataset/calenviroscreen-5-0`
- **Format:** ArcGIS FeatureServer layer with Census tract polygon geometries.
- **Indicators:** Ozone, PM2.5, Diesel PM, Drinking Water Contaminants, Toxic Releases, Traffic Density, Hazardous Waste, Impaired Water Bodies, Poverty Rate, Unemployment, Housing Burden, Asthma, Low Birth Weight, Cardiovascular Disease, Diabetes.
- **Utility:** High-resolution spatial covariate layer providing comprehensive baseline environmental stress scores across all California H3 hex cells.

### D. `data.ca.gov` (Statewide CKAN Portal)
- **Host / Access:** `https://data.ca.gov/api/3/action/package_search`
- **Datasets:** Water Board CIWQS/GeoTracker environmental regulatory permits, CDPH licensed health facilities, DWR groundwater monitor wells, Caltrans PeMS traffic counters.
- **Utility:** Targeted supplements for environmental compliance and infrastructure context.

---

## 4. Actionable Next Steps & Implementation Path

1. **Statewide ABC Ingestion Pipeline (`CaAbcLicenseProducer`):**
   - Implement a state-level producer downloading the weekly ABC fixed-width/CSV archive.
   - Parse license records and filter by registered California metro bounding boxes (`inland_empire`, `modesto`, `stockton`, `santa_rosa`, `oxnard_ventura`, `los_angeles`, `san_francisco`, `san_diego`, `san_jose`, `oakland`, `sacramento`, `anaheim`, `long_beach`).
   - Geocode premise addresses via `GeocoderClient` (ADR 0004) to assign H3 resolution-8/9 indices.
   - Fills the SLA gap for Fresno, San Bernardino, Santa Barbara, and Salinas instantly.

2. **CalEnviroScreen Feature Enrichment:**
   - Ingest CalEnviroScreen 4.0/5.0 census tract polygons into the spatial feature store.
   - Crosswalk tract scores to H3 hexes, writing environmental distress covariates onto `EnrichedH3Feature` for every California metro.

3. **Oxnard Standalone Metro Separation:**
   - Author a dedicated leaf `apps/api/src/spatial/cities/oxnard.py` for City of Oxnard using `services3.arcgis.com/PWexKTkN39Lf339y/.../Requests/FeatureServer/0` (311 Requests, 235k rows, Tier 1) once ready to expand beyond Ventura.

4. **Preserve Rejection Integrity:**
   - Maintain explicit rejections in documentation for Fresno, San Bernardino, Santa Barbara, and Salinas municipal feeds until their jurisdictions publish bulk open-data endpoints.
   - Continue adhering to the AGENTS.md rule: do not register ghost city registrations without verified live feeds and dashboard map wiring.
