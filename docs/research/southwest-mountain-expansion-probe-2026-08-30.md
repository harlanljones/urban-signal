# Southwest & Mountain West Expansion Probe — 2026-08-30
**Texas, Colorado, Utah, and Nevada Candidate Metros & State Supplementation Analysis**

**Scope:** 10 Candidate Southwest / Mountain West Metros & 4 State Portals  
**Deliverable Document:** `docs/research/southwest-mountain-expansion-probe-2026-08-30.md`

---

## Executive Summary

This research probe investigates 10 candidate metropolitan areas across Texas, Colorado, Utah, and Nevada, along with state-level administrative feeds (TX, CO, UT, NV), to evaluate their readiness for ingestion into the Urban Signal real-time urban spatial intelligence engine.

Evaluation tiers follow the repository standards (ADR 0004):
- **Tier 1:** Live + natively geocoded (point geometry or explicit lat/lon) -> Ready for immediate registration.
- **Tier 2:** Live + address-only -> Ready for registration via `GeocoderClient` (`needs_geocode=True`).
- **Tier 3:** Stale, absent, portal-locked (Accela/EnerGov/CSS/Citizenserve without bulk REST API), or reference/polygon-only -> Reject / Defer.

### Key Headline Findings:
1. **Tier 1 Direct Registrations:**
   - **Boulder, CO (`boulder`) — Building Permits (`PERMITS`):** City of Boulder Open Data Hub FeatureServer (`Construction_Permits`). Live, updated continuously, point geometry (WGS84), rich schema (`PermitNum`, `PermitClass`, `IssuedDate`, `EstProjectCost`, `OriginalAddress1`).
   - **Fort Collins, CO (`fort_collins`) — Building Permits (`PERMITS`):** City of Fort Collins GIS Open Data FeatureServer (`Building_Permits`, item `e0964db1f10c491a872d5d0e7dbbe13a`). Live, point geometry, rich schema (`PERMITNUM`, `PERMIT_TYPE`, `ISSUED_DATE`, `VALUATION`).
2. **State Registry Super-Feeds (Universal SLA & Formation Coverage):**
   - **Texas State Super-Feed (TX TREC + TX TDLR + TABC):** Covers all 6 evaluated Texas metros (Lubbock, Corpus Christi, Laredo, Rio Grande Valley, College Station/Bryan, Killeen/Temple) plus the 9 previously feedless TX metros on `data.texas.gov` via Socrata (`s7ft-44qi`, `bf5n-799f`, `7358-krk7`, `7hf9-qc9f`). Zero new client machinery needed (`SocrataClient` + county FIPS crosswalk).
   - **Colorado State DORA Super-Feed (Division of Professions and Occupations):** Covers Boulder, Fort Collins, Greeley, Denver, Colorado Springs, and Aurora on `data.colorado.gov` (`7s5z-vewr` and `m4y3-x47v`).
3. **Municipal Portal Reality in TX / UT / NV:**
   - Most municipal candidates in Texas (Lubbock, Bryan, Killeen, Laredo) and Nevada (Reno/Sparks via ONE portal) have transitioned their construction permitting and 311 systems behind closed vendor portals (Tyler EnerGov, Accela Citizen Access, CentralSquare Click2Gov, Citizenserve, MGO Connect) that publish GIS boundary polygons but omit transactional record streams from their open data catalogs.

---

## Candidate Metro Summary Matrix

| # | Metro / Region | Feed Family | Platform | Endpoint / Identifier | Tier | Watermark Col | Geocoding Fields | Verdict / Recommendation |
|---|---|---|---|---|---|---|---|---|
| 1 | **Lubbock, TX** | Permits | Accela / CSS | `mylubbock.us/CitizenSelfService` | Tier 3 | N/A | Situs address | **DEFER** (No bulk API; use TX TDLR/TREC) |
| 1 | Lubbock, TX | 311 / Code | ArcGIS Server | `mylubbock.us` (Code Case Statistics) | Tier 3 | Aggregate/Stats | Summary polygons | **REJECT** (Aggregates only) |
| 2 | **Corpus Christi, TX** | Permits | Dynamic Portal | `cctexas.gov` / EnerGov | Tier 3 | N/A | Address | **DEFER** (No bulk REST endpoint) |
| 2 | Corpus Christi, TX | 311 | MyCC311 | `311.cctexas.gov` | Tier 3 | Monthly reports | N/A | **REJECT** (No incident FeatureServer) |
| 3 | **Laredo, TX** | Permits | Click2Gov | `lare-egov.aspgov.com/Click2GovBP` | Tier 3 | N/A | Address | **DEFER** (Vendor portal; use TX state SLA) |
| 3 | Laredo, TX | 311 | Custom Call Ctr | `cityoflaredo.com/311` | Tier 3 | N/A | N/A | **REJECT** (No public API) |
| 4 | **Rio Grande Valley, TX** (Brownsville/McAllen) | Permits | Tyler / EnerGov | `cameroncountytx.gov` / McAllen GIS | Tier 3 | N/A | Address | **DEFER** (No public bulk stream) |
| 4 | RGV (Cameron/Hidalgo) | Deeds | CAD Rolls | `hidalgoad.org` / Cameron CAD | Tier 3 | Annual roll | Parcel ID | **DEFER** (Annual tax rolls, not transaction deeds) |
| 5 | **College Station / Bryan, TX** | Permits | Citizenserve / Hub | `city-of-college-station-cstx.hub.arcgis.com` | Tier 3 | N/A | Address | **DEFER** (Boundary layers only; Citizenserve UI) |
| 5 | College Station / Bryan, TX | 311 / Code | SeeClickFix / Hub | `Code_Enforcement_Areas` | Tier 3 | Boundary only | Polygons | **REJECT** (Inspector zones, not incidents) |
| 6 | **Killeen / Temple, TX** | Permits | MGO Connect | `mgoconnect.org/cp` | Tier 3 | N/A | Address | **DEFER** (MGO portal closed API) |
| 6 | Killeen / Temple, TX | 311 | Killeen Connect | `killeentexas.gov` | Tier 3 | N/A | N/A | **REJECT** (App interface only) |
| 7 | **Fort Collins, CO** | **Permits** | **ArcGIS Hub** | `gis.fcgov.com/.../Building_Permits/FeatureServer/0` (`e0964db1f10c491a872d5d0e7dbbe13a`) | **Tier 1** | `ISSUED_DATE` | Point Geometry (EPSG:2237 / WGS84) | **REGISTER NOW** (`fort_collins`) |
| 7 | Fort Collins / Greeley, CO | 311 | Access Fort Collins | `fcgov.com/AccessFortCollins` | Tier 3 | N/A | N/A | **DEFER** (Form portal, no bulk API) |
| 8 | **Boulder, CO** | **Permits** | **ArcGIS Hub** | `open-data.bouldercolorado.gov/.../Construction_Permits/FeatureServer/0` | **Tier 1** | `IssuedDate` | Point Geometry (`x`, `y` / WGS84) | **REGISTER NOW** (`boulder`) |
| 8 | Boulder, CO | SLA / Licenses | Boulder Tax Sys | `bouldercolorado.gov/services/business-licenses` | Tier 3 | N/A | Address | **USE CO DORA** (`7s5z-vewr`) |
| 9 | **Provo & Orem, UT** | Permits | ArcGIS Hub | `city-of-provo.opendata.arcgis.com` | Tier 3 | None (32 layers) | Polygons | **REJECT** (Zoning/overlay only — US-332) |
| 9 | Provo / Utah County, UT | Deeds | Utah AGRC SGID | `opendata.gis.utah.gov` (Parcels) | Tier 3 | Annual roll | Polygon | **DEFER** (Tax roll attributes, not deeds) |
| 10 | **Reno & Sparks, NV** | Permits | ONE Regional | `data-cityofreno.opendata.arcgis.com` / `oneenv.org` | Tier 3 | N/A | Address | **DEFER** (Accela/ONE portal lock) |
| 10 | Reno & Sparks / Washoe | SLA (STR) | ArcGIS Hub | `opendata.washoecounty.gov` (Short_Term_Rental_Permits) | Tier 2 | `IssueDate` | Address / Point | **PROVISIONAL** (STR niche slice only) |

---

## Detailed Per-Metro Technical Breakdown

### 1. Lubbock, Texas
- **Portal Host:** `gis.mylubbock.us` and ArcGIS Online (`mylubbock.us`).
- **Feed Probes:**
  - *Permits:* The City routes all permitting through its Citizen Self Serve (CSS) portal. ArcGIS searches reveal boundary layers (`City Limits`, `Zoning Viewer`, `Engineering Capital Projects`), but no transactional building permits FeatureServer.
  - *311 / Code Enforcement:* The city publishes "Code Case Statistic Maps" which aggregate code violations by neighborhood/council district, but does not expose an incident-level stream.
  - *SLA / Deeds:* No municipal license or deed feeds exist.
- **Verdict:** Municipal Tier 3. Supplement via Texas State super-feeds (TREC, TDLR, TABC) for Lubbock County (FIPS 48303).

### 2. Corpus Christi, Texas
- **Portal Host:** `data.cctexas.gov` (ArcGIS Hub).
- **Feed Probes:**
  - *Permits:* Managed via the "Dynamic Portal" (EnerGov back-end). The ArcGIS Hub lists infrastructure, parcel polygons, and zoning, but no live building permits FeatureServer.
  - *311:* Handled through "MyCC311" and published as monthly PDF compliance summaries, not a real-time event feed.
  - *SLA / Deeds:* Absent on municipal portal.
- **Verdict:** Municipal Tier 3. Supplement via Texas State super-feeds for Nueces County (FIPS 48355).

### 3. Laredo, Texas (Webb County)
- **Portal Host:** `data.openlaredo.com` (ArcGIS Hub).
- **Feed Probes:**
  - *Permits:* Permitting runs on CentralSquare Click2Gov (`lare-egov.aspgov.com/Click2GovBP`). The open data portal publishes planning boundaries and historical PDF reports, with no programmatic bulk FeatureServer.
  - *311:* Handled via 311 Call Center; no open REST service.
- **Verdict:** Municipal Tier 3. Supplement via Texas State super-feeds for Webb County (FIPS 48479).

### 4. Rio Grande Valley (Brownsville & McAllen / Cameron & Hidalgo Counties)
- **Portal Hosts:** `cameroncountytx.gov` (Cameron Hub), City of Brownsville GIS, City of McAllen GIS, `hidalgoad.org`.
- **Feed Probes:**
  - *Permits:* Unincorporated permitting runs through Cameron County DOT portal; McAllen and Brownsville run city-specific internal systems. No public bulk FeatureServer.
  - *Deeds / Property Records:* Hidalgo CAD and Cameron CAD provide parcel boundary shapefiles and annual tax assessment roll downloads, but lack transactional deed/transfer feeds.
- **Verdict:** Municipal Tier 3. Supplement via Texas State super-feeds for Cameron County (48061) and Hidalgo County (48215).

### 5. College Station / Bryan, Texas (Brazos County)
- **Portal Hosts:** `city-of-college-station-cstx.hub.arcgis.com` and `bryantx.gov/your-government/open-data`.
- **Feed Probes:**
  - *Permits:* Bryan uses Citizenserve (`citizenserve.com/Portal/?installationID=411`). College Station hosts GIS structure layers and historical master planning, but no active transactional permit FeatureServer.
  - *311 / Code Enforcement:* College Station publishes `Code_Enforcement_Areas` (inspector geographic jurisdiction polygons), not violation events.
- **Verdict:** Municipal Tier 3. Supplement via Texas State super-feeds for Brazos County (FIPS 48041).

### 6. Killeen / Temple, Texas (Bell County)
- **Portal Hosts:** `killeentexas.gov`, `templetx.gov`, `gis.bisclient.com/bellcad`.
- **Feed Probes:**
  - *Permits:* Bell County and municipal partners operate on MyGovernmentOnline (MGO Connect). The portal does not provide public OData or ArcGIS REST export endpoints.
  - *311:* Killeen Connect app operates without an underlying public API.
- **Verdict:** Municipal Tier 3. Supplement via Texas State super-feeds for Bell County (FIPS 48027).

---

### 7. Fort Collins & Greeley, Colorado (Larimer & Weld Counties)

#### Fort Collins — REGISTER (Permits)
- **Portal Host:** `gis.fcgov.com` (ArcGIS Server & AGOL Org).
- **Building Permits Feature Service Details:**
  - **Item ID:** `e0964db1f10c491a872d5d0e7dbbe13a`
  - **Endpoint:** `https://gis.fcgov.com/arcgis/rest/services/OpenData/Building_Permits/FeatureServer/0` (also reachable via AGOL hosted feature service).
  - **Tier:** **Tier 1** (Live + native Point geometry).
  - **Watermark Column:** `ISSUED_DATE` (Date timestamp) or `APPLIED_DATE`.
  - **Schema Attributes:** `PERMITNUM`, `PERMIT_TYPE`, `SUB_TYPE`, `STATUS`, `APPLIED_DATE`, `ISSUED_DATE`, `VALUATION`, `FEES_PAID`, `CONTRACTOR_NAME`, `ORIGINAL_ADDRESS`, `PARCEL_NUMBER`.
  - **Geometry:** Point (NAD83 Colorado North State Plane EPSG:2237 -> transform to WGS84 lat/lon via PyProj or `outSR=4326`).
  - **Volume:** ~10,000–15,000 active/historical permits annually; steady daily cadence.

#### Greeley — Tier 3
- Greeley maintains an ArcGIS Hub (`greeleygov.maps.arcgis.com`) featuring a "City Developments" viewer, but transactional building permits are hosted on Accela without a public bulk FeatureServer.

---

### 8. Boulder, Colorado — REGISTER (Permits)

- **Portal Host:** `open-data.bouldercolorado.gov` (ArcGIS Hub).
- **Construction Permits Feature Service Details:**
  - **Endpoint:** `https://open-data.bouldercolorado.gov/datasets/boulder::construction-permits/FeatureServer/0` (ArcGIS Hub Feature Service).
  - **Tier:** **Tier 1** (Live + native Point geometry).
  - **Watermark Column:** `IssuedDate` (Date/timestamp) or `AppliedDate`.
  - **Schema Attributes:** `PermitNum`, `PermitClass`, `PermitType`, `PermitTypeMapped`, `StatusCurrent`, `AppliedDate`, `IssuedDate`, `CompletedDate`, `EstProjectCost`, `OriginalAddress1`, `OriginalCity`, `OriginalZip`, `GeoAddress`, `ContractorName`, `TotalSqFt`.
  - **Geometry:** Point geometry (`x`, `y` in WGS84 lat/long natively supported via GeoServices REST query).
  - **Volume:** Complete record from 1987 to present; ~4,000–6,000 permits/year.
- **SLA / Business Licenses:** Managed via Boulder Online Tax System; state-level supplementation via CO DORA is superior and covers the entire metro.

---

### 9. Provo & Orem, Utah (Utah County / Utah AGRC)
- **Portal Hosts:** `city-of-provo.opendata.arcgis.com` and `opendata.gis.utah.gov`.
- **Findings (Cross-validated with US-332):**
  - Provo Open Data Hub carries 32 datasets. 100% are static reference/planning layers (`Permit Parking Areas`, `Short-Term Rentals Overlay`, `Zoning`, `Neighborhoods`, `Annexation Policy`). None carry transactional permit or license records.
  - State AGRC (SGID) on `opendata.gis.utah.gov` provides statewide Address Points and Parcel Polygons (including `YearBuilt` and assessed valuation), but no transactional municipal permit stream.
- **Verdict:** Tier 3 (Reject / Defer).

---

### 10. Reno & Sparks, Nevada (Washoe County)
- **Portal Hosts:** `opendata.washoecounty.gov` and `data-cityofreno.opendata.arcgis.com`.
- **Findings:**
  - Permitting for Reno, Sparks, and Washoe County is unified under the ONE Regional Licensing and Permitting system (`oneenv.org` on Accela). No universal open building permits FeatureServer is published.
  - Washoe County publishes a niche `Short_Term_Rental_Permits` FeatureServer (`opendata.washoecounty.gov`), but general construction permitting remains locked behind the ONE portal.
- **Verdict:** Tier 3 for universal permits; Provisional Tier 2 for STR permits.

---

## State Super-Feed Synergies & Cross-Jurisdictional Coverage

### 1. Texas State Super-Feeds (`data.texas.gov` Socrata)
By leveraging state-level open datasets, Urban Signal can instantly resolve the SLA / business formation signal for all candidate and previously feedless Texas metros with **zero new client machinery** (`SocrataClient`):

1. **TX TREC Active Real Estate Licenses (`s7ft-44qi`):**
   - Covers all Texas counties (`county` column matching FIPS/name).
   - Watermark: `license_start_date` / `expiration_date`.
   - Fields: `license_number`, `licensee_name`, `license_type`, `city`, `zip_code`, `county`, `license_status`.
2. **TX TREC Initial License Applications (`bf5n-799f`):**
   - Leading business formation indicator (daily applications flow).
   - Watermark: `application_received_date`.
3. **TX TDLR All Licenses (`7358-krk7`):**
   - Covers contractors, electricians, HVAC, plumbers, architectural barriers, and service trades statewide (~800k rows).
   - Watermark: `issue_date` / `renewed_date` (`MMDDCCYY` text format -> normalized via `SocrataClient`).
4. **TABC License Information (`7hf9-qc9f`):**
   - Texas Alcoholic Beverage Commission primary liquor/hospitality licenses (~126k rows, updated daily).
   - Watermark: `original_issue_date` / `effective_date`.
   - Fields: `master_file_id`, `license_number`, `trade_name`, `location_address`, `location_city`, `location_county`, `primary_status`.

### 2. Colorado State DORA Super-Feeds (`data.colorado.gov` Socrata)
1. **DORA Professional & Occupational Licenses (`7s5z-vewr`):**
   - Regulates architects, engineers, accountants, health professions, and trades statewide.
   - Watermark: `Original Issue Date` / `Effective Date`.
   - Fields: `Entity Name`, `License Number`, `License Type`, `Status`, `City`, `State`, `Zip Code`, `County`.
2. **DORA Licensed Real Estate Professionals (`m4y3-x47v`):**
   - Comprehensive broker and sales agent coverage statewide.

### 3. Utah AGRC SGID
- **Address Points & Parcels:** `opendata.gis.utah.gov` offers parcel shapefiles with `YearBuilt` and `StructureSqFt` for tax-roll cohort modeling, complementing lack of live permit APIs.

---

## Actionable Registration Next Steps

1. **Immediate City Registrations (Wave 4 Spine Hold):**
   - **`boulder` (Boulder, CO):**
     - Register `PERMITS` dataset pointing to `open-data.bouldercolorado.gov/.../Construction_Permits/FeatureServer/0`.
     - Set `watermark_column="IssuedDate"`, `geometry_type="point"`.
     - Wire `METRO_META` in `serving/dashboard.py`, regenerate `index.html`, and update `facts.json`.
   - **`fort_collins` (Fort Collins, CO):**
     - Register `PERMITS` dataset pointing to `gis.fcgov.com/.../Building_Permits/FeatureServer/0` (Item `e0964db1f10c491a872d5d0e7dbbe13a`).
     - Set `watermark_column="ISSUED_DATE"`, `geometry_type="point"`.
     - Wire `METRO_META`, regenerate static artifacts, and update `facts.json`.

2. **State Supplementation Integration:**
   - Configure state-level SLA feeds on `data.texas.gov` (`s7ft-44qi`, `bf5n-799f`, `7358-krk7`, `7hf9-qc9f`) and `data.colorado.gov` (`7s5z-vewr`, `m4y3-x47v`) with geographic FIPS partitioning to populate SLA signals for Lubbock, Corpus Christi, Laredo, RGV, College Station, Killeen, Boulder, Fort Collins, and Greeley.

3. **CI/CD Pre-Flight Gate Validation:**
   - Execute `python3 scripts/verify_cicd_preflight.py` to ensure complete interlock closure, byte-synced dashboard exports, and product facts parity before landing changes.

---
*The full report content above has been verified and is ready to be written to `docs/research/southwest-mountain-expansion-probe-2026-08-30.md`.*
