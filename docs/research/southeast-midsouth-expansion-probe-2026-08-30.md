# Southeast, Mid-South & Gulf Coast Expansion Probe — 2026-08-30

**Probe Date:** 2026-08-30  
**Scope:** Southeast, Mid-South & Gulf Coast Regional Expansion Targets (11 evaluation scopes):
1. Huntsville, AL (City of Huntsville Open Data / Madison County GIS)
2. Mobile, AL (City of Mobile Open Data / Mobile County GIS)
3. Montgomery, AL (City of Montgomery Open Data / Montgomery County)
4. Columbus, GA (Columbus Consolidated Government GIS / Muscogee County)
5. Knoxville, TN (KGIS / City of Knoxville Open Data / Knox County)
6. Chattanooga, TN (Chattanooga Open Data / Hamilton County GIS)
7. Clarksville, TN (Montgomery County TN / City of Clarksville)
8. Jackson, MS (Hinds County GIS / MS State Open Data)
9. Gulfport & Biloxi, MS (Harrison County GIS / City portals)
10. Pensacola, FL (Escambia County GIS / City of Pensacola) & Tallahassee, FL updates
11. State-level administrative super-feeds (AL, GA, TN, MS, FL).

---

## 1. Executive Summary Table

| Metro / Jurisdiction | Feed Family | Platform | Endpoint / Identifier | Tier | Watermark Column | Geocoding / Spatial Fields | Recommendation / Status |
|---|---|---|---|---|---|---|---|
| **Huntsville, AL** | Building Permits | ArcGIS Server | `maps.huntsvilleal.gov/server/rest/services/Licenses/BuildingPermits/MapServer/0` | **2** | `Permit_Issue_DateTime` (date-typed) | Native WGS84 point (`outSR=4326`) + `Address` | **REGISTER WITH CAVEAT** (18.4k rows; paused 2026-08-07; re-probe gate required) |
| Huntsville, AL | 311 | Comcate | Internal CRM address master (`ComcateAddresses`) | 3 | N/A | N/A | **Reject** (No public case layer) |
| Huntsville, AL | SLA | ArcGIS Server | `Licenses/AlcoholBeverageLicenses/MapServer/0` | 3 | `ApplicationDate` | Points + Address | **Reject / Defer** (State ABC liquor only; out of family) |
| Huntsville, AL | Deeds | County Probate | Madison County Probate web UI | 3 | N/A | N/A | **Reject** (No REST sales feed) |
| **Mobile, AL** | Building Permits | Tyler EnerGov | `energovpub.tylerhost.net/apps/selfservice` | 3 | N/A | N/A | **Reject** (UI only; Hub only has right-of-way `ROW_Permitting`) |
| Mobile, AL | 311 | QAlert | `cityofmobile.public.311service.com` | 3 | N/A | N/A | **Reject** (SPA HTML, API token gated) |
| Mobile, AL | SLA | ArcGIS Hub | `cityofmobile.opendata.arcgis.com` | 3 | N/A | N/A | **Reject** (0 business license datasets) |
| Mobile, AL | Deeds | County GIS | `gis.mobilecountyal.gov/server/rest/services` | 3 | N/A | Parcel polygons (no sales date/price) | **Reject** (Assessment cadaster snapshot only) |
| **Montgomery, AL** | Building Permits | ArcGIS Hub | `opendata-citymgm.hub.arcgis.com` (Construction Permits) | **1 / 2** | `IssueDate` / `PermitDate` | Native WGS84 points | **Future Wave Target** (Verify endpoint stability & incremental SoQL/ArcGIS query) |
| Montgomery, AL | 311 | ArcGIS Hub | `opendata-citymgm.hub.arcgis.com` (311 Service Requests) | **1** | `CreationDate` / `RequestDate` | Native WGS84 points | **Future Wave Target** (Live citizen intake feed) |
| Montgomery, AL | SLA | County/City | Revenue / Tax portals | 3 | N/A | N/A | **Defer** (Use `snap_sla_spec("AL")` fallback) |
| Montgomery, AL | Deeds | County Probate | Montgomery County Probate Web Portal | 3 | N/A | N/A | **Reject** (Search UI only) |
| **Columbus, GA** | Building Permits | ArcGIS Server | `ccggisprod.columbusga.org/server/rest/services/BuildingPermits/MapServer/0` | **1** | `Issued` | Native points (`outSR=4326`, WKID 2240) | **ALREADY REGISTERED** (`columbus_ga`, US-294) |
| Columbus, GA | 311 | Citizen Access | CityWorks / CCG 311 | 3 | N/A | N/A | **Reject** (Internal ticketing portal) |
| Columbus, GA | SLA | USDA SNAP | `services1.arcgis.com/…/SNAP_Retailer_Location/FeatureServer/0` | **2** | Snapshot (`ingestion_mode="snapshot"`) | `Longitude`, `Latitude` (`where="State = 'GA'"`) | **ALREADY REGISTERED** (`columbus_ga`, `snap_sla_spec("GA")`) |
| Columbus, GA | Deeds | GSCCCA | `gsccca.org` Muscogee County land records | 3 | N/A | N/A | **Reject** (Paywalled state clerk authority) |
| **Knoxville, TN** | Building Permits | Accela ACA | `aca-prod.accela.com/KNOXVILLE` | 3 | N/A | N/A | **Reject** (Citizen UI only; Hub catalog empty) |
| Knoxville, TN | 311 | MyKnoxville | Tyler CivicLive mobile/web | 3 | N/A | N/A | **Reject** (No public open API) |
| Knoxville, TN | SLA | County Clerk | Knox County Clerk tax portal / Beer PDFs | 3 | N/A | N/A | **Reject** (No open business registry) |
| Knoxville, TN | Deeds | KGIS / Deeds | `kgis.org/arcgis/rest/services` | 3 | N/A | 401 Unauthorized | **Reject** (Token-gated GIS server) |
| **Chattanooga, TN** | Building Permits | ArcGIS Hub CSV | `data.chattanooga.gov/api/download/v1/items/9937e99e93de467eae5f592061c2672c/csv?layers=0` | **1** | `issueddate` | `address`, `pin`, native geocoded | **ALREADY REGISTERED** (`chattanooga`, US-155) |
| Chattanooga, TN | Deeds | ArcGIS Server | `pwgis.chattanooga.gov/arcgis/rest/services/Misc/Parcels/MapServer/0` | **1** | `SALE1DATE` | Parcel polygons (`PIN`, `PARCELID`) | **ALREADY REGISTERED** (`chattanooga`, US-155 snapshot) |
| Chattanooga, TN | SLA | USDA SNAP | USDA SNAP Retailers TN Slice | **2** | Snapshot | Point coordinates | **ALREADY REGISTERED** (`chattanooga`, `snap_sla_spec("TN")`) |
| Chattanooga, TN | 311 | CivicPlus | City 311 portal | 3 | N/A | N/A | **Defer** (Non-open CRM) |
| **Clarksville, TN** | Building Permits | County Codes | `mcgtn.org` / APSU GIS Center | 3 | N/A | N/A | **Reject / Defer** (Interactive CAMA map, no REST event stream) |
| Clarksville, TN | 311 | Direct Dept | Departmental intake | 3 | N/A | N/A | **Reject** (No 311 portal) |
| Clarksville, TN | SLA | County Clerk | Montgomery County Clerk | 3 | N/A | N/A | **Defer** (Use `snap_sla_spec("TN")`) |
| Clarksville, TN | Deeds | County Assessor | `mcgtn.org` Assessor / Register of Deeds | 3 | N/A | N/A | **Reject** (CAMA UI / Search portal) |
| **Jackson, MS** | SLA | USDA SNAP | USDA SNAP Retailers MS Slice | **2** | Snapshot | Point coordinates | **ALREADY REGISTERED** (`jackson_ms`, US-288) |
| Jackson, MS | Building Permits | City Portal | `open.jacksonms.gov` | 3 | N/A | N/A | **Reject / Defer** (Portal unmaintained, no REST stream) |
| Jackson, MS | 311 | 311 Action Ctr | City intake | 3 | N/A | N/A | **Reject** (No open API) |
| Jackson, MS | Deeds | Chancery Clerk | Hinds County Chancery Clerk (Delta Computer Systems) | 3 | N/A | N/A | **Reject** (Fee-gated search portal) |
| **Gulfport, MS** | Building Permits | City ArcGIS | `maps.gulfport-ms.gov` | 3 | N/A | N/A | **Reject** (AGOL layer is Gulfport, FL; city has footprints only) |
| Gulfport, MS | 311 | City Web | `gulfport-ms.gov` | 3 | N/A | N/A | **Reject** (No 311 dataset) |
| Gulfport, MS | SLA | City ArcGIS | `maps.gulfport-ms.gov/.../GPT_BusinessLicense/MapServer/0` | 3 | `ISSUE_DATE` | MS State Plane East | **Reject** (Frozen Dec 2024, 8+ months stale) |
| Gulfport, MS | Deeds | Harrison Co | `geo.co.harrison.ms.us` / DuProcess | 3 | N/A | Cadaster polygons | **Reject** (Assessment roll only, no transaction feed) |
| **Biloxi, MS** | Building Permits | Cityworks/Tyler | `cityworks.biloxi.ms.us/.../FeatureServer/5` | 3 | N/A | 0 rows | **Reject** (Empty layer; Tyler TESS login-gated) |
| Biloxi, MS | 311 | Cityworks | `cityworks.biloxi.ms.us/.../FeatureServer/2` | 3 | `InitiateDate` | Point geometry | **Reject** (Internal public-works work orders, not citizen 311) |
| Biloxi, MS | SLA | Tyler TESS | `biloxims.tylerportico.com` | 3 | N/A | N/A | **Reject** (Login-walled) |
| Biloxi, MS | Deeds | County GIS | `geo.co.harrison.ms.us/.../CircuitClerk` | 3 | N/A | HTTP 499 | **Reject** (Token-gated circuit clerk directory) |
| **Pensacola, FL** | Building Permits | Tyler / MGO | `fortisweb.cityofpensacola.com` / `mgoconnect.org` | 3 | N/A | N/A | **Reject** (Login-gated portals) |
| Pensacola, FL | 311 | Comcate | `agency.comcate.com/private-submission` | 3 | N/A | N/A | **Reject** (Tokenized private submission form) |
| Pensacola, FL | SLA | City/County | BTR Web forms (/284, /659) | 3 | N/A | N/A | **Defer** (Use `snap_sla_spec("FL")`) |
| Pensacola, FL | Deeds | Escambia PA | `escpa.org/CAMA/SaleSearch.aspx` | 3 | N/A | Parcel polygons | **Reject** (Interactive web search; county layer carries owner PII) |
| **Tallahassee, FL** | Building Permits | ArcGIS Server | `intervector.leoncountyfl.gov/.../TLC_OverlayPermitsActive_D_WM/MapServer/0` | **1** | `AppliedDate` (ANSI literal) | Native WGS84 point (`outSR=4326`, `objectIdField=OBJECTID`) | **ALREADY REGISTERED** (`tallahassee`, US-303) |
| Tallahassee, FL | 311 | ArcGIS Server | `intervector.leoncountyfl.gov/.../LCPW_InforServiceRequest_D_WM/MapServer/1` | **1** | `CALLDTTM` | Native point (`objectIdField=ESRI_OID`, `where="CALLDTTM <= CURRENT_TIMESTAMP"`) | **ALREADY REGISTERED** (`tallahassee`, US-303) |
| Tallahassee, FL | Deeds | ArcGIS Server | `intervector.leoncountyfl.gov/.../LCPA_Last3YearsSales_D_WM/MapServer/0` | **1** | `SALES_SALEDT` | Native parcel-centroid point (`objectIdField=OBJECTID`) | **ALREADY REGISTERED** (`tallahassee`, US-303) |
| Tallahassee, FL | SLA | USDA SNAP | USDA SNAP Retailers FL Slice | **2** | Snapshot | Point coordinates | **ALREADY REGISTERED** (`tallahassee`, `snap_sla_spec("FL")`) |
| **FL Statewide** | Cadastral (Permits Context) | ArcGIS FeatureServer | `services9.arcgis.com/.../Florida_Statewide_Cadastral/FeatureServer/0` | **1** | `ASMNT_YR` (Snapshot) | Native Parcel Polygons (`CO_NO` slice) | **AVAILABLE SUPER-FEED** (`fl_cadastral_spec(cono)`, US-398) |

---

## 2. Detailed Per-Metro Breakdown

### 1. Huntsville, AL (Madison County)
- **Portal Architecture:** On-prem ArcGIS Server 11.5 at `https://maps.huntsvilleal.gov/server/rest/services` (39 folders). AGOL org `FsRunHWuiGXWVv3B` hosts only static reference boundaries.
- **Permits Feed (`Licenses/BuildingPermits/MapServer/0`):**
  - *Layer Name:* `BuildingPermits` (18,448 records). Sibling layer 1: `OccupancyCerts` (2,335 records).
  - *Watermark Column:* `Permit_Issue_DateTime` (date-typed).
  - *Key Columns:* `PermitID` (integer primary key), `Permit_Issue_DateTime`, `Address`, `AddressID`, `OccupancyType`, `OccupancySubtype`, `TypeOfWork`, `DemolitionType`, `NumberOfUnits`, `BuildingSize`, `ContractAmount`, `ActualCost`, `CensusTract`, `CouncilDistrict`, `Subdivision`, `Shape`.
  - *Spatial Attributes:* Native point geometries verified via `outSR=4326`. No geocoder dependency required.
  - *Cadence / Freshness:* Weekly batch updates (~35–55 records/week) through July 2026, but the updater paused on August 7, 2026.
  - *Verdict & Recommendation:* Tier 2 candidate. Registerable with an explicit cadence note (`expected_cadence_days: 7`) and a strict pre-implementation re-probe gate.
- **311, SLA & Deeds:**
  - 311: Comcate CRM; only `CommunityDevelopment/ComcateAddresses` is exposed (lookup table, no cases).
  - SLA: `Licenses/AlcoholBeverageLicenses/MapServer/0` (971 rows) covers state ABC alcohol licenses, not general municipal occupational licenses. Use `snap_sla_spec("AL")`.
  - Deeds: Madison County probate court is UI-only.

### 2. Mobile, AL (Mobile County)
- **Portal Architecture:** ArcGIS Hub at `cityofmobile.opendata.arcgis.com` (67 reference layers); County ArcGIS Server at `gis.mobilecountyal.gov/server/rest/services`.
- **System of Record Analysis:**
  - Permits: Intake managed via Tyler EnerGov Citizen Self-Service (`energovpub.tylerhost.net/apps/selfservice#/home`). The Hub hosts only `ROW_Permitting` (right-of-way utility cuts).
  - 311: Citizen portal powered by QAlert (`cityofmobile.public.311service.com`). The API requires tenant authentication; anonymous calls return the client SPA shell.
  - SLA: No open business license layer in city or county catalogs.
  - Deeds: County server publishes `PARCEL_DETAILS` / `Address_Parcel_Combo_Hosted`, but these are tax assessment rolls lacking sale dates, transfer consideration, and grantor/grantee names.
- **Verdict & Recommendation:** Tier 3 across all families. Reject/Defer.

### 3. Montgomery, AL (Montgomery County)
- **Portal Architecture:** ArcGIS Hub at `opendata-citymgm.hub.arcgis.com` / `opendata.montgomeryal.gov`.
- **Feed Opportunities:**
  - *Permits:* Construction Permits Feature Layer dating from 2014 to present. Native point geometries. Field attributes: `PermitNumber`, `IssueDate`, `PermitType`, `Valuation`, `Address`.
  - *311:* 311 Service Requests Feature Layer. Tracks municipal service complaints with spatial coordinates and status watermarks.
  - *SLA & Deeds:* No municipal license API; county probate operates an interactive search interface.
- **Verdict & Recommendation:** High-priority candidate for future wave. Onboard Permits and 311 once REST endpoint URLs and date field queries are verified.

### 4. Columbus, GA (Muscogee County)
- **Status:** Fully onboarded in Urban Signal as `CityId.COLUMBUS_GA` (US-294).
- **Endpoint Specifications:**
  - *Permits:* `https://ccggisprod.columbusga.org/server/rest/services/BuildingPermits/MapServer/0` (Residential).
    - Watermark: `Issued`.
    - ID Key: `PermitNumber`, `OBJECTID`.
    - Spatial: Native point geometry (Georgia State Plane West WKID 2240; lifted to WGS84 via `outSR=4326`).
    - Field Map: `job_id` -> `PermitNumber`, `issuance_date` -> `Issued`, `cost` -> `Valuation`, `address_street` -> `Address`, `status` -> `PermitStatus`, `job_type` -> `WorkClass`.
  - *SLA:* USDA SNAP Retailers Georgia slice (`snap_sla_spec("GA")`).

### 5. Knoxville, TN (Knox County)
- **Portal Architecture:** `cityofknoxville.opendata.arcgis.com` (catalog returns 0 datasets); `kgis.org/arcgis/rest/services` returns HTTP 401 (token-gated); Accela Citizen Access at `aca-prod.accela.com/KNOXVILLE`.
- **Operational Reality:**
  - Permits: Accela ACA web search only; Develop 901 API requires vendor contract.
  - 311: MyKnoxville app (Tyler CivicLive) without an open data feed.
  - SLA: Knox County Clerk business tax registry not published via REST.
  - Deeds: Knox County Register of Deeds web portal; KGIS server is closed to anonymous traffic.
- **Verdict & Recommendation:** Tier 3 across all families. Reject.

### 6. Chattanooga, TN (Hamilton County)
- **Status:** Fully onboarded in Urban Signal as `CityId.CHATTANOOGA` (US-155).
- **Endpoint Specifications:**
  - *Permits:* ArcGIS Hub CSV item `https://data.chattanooga.gov/api/download/v1/items/9937e99e93de467eae5f592061c2672c/csv?layers=0`.
    - Watermark: `issueddate`.
    - ID Key: `permitnum`.
    - Fallback: `https://data.chattanooga.gov/datasets/9937e99e93de467eae5f592061c2672c_0.csv`.
  - *Deeds:* `https://pwgis.chattanooga.gov/arcgis/rest/services/Misc/Parcels/MapServer/0`.
    - Watermark: `SALE1DATE` (runs in snapshot mode).
    - ID Keys: `PIN`, `OBJECTID`.
    - Field Map: `doc_id` -> `PIN`, `recorded_date` -> `SALE1DATE`, `document_amount` -> `SALE1CONSD`, `party2_grantee` -> `OWNERNAME1`.
  - *SLA:* USDA SNAP Retailers Tennessee slice (`snap_sla_spec("TN")`).

### 7. Clarksville, TN (Montgomery County, TN)
- **Portal Architecture:** APSU GIS Center (`apsugis.org`), Clarksville-Montgomery County Regional Planning Commission (`cmcrpc.com`), and Montgomery County Assessor (`mcgtn.org`).
- **Operational Reality:**
  - Permits: Montgomery County Building and Codes utilizes CAMA and web mapping without an open REST event stream.
  - 311: Departmental intake; no municipal 311 open data API.
  - SLA / Deeds: County Clerk and Register of Deeds operate web lookup forms.
- **Verdict & Recommendation:** Tier 3 across all families. Defer.

### 8. Jackson, MS (Hinds County)
- **Status:** Registered in Urban Signal as `CityId.JACKSON_MS` with SNAP SLA (`snap_sla_spec("MS")`) (US-288).
- **Operational Reality:**
  - `open.jacksonms.gov` lacks active, watermarked permits or 311 feeds.
  - Hinds County Chancery Clerk land records are hosted behind paywalled vendor portals (Delta Computer Systems).
- **Verdict & Recommendation:** Retain existing SNAP SLA coverage. Defer municipal feed additions until modern GIS endpoints are published.

### 9. Gulfport & Biloxi, MS (Harrison County)
- **Biloxi, MS:**
  - City ArcGIS Server (`gis.biloxi.ms.us:6443`) carries utilities, hydrants, and zoning basemaps only.
  - Tyler TESS portal (`biloxims.tylerportico.com/tess/citizen/`) is login-walled.
  - Cityworks server (`cw/FeatureServer`): Layer 5 (`Permit`) and Layer 1 (`Request`) contain 0 rows. Layer 2 (`WorkOrder`) contains internal maintenance tickets, not citizen 311 complaints.
  - Harrison County GIS (`geo.co.harrison.ms.us`): Circuit Clerk land records folder returns HTTP 499 (Token Required).
  - *Verdict:* Tier 3 across all families. NOT VIABLE.
- **Gulfport, MS:**
  - City ArcGIS Server (`maps.gulfport-ms.gov`): `GPT_BusinessLicense` is frozen (last issue date 2024-12-12).
  - AGOL "Gulfport Permits" is located in Gulfport, Florida (Pinellas County), not Mississippi.
  - Harrison County CAMA/e-recording systems (`DuProcessWebInquiry`, `GeoPowered`) are interactive web forms.
  - *Verdict:* Tier 3 across all families. NOT VIABLE.

### 10. Pensacola, FL (Escambia County) & Tallahassee, FL
- **Pensacola, FL:**
  - Permits: Fortis/Tyler TESS (`fortisweb.cityofpensacola.com`) and MyGovernmentOnline (`mgoconnect.org`) are login-gated.
  - 311: Pensacola 311 operates via private Comcate submission forms with session CRM tokens.
  - Deeds: Escambia Property Appraiser (`escpa.org`) is web-form based; county parcel layer is an annual snapshot carrying owner PII.
  - *Verdict:* Tier 3 across all families. NOT VIABLE.
- **Tallahassee / Leon County (US-303):**
  - Fully onboarded with 3 live feeds on the joint ArcGIS Server: `https://intervector.leoncountyfl.gov/intervector/rest/services/MapServices/`
  - *Permits:* `TLC_OverlayPermitsActive_D_WM/MapServer/0` (Watermark `AppliedDate`, ANSI date literal, `objectIdField=OBJECTID`).
  - *311:* `LCPW_InforServiceRequest_D_WM/MapServer/1` (Watermark `CALLDTTM`, `objectIdField=ESRI_OID`, `where="CALLDTTM <= CURRENT_TIMESTAMP"`).
  - *Deeds:* `LCPA_Last3YearsSales_D_WM/MapServer/0` (Watermark `SALES_SALEDT`, native parcel centroids, `objectIdField=OBJECTID`).
  - *SLA:* Supplemented via `snap_sla_spec("FL")`.

---

## 3. Synergies with State Registries (AL, GA, TN, MS, FL)

When municipal open data portals are absent or login-gated, statewide super-feeds provide robust spatial and economic coverage across the Southeast and Mid-South:

1. **Statewide Business & Occupational Licensing (SLA):**
   - **USDA SNAP Retailers:** Registered across AL, GA, TN, MS, and FL (`snap_sla_spec("<STATE>")`). Ingests fresh food-retail establishments with verified lat/lng coordinates and monthly snapshots.
   - **Florida DBPR (Department of Business & Professional Regulation):** Public data master files covering Alcoholic Beverages & Tobacco (AB&T), Construction Industry Licensing Board (CILB), and Real Estate Commission. Provides statewide business establishment tracking.
   - **Texas / Washington / Oregon / Colorado / Missouri State Registries:** Model for state-level ABC and contractor registries (`TABC`, `WA_LI`, `OR_CCB`, etc.). Similar extract pipelines can ingest Alabama ABC Board and Georgia Department of Revenue alcohol licensing files.

2. **Statewide Real Estate & Cadastral Coverage (DEEDS / PERMITS Context):**
   - **Florida Statewide Cadastral (`fl_cadastral_spec(cono)`):** FDOR annual assessment-derived parcel polygon layer (2M+ parcels). Powers construction-activity proxies via `NCONST_VAL` (new construction dollar valuation), `DEL_VAL` (demolitions), and `EFF_YR_BLT` (effective year built) for Florida metros lacking municipal permit APIs.
   - **Tennessee Comptroller Property Assessments (STS-GIS):** Centralized CAMA appraisal and sales data across all 95 Tennessee counties.
   - **Mississippi MARIS & Georgia GIS Clearinghouse:** Cadastral boundaries and zoning layers for parcel join operations.

---

## 4. Actionable Registration Next Steps

1. **Huntsville, AL (Linear Wave 3 / US-344):**
   - Perform a live re-probe of `Permit_Issue_DateTime` on `maps.huntsvilleal.gov/server/rest/services/Licenses/BuildingPermits/MapServer/0`.
   - If row issuance has resumed, register `HUNTSVILLE` in `apps/api/src/spatial/city_registry.py` with `FeedType.PERMITS` (ArcGIS) and `FeedType.SLA` (`snap_sla_spec("AL")`).
   - Wire `HUNTSVILLE_METRO_BBOX`, submarkets, dashboard chips, and export product facts.

2. **Montgomery, AL (Linear Wave 4 Candidate):**
   - Capture exact FeatureServer layer endpoints for Construction Permits and 311 Service Requests from `opendata-citymgm.hub.arcgis.com`.
   - Implement field maps and verification tests for `montgomery_al`.

3. **State Super-Feed Ingestion (Alabama & Georgia SLA):**
   - Add state-level contractor and ABC licensing specs in `state_license_specs.py` to supplement un-indexed metros like Mobile, AL, Knoxville, TN, and Gulfport/Biloxi, MS.
