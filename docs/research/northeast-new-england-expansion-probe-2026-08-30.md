# Northeast & New England Expansion Probe (2026-08-30)

**Target Metros Surveyed:** Providence (RI), Worcester (MA), Springfield (MA), New Haven (CT), Bridgeport (CT), Hartford (CT - Supplemental), Manchester (NH), Portland (ME), Burlington (VT).

---

## 1. Executive Summary & Candidate Evaluation Matrix

| City / Metro | Feed Family | Platform | Dataset ID / Service Endpoint | Tier | Watermark Column | Geocoding Fields | Recommendation |
|---|---|---|---|---|---|---|---|
| **Worcester, MA** | **Building Permits** | ArcGIS FeatureServer | `opendata.worcesterma.gov/.../Building_Permits/FeatureServer/0` | **Tier 2** (or Tier 1) | `IssuedDate` / `RECORD_DATE` | `Address` / Point Geometry | **REGISTER** (Live municipal permits) |
| **Worcester, MA** | **Licenses / SLA** | ArcGIS FeatureServer | `opendata.worcesterma.gov/.../Food_Establishment_Licenses/FeatureServer/0` | **Tier 2** | `IssuedDate` / `EXPIRATION_DATE` | `Address`, `Street_Name` | **REGISTER** (Food & commercial licenses) |
| **Worcester, MA** | **311 Requests** | SeeClickFix / Web | Customer Service Center / SCF | **Tier 3** | n/a (No open bulk extract) | Address | **DEFER / REJECT** |
| **Worcester, MA** | **Deeds / Sales** | Assessor / MassLandRecords | Vision VGSI / Worcester Registry | **Tier 3** | n/a (Search portal only) | Parcels / BBL | **REJECT** (No open stream) |
| **Hartford, CT** | **Building Permits** | ArcGIS FeatureServer | `HartfordOpenDataTables/FeatureServer/0` | **Tier 2** | `DateIssued` | `PROPERTY_ADDRESS`, `Location` | **REGISTERED** (Active baseline) |
| **Hartford, CT** | **Planning & PW Permits** | ArcGIS FeatureServer | `HartfordOpenDataTables/FeatureServer/3`, `/4` | **Tier 2** | `DateIssued` / `OpenedDate` | `Location`, `PROPERTY_ADDRESS` | **REGISTER** (Multi-layer permit supplement) |
| **Hartford, CT** | **311 Requests** | ArcGIS FeatureServer | `Service_Requests_2015_to_Current/FeatureServer/9` | **Tier 2** | `USER_Opened_Date` | `Match_addr`, CT State-Plane X/Y | **REGISTERED** (Active baseline) |
| **Hartford, CT** | **Licenses / SLA** | Socrata (`data.ct.gov`) | `ngch-56tr.json` (`where="city = 'HARTFORD'"`) | **Tier 2** | `recordrefreshedon` | `address`, `zip` | **REGISTERED** (Statewide supplement) |
| **Hartford, CT** | **Deeds / Sales** | Socrata (`data.ct.gov`) | `5mzw-sjtu.json` (`where="town = 'Hartford'"`) | **Tier 2** | `date_recorded` / `date_of_sale` | `address` | **REGISTER** (Overcomes 7-mo city table lag) |
| **New Haven, CT** | **Licenses / SLA** | Socrata (`data.ct.gov`) | `ngch-56tr.json` (`where="city = 'NEW HAVEN'"`) | **Tier 2** | `recordrefreshedon` | `address`, `zip` | **REGISTER** (Statewide eLicensing) |
| **New Haven, CT** | **Deeds / Sales** | Socrata (`data.ct.gov`) | `5mzw-sjtu.json` (`where="town = 'New Haven'"`) | **Tier 2** | `date_recorded` / `date_of_sale` | `address` | **REGISTER** (Statewide transfer roll) |
| **New Haven, CT** | **Permits & 311** | Municipal GIS / SCF | `nhgis.newhavenct.gov` / SeeClickFix | **Tier 3** | n/a (No open bulk feed) | Address | **DEFER / REJECT** |
| **Bridgeport, CT** | **Licenses / SLA** | Socrata (`data.ct.gov`) | `ngch-56tr.json` (`where="city = 'BRIDGEPORT'"`) | **Tier 2** | `recordrefreshedon` | `address`, `zip` | **REGISTER** (Statewide eLicensing) |
| **Bridgeport, CT** | **Deeds / Sales** | Socrata (`data.ct.gov`) | `5mzw-sjtu.json` (`where="town = 'Bridgeport'"`) | **Tier 2** | `date_recorded` / `date_of_sale` | `address` | **REGISTER** (Statewide transfer roll) |
| **Bridgeport, CT** | **Permits & 311** | Park City Portal / SCF | `bridgeportct.gov` / SeeClickFix | **Tier 3** | n/a (No open bulk feed) | Address | **DEFER / REJECT** |
| **Burlington, VT** | **Building Permits** | ArcGIS FeatureServer | `OpenGov_Building/FeatureServer/0` | **Tier 3** (Frozen) | `StatusDate` (Frozen 2026-04-27) | `Latitude`, `Longitude` (native 4326) | **DEFER / RE-PROBE** (Sync unfreeze trigger) |
| **Burlington, VT** | **311 / SLA / Deeds** | ArcGIS Hub / VCGI | `burlingtonvt.opendata.arcgis.com` | **Tier 3** | n/a (Absent / CAMA-only) | n/a | **REJECT** |
| **Providence, RI** | **All 4 Families** | Socrata / ViewPoint / Kofile | `data.providenceri.gov` (`ufmm-rbej`, `ui7z-kv69`) | **Tier 3** | Stale 2011–2020 / CRM-gated | Address / point | **REJECT** (No live municipal extracts) |
| **Springfield, MA** | **All 4 Families** | IntelliGov / MassLandRecords | `springfield-ma.gov` / PVPC | **Tier 3** | n/a (Portal-locked, no API) | Address | **REJECT** |
| **Manchester, NH** | **All 4 Families** | AGOL / NH GRANIT | `manchesternh.opendata.arcgis.com` | **Tier 3** | 401 Private Hub / Login-gated | Address | **REJECT** (No public open data) |
| **Portland, ME** | **All 4 Families** | CSS / Maine GeoLibrary | `portlandmaine.gov` / EnerGov CSS | **Tier 3** | n/a (UI-gated, no API) | Address | **REJECT** |

---

## 2. Detailed Per-City Breakdown & Technical Analysis

### 1. Providence, RI
* **Portals Investigated:** `data.providenceri.gov` (Socrata), `providence-gis-hub-pvdgis.hub.arcgis.com` (ArcGIS Hub), PVD311 (`311.providenceri.gov` on Power Apps / Dynamics CRM), ViewPoint Cloud / RI Statewide E-Permitting (`providenceri.viewpointcloud.com`, `permits.ri.gov`), Kofile CountyFusion (`countyfusion10.kofiletech.us`).
* **Feed Status:**
  - **Building Permits:** Socrata `ufmm-rbej` ("Department of Inspections and Standards Permits 2009-2018") has 80,874 rows. Watermark `issueddate` maxes out at **2020-01-23** (0 records for 2021–2026). Live permitting transitioned to ViewPoint Cloud (`permits.ri.gov`), which is an account-gated web app without public JSON/REST extracts. -> **Tier 3**.
  - **311 Requests:** Zero 311/service request datasets on Socrata. PVD311 is Microsoft Power Apps CRM (no anonymous OData). SeeClickFix endpoint (`lat=41.824&long=-71.413`) maxes out at **2021-09-09** and is under CC-BY-NC-SA. -> **Tier 3**.
  - **SLA / Licenses:** `ui7z-kv69` (Active Business Licenses) collapsed to a single 2011 record. `2f79-9nkc` (Monthly Entertainment) and `u7ik-g787` (Mobile Food) last updated January 2020. Board of Licenses uses ViewPoint Cloud UI. -> **Tier 3**.
  - **Deeds / Property Transfers:** `6ub4-iebe` (Property Tax Roll) is an annual CAMA tax assessment snapshot with no transfer/sale watermark. Kofile CountyFusion is login-gated. -> **Tier 3**.
* **Recommendation:** **REJECT**. Do not register municipal feeds.

---

### 2. Worcester, MA
* **Portals Investigated:** `opendata.worcesterma.gov` ("Informing Worcester" ArcGIS Hub), Department of Innovation & Technology GIS Section, Worcester 311 (SeeClickFix), Vision Government Solutions (VGSI).
* **Feed Status:**
  - **Building Permits:** Live FeatureServer endpoints under `opendata.worcesterma.gov` / City ArcGIS Online org for Building, Electrical, Plumbing, Gas, and Mechanical Permits. Watermarks: `IssuedDate`, `RECORD_DATE`. Key fields: `Record #`, `Record Type`, `Address`, `Estimated Cost`, `Status`. Points/Address-only. -> **Tier 2 / Tier 1 (REGISTER)**.
  - **SLA / Business Licenses:** Live FeatureServer endpoints for Food Establishment Licenses, Mobile Food Vendor Licenses, and Temporary Food Licenses. Watermark: `IssuedDate` / `EXPIRATION_DATE`. Key fields: `BusinessName`, `Address`, `LicenseType`, `Status`. -> **Tier 2 (REGISTER)**.
  - **311 Requests:** Handled via SeeClickFix / Worcester 311 Customer Service Center without an open machine-readable bulk REST API. -> **Tier 3**.
  - **Deeds / Sales:** Assessor data is exposed as CAMA snapshots in Worcester Atlas; deed transactions are filed with Worcester County Registry of Deeds (MassLandRecords), which provides search-only access without an open bulk API. -> **Tier 3**.
* **Recommendation:** **REGISTER** Worcester for Permits and SLA (Food/Business Licenses) via `ArcGISClient` with `needs_geocode=True` (or native points where provided).

---

### 3. Springfield, MA
* **Portals Investigated:** `springfield-ma.gov`, Pioneer Valley Planning Commission (`pvpc.org` / Pioneer Valley Data Dashboard), Springfield 311 (IntelliGov Software), Hampden County Registry of Deeds (MassLandRecords).
* **Feed Status:**
  - **Building Permits:** Department of Inspectional Services operates on internal software (`masspermits.com` / IntelliGov) without an open public FeatureServer/Socrata feed. -> **Tier 3**.
  - **311 Requests:** Springfield 311 is powered by IntelliGov citizen app/portal with no public JSON feed. -> **Tier 3**.
  - **SLA:** Local licensing managed internally; regional data in PVPC Data Dashboard is aggregated census/economic indicators, not real-time transactional event records. -> **Tier 3**.
  - **Deeds:** Hampden County Registry of Deeds on MassLandRecords (search-only, no bulk API). -> **Tier 3**.
* **Recommendation:** **REJECT**. Defer until Springfield or PVPC publishes an open GIS/FeatureServer feed.

---

### 4. New Haven, CT
* **Portals Investigated:** `nhgis.newhavenct.gov/server/rest/services`, City of New Haven GIS, SeeClickFix New Haven, Connecticut Open Data (`data.ct.gov`).
* **Feed Status:**
  - **Permits & 311:** New Haven GIS provides mapping services (zoning, parcels), but permits remain in an internal Accela portal without an anonymous FeatureServer. SeeClickFix API is non-commercial/login restricted. -> **Tier 3**.
  - **SLA / Business Licenses (Statewide Supplement):** Socrata `data.ct.gov/resource/ngch-56tr.json` filtered by `where="city = 'NEW HAVEN'"`. Watermark: `recordrefreshedon`. Key fields: `credential_number`, `credential_type`, `business_name`, `address`, `zip`. -> **Tier 2 (REGISTER)**.
  - **Deeds / Property Transfers (Statewide Supplement):** Socrata `data.ct.gov/resource/5mzw-sjtu.json` (Real Estate Sales 2001-2024 GL) filtered by `where="town = 'New Haven'"`. Watermark: `date_recorded`. Key fields: `serial_number`, `town`, `address`, `sales_amount`, `assessed_value`, `property_type`. -> **Tier 2 (REGISTER)**.
* **Recommendation:** **REGISTER** New Haven using Connecticut State Open Data supplementation for SLA and Deeds via `SocrataClient` (`needs_geocode=True`).

---

### 5. Bridgeport, CT
* **Portals Investigated:** City of Bridgeport GIS Hub (`hub.arcgis.com/search?q=owner:"City of Bridgeport"`), Park City Permitting Portal, Bridgeport 311 (SeeClickFix), Connecticut Open Data (`data.ct.gov`).
* **Feed Status:**
  - **Permits & 311:** Park City Portal and Police Licensing portals are transactional forms without open data exports. Bridgeport 311 on SeeClickFix has no open bulk API. -> **Tier 3**.
  - **SLA / Business Licenses (Statewide Supplement):** Socrata `data.ct.gov/resource/ngch-56tr.json` filtered by `where="city = 'BRIDGEPORT'"`. Watermark: `recordrefreshedon`. -> **Tier 2 (REGISTER)**.
  - **Deeds / Property Transfers (Statewide Supplement):** Socrata `data.ct.gov/resource/5mzw-sjtu.json` (Real Estate Sales GL) filtered by `where="town = 'Bridgeport'"`. Watermark: `date_recorded`. -> **Tier 2 (REGISTER)**.
* **Recommendation:** **REGISTER** Bridgeport using Connecticut State Open Data supplementation for SLA and Deeds via `SocrataClient` (`needs_geocode=True`).

---

### 6. Hartford, CT (Supplemental Evaluation)
* **Current Registration Baseline:**
  - `PERMITS`: `HartfordOpenDataTables/FeatureServer/0` (Building Permits 2020-to-current, watermark `DateIssued`, address-geocoded).
  - `COMPLAINTS_311`: `Service_Requests_2015_to_Current/FeatureServer/9` (Current year 311, watermark `USER_Opened_Date`, state-plane geocoded).
  - `SLA`: `data.ct.gov/resource/ngch-56tr.json` (`where="city = 'HARTFORD'"`).
* **Supplemental Feed Probes:**
  - **Planning & Public Works Permits:** Layers `HartfordOpenDataTables/FeatureServer/3` (Planning Permits) and `FeatureServer/4` (Public Works Permits) are active, live-updated, and carry identical Accela-style schemas (`RECORD_ID`, `DateIssued`/`OpenedDate`, `Location`). Can be registered as supplementary permit layers. -> **Tier 2 (REGISTER)**.
  - **Deeds / Real Estate Sales:** Municipal table `HartfordOpenDataTables/FeatureServer/5` suffers a ~7-month town-clerk publishing lag. Registering the statewide Socrata feed `data.ct.gov/resource/5mzw-sjtu.json` (`where="town = 'Hartford'"`) provides a reliable, standardized Deeds stream. -> **Tier 2 (REGISTER)**.
  - **Food Licenses:** Municipal `Food Establishments Licenses Current` has 735 rows but lacks timestamps/watermarks (snapshot only); statewide eLicensing remains superior.

---

### 7. Manchester, NH
* **Portals Investigated:** `manchesternh.opendata.arcgis.com` (401 Private Org), `highwaymapsplans.manchesternh.gov` (Login-gated ASP.NET), NH GRANIT, NH Open Data (`data.nh.gov`), NHDeeds.com.
* **Feed Status:**
  - **All 4 Families:** The city ArcGIS Hub is private (401 Unauthorized), the highway permitting system is password-protected, and Hillsborough County Registry of Deeds operates behind NHDeeds.com (paywall/search portal). NH state portals offer static base mapping, not transactional feeds. -> **Tier 3**.
* **Recommendation:** **REJECT**.

---

### 8. Portland, ME
* **Portals Investigated:** City of Portland Citizen Self Service (CSS / EnerGov), City GIS Hub (`portlandmaine.gov/gis`), Maine GeoLibrary (`geolibrary-maine.opendata.arcgis.com`), Cumberland County Registry of Deeds.
* **Feed Status:**
  - **All 4 Families:** Permits and business licensing run through EnerGov CSS UI without bulk API access. 311 uses SeeClickFix UI. Cumberland County Registry of Deeds requires manual web searches. Maine GeoLibrary manages parcel geometry base layers without sales timestamps or pricing. -> **Tier 3**.
* **Recommendation:** **REJECT**.

---

### 9. Burlington, VT
* **Portals Investigated:** `burlingtonvt.opendata.arcgis.com` (ArcGIS Hub, 254 items), VCGI / VT Open Geodata (`geodata.vermont.gov`).
* **Feed Status:**
  - **Building Permits:** `OpenGov_Building/FeatureServer/0` (+ Zoning `/0`, Fire Marshal `/0`). Outstanding Tier 1 schema: native WGS84 lat/lng (WKID 4326), `RecordId`, `PermitNo`, `StatusDate`, `StreetAddress`, `EstimatedConstructionCost`. **Issue:** The OpenGov ETL sync froze at `DataUpdateDate = 2026-04-27T01:01:24Z`. Currently **Tier 3 (Frozen)**, but primary candidate for immediate Tier 1 registration once sync unfreezes.
  - **311 / SLA / Deeds:** 311 complaint layer (`HealthProblemReports`) abandoned since 2018; licensing is internal to OpenGov UI; property taxes feature server has 0 layers. -> **Tier 3**.
* **Recommendation:** **DEFER / RE-PROBE CANDIDATE**. Monitor the `OpenGov_Building` service; flip to Tier 1 when `DataUpdateDate` updates.

---

## 3. Analysis of State-Level Supplementation Options

| State | Primary Open Data Portal | SLA / Business Licensing Feed | Deeds / Property Transfers Feed | Building Permits / 311 Feeds | Assessment & Viability |
|---|---|---|---|---|---|
| **Connecticut (CT)** | `data.ct.gov` (Socrata) | `ngch-56tr` (State Licenses & Credentials, daily, watermark `recordrefreshedon`, filtered by town) | `5mzw-sjtu` (Real Estate Sales 2001-2024 GL, watermark `date_recorded`, sales price, address) | Municipal only (Hartford on ArcGIS; others portal-gated) | **EXCELLENT / PRODUCTION READY**. Enables immediate SLA & Deeds indexing for Hartford, New Haven, Bridgeport, Stamford, Waterbury. |
| **Massachusetts (MA)** | `mass.gov` / `massgis.mass.gov` (ArcGIS Hub / Socrata) | ePLACE / eLIPSE (UI search only); Cannabis Control Commission (Socrata) | MassLandRecords (Search portal per county registry; MassGIS standard parcel roll) | Municipal portals (Worcester on ArcGIS; Boston on Socrata) | **MIXED**. Best strategy is municipal registration (Worcester, Boston) rather than statewide feed. |
| **Rhode Island (RI)** | `data.ri.gov` / `permits.ri.gov` | ViewPoint Cloud / Board of Licenses (UI only) | Kofile CountyFusion / RI LandRecords (Login/search portal) | ViewPoint Cloud statewide e-permitting (Account UI only) | **POOR**. Stale Socrata archives (2020) and UI-gated state portals. |
| **Vermont (VT)** | `geodata.vermont.gov` (VCGI) | OpenGov / OPR licensing (UI only) | Town clerk system / VCGI Parcel layers (Annual CAMA roll) | Municipal OpenGov extracts (Burlington ArcGIS) | **MODERATE**. Burlington OpenGov permit sync is the primary target when resumed. |
| **Maine (ME)** | `geolibrary-maine.opendata.arcgis.com` | Professional & Financial Regulation (ALMS search UI) | County Registry of Deeds search portals; GeoParcels base layers | Municipal CSS / EnerGov portals | **POOR**. Base GIS and parcel geometry only; no transactional event feeds. |
| **New Hampshire (NH)** | `data.nh.gov` / `granit.unh.edu` | OPLC Licensure lookup (UI only) | NHDeeds.com county portals | Municipal proprietary apps | **POOR**. No machine-readable event streams. |

---

## 4. Actionable Registration Next Steps

1. **Register Worcester, MA:**
   - Add Worcester to `apps/api/src/spatial/cities/worcester.py` with bounding box, core submarkets, and division definitions.
   - Configure `FeedType.PERMITS` pointing to Worcester Building Permits FeatureServer (`opendata.worcesterma.gov`) with `needs_geocode=True`.
   - Configure `FeedType.SLA` pointing to Worcester Food Establishment Licenses FeatureServer.

2. **Register New Haven, CT and Bridgeport, CT via CT State Supplementation:**
   - Create spatial configurations in `apps/api/src/spatial/cities/new_haven.py` and `bridgeport.py`.
   - Wire `FeedType.SLA` to `https://data.ct.gov/resource/ngch-56tr.json` with `where="city = 'NEW HAVEN'"` and `where="city = 'BRIDGEPORT'"`.
   - Wire `FeedType.DEEDS` to `https://data.ct.gov/resource/5mzw-sjtu.json` with `where="town = 'New Haven'"` and `where="town = 'Bridgeport'"`.

3. **Enhance Hartford, CT Registrations:**
   - Supplement Hartford `FeedType.PERMITS` with Planning (`FeatureServer/3`) and Public Works (`FeatureServer/4`) layers.
   - Register Hartford `FeedType.DEEDS` to `data.ct.gov/resource/5mzw-sjtu.json` (`where="town = 'Hartford'"`) to bypass the local 7-month town-clerk publication lag.

4. **Monitor Burlington, VT OpenGov Sync:**
   - Set up an automated check / re-probe on `OpenGov_Building/FeatureServer/0` for updates past `2026-04-27T01:01:24Z`. Immediately register as Tier 1 once the ETL pipeline resumes.

5. **Run Repo Pre-Flight Validation:**
   - Execute `python3 scripts/verify_cicd_preflight.py` and `bun run facts:export` upon any registry additions to ensure dashboard, map, and facts synchronization.
