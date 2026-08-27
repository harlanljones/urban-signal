# Wave 3 probe — Miami-Dade County, FL

**Date of probe: 2026-08-27.** Every watermark, count, and schema line below
is a row-level read from that day. Catalog `modified` was not used as
evidence. City of Miami `gis.miamigov.com` was skipped (host timeout,
fingerprint). Broward / Fort Lauderdale are sibling streams — not probed
here.

Parent ticket: US-199. Stream: `probe-miami-dade`.

## Headline

**Wave-3-ready: yes, as a partial county metro (3 of 4 families).** Permits
are live and address-geocodable (Tier 2). Local business tax and property-
appraiser last-sale points are live and natively geocoded (Tier 1). There is
**no anonymously queryable current 311** — public year-slices stop at 2023;
`data_311_2024` exists but returns `Token Required`.

| Family | Tier | Layer | Newest-row watermark | Geocode path |
|---|---|---|---|---|
| Permits | **2** | `miamidade_permit_data/FeatureServer/0` | `PermitIssuedDate` **2026-08-25** (DateOnly) | address-only `PropertyAddress` → ADR 0004 (`needs_geocode=True`). No geometry. |
| 311 | **3** | Hub `data_311_YYYY` 2013–2023; 2024 token-gated | 2023 slice newest created **2023-12-31** / timezone-edge 2024-01-01; **0** rows in 2026 | Archive has native `latitude`/`longitude` attrs (99.3%) but is frozen. Live 2024 is not public. |
| SLA | **1** | `Local_Business_Tax_Feature_Layer_View/FeatureServer/0` | Current-year snapshot, all **193,868** rows `YEAR=2026`; newest `BUSSDATE` **2026-09-29** (future start) | Native point geometry + `LAT`/`LON` **100%**. |
| Deeds | **1** | `MD_ComparableSales/MapServer/5` (`MDC.PaGis`) | `DOS_1` **20260821** (YYYYMMDD); newest market ≥$10k **20260817** | Native point; query `outSR=4326`. Last-sale-on-parcel, not a deed stream. |

Register permits + SLA + deeds. Do not register live 311. City of Miami
municipal GIS was not reached; this contract is Miami-Dade County only
(ADR 0007 — sibling streams own Broward / Fort Lauderdale / City of Miami).

## Platform

| Surface | Result 2026-08-27 |
|---|---|
| ArcGIS Hub | Live: `https://opendata.miamidade.gov/` and `https://gis-mdc.opendata.arcgis.com/`. Search `GET /api/search/v1/collections/dataset/items?q=…` returns GeoJSON items. Hosted services live under AGOL org `8Pc9XBTAsYuxx9Ny`. |
| DCAT / data.json | Both URLs return HTTP 200 (fingerprint) but the JSON bodies are truncated / unparseable (`Expecting ',' delimiter` ~2.1–2.5 MB). Discovery used Hub search v1, not the broken catalogs. |
| Socrata | Not retried. Fingerprint: `api.us.socrata.com` → Domain not found for `opendata.miamidade.gov`. |
| CKAN | Not retried. Fingerprint: `/api/3/action/status_show` 404. |
| ArcGIS Server 11.1 | `https://gisweb.miamidade.gov/ArcGIS/rest/services`. Folders include `311` (empty — no services), `EnerGov`, `LandManagement`, `RER`, `CommunityServices`, `EAMS`. Root services include `BusinessTracker` and `MD_ComparableSales`. |
| `gis.miamigov.com` | Skipped (timeout). |

Existing `ArcGISClient` covers every live layer below. No new platform
client.

## Method

Hub dataset search for `permit`, `building permit`, `311`, `service request`,
`license`, `occupational`, `business license`, `local business tax`,
`certificate of use`, `deed`, `sales`, `property sales`, `parcel`, plus
`csr` / `seeclickfix` / `open311` (all zero). Candidate FeatureServers and
the `EnerGov` / `311` / `RER` / `LandManagement` / `CommunityServices` /
`EAMS` REST folders were then queried: layer metadata, `returnCountOnly`,
`orderByFields=<watermark> DESC&resultRecordCount=1` with `outSR=4326`,
and recent-window counts. Newest-row dates are the evidence; Hub item
`modified` was ignored.

## Permits — Tier 2 (live, address-only)

**Dataset:** "Building Permits Issued By Miami-Dade County - 2 Previous Years
to Present" (Hub item `6db5f56e886446df88313ca279e59120`).

- **Endpoint:** `https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/miamidade_permit_data/FeatureServer/0`
- **Type:** non-spatial **Table** (`geometryType` null). `maxRecordCount` 1000. `objectIdField` = `ObjectId`.
- **Rows:** 139,586. Title is honest: oldest `PermitIssuedDate` **2024-08-26**, newest **2026-08-25** — a rolling ~2-year issued window, not a full archive.
- **Watermark:** `PermitIssuedDate` (`esriFieldTypeDateOnly`, `YYYY-MM-DD`). Detroit-style DateOnly; lexical/`DATE` filters both work. Companions: `ApplicationDate` (epoch date, newest 2026-08-25), `LastInspectionDate` (newest **2026-08-26**).
- **Recent window:** 46,190 issued YTD 2026; 5,928 in the 30 days before the probe. 39,743 applications YTD.
- **Schema (useful):** `PermitNumber`, `ProcessNumber`, `MasterPermitNumber`, `PermitType` (`BLDG`/`PLUM`/`MECH`/…), `ResidentialCommercial`, `EstimatedValue` (string), `ApplicationTypeDescription`, `ProposedUseDescription`, `FolioNumber`, `PropertyAddress`, `City`, `State`, `OwnerName`, `SquareFootage`, `StructureUnits`, `StructureFloors`, inspection dates, `PermitTotalFee`.
- **Geocoding:** no lat/lng, no geometry. `PropertyAddress` present on 138,886 / 139,586 (**99.5%**); same 700 rows lack folio. Compose `PropertyAddress` + `City` + `FL` via ADR 0004 (`needs_geocode=True`, `geocode_context="Miami-Dade County, FL"`). Optional later upgrade: `parcel_join` on `FolioNumber` → PaGIS `FOLIO` (out of the G1 geocoder path; not required).
- **Not the permit register:** Hub "Tbl Bldg Permit Prop Use / App Type" are code tables. DERM/wetland/well permit layers are environmental subsets. EnerGov `MD_LandMgtEditing/FeatureServer/3` "Spatial Collection Points" has **4** generic rows (`NAME`/`DESCRIPTION`) — not permits. `certif_of_occupancy_daily_data` is a live CO table (newest `ISSUE_DATE` **2026-08-26**, 146,320 rows, address-only) — companion to permits, not a substitute.

**Verdict:** register as `FeedType.PERMITS`, platform `arcgis`,
`needs_geocode=True`.

## 311 — Tier 3 (stale public slices; current year gated)

Hub publishes one FeatureServer **table** per calendar year, 2013–2023
(`data_311_2013` … `data_311_2023`). No Hub hit for 2024/2025/2026 titles.
`csr` / `seeclickfix` / `open311` matched 0.

| Slice | URL | Public? | Newest created (row-level) |
|---|---|---|---|
| 2023 | `…/data_311_2023/FeatureServer/0` | yes | **2023-12-31** (one timezone-edge row `2024-01-01T04:57Z`); 343,851 rows; **0** created in 2026 |
| 2024 | `…/data_311_2024/FeatureServer` | **no** — `{code: 499, message: "Token Required"}` | not readable anonymously |
| 2025, 2026 | same URL pattern | **no** — `{code: 400, Invalid URL}` | do not exist |

2023 schema is otherwise product-shaped: `ticket_id`, `issue_type`,
`ticket_created_date_time` / `ticket__last_update_date_time` /
`ticket_closed_date_time`, `ticket_status`, `street_address`, native
`latitude`/`longitude` (341,559 / 343,851 = **99.3%**; also State-Plane
`sr_xcoordinate`/`sr_ycoordinate`). Non-spatial table — coordinates are
attributes, not Esri geometry. That would have been Tier 1 if the current
year were public.

`gisweb.miamidade.gov/ArcGIS/rest/services/311` is an **empty folder** (no
services). Root `CAD911` is 911 CAD, not 311. `animal_services` is a
separate table, not a general SR feed.

**Verdict:** do not register live 311. Year-sliced 2013–2023 is a backfill
corpus only; `endpoint_by_year` cannot roll to 2024 without a token. Revisit
if the 2024 service is published anonymously.

## SLA — Tier 1 (live current-year occupational register, native points)

**Primary:** "Local Business Tax - View" (Hub item `fba37cce964e4c55bd6a1614c6f789a0`).

- **Endpoint:** `https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/Local_Business_Tax_Feature_Layer_View/FeatureServer/0`
- **Twin (same 193,868 rows, `maxRecordCount` 1000):** `https://gisweb.miamidade.gov/ArcGIS/rest/services/BusinessTracker/MapServer/0` — prefer the Hub view (`maxRecordCount` **16000**).
- **Geometry:** point, Web Mercator extent; `outSR=4326` returns WGS84. Attribute `LAT`/`LON` on **193,868 / 193,868**.
- **Snapshot shape:** every row has `YEAR=2026`; 178,336 `ACCSTATUS='Active'`. This is the current local-business-tax / occupational roll, not an incremental issuance log. `ingestion_mode="snapshot"`.
- **Dates:** `BUSSDATE` (business start) and `BUSCDATE` (close). Newest start **2026-09-29** (future-dated new business). Starts by month 2026: Jan–Jun 688–1008/mo, then **27 in July, 10 in August, 3 in September** — new-start intake lags, but the year-roll itself is current. 5,060 starts YTD; 8,078 closes YTD.
- **Schema:** `ACCOUNTNO`, `RECEIPTNO`, `BUSNAME`, `OWNERNAME`, `BUSADDR`/`BUSCITY`/`ZIPCODE`, `CLASSCODE`/`CLASSDESC`/`CATGRYNAME`/`OCCDESC`/`BUSNAICSCD`, `FOLIO`, `PAIDSTATUS`, `NEWBUS`, `GEOADDR`.

**Companion (optional incremental):** "Certificates of Use Issued by
Miami-Dade County - Jan 2003 to present"
(`CertificateOfUse_New_gdb/FeatureServer/0`, item `1952228619b0463cb6f9f7dc839bff88`).
147,074 points, `USER_ISSUED_DATE` newest **2026-08-21**, 1,703 issued YTD /
184 in 30 days / ~200 per month May–August, native `X`/`Y` 100%. Zoning CU,
not the occupational tax roll — wire as `companion_endpoints` if the SLA
producer wants an issuance stream.

Hub `q=license` / `q=business license` did not find this layer; the hit was
`q=local business tax`. Occupational licenses are the county Local Business
Tax, not a liquor-only register.

**Verdict:** register LBT as `FeedType.SLA`, native geocode, snapshot mode.

## Deeds — Tier 1 (live last-sale points, native geometry)

Two copies of the Property Appraiser point universe (~943k rows):

| Copy | Endpoint | Sale watermark | Extra fields |
|---|---|---|---|
| **gisweb (register this)** | `https://gisweb.miamidade.gov/ArcGIS/rest/services/MD_ComparableSales/MapServer/5` (`MDC.PaGis`) | `DOS_1` string `YYYYMMDD`, newest **20260821** | `GRANTOR_1`/`GRANTEE_1`, `OR_BK_1`/`OR_PG_1`, `PRICE_1`, `QU_FLG_1` (Q/U), plus `DOS_2`/`DOS_3` history slots |
| Hub view (staler) | `PaGISView_gdb/FeatureServer/0` (item `bf92e51f90a8426cae904ebc15018067`) | `DATEOFSALE_UTC` newest market **2026-08-03**; Aug 2026 count 13 vs gisweb 37 | `DOS_1`/`PRICE_1` only — no grantor/book |

- **Rows:** 943,254 (gisweb). Point geometry; layer native SR is Florida East
  State Plane (`wkid` 102658 / 2236). `outSR=4326` returns lon/lat (verified
  on the newest rows). `maxRecordCount` **20000**. `supportsPagination` true.
  Metadata `objectIdField` is null; the OID column is still `OBJECTID` —
  set `oid_field="OBJECTID"` explicitly.
- **Watermark:** `DOS_1` text `YYYYMMDD` (ADR 0005: `watermark_type="text"`,
  `watermark_format="%Y%m%d"`). Newest row 2026-08-21 is a $100 unqualified
  transfer; newest market `PRICE_1 >= 10000` is **20260817** ($700,100). A
  qualified (`QU_FLG_1='Q'`) $385,000 sale landed **20260812**.
- **Volume / lag:** ~4.2k–6.4k last-sales/month Jan–Jun 2026, then assessor
  lag (July 439, August 37 on gisweb). That is current-month processing lag
  on a live PA extract, not a dead feed. `PRICE_1 >= 10000` on 588k of the
  Hub twin; many recent official-record rows are $0/$100 `QU_FLG_1='U'`.
- **What it is:** last sale (plus two prior slots) **on the current parcel**,
  not an ACRIS-style recorded-document stream. Multi-sale parcels keep at
  most three. Filter `PRICE_1 >= 10000` and/or `QU_FLG_1='Q'` for the market
  signal. `TRUE_SITE_ADDR` is occasionally null on condo/folio rows; geometry
  is still present.
- **Not deeds:** `Parcelpoly_gdb` / gisweb `Parcel_poly` are cadastral
  polygons (`EDIT_DATE` 2026-08-20) with no sale amount. `PaParcelView` has
  `DOS_1`/`PRICE_1` as strings on polygons but no `DATEOFSALE_UTC`. Prefer
  the point layer.

**Verdict:** register gisweb `MapServer/5` as `FeedType.DEEDS`, native
geocode, text watermark on `DOS_1`. Snapshot-or-incremental both work;
incremental on `DOS_1` will see new last-sales as parcels update.

## REST folders that looked like hits and were not

| Folder / service | Finding |
|---|---|
| `311/` | Empty. |
| `EnerGov/MD_LandMgtEditing` | Edit workspace; point layer has 4 rows. Not permits. |
| `EnerGov/MD_LandMgtViewer` | Zoning / PA parcels / urban-center overlays. No permit table. |
| `RER/` | `MD_EELVolRegistration` only. |
| `EAMS/` | Stormwater / pavement inventory. |
| `MD_EAMSCodeEnforcement` | Address + parcel basemap, no case table. |
| `LandManagement/` | CDMP / zoning / platting. |
| `CommunityServices/MD_Parcel` | `GeoAddress` + `PAParcel` polygons, no sales. |

## Registration contract (`miami_dade`, partial)

Spine is **not** applied in this stream. Sketch for the interlock holder.
City identity is Miami-Dade **County**; do not fold Broward or the City of
Miami into this `CityId` (ADR 0007).

```python
# PERMITS — Tier 2
DatasetSpec(
    endpoint="https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/miamidade_permit_data/FeatureServer/0",
    platform="arcgis",
    watermark_col="PermitIssuedDate",
    id_keys=["PermitNumber", "ProcessNumber", "ObjectId"],
    producer_key="permits",
    needs_geocode=True,
    geocode_context="Miami-Dade County, FL",
    oid_field="ObjectId",
    max_record_count=1000,
    expected_cadence_days=1,
    non_spatial=True,
    rolling_window_days=730,  # titled "2 Previous Years to Present"
    field_map={
        "job_id": ["PermitNumber"],
        "job_type": ["PermitType", "ApplicationTypeDescription"],
        "cost": ["EstimatedValue"],
        "issued_date": ["PermitIssuedDate"],
        "filing_date": ["ApplicationDate"],
        "incident_address": ["PropertyAddress"],
        "borough": ["City"],
        "bbl": ["FolioNumber"],
    },
)

# SLA — Tier 1 snapshot
DatasetSpec(
    endpoint="https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/Local_Business_Tax_Feature_Layer_View/FeatureServer/0",
    platform="arcgis",
    watermark_col="BUSSDATE",
    id_keys=["ACCOUNTNO", "RECEIPTNO", "OBJECTID"],
    producer_key="sla",
    ingestion_mode="snapshot",
    oid_field="OBJECTID",
    max_record_count=16000,
    expected_cadence_days=30,
    companion_endpoints={
        "certificate_of_use": "https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/CertificateOfUse_New_gdb/FeatureServer/0",
        "enterprise_twin": "https://gisweb.miamidade.gov/ArcGIS/rest/services/BusinessTracker/MapServer/0",
    },
    field_map={
        "license_id": ["ACCOUNTNO"],
        "dba": ["BUSNAME"],
        "premises_name": ["OWNERNAME"],
        "license_type": ["CLASSDESC", "CATGRYNAME", "OCCDESC"],
        "effective_date": ["BUSSDATE"],
        "address_street": ["BUSADDR"],
        "latitude": ["LAT"],
        "longitude": ["LON"],
    },
)

# DEEDS — Tier 1 last-sale points
DatasetSpec(
    endpoint="https://gisweb.miamidade.gov/ArcGIS/rest/services/MD_ComparableSales/MapServer/5",
    platform="arcgis",
    watermark_col="DOS_1",
    watermark_type="text",
    watermark_format="%Y%m%d",
    id_keys=["FOLIO", "OR_BK_1", "OR_PG_1", "OBJECTID"],
    producer_key="deeds",
    where="PRICE_1 >= 10000",  # drop $0/$100 non-market; tighten to QU_FLG_1='Q' if G5/G8 need it
    oid_field="OBJECTID",
    max_record_count=20000,
    expected_cadence_days=7,
    field_map={
        "doc_id": ["OR_BK_1", "OR_PG_1", "FOLIO"],
        "bbl": ["FOLIO"],
        "document_amount": ["PRICE_1"],
        "recorded_date": ["DOS_1"],
        "party1_grantor": ["GRANTOR_1"],
        "party2_grantee": ["GRANTEE_1"],
        "incident_address": ["TRUE_SITE_ADDR"],
        "zipcode": ["TRUE_SITE_ZIP_CODE"],
    },
)
```

Gates: permits G5 floor is 95% for address-geocoded feeds (ADR 0004 / Wave 3);
99.5% of rows carry `PropertyAddress`. SLA/deeds are native-geocode; G8
null-H3 should be ~0 for LBT and ~geometry-present for PaGis. Deeds
`where=PRICE_1 >= 10000` is the market-volume filter; document it so G8 is
not blamed on $0 transfers. Permits rolling 2-year window: declare
`rolling_window_days=730` so the staleness probe does not expect a deep
archive.

## Wave-3-ready

**Yes — partial.** Three live families on the existing ArcGIS client; 311
blocked on a token. Implementation is a leaf `cities/miami_dade.py` plus a
serial spine hold (`CityId`, aliases, `REGISTRY`, three endpoint settings,
field maps). Do not wait on 311.
