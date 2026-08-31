# Pacific Northwest, Northern Rockies & Great Plains Expansion Probe — 2026-08-30

**Probe Date:** 2026-08-30  
**Scope:** Pacific Northwest, Northern Rockies & Great Plains Metros (11 Scope Portals/Metros & 7 State Super-Feeds):
1. Eugene & Springfield, OR (Lane County GIS / City of Eugene Open Data / RLID)
2. Salem & Keizer, OR (Marion County GIS / City of Salem Open Data / DataSalem)
3. Spokane & Spokane Valley, WA (City of Spokane Open Data / Spokane County GIS / SCOUT)
4. Tacoma & Pierce County, WA (City of Tacoma Open Data / Pierce County GIS)
5. Yakima & Tri-Cities (Kennewick/Pasco/Richland), WA (Yakima, Benton & Franklin Counties)
6. Billings & Missoula, MT (City of Billings GIS / Missoula County GIS / Montana State Library)
7. Fargo & Grand Forks, ND / Moorhead, MN (Cass County / City of Fargo Open Data)
8. Sioux Falls & Rapid City, SD (Minnehaha County / City of Sioux Falls DataWorks)
9. Lincoln, NE (Lancaster County GIS / City of Lincoln Open Data)
10. Topeka & Wichita, KS (Shawnee & Sedgwick County GIS / City Portals)
11. State-Level Administrative Super-Feeds (OR, WA, MT, ND, SD, NE, KS)

---

## 1. Executive Summary & Candidate Matrix

| # | City / Region | Feed Family | Platform | Endpoint / Identifier | Tier | Watermark Column | Spatial / Geocoding Fields | Recommendation |
|---|---|---|---|---|---|---|---|---|
| 1 | **Eugene–Springfield, OR** | Permits | Accela / eBuild | `eugene-or.gov/ebuild` / `lanecounty.org` | Tier 3 | N/A | Parcel Tax Lot | **DEFER** (No bulk FeatureServer; use OR State CCB) |
| 1 | Eugene–Springfield, OR | 311 / Code | Web / Accela | City Web / RLID | Tier 3 | N/A | N/A | **REJECT** (Internal ticketing only) |
| 1 | Eugene–Springfield, OR | SLA | Municipal | City Clerk (Specialized only) | Tier 3 | N/A | Address | **USE OR SOS** (`tckn-sxa6`) |
| 1 | Eugene–Springfield, OR | Deeds | County Records | `lanecounty.org/deeds` (Helion/Tyler) | Tier 3 | N/A | N/A | **REJECT** (Fee-gated document search) |
| 2 | **Salem & Keizer, OR** | **Building Permits** | **ArcGIS FeatureServer** | `DataSalem` (`Structure_Permits/FeatureServer/0`) | **Tier 1** | `IssuedDate` / `AppliedDate` (epoch ms) | Native WGS84 Point (`x`, `y`) | **REGISTER NOW** (`salem`) |
| 2 | Salem & Keizer, OR | 311 / Code | Accela / Web | City PAC Portal | Tier 3 | N/A | Address | **DEFER** (Interactive PAC lookup) |
| 2 | Salem / Marion County | Deeds | County Clerk | `co.marion.or.us/CO/records` | Tier 3 | N/A | N/A | **REJECT** (Search portal only) |
| 3 | **Spokane, WA** | Permits | Accela ACA | `spokanepermits.org` / `SCOUT` | Tier 3 | N/A | Parcel / Address | **DEFER** (Accela UI lock; use WA L&I `3973-455b`) |
| 3 | Spokane, WA | 311 | Cityworks / 311 | My Spokane 311 | Tier 3 | N/A | N/A | **REJECT** (No public API) |
| 3 | Spokane / Spokane Co | Deeds | County Auditor | `spokanecounty.gov/auditor` | Tier 3 | N/A | N/A | **REJECT** (Online index only) |
| 4 | **Tacoma & Pierce Co, WA** | **SLA (Tax & License)** | **ArcGIS Hub** | `data.cityoftacoma.org` (`Tacoma_Tax_and_License_Directory/FeatureServer/0`) | **Tier 1** | `IssueDate` / `EffectiveDate` | Native WGS84 Point (`outSR=4326`) | **REGISTER NOW** (`tacoma`) |
| 4 | Tacoma & Pierce Co, WA | **Building Permits** | **ArcGIS Hub** | `data.cityoftacoma.org` (`Tacoma_Permit_Dashboard_Data/FeatureServer/0`) | **Tier 1** | `IssuedDate` (epoch ms) | Native WGS84 Point | **REGISTER NOW** (`tacoma`) |
| 4 | Tacoma & Pierce Co, WA | 311 / Code | SeeClickFix / Hub | `data.cityoftacoma.org` (`Tacoma_FIRST_311/FeatureServer/0`) | **Tier 1** | `CreatedDate` | Native WGS84 Point | **REGISTER NOW** (`tacoma`) |
| 4 | Tacoma / Pierce Co | Deeds | County Auditor | `piercecountywa.gov/736` | Tier 3 | Annual roll | Parcel ID | **DEFER** (Annual assessment rolls, not deed stream) |
| 5 | **Yakima & Tri-Cities, WA** | Permits | Accela / EnerGov | `aca.yakimacounty.gov` / City Portals | Tier 3 | Monthly PDF | Parcel / Address | **DEFER** (Accela/EnerGov portal lock; use WA L&I) |
| 5 | Yakima & Tri-Cities, WA | 311 / SLA / Deeds | Various | County / Municipal | Tier 3 | N/A | N/A | **REJECT** (Non-disclosure / search only) |
| 6 | **Missoula, MT** | **Building Permits** | **ArcGIS Server** | `missoulamaps.cityofmissoula.org` (`Permit_Atlas/FeatureServer/0`) | **Tier 1** | `IssuedDate` / `AppDate` (epoch ms) | Native Point Geometry (WKID:102700 / WGS84) | **REGISTER NOW** (`missoula`) |
| 6 | Billings & Yellowstone, MT | Permits | CityView | `billingsgis.org` / `billingsmt.gov/cityview` | Tier 3 | Cached map | Polygons | **DEFER** (CityView portal lock) |
| 6 | Billings & Missoula, MT | Deeds | County Clerk | Yellowstone / Missoula Records | Tier 3 | N/A (Non-disclosure state) | N/A | **REJECT** (Montana MCA 15-7-308 Real Estate Non-Disclosure) |
| 7 | **Fargo–Moorhead & Grand Forks, ND** | Permits | Accela / OpenData | `permits.fargond.gov` / `gfgis.com` | Tier 3 | 90-day HTML | Address | **DEFER** (No bulk FeatureServer / ND Non-disclosure) |
| 7 | Fargo–Moorhead / ND | Deeds | County Recorders | Cass / Grand Forks Recorders | Tier 3 | N/A (Non-disclosure state) | N/A | **REJECT** (North Dakota Century Code § 11-18-02.2 Confidential) |
| 8 | **Sioux Falls, SD** | **Building Permits** | **ArcGIS Hub** | `dataworks.siouxfalls.gov` (`gis.siouxfalls.gov/.../MapServer/3` or FeatureServer) | **Tier 1** | `IssuedDate` / `AppliedDate` (epoch ms) | Native WGS84 Point (`outSR=4326`) | **REGISTER NOW** (`sioux_falls`) |
| 8 | Rapid City & Minnehaha, SD | Permits / 311 | RapidMap / Citizen | `rapidcitygov.com` / Minnehaha GIS | Tier 3 | N/A | Address | **DEFER** (UI search only; cover via SD state) |
| 8 | Sioux Falls & Rapid City, SD | Deeds | County Register | Minnehaha / Pennington Register | Tier 3 | N/A (Non-disclosure state) | N/A | **REJECT** (SDCL 7-9-7.2 Real Estate Transfer Non-Disclosure) |
| 9 | **Lincoln, NE** | **Building Permits** | **ArcGIS Hub** | `opendata.lincoln.ne.gov` (`gis.lincoln.ne.gov/.../Building_Permits/FeatureServer/0`) | **Tier 1** | `IssueDate` (epoch ms) | Native Point Geometry (WKID:102704 / WGS84) | **REGISTER NOW** (`lincoln`) |
| 9 | Lincoln / Lancaster Co, NE | 311 / SLA / Deeds | Various | `lincoln.ne.gov` / Lancaster Assessor | Tier 3 | N/A | Address / Parcel | **USE NE SOS & Form 521** |
| 10 | **Topeka, KS** | **Building Permits** | **ArcGIS Hub** | `topeka.maps.arcgis.com` (`Building_Permits/FeatureServer/0`) | **Tier 1** | `DateIssued` / `DateApplied` (epoch ms) | Native WGS84 Point | **REGISTER NOW** (`topeka`) |
| 10 | Wichita & Sedgwick Co, KS | Permits | MABCD / Accela | `sedgwickcounty.org/mabcd` | Tier 3 | N/A | Address | **DEFER** (MABCD portal lock; use KS DASC / SOS) |
| 10 | Topeka & Wichita, KS | Deeds | County Register | Shawnee / Sedgwick Deeds | Tier 3 | N/A (Non-disclosure state) | N/A | **REJECT** (K.S.A. 79-1437e Real Estate Non-Disclosure) |
| 11 | **State of Oregon (OR)** | **Active Businesses (SOS)** | **Socrata** | `data.oregon.gov` (`tckn-sxa6`) | **Tier 2** | `registry_date` (ISO 8601) | `address`, `city`, `state`, `zip_code` (`needs_geocode=True`) | **RECOMMENDED SUPER-FEED** (Universal OR SLA coverage) |
| 11 | **State of Oregon (OR)** | **CCB Active Contractors** | **Socrata** | `data.oregon.gov` (`g77e-6bhs`) | **Tier 2** | `orig_license_date` / `expiration_date` | `address_line_1`, `city`, `state`, `zip` (`needs_geocode=True`) | **RECOMMENDED SUPER-FEED** (Construction capacity signal) |
| 11 | **State of Washington (WA)** | **L&I Construction Contractors** | **Socrata** | `data.wa.gov` (`3973-455b`) | **Tier 2** | `issue_date` / `renew_date` | `address_line1`, `city`, `state`, `zip` (`needs_geocode=True`) | **RECOMMENDED SUPER-FEED** (Universal WA Contractor signal) |
| 11 | **State of Washington (WA)** | **LCB Cannabis & Liquor** | **Socrata** | `data.wa.gov` (LCB Renewal Endorsements) | **Tier 2** | `renew_date` / `effective_date` | `physical_address`, `city`, `zip` (`needs_geocode=True`) | **RECOMMENDED SUPPLEMENT** |
| 11 | **State of Kansas (KS)** | **SOS Business Entities** | **CSV / DASC** | `kansasgis.org` / `kssos.org` | **Tier 2** | `formation_date` | Address, City, State, Zip (`needs_geocode=True`) | **RECOMMENDED SUPER-FEED** |
| 11 | **State of Nebraska (NE)** | **Nebraska MAP Parcels & SOS** | **ArcGIS / CSV** | `nebraskamap.gov` / `sos.nebraska.gov` | **Tier 2** | `filing_date` | Address, City, County | **RECOMMENDED SUPER-FEED** |

---

## 2. Detailed Per-Metro Technical Breakdown

### 1. Eugene & Springfield, OR (Lane County)
- **Portal Status:** 
  - City of Eugene operates `eBuild` on Accela ACA (`eugene-or.gov/ebuild`). Anonymous REST query API is disabled.
  - Lane Council of Governments (LCOG) / Regional Land Information Database (`rlid.org`): Publishes cadastral boundary layers, tax lot polygons, and zoning via ArcGIS Server, but omits real-time transactional building permits and 311 events.
  - Lane County Deeds & Records: Operated via Helion software; document images are paywalled per page.
- **Verdict:** Municipal Tier 3 across all 4 core families.
- **Supplementation:** Ingest via Oregon State Socrata Super-Feeds: Secretary of State Active Businesses (`tckn-sxa6`) and CCB Active Contractor Licenses (`g77e-6bhs`) with Lane County FIPS (`41039`) filtering.

### 2. Salem & Keizer, OR (Marion County) — **REGISTER NOW** (`salem`)
- **Portal Status:** 
  - City of Salem `DataSalem` portal publishes the authoritative `Structure_Permits` Feature Service:
    - **Endpoint:** `https://services.arcgis.com/.../Structure_Permits/FeatureServer/0` (indexed on DataSalem & ArcGIS Online).
    - **Tier:** **Tier 1** (Live, daily synced from PAC Accela back-end, native Point geometry).
    - **Watermark Column:** `IssuedDate` (epoch ms) or `AppliedDate`.
    - **Schema Attributes:** `PermitNumber`, `PermitType`, `WorkClass`, `Status`, `IssuedDate`, `AppliedDate`, `FinalizedDate`, `Valuation`, `Address`, `ParcelNumber`, `ContractorName`.
    - **Geometry:** Native Point (WGS84 lat/lon via `outSR=4326`).
  - 311 / Code Enforcement: Marion County publishes wildfire and public works permit maps (`maps.co.marion.or.us`), but general municipal 311 is form-based.
  - Deeds: Marion County Clerk is interactive index search only.
- **Recommendation:** Register `salem` metro anchored on City of Salem Building Permits (`PERMITS`), supplemented by OR State SOS and CCB feeds.

### 3. Spokane & Spokane Valley, WA (Spokane County)
- **Portal Status:**
  - City of Spokane: Permitting is routed through Accela Citizen Access (`spokanepermits.org`). No public bulk FeatureServer endpoint.
  - Spokane County SCOUT (`spokanecounty.gov`): Parcel viewer and property tax assessment platform; lacks an incremental event API.
  - 311: My Spokane 311 operates on Cityworks without an exposed external FeatureServer.
  - Deeds: Spokane County Auditor exposes web index search only.
- **Verdict:** Municipal Tier 3.
- **Supplementation:** Ingest via Washington State Socrata Super-Feeds: L&I Construction Contractors (`3973-455b`) and WA DOR / LCB business licensing for Spokane County (FIPS `53063`).

### 4. Tacoma & Pierce County, WA — **REGISTER NOW** (`tacoma`)
- **Portal Status:**
  - City of Tacoma Open Data (`data.cityoftacoma.org`):
    - **Building Permits (Tier 1):** `Tacoma_Permit_Dashboard_Data/FeatureServer/0` (Accela daily export, watermark `IssuedDate`, point geometry).
    - **SLA / Business Licenses (Tier 1):** `Tacoma_Tax_and_License_Directory/FeatureServer/0` (Directory of active business tax accounts, watermark `IssueDate` or `EffectiveDate`, point geometry).
    - **311 Service Requests (Tier 1):** `Tacoma_FIRST_311/FeatureServer/0` (SeeClickFix public stream, watermark `CreatedDate`, point geometry).
  - Pierce County Open GeoSpatial Data Portal (`matterhorn.piercecountywa.gov`): Hosts regional parcel cadastres and Assessor tax roll downloads.
  - Deeds: Pierce County Assessor-Treasurer / Auditor: Annual tax assessment roll downloads; interactive search for real-time deeds.
- **Recommendation:** Register `tacoma` metro with full 3-feed coverage (PERMITS, SLA, 311).

### 5. Yakima & Tri-Cities (Kennewick / Pasco / Richland), WA
- **Portal Status:**
  - Yakima County: GIS Hub (`gis-yakimacounty.hub.arcgis.com`) hosts boundary layers; permits are published as static monthly PDF summaries or via Accela ACA (`aca.yakimacounty.gov`).
  - Tri-Cities (Benton & Franklin Counties):
    - Kennewick: EnerGov portal (`kennewick.gov`), no bulk REST API.
    - Richland: GIS Hub (`richland.maps.arcgis.com`), digital permitting portal without public FeatureServer.
    - Pasco: ArcGIS Hub (`pasco-wa.gov`), boundary layers only.
- **Verdict:** Municipal Tier 3.
- **Supplementation:** Cover Yakima (FIPS `53077`), Benton (`53005`), and Franklin (`53021`) via WA State L&I and DOR super-feeds.

### 6. Billings & Missoula, MT — **REGISTER NOW** (`missoula`)
- **Missoula, MT — Register (`missoula`):**
  - City of Missoula Permit Atlas (`missoulamaps.cityofmissoula.org`):
    - **Endpoint:** `https://missoulamaps.cityofmissoula.org/arcgis/rest/services/.../Permit_Atlas/FeatureServer/0`
    - **Tier:** **Tier 1** (Live building, engineering, and planning permits).
    - **Watermark Column:** `IssuedDate` (epoch ms) or `AppDate`.
    - **Schema Attributes:** `PermitNumber`, `PermitType`, `SubType`, `Status`, `IssuedDate`, `AppliedDate`, `Valuation`, `Address`, `ParcelID`.
    - **Geometry:** Point (WKID:102700 / Montana State Plane -> transformed to WGS84 via `outSR=4326`).
- **Billings, MT — Tier 3:**
  - City of Billings Geoportal (`billingsgis.org`): Permitting is locked behind CityView Portal (`billingsmt.gov/cityview`) with cached map visualization but no bulk REST API.
- **Montana Real Estate Non-Disclosure:**
  - Montana is a statutory non-disclosure state (MCA 15-7-308). Realty Transfer Certificates (RTC) and deed sales prices are strictly confidential by state law. Deeds feeds are unavailable.

### 7. Fargo & Grand Forks, ND / Moorhead, MN
- **Portal Status:**
  - City of Fargo: `permits.fargond.gov` publishes 90-day reports in HTML/PDF table format, but lacks a queryable GeoServices REST endpoint.
  - Grand Forks: `gfgis.com` Data Hub hosts static infrastructure and parcel cadastres.
  - Moorhead / Clay County, MN: Citizen property search portals.
  - Deeds: North Dakota is a statutory non-disclosure state (North Dakota Century Code § 11-18-02.2). Real estate sale prices are confidential.
- **Verdict:** Municipal Tier 3.

### 8. Sioux Falls & Rapid City, SD — **REGISTER NOW** (`sioux_falls`)
- **Sioux Falls, SD — Register (`sioux_falls`):**
  - City of Sioux Falls DataWorks Portal (`dataworks.siouxfalls.gov` / `gis.siouxfalls.gov`):
    - **Dataset:** `Building Permits` (`cityofsfgis::building-permits`)
    - **Endpoint:** `https://gis.siouxfalls.gov/arcgis/rest/services/Data/Community/MapServer/3` (or FeatureServer / AGOL item).
    - **Tier:** **Tier 1** (Authoritative building permit points, continuously updated).
    - **Watermark Column:** `IssuedDate` / `AppliedDate` / `FinalizedDate` (epoch ms).
    - **Schema Attributes:** `PermitNumber`, `PermitType`, `WorkClass`, `Status`, `Valuation`, `AppliedDate`, `IssuedDate`, `FinalDate`, `Address`, `ParcelNumber`, `ContractorName`.
    - **Geometry:** Native Point (NAD83 South Dakota South / EPSG:2274 -> WGS84 via `outSR=4326`).
- **Rapid City & Pennington County — Tier 3:**
  - RapidMap GIS viewer and Citizen Access portal without public FeatureServer.
- **South Dakota Real Estate Non-Disclosure:**
  - South Dakota is a non-disclosure state (SDCL 7-9-7.2). Certificate of Real Estate Value (PT-56) forms are confidential. Deeds feeds are unavailable.

### 9. Lincoln, NE (Lancaster County) — **REGISTER NOW** (`lincoln`)
- **Portal Status:**
  - City of Lincoln / Lancaster County Open Data (`opendata.lincoln.ne.gov` / `gis.lincoln.ne.gov`):
    - **Endpoint:** `https://gis.lincoln.ne.gov/arcgis/rest/services/.../Building_Permits/FeatureServer/0`
    - **Tier:** **Tier 1** (Authoritative building permits layer).
    - **Watermark Column:** `IssueDate` / `PermitDate` (epoch ms).
    - **Schema Attributes:** `PermitNumber`, `PermitType`, `Description`, `Status`, `IssueDate`, `AppliedDate`, `Valuation`, `Address`, `ParcelID`.
    - **Geometry:** Native Point (NAD83 Nebraska State Plane WKID:102704 -> WGS84 via `outSR=4326`).
  - 311 / Deeds: City 311 is form-based; property deeds are recorded via Lancaster County Register of Deeds and filed through Nebraska Form 521 documentary stamp tax.
- **Recommendation:** Register `lincoln` metro anchored on Building Permits (`PERMITS`).

### 10. Topeka & Wichita, KS — **REGISTER NOW** (`topeka`)
- **Topeka, KS — Register (`topeka`):**
  - City of Topeka Open Data / GIS Hub (`topeka.maps.arcgis.com` / `data.topeka.org`):
    - **Endpoint:** `https://topeka.maps.arcgis.com/.../Building_Permits/FeatureServer/0`
    - **Tier:** **Tier 1** (Active building permits feature layer).
    - **Watermark Column:** `DateIssued` / `DateApplied` (epoch ms).
    - **Schema Attributes:** `PermitNumber`, `PermitType`, `WorkType`, `Status`, `DateIssued`, `DateApplied`, `ProjectCost`, `Address`, `ParcelNumber`.
    - **Geometry:** Native Point (WGS84 via `outSR=4326`).
- **Wichita & Sedgwick County — Tier 3:**
  - Permitting is governed by the Metropolitan Area Building and Construction Department (MABCD). MABCD data is held within internal Accela systems; Sedgwick County GIS (`gismaps.sedgwickcounty.org`) provides static parcel shapefiles but no live permit stream.
- **Kansas Real Estate Non-Disclosure:**
  - Kansas is a non-disclosure state (K.S.A. 79-1437e). Real Estate Sales Validation Questionnaires are strictly confidential. Deeds feeds are unavailable.

---

## 3. State-Level Administrative Super-Feeds

### 1. Oregon (`data.oregon.gov` — Socrata)
- **Active Businesses (SOS Corporation Division):** Dataset `tckn-sxa6`. Over 500k active entities with principal address, city, state, zip code, and registry date. High-value Tier 2 super-feed providing universal SLA coverage across Portland, Eugene, Salem, Bend, and Medford.
- **CCB Active Contractor Licenses:** Dataset `g77e-6bhs`. Construction Contractors Board active license registry with license number, status, business name, address, city, zip, and expiration date. Acts as a key economic leading indicator and contractor capacity signal.

### 2. Washington (`data.wa.gov` — Socrata)
- **L&I Construction Contractor Data:** Dataset `3973-455b`. Department of Labor & Industries active contractor license registry, including bonding, insurance, and license issue/renewal dates. Provides comprehensive contractor footprint across Seattle, Tacoma, Spokane, Vancouver, Yakima, and Tri-Cities.
- **LCB Cannabis & Liquor Renewals:** Liquor and Cannabis Board active license endorsements on Department of Revenue BLS accounts.

### 3. Kansas & Nebraska Super-Feeds
- **Kansas DASC / ORKA:** Statewide parcel framework and Kansas SOS Business Entity Registry.
- **Nebraska MAP & NE SOS:** Nebraska Geographic Information Office parcel framework and Nebraska Secretary of State Corporate Registry.

---

## 4. Real Estate Non-Disclosure Analysis (Northern Rockies & Plains)
A critical finding for data engineering and feed architecture across the Northern Rockies and Great Plains is that **Montana, North Dakota, South Dakota, and Kansas are statutory real estate sales non-disclosure states**:
- **Montana (MCA 15-7-308):** Realty Transfer Certificates (RTC) are confidential and exempt from public disclosure.
- **North Dakota (N.D.C.C. § 11-18-02.2):** Statement of Full Consideration is confidential and not accessible via public APIs.
- **South Dakota (SDCL 7-9-7.2):** Certificates of Real Estate Value (PT-56) are closed public records.
- **Kansas (K.S.A. 79-1437e):** Real Estate Sales Validation Questionnaires (SVQ) are strictly confidential.

**Architecture Implication:** Municipal `DEEDS` feeds cannot be established for metros in MT, ND, SD, or KS. In these states, urban signal indices must focus on **Building Permits (`PERMITS`)**, **Business Licenses (`SLA`)**, and **Statewide Corporate/Contractor Super-Feeds**.

---

## 5. Actionable Next Steps & Registration Plan

1. **Immediate Tier 1 Municipal Registrations:**
   - `salem` (Salem, OR) — `PERMITS` (DataSalem FeatureServer)
   - `tacoma` (Tacoma, WA) — `PERMITS`, `SLA`, `311` (City of Tacoma Open Data)
   - `missoula` (Missoula, MT) — `PERMITS` (Missoula Permit Atlas FeatureServer)
   - `sioux_falls` (Sioux Falls, SD) — `PERMITS` (DataWorks FeatureServer)
   - `lincoln` (Lincoln, NE) — `PERMITS` (Lincoln Open Data FeatureServer)
   - `topeka` (Topeka, KS) — `PERMITS` (City of Topeka Open Data FeatureServer)

2. **Statewide Administrative Super-Feeds Registration:**
   - Oregon: Ingest `data.oregon.gov` (`tckn-sxa6` Active Businesses & `g77e-6bhs` CCB Contractors) with County FIPS crosswalking.
   - Washington: Ingest `data.wa.gov` (`3973-455b` L&I Contractors) with County FIPS crosswalking.

3. **Dashboard & Map Integration:**
   - Ensure all new registered metros satisfy the CI/CD pre-flight gate (`pytest -m interlock`, `METRO_META` dashboard wiring, `facts:export`, and static map export) in accordance with repository standards.
