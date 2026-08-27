# Wave 3 Phase-0 probe — Phoenix, AZ

**Probe stamp: 2026-08-27.** Every host, dataset, watermark, and row below
was read live that day. Catalog `modified` / Hub `item.modified` is recorded
only as a label; **freshness evidence is always newest-row-by-watermark**.
This re-probe supersedes the 2026-08-24 CKAN-only skip in
`docs/research/nine-unidentified-metros-platform.md` (that pass never opened
the Planning & Development GIS REST folders).

Success criterion (Wave 3 / ADR 0004): live **and** (native geometry **or**
address-geocodable). Tiers: **1** live + native geocode; **2** live +
address-only; **3** stale / absent / wrong family.

## Platform

| Host | What it is | Probe |
|---|---|---|
| `phoenixopendata.com` / `www.phoenixopendata.com` | **CKAN 2.9.11** (OpenGov theme; `datastore`, `ags_fs_view`, `ags_ms_view`, `dcat`) | `GET /api/3/action/status_show` → `ckan_version=2.9.11`; `package_list` **158** names |
| same host `/api/search/v1` and `/api/v3/views.json` | not ArcGIS Hub, not Socrata | both **404** — this is the 2026-08 Hub-API miss |
| `egishub-phoenix.hub.arcgis.com` | ArcGIS Hub, GIS catalog | dataset collection `numberMatched=129`; family searches do not surface transactional permits/311/SLA/deeds |
| `mapportal.phoenix.gov/pds` and `maps.phoenix.gov/pds` | ArcGIS Server **11.3** (Planning & Development) | folders `PDD`, `ShapePHX`, `Hosted` |
| `maps.phoenix.gov/pub` | public ArcGIS Server **11.3** | folder `Public`, 179 services including `Planning_Permit`, `LIQUOR_RACMap` |
| `phxatyourservice.dynamics365portals.us` | **myPHX311** (Dynamics 365 CRM) | resident portal; no bulk REST / Open311 found |

Phoenix is **CKAN (catalog) + ArcGIS Server (the live layers)**. No Socrata
domain. The existing `ArcGISClient` (`outSR=4326`) covers every Tier 1 hit; no
fifth client is required.

## Summary

| Family | Dataset | Newest watermark | Geocode | 30-day window | Tier |
|---|---|---|---|---|---|
| **PERMITS** | `Public/Planning_Permit/MapServer/1` ("Permits") | `PER_ISSUE_DATE` = **2026-08-26** | native point (`outSR=4326`); `STREET_FULL_NAME` on 67,857 / 68,376 | **986** issued ≥ 2026-07-28 | **1** |
| **PERMITS** (companion) | `ShapePHX/ShapePHXPermitsPoints_DL/MapServer/0` | `PERMIT_ISSUE_DATE` = **2026-08-19** | native point (`outSR=4326`); `ADDRESS` **0 / 14,821** | **1,678** issued ≥ 2026-07-28 | **1** |
| **311** | none (police CFS is the live near-miss) | — | — | — | **3** |
| **SLA** | `ShapePHX/ShapePHX_Short_Term_Rentals/MapServer/0` | `ISSUED_DATE` = **2026-08-19** | native `LATITUDE`/`LONGITUDE` + point; `PROPERTY_ADDRESS` 2,273 / 2,273 | **111** issued ≥ 2026-07-28 | **1** |
| **DEEDS** | none registrable | — | — | — | **3** |

**Wave-3-ready: yes, as a partial metro** (PERMITS + SLA/STR). Same shape as
Honolulu / Orlando / Austin: register what is live; `get_dataset()` raises for
311 and deeds. Do **not** register the frozen non-`_DL` ShapePHX permits layer
or the CKAN SOCDS annual aggregate.

## Method

CKAN `package_search` + full `package_list` (158 names) for the four family
keywords. ArcGIS Hub dataset search on `egishub-phoenix`. REST directory walks
of `mapportal.phoenix.gov/pds`, `maps.phoenix.gov/pds`, `maps.phoenix.gov/pub`.
For every survivor: layer metadata, `returnCountOnly`, `outStatistics` min/max
on the date field, `orderByFields=<watermark> DESC` with `outSR=4326`, and a
`DATE '2026-07-28'` window count. Date filters used Esri `DATE '…'` literals
(epoch-ms `where` clauses 400 on the ShapePHX service).

## Permits — Tier 1 (register)

Two live layers, complementary type mixes. Register both (primary +
`companion_endpoints`), matching Montgomery / Orlando companion pattern.

### Primary — `Public/Planning_Permit` layer 1

- **URL:** `https://maps.phoenix.gov/pub/rest/services/Public/Planning_Permit/MapServer/1`
- **Platform:** ArcGIS MapServer (Server 11.3), `maxRecordCount=2000`,
  `geometryType=esriGeometryPoint`, WKID 3857 native → WGS84 via client
  `outSR=4326`.
- **Rows:** 68,376 (DONE 41,302 / OPEN 26,997 / EXPR 60 / VOID 17).
- **Watermark:** `PER_ISSUE_DATE` (esriFieldTypeDate). Newest **2026-08-26
  16:16 UTC**; oldest 2015-01-06. `PER_ENT_DATE` max same day (plan-review
  intake). **986** issued in the 30 days to 2026-08-27; **12,559** issued in
  2026 YTD.
- **Columns (layer):** `OBJECTID`, `PER_TYPE`, `PER_NUM`, `PROJECT`,
  `PERMIT_NAME`, `PERMIT_STAT`, `PER_ENT_DATE`, `PER_ISSUE_DATE`,
  `PER_EXPIRE_DATE`, `PER_COMPL_DATE`, `STREET_FULL_NAME`, `PROFESS_NAME`,
  `PERMIT_LEAD`, `PID`, `PER_TYPE_DESC`, `MOD_DESC`, `SCOPE_CODE`,
  `SCOPE_DESC`, `SHAPE`.
- **Geocoding:** 0 null geometries. Sample WGS84 (−112.005, 33.394) is inside
  Phoenix. `STREET_FULL_NAME` blank on 519 rows (0.76%). Native path; no
  `needs_geocode`.
- **Cadence:** daily (newest issue date = probe-day minus one).
  `expected_cadence_days: 1`.
- **Scope caveat:** 30-day issued mix is solar OTC, structural/MEP, fire
  sprinkler, water, signs, site, civil — a **Planning & Development** permit
  universe, not housing-only. That is the right family, not a defect.
- **Ids:** `PER_NUM` + `PID` + `OBJECTID`.

### Companion — `ShapePHXPermitsPoints_DL`

- **URL:** `https://mapportal.phoenix.gov/pds/rest/services/ShapePHX/ShapePHXPermitsPoints_DL/MapServer/0`
- **Service description:** "derived from ShapePHX, and updated on a weekly
  basis."
- **Rows:** 14,821, **all `STATUS=Issued`**. Date range 2024-08-19 →
  2026-08-19. **1,678** issued ≥ 2026-07-28; **8,568** in 2026 YTD.
- **Watermark:** `PERMIT_ISSUE_DATE`. Newest **2026-08-19** (≈8 calendar-day
  lag, consistent with weekly). `LASTMODIFIEDDATE` is a string and was null
  on the newest page — do not watermark on it.
- **Geocoding:** 0 null geometries; `outSR=4326` sample (−112.051, 33.568).
  **`ADDRESS` is null on every row** (14,821 / 14,821); `APN` also null on
  the newest page. Geometry-only; still Tier 1.
- **Scope:** ShapePHX (the April 2026 PDD portal) Issued permits — residential
  new/standard homes, electrical quick-permits, solar, demolition, commercial
  miscellaneous. Complements layer 1's solar/fire/civil mix.
- **Do not register** `ShapePHX/ShapePHXPermitsPoints/MapServer/0` (no `_DL`):
  3,734 rows, newest `PERMIT_ISSUE_DATE` **2022-06-29**, despite the same
  "updated weekly" blurb. Row-level freeze.

### Rejected permit lookalikes

| Item | Why not |
|---|---|
| CKAN `phoenix-az-building-permit-data` (`1c61b4b2-…`) | SOCDS **annual aggregate**, 22 rows, newest **year=2021** |
| `Public/Planning_Permit/MapServer/0` "Plan Review" | intake/revisions, not issued building permits (though `PER_ENT_DATE` is live 2026-08-27) |
| `ShapePHX_Application_Points` | zoning / historic / site-plan **applications**; `CREATED_DATE` live 2026-08-18 |
| `PDD/Permits_20xx_Annual_Report`, `Permit_Annual_Plan` | annual/outdated plan layers |

## 311 — Tier 3 (do not register)

No citizen 311 dataset exists on CKAN (zero `package_list` hits for `311`,
`myphx`, `seeclickfix`) or on the Hub dataset collection. myPHX311 is a
Dynamics 365 portal (`phxatyourservice.dynamics365portals.us`) with no public
bulk API / Open311.

Near-misses, explicitly **not** 311:

| Item | Evidence | Why not 311 |
|---|---|---|
| CKAN `calls-for-service` 2026 resource `ed707785-26b6-4949-9b04-5700b8a0125c` | datastore 446,406 rows; `CALL_RECEIVED` max **2026-08-19 12:59** (text `MM/DD/YYYY`; notes say daily by 11:00, through ~7 days prior) | **Police 911 dispatch.** Columns: `INCIDENT_NUM`, `DISP_CODE`, `FINAL_CALL_TYPE`, `HUNDREDBLOCKADDR`, `GRID`. Hundred-block only, no lat/lng. Notes: "citizen-generated dispatched calls for police service." |
| CKAN `property-maintenance` `51cdfdd8-…` | 99,645 rows; file `last_modified` 2026-08-01; columns `CSM_CASENO`, `CSM_ADDRESS`, `CSM_STATUS`, `NOTES` | Neighborhood Services **code-enforcement cases**, monthly snapshot, **no date column**. Address-only. Not a 311 request stream. |

## SLA — Tier 1 STR (register); liquor snapshot skip

### Register — ShapePHX Short Term Rentals

- **URL:** `https://mapportal.phoenix.gov/pds/rest/services/ShapePHX/ShapePHX_Short_Term_Rentals/MapServer/0`
- **Rows:** 2,273 current (Operational 2,261 / Issued-pending 12).
- **Watermark:** `ISSUED_DATE`. Newest **2026-08-19** (weekly, same ShapePHX
  cadence); min 2024-12-20. **111** issued ≥ 2026-07-28; **1,425** in 2026
  YTD. `EXPIRATION_DATE` range 2026-09-19 → 2027-09-04.
- **Geocoding:** 0 null `LATITUDE`; 0 blank `PROPERTY_ADDRESS`. Native
  lat/lng **and** point geometry (`outSR=4326` sample −112.077, 33.621).
  Address strings carry a trailing ` (Active)` that the ADR 0004 normalizer
  should strip if the address path is ever used.
- **Ids:** `NAME` (e.g. `STR-2026-002954`) + `ID` + `OBJECTID`.
- **Precedent:** Orlando STR as SLA companion (`ssrj-rbua`). Phoenix has no
  broader business-tax feed, so STR **is** the SLA registration (narrow,
  notifications-grade), not a companion.

### Skip — liquor (`Public/LIQUOR_RACMap`)

Hourly-updated point layers split by license series
(`LICENSE SERIES 1` … `18`). Sample series-4 row is live, WGS84
(−112.073, 33.410), `LICENSE_STATUS=ACTIVE`, `BUSINESS_ADDRESS` present.
**No date column** (no issue / expiry / received). `returnCountOnly` is
unreliable (scale / definition query). Same failure mode as Denver active
licenses (skip) rather than Milwaukee liquor (had `EXP_DATE`). Do not
register; do not use snapshot mode to invent a watermark.

CKAN has **zero** license / privilege-tax / business-tax packages.

## Deeds — Tier 3 (do not register)

| Candidate | Row-level result |
|---|---|
| CKAN | no deed/sale/recorder packages (name filter empty; `city-parcels` is a boundary layer) |
| `Public/COUNTY_PARCELS` | 1,759,743 polygons; owner/address only; **no sale/deed date** |
| AGO `Maricopa_County_Parcels_for_Apps` (`services1.arcgis.com/ypdMhhEhrtBXLtQv/…/FeatureServer/0`) | 74,693-row **subset**; `DEED_DATE` newest real value **2025-09-30**; **0** rows with `DEED_DATE` in 2026; `SALE_PRICE` null on that page; `dataLastEditDate` 2025-10-09. Last-sale parcel snapshot, frozen. Future sentinel `DEED_DATE` exists (year-2099) — any later consumer must exclude it. |
| Maricopa Assessor **Sales Affidavits** ZIP (AGO item `f3484c72a938497286adc4e5de7e9963`) | CSV Collection, ~61 MB, "updated weekly", `hasApi: false`. `item.modified` **2026-08-03** (catalog only — not a row read). Pipe-delimited last-recorded sale file with parcel address / grantor / grantee / sale date / price / deed number. **No queryable watermark this probe** (anonymous REST is a binary ZIP, not a FeatureServer). Treat as a future CSV-client candidate, not a Wave-3 registration. Assessor parcel-search API is **token-gated**. |

County GIS `gis.mcassessor.maricopa.gov` `MaricopaDynamicQueryService` parcels
are scale-restricted reference layers, not a sales stream.

## Registration contract (`phoenix`)

Partial city. Spine copies these as `DatasetSpec` data; this file is the
probe, not the implementation. Re-probe ≤ 72 h before the city stream
claims (roadmap §5.3).

| City (`job_suffix`) | Feeds → datasets (watermark) | Platform | field_map budget | Quirks tests must pin |
|---|---|---|---|---|
| **Phoenix** `phoenix` | PERMITS `Public/Planning_Permit/MapServer/1` (`PER_ISSUE_DATE`) · companion `ShapePHX/ShapePHXPermitsPoints_DL/MapServer/0` (`PERMIT_ISSUE_DATE`) · SLA `ShapePHX/ShapePHX_Short_Term_Rentals/MapServer/0` (`ISSUED_DATE`) | arcgis ×2–3 | ~8 | `ArcGISClient` `outSR=4326` on WKID 2868/3857; ShapePHX `ADDRESS` always null (geometry-only); ShapePHX + STR weekly (`expected_cadence_days: 7`); Planning_Permit daily; STR `PROPERTY_ADDRESS` suffix ` (Active)`; **do not** point at non-`_DL` ShapePHX permits (frozen 2022-06-29); 311/DEEDS absent (`get_dataset` raises) |

Suggested spec payloads (leaf `cities/phoenix.py`, not applied this ticket):

```
PERMITS
  endpoint: https://maps.phoenix.gov/pub/rest/services/Public/Planning_Permit/MapServer/1
  platform: arcgis
  watermark_col: PER_ISSUE_DATE
  id_keys: [PER_NUM, PID, OBJECTID]
  extra:
    expected_cadence_days: 1
    oid_field: OBJECTID
    max_record_count: 2000
    companion_endpoints:
      shapephx_issued: https://mapportal.phoenix.gov/pds/rest/services/ShapePHX/ShapePHXPermitsPoints_DL/MapServer/0
    field_map:
      job_id: [PER_NUM, PID, OBJECTID]
      issuance_date: [PER_ISSUE_DATE]
      filing_date: [PER_ENT_DATE]
      status: [PERMIT_STAT]
      job_type: [PER_TYPE_DESC, SCOPE_DESC, PER_TYPE]
      address_street: [STREET_FULL_NAME]
      # lat/lng from geometry; ShapePHX companion: PERMIT_NUMBER / PERMIT_ISSUE_DATE / PERMIT_TYPE

SLA
  endpoint: https://mapportal.phoenix.gov/pds/rest/services/ShapePHX/ShapePHX_Short_Term_Rentals/MapServer/0
  platform: arcgis
  watermark_col: ISSUED_DATE
  id_keys: [NAME, ID, OBJECTID]
  extra:
    expected_cadence_days: 7
    oid_field: OBJECTID
    max_record_count: 2000
    field_map:
      license_id: [NAME, ID]
      license_type: [REGISTRATION_TYPE]
      effective_date: [ISSUED_DATE]
      expiration_date: [EXPIRATION_DATE]
      dba: [POW_NAME]
      latitude: [LATITUDE]
      longitude: [LONGITUDE]
      address_street: [PROPERTY_ADDRESS]
```

`needs_geocode` is **false** on both registered families (native points /
lat-lng). G5 ≥ 99% on geometry; G8 null-H3 share should be ~0.

## Correction to the 2026-08-24 survey

`nine-unidentified-metros-platform.md` concluded "Phoenix — register none"
after a CKAN keyword search (SOCDS aggregate, police CFS, no licenses/deeds).
That catalog reading is still true **of CKAN**. It missed:

1. `maps.phoenix.gov/pub` `Planning_Permit` (daily, live 2026-08-26).
2. `mapportal.phoenix.gov` `ShapePHXPermitsPoints_DL` (weekly Issued, live
   2026-08-19) vs the frozen non-`_DL` twin.
3. ShapePHX STR licenses (weekly, live 2026-08-19).

Hub API 404 on `phoenixopendata.com` is expected: the site is CKAN, not Hub.
`egishub-phoenix.hub.arcgis.com` answers but is not where the transactional
layers live.
