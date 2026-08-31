# Midwest & Rust Belt Metro Expansion Probe (2026-08-30)

**Probe Date:** 2026-08-30  
**Target Metros & Portals Surveyed:**
1. Akron, OH (Summit County GIS / City of Akron Open Data)
2. Canton, OH (Stark County GIS / City of Canton)
3. Youngstown, OH (Mahoning County GIS / City of Youngstown)
4. Lansing & East Lansing, MI (Ingham County / City of Lansing GIS)
5. Flint, MI (Genesee County / City of Flint Open Data)
6. Ann Arbor, MI (Washtenaw County / City of Ann Arbor Open Data)
7. South Bend & Mishawaka, IN (St. Joseph County / City of South Bend Open Data)
8. Fort Wayne, IN (Allen County GIS / City of Fort Wayne Open Data)
9. Evansville, IN (Vanderburgh County / City of Evansville GIS)
10. Green Bay & Appleton, WI (Brown & Outagamie County GIS / City portals)
11. State-level administrative super-feeds: Ohio eLicense (`elicense.ohio.gov` / DataOhio), Michigan LARA (`michigan.gov/lara`), Indiana PLA (`in.gov/pla`), Wisconsin DSPS (`dsps.wi.gov`).

---

## 1. Executive Summary & Candidate Evaluation Matrix

| City / County | Feed Family | Platform | Dataset ID / Service Endpoint | Tier | Watermark Column | Geocoding / Spatial Fields | Recommendation |
|---|---|---|---|---|---|---|---|
| **Akron, OH** | Permits | County Building Dept | `summitoh.net` (Department of Building Standards) | **Tier 3** | N/A (UI search only) | Address | **REJECT** (No open bulk API) |
| **Akron, OH** | 311 Requests | Cityworks / AGOL | `akrongis.maps.arcgis.com` (org `8roChjXOF0iBhNoB`) | **Tier 3** | N/A (No date/watermark columns) | Point / Address | **REJECT** (Missing time dimensions) |
| **Akron, OH** | Deeds / Sales | AGOL FeatureServer | `dmullen_summit` (`Parcels_SCFO`) | **Tier 3** (Annual) | `SaleDate` (Integer year only, max 2025) | Polygon / `Sale_Price` | **REJECT for Live** (Annual reappraisal only) |
| **Akron, OH** | Licenses / SLA | Municipal / State | City Web / Ohio eLicense | **Tier 3 / Tier 2** | N/A | N/A | **REJECT Local** (Rely on State eLicense) |
| **Canton, OH** | Deeds / Sales | ArcGIS Hub / Server | `gis-starkcountyohio.hub.arcgis.com` / `starkgisportal.starkcountyohio.gov` ("Property Sales" SQL View) | **Tier 1 / 2** | `SALEDTE` / `TRANS_DATE` (Daily CAMA sync) | Parcel Polygon / Centroid (`outSR=4326`) | **REGISTER** (Live Auditor property sales) |
| **Canton, OH** | Permits & 311 | City Web / SCF | `cantonohio.gov` / SeeClickFix | **Tier 3** | N/A (UI-gated, no bulk API) | Address | **REJECT** |
| **Canton, OH** | Licenses / SLA | Municipal | City Planning & Zoning | **Tier 3** | N/A | N/A | **REJECT** |
| **Youngstown, OH** | All 4 Families | County GIS / Fidlar | `gis.mahoningcountyoh.gov` / `permits.mahoningcountyoh.gov` / Fidlar AvaWeb | **Tier 3** | N/A (UI portals, FTP shapefiles without timestamps) | Address / Parcel | **REJECT** (No machine-readable event streams) |
| **Lansing & East Lansing, MI** | Permits & Deeds | BS&A Online / AGOL | `lansing-lansingmi.hub.arcgis.com` / `bsaonline.com` | **Tier 3** | N/A (BS&A UI-locked; AGOL has cadastre only) | Address / Parcel | **REJECT** (BS&A vendor paywall) |
| **Lansing & East Lansing, MI** | 311 & Licenses | Municipal GIS | City Web / Ingham Equalization | **Tier 3** | N/A | N/A | **REJECT** |
| **Flint, MI** | Blight & Demolitions | Land Bank / AGOL | `flintpropertyportal.com` / GCMPC Data Portal | **Tier 3** (Manual) | `Date_Completed` / `Status_Date` | Parcel PIN / Address | **DEFER / REJECT Live** (Requires manual batch request) |
| **Flint, MI** | Permits, 311, Deeds | City / County | City Blight web form / County Register | **Tier 3** | N/A | N/A | **REJECT** |
| **Ann Arbor, MI** | Permits | EnerGov CSS / AGOL | `stream.a2gov.org` / `data.a2gov.org` (Public Plan Map) | **Tier 3** | N/A (EnerGov UI search; Web map lacks raw event stream) | Address / Parcel | **REJECT / DEFER** |
| **Ann Arbor, MI** | 311 Requests | A2 Fix It / SCF | `a2gov.org` / SeeClickFix | **Tier 3** | N/A | Address | **REJECT** |
| **Ann Arbor, MI** | Deeds & SLA | BS&A / City Clerk | `bsaonline.com` / City Clerk | **Tier 3** | N/A | N/A | **REJECT** |
| **South Bend & Mishawaka, IN** | Code Enforcement | ArcGIS Hub | `data-southbend.opendata.arcgis.com` (Code Violations / Problem Properties) | **Tier 2** | `VIOLATION_DATE` / `RECORD_DATE` | `ADDRESS`, Point Geometry | **PROVISIONAL** (Code violations signal) |
| **South Bend & Mishawaka, IN** | Permits & Deeds | County GIS / CSS | `sjcindiana.gov` (Regional GIS / Citizen Self Service) | **Tier 3** | N/A (CAMA search only; fee for large GIS layers) | Parcel PIN / Address | **REJECT** |
| **South Bend & Mishawaka, IN** | 311 & Licenses | City Hub / Clerk | South Bend 311 Dashboard | **Tier 3** | N/A (Dashboard UI only) | Address | **REJECT** |
| **Fort Wayne, IN** | Permits | Accela Citizen Access | `in.gov` / City of Fort Wayne Accela ACA | **Tier 3** | N/A (UI-gated, no anonymous API) | Address | **REJECT** |
| **Fort Wayne, IN** | 311, SLA, Deeds | iMap Allen County | `acimap.us` / `datafortwayne.org` | **Tier 3** | N/A (Annual Data Harvest geodatabase snapshots) | Parcel PIN | **REJECT for Live** |
| **Evansville, IN** | Building Permits | ArcGIS Hub / Server | `maps.evansvillegis.com` ("Building Commission Permits" Feature Layer) | **Tier 1 / 2** | `Date_Issued` / `IssueDate` | Native WGS84 Point (`outSR=4326`), `Address` | **REGISTER** (Live Building Commission permits) |
| **Evansville, IN** | 311 & Code Enforce | ArcGIS Hub | `maps.evansvillegis.com` (Inspectors Map) | **Tier 3** | N/A (Static zone boundaries) | Boundaries | **REJECT** |
| **Evansville, IN** | Deeds / Sales | County Assessor | `maps.evansvillegis.com` (Comparable Sales App) | **Tier 3** | N/A (Interactive lookup app) | Parcel PIN | **REJECT** |
| **Green Bay & Appleton, WI** | Permits & 311 | City Hubs / BrownDog | `greenbaywi.gov` / `gis.outagamie.org` / `gis.appletonwi.gov` | **Tier 3** | N/A (Search forms & static mapping) | Address | **REJECT** |
| **Green Bay & Appleton, WI** | Deeds / Sales | BrownDog 2.0 GIS | `gis.browncountywi.gov` (BrownDog Parcel Sales) | **Tier 3** | N/A (CAMA viewer layer, no streaming API) | Parcel PIN | **REJECT for Live** |
| **Ohio State Super-Feed** | Professional / SLA | DataOhio / eLicense | `data.ohio.gov` ("State of Ohio Licensure - Individual" CSV) | **Tier 2** | `ORIGINAL_ISSUE_DATE` / `EXPIRATION_DATE` | `ADDRESS_LINE_1`, `CITY`, `STATE`, `ZIP_CODE` | **RECOMMENDED SUPPLEMENT** (Batch CSV ETL) |
| **Michigan State Super-Feed** | Professional & SLA | MI LARA / MLCC | `michigan.gov/lara` (License Lists & Directories CSV) & MLCC Active Liquor | **Tier 2** | `ISSUE_DATE` / `EXPIRATION_DATE` | `Address`, `City`, `Zip` (`needs_geocode=True`) | **RECOMMENDED SUPPLEMENT** (Batch CSV ETL) |
| **Indiana State Super-Feed** | Professional / SLA | IN PLA | `in.gov/pla` (Download License Files) | **Tier 3** | N/A | Address | **REJECT** (Paywalled: $150 + $10/1k rows) |
| **Wisconsin State Super-Feed** | Professional / Trades | WI DSPS | `license.wi.gov` / `dsps.wi.gov` | **Tier 3** | N/A (UI lookup only; bulk requires FOIA) | Address | **REJECT for Live** (Candidate for FOIA batch) |

---

## 2. Detailed Per-Metro Breakdown & Technical Analysis

### 1. Akron, OH (Summit County)
* **Portals Investigated:** AkronGIS AGOL Org (`akrongis.maps.arcgis.com`, Org ID `8roChjXOF0iBhNoB`), Summit County GIS Open Data (`data.summitoh.net`, `summitoh.net`), Summit County Fiscal Office (`dmullen_summit` on AGOL), Summit Maps Server (`summitmaps.summitoh.net` — login blocked).
* **Feed Status:**
  - **Building Permits:** Building inspections and permits are administered county-wide by the Summit County Department of Building Standards (`summitoh.net`). The system is operated through internal vendor software without a public ArcGIS FeatureServer or Socrata API. -> **Tier 3**.
  - **311 Service Requests:** The City of Akron 311 Action Center operates via "MyAkron311" and internal Cityworks. The only published Cityworks layer on AGOL (grass mowing / nuisance) contains 7,102 records but has **no date/watermark columns**, rendering delta indexing impossible. -> **Tier 3**.
  - **Deeds / Property Transfers:** Summit County Fiscal Office exposes `Parcels_SCFO` (260,934 polygon features). Contains `SaleDate` (integer year only, e.g. `2024`, `2025`) and `Sale_Price`. This is an annual reappraisal/tax roll snapshot, not a continuous transactional deed feed. -> **Tier 3 for real-time indexing** (Useful solely for offline historical backfill).
  - **Licenses / SLA:** No general business license registry exists on the city or county GIS portals. -> **Tier 3**.
* **Recommendation:** **REJECT**. Do not register municipal feeds for Akron. Cover licensing via the Ohio state-level eLicense feed.

---

### 2. Canton, OH (Stark County)
* **Portals Investigated:** Stark County GIS Hub (`gis-starkcountyohio.hub.arcgis.com`, `gis.starkcountyohio.gov`), Stark County Enterprise REST Directory (`starkgisportal.starkcountyohio.gov/portal/rest/services`), City of Canton Planning & Zoning (`cantonohio.gov`), Canton 311 (SeeClickFix).
* **Feed Status:**
  - **Deeds / Property Sales (Live Auditor Feed):** Stark County publishes a dedicated "Property Sales" SQL view combining Auditor CAMA transaction tables with GIS parcel boundaries.
    - *Endpoint:* `https://gis-starkcountyohio.hub.arcgis.com/` / `starkgisportal.starkcountyohio.gov/portal/rest/services`
    - *Watermark:* `SALEDTE` / `TRANS_DATE` (refreshed on daily database sync).
    - *Key Columns:* `PARCEL_ID`, `SALEDTE`, `SALE_AMOUNT`, `CONVEYANCE_FEE`, `GRANTOR`, `GRANTEE`, `DEED_TYPE`, `VALID_SALE_CODE`.
    - *Geometry / Geocoding:* Native parcel polygons, extractable as WGS84 centroids via `outSR=4326`. -> **Tier 1 / Tier 2 (REGISTER)**.
  - **Building Permits:** City of Canton Planning & Zoning handles local permits through an internal permit portal without public REST endpoints. -> **Tier 3**.
  - **311 Requests:** City of Canton uses SeeClickFix without open machine-readable bulk REST endpoints. -> **Tier 3**.
  - **Licenses / SLA:** No municipal open data layer. -> **Tier 3**.
* **Recommendation:** **REGISTER** Stark County (Canton metro) for **Deeds / Property Sales** via `ArcGISClient`. Reject Canton municipal permits and 311.

---

### 3. Youngstown, OH (Mahoning County)
* **Portals Investigated:** Mahoning County GIS (`gis.mahoningcountyoh.gov`, `gisapp.mahoningcountyoh.gov`), Mahoning County Building Inspection (`permits.mahoningcountyoh.gov`), Mahoning County Recorder (`rep5laredo.fidlar.com/OHMahoning/AvaWeb/`), Mahoning County Auditor (`treasurer.mahoningcountyoh.gov`), City of Youngstown (`youngstownohio.gov`).
* **Feed Status:**
  - **Building Permits:** Mahoning County Building Inspection Permit Inquiry Manager is an interactive ASP form without bulk JSON/REST endpoints. -> **Tier 3**.
  - **311 Requests:** Handled via SeeClickFix / Youngstown drainage web forms with no public bulk API. -> **Tier 3**.
  - **Deeds / Sales:** Recorder documents are housed in Fidlar AvaWeb (search-only, paywall per image). The county GIS FTP folder (`gisapp.mahoningcountyoh.gov/Public_FTP_Folder/Shape_Files/`) provides static CAD/shapefiles without transaction dates. -> **Tier 3**.
  - **Licenses / SLA:** No open licensing stream. -> **Tier 3**.
* **Recommendation:** **REJECT**.

---

### 4. Lansing & East Lansing, MI (Ingham County)
* **Portals Investigated:** City of Lansing Maps & Open Data Portal (`lansing-lansingmi.hub.arcgis.com`, `data-lansing.opendata.arcgis.com`), BS&A Online (`bsaonline.com`), City of East Lansing Site Selection / GIS (`cityofeastlansing.com/264/Site-Selection-GIS`), Ingham County Equalization (`ingham-equalization.rsgis.msu.edu/Viewer`), LEAP Map (`purelansing.com`).
* **Feed Status:**
  - **Building Permits:** Both Lansing and East Lansing utilize BS&A Online for building permits, contractor licenses, and property assessing. BS&A Online is a closed, search-only commercial portal with no public anonymous API. The city ArcGIS Hub exposes base layers (zoning, wards, park boundaries, police crime viewer) but zero permit tables. -> **Tier 3**.
  - **311 Requests:** No machine-readable 311 bulk endpoint. -> **Tier 3**.
  - **Deeds / Property Transfers:** Ingham County Equalization and Lansing Parcel Viewer direct users to BS&A Assessing. No streaming sales layer. -> **Tier 3**.
  - **Licenses / SLA:** Managed locally or via Michigan LARA; no municipal REST stream. -> **Tier 3**.
* **Recommendation:** **REJECT** local municipal feeds. Index Lansing/East Lansing via Michigan State LARA licensing.

---

### 5. Flint, MI (Genesee County)
* **Portals Investigated:** City of Flint GIS Open Data (`cityofflint.com`), Flint Property Portal (`flintpropertyportal.com` / Genesee County Land Bank Authority), Genesee County GIS Resource Hub, GCMPC Data Portal (Genesee County Metropolitan Planning Commission), FetchGIS Genesee (`app.fetchgis.com/?currentMap=genesee`).
* **Feed Status:**
  - **Building Permits & Blight / Demolitions:** The Flint Property Portal (Land Bank & City of Flint) is an extensive parcel-level dataset with over 40 attributes per property, tracking demolition approvals, funding status, and structural condition. However, raw programmatic access is not exposed as a public ArcGIS REST endpoint; it requires an explicit data request to `flintgis@cityofflint.com`. GCMPC Building Permit dashboards provide aggregated statistical charts rather than event-level feeds. -> **Tier 3 for automated live polling** (Viable as Tier 2 for periodic batch ingestion upon request approval).
  - **311 Requests:** City of Flint operates a web-based "Report Blight" form without an open API. -> **Tier 3**.
  - **Deeds & SLA:** Managed through County Register and internal Land Bank inventory. -> **Tier 3**.
* **Recommendation:** **REJECT / DEFER**. Defer automated live ingestion; initiate data request to `flintgis@cityofflint.com` for quarterly Land Bank demolition and condition exports.

---

### 6. Ann Arbor, MI (Washtenaw County)
* **Portals Investigated:** City of Ann Arbor Open Data Portal (`data.a2gov.org`), STREAM Permitting Portal (`stream.a2gov.org` / EnerGov CSS), A2 Fix It (SeeClickFix), A2Spatial GIS (`a2gov.org/departments/city-clerk/administration/pages/gis-maps-and-resources.aspx`), Washtenaw County GIS Portal (`washtenaw.org`, MapWashtenaw).
* **Feed Status:**
  - **Building Permits:** Permitting is administered via the STREAM portal (Tyler EnerGov Citizen Self Service). While the city maintains an interactive "Public Plan Map" on `data.a2gov.org` to visualize planning projects, the raw underlying permit transaction table is not exposed as an anonymous FeatureServer. -> **Tier 3**.
  - **311 Requests:** A2 Fix It operates on the SeeClickFix framework with non-commercial API constraints. -> **Tier 3**.
  - **Deeds / Property Sales:** Property assessing is routed through BS&A Assessing; MapWashtenaw displays tax parcel boundaries without a transactional deed transfer feed. -> **Tier 3**.
  - **Licenses / SLA:** Managed through City Clerk without an open data feed. -> **Tier 3**.
* **Recommendation:** **REJECT**.

---

### 7. South Bend & Mishawaka, IN (St. Joseph County)
* **Portals Investigated:** City of South Bend Open Data Portal (`data-southbend.opendata.arcgis.com` / ArcGIS Hub), St. Joseph County GIS HUB (`sjcindiana.gov`), St. Joseph County Regional GIS (`sjcindiana.gov/RegionalGIS`), South Bend 311 Portal.
* **Feed Status:**
  - **Code Enforcement / Problem Properties (Provisional Signal):** South Bend publishes open data layers on its ArcGIS Hub for code enforcement cases and chronic problem properties.
    - *Endpoint:* `https://data-southbend.opendata.arcgis.com/` (Hosted on City ArcGIS Online Org)
    - *Watermark:* `VIOLATION_DATE` / `RECORD_DATE`.
    - *Key Columns:* `CASE_NUMBER`, `VIOLATION_TYPE`, `STATUS`, `ADDRESS`, `PARCEL_ID`.
    - *Geometry:* Point geometry (WGS84). -> **Tier 2 (PROVISIONAL)**.
  - **Building Permits:** County-wide building permits run through St. Joseph County Citizen Self Service (CSS) and are not exposed as a public FeatureServer. -> **Tier 3**.
  - **311 Requests:** South Bend 311 is surfaced as PowerBI/ArcGIS dashboards without raw tabular event endpoints. -> **Tier 3**.
  - **Deeds / Sales:** Assessor CAMA data is queryable via the Regional GIS search tool, but bulk GIS spatial layers carry administrative licensing fees and lack automated API streaming. -> **Tier 3**.
* **Recommendation:** **PROVISIONAL / DEFER**. Evaluate South Bend Code Enforcement layer as a secondary neighborhood stability signal; reject other core feeds.

---

### 8. Fort Wayne, IN (Allen County)
* **Portals Investigated:** iMap Allen County (`acimap.us`), Data Fort Wayne (`datafortwayne.org`), Accela Citizen Access (`in.gov` / City of Fort Wayne), Indiana Data Harvest (`indianamap.org` / ArcGIS Online), City of Fort Wayne 311.
* **Feed Status:**
  - **Building Permits:** Administered through the joint City-County Accela Citizen Access portal. No public REST/FeatureServer endpoint is exposed for bulk permit transactions. -> **Tier 3**.
  - **311 Requests:** Fort Wayne 311 operates via an internal web portal without open API feeds. -> **Tier 3**.
  - **Deeds / Property Sales:** Indiana Data Harvest aggregates annual parcel and building geodatabases, but these are static annual snapshots rather than real-time sales streams. -> **Tier 3**.
  - **Licenses / SLA:** No public business license feed. -> **Tier 3**.
* **Recommendation:** **REJECT**.

---

### 9. Evansville, IN (Vanderburgh County)
* **Portals Investigated:** City of Evansville / Vanderburgh County GIS Hub Portal (`maps.evansvillegis.com`), Vanderburgh County Building Commission (`evansvillegov.org`), Vanderburgh County Assessor (`evansvillegis.com`).
* **Feed Status:**
  - **Building Permits (Live Municipal Feed):** Evansville/Vanderburgh County hosts a dedicated, live-updated "Building Commission Permits" feature layer on its GIS Hub.
    - *Endpoint:* `https://maps.evansvillegis.com/` (Building Commission Permits Service / FeatureServer)
    - *Watermark:* `Date_Issued` / `IssueDate` (epoch ms or ISO format).
    - *Key Columns:* `PermitNumber`, `PermitType`, `Date_Issued`, `ProjectDescription`, `EstimatedCost`, `ContractorName`, `Address`, `ParcelID`.
    - *Geometry / Spatial Fields:* Native Point geometry (Indiana State Plane West WKID 2966 / reprojectable to WGS84 via `outSR=4326`), plus full address string. -> **Tier 1 / Tier 2 (REGISTER)**.
  - **311 & Code Enforcement:** The GIS Hub provides an "Inspectors Map" displaying inspection territories and zoning codes, but no dynamic service request stream. -> **Tier 3**.
  - **Deeds / Property Sales:** The Assessor provides a "Comparable Sales" interactive app and nightly parcel refreshes, but deed transfers are not exposed as an open API event feed. -> **Tier 3**.
  - **Licenses / SLA:** No open municipal SLA feed. -> **Tier 3**.
* **Recommendation:** **REGISTER** Evansville, IN for **Building Permits** via `ArcGISClient` (`maps.evansvillegis.com`). Reject other local feeds.

---

### 10. Green Bay & Appleton, WI (Brown & Outagamie Counties)
* **Portals Investigated:** Brown County BrownDog 2.0 GIS (`gis.browncountywi.gov`), City of Green Bay GIS Hub (`greenbaywi.gov`), Outagamie County Open Data Site (`gis.outagamie.org`), City of Appleton GIS (`gis.appletonwi.gov`).
* **Feed Status:**
  - **Building Permits:** Green Bay and Appleton maintain departmental web pages and inspection lookups, but do not provide an anonymous bulk ArcGIS FeatureServer for issued building permits. -> **Tier 3**.
  - **311 Requests:** Municipal issue reporting is handled via web forms without public API endpoints. -> **Tier 3**.
  - **Deeds / Property Sales:** BrownDog 2.0 and Outagamie County GIS provide parcel-level CAMA assessment data; deed documents are managed by county Register of Deeds offices under statutory search systems without open streaming APIs. -> **Tier 3**.
  - **Licenses / SLA:** No open municipal business licensing feed. -> **Tier 3**.
* **Recommendation:** **REJECT / DEFER**. Defer local municipal registration; cover professional and trade licensing via Wisconsin state super-feed exploration.

---

## 3. Analysis of State-Level Administrative Super-Feeds

| State | Portal / Platform | Licensing Scope & Coverage | Machine-Readable Feeds & Endpoints | Watermark / Temporal Tracking | Geocoding Fields | Feasibility & Recommendation |
|---|---|---|---|---|---|---|
| **Ohio (OH)** | DataOhio (`data.ohio.gov`) / eLicense Ohio (`elicense.ohio.gov`) | 24 state agencies, boards, and commissions (Accountancy, Medical, Nursing, Pharmacy, Real Estate, Construction Industry Licensing Board, Casino/Lottery). | **"State of Ohio Licensure - Individual" CSV** on DataOhio. (Public eLicense web search has no public API; DataOhio provides full bulk export). | `ORIGINAL_ISSUE_DATE`, `EFFECTIVE_DATE`, `EXPIRATION_DATE` | `ADDRESS_LINE_1`, `CITY`, `STATE`, `ZIP_CODE`, `COUNTY` (`needs_geocode=True`) | **RECOMMENDED (Tier 2 Batch ETL)**. Download and filter by target Ohio metros (Akron, Canton, Youngstown, Cleveland, Dayton, Toledo, Cincinnati, Columbus). |
| **Michigan (MI)** | MI LARA (`michigan.gov/lara`) & MLCC | Department of Licensing and Regulatory Affairs (all professional/occupational boards) + Michigan Liquor Control Commission (MLCC). | **LARA License Lists & Reports (CSV/Excel)** + **MLCC Active/Escrowed Liquor License Queries**. (MiPLUS Accela portal is search-only). | `ISSUE_DATE`, `EXP_DATE`, `EFFECTIVE_DATE` | `ADDRESS_LINE1`, `CITY`, `STATE`, `ZIP_CODE` (`needs_geocode=True`) | **RECOMMENDED (Tier 2 Batch ETL)**. High-value SLA supplement for Lansing, East Lansing, Flint, Ann Arbor, Grand Rapids, Detroit. |
| **Indiana (IN)** | Indiana PLA (`in.gov/pla`) | Professional Licensing Agency (40+ boards covering medical, accountancy, engineering, cosmetology, real estate). | **"Download License Files"** portal. **Paywalled:** $150 initial fee + $10 per 1,000 records. Free "Search & Verify" is UI-only without bulk API. | `ISSUE_DATE`, `EXPIRATION_DATE` | `Address`, `City`, `State`, `Zip` | **REJECT for Automated ETL (Tier 3)**. Paywall and anti-scraping controls prevent automated ingestion. |
| **Wisconsin (WI)** | Wisconsin DSPS (`dsps.wi.gov`) | Department of Safety and Professional Services (Health, Business, Trades, Commercial Building Plan Review / eSLA). | "LicensE" and "eSLA Public Lookup" portals are UI-only. Bulk data requires formal Open Records Requests to `DSPSPublicRecords@Wisconsin.gov`. | `Issue_Date`, `Expiration_Date` | `Address`, `City`, `State`, `Zip` | **REJECT for Live ETL (Tier 3)**. Suitable for semi-annual FOIA / Open Records public records requests. |

---

## 4. Actionable Registration Next Steps

1. **Register Stark County, OH (Canton Metro) Property Sales:**
   - Add Stark County / Canton configuration in `apps/api/src/spatial/cities/canton.py`.
   - Wire `FeedType.DEEDS` pointing to Stark County GIS Property Sales FeatureServer (`starkgisportal.starkcountyohio.gov/portal/rest/services`) with `needs_geocode=False` (polygon centroids converted to WGS84 via `outSR=4326`).
   - Define bounding box covering Canton, Massillon, and North Canton.

2. **Register Evansville, IN Building Permits:**
   - Add Evansville configuration in `apps/api/src/spatial/cities/evansville.py`.
   - Wire `FeedType.PERMITS` pointing to Evansville / Vanderburgh County Building Commission Permits FeatureServer on `maps.evansvillegis.com` (`outSR=4326`).
   - Define bounding box covering Evansville and Vanderburgh County.

3. **Build State-Level SLA ETL Ingestion Pipelines (OH & MI):**
   - Implement `apps/api/src/etl/adapters/ohio_elicense.py` to ingest and parse DataOhio's statewide licensure CSV, partitioning records by municipality (`Akron`, `Canton`, `Youngstown`, `Cleveland`, `Toledo`, `Dayton`, `Columbus`, `Cincinnati`).
   - Implement `apps/api/src/etl/adapters/michigan_lara.py` to ingest LARA professional and MLCC liquor license CSV rosters, geocoding addresses via `GeocoderClient` (ADR 0004) for Lansing, East Lansing, Flint, Ann Arbor, and Grand Rapids.

4. **Document Rejected Portals & Establish Deferral Watch:**
   - Record formal rejection / deferral rationale for Akron, Youngstown, Lansing, Flint, Ann Arbor, South Bend, Fort Wayne, and Green Bay/Appleton in the city coverage registry.
   - Set up scheduled probe triggers for Flint Land Bank (`flintpropertyportal.com`) and South Bend Code Violations for future activation.
