# Wave 3 Phase-0 probe — Broward County, FL

**Date of probe: 2026-08-27.** Every host, dataset, watermark, and row below
was read live that day. Hub `item.modified` / catalog `modified` is a label
only; **freshness evidence is newest-row-by-watermark**. Linear **US-199**
sub-stream `.streams/probe-broward.md`. County leaf — does not replace the
Fort Lauderdale or Miami-Dade probes.

Success criterion (Wave 3 / ADR 0004): live **and** (native geometry **or**
address-geocodable). Tiers: **1** live + native geocode; **2** live +
address-only; **3** stale / absent / wrong family.

## Headline

**Wave-3-ready: yes, as a partial county metro (SLA only).** Same Austin / LA
/ Honolulu shape: register the live family; `get_dataset()` raises for
permits, 311, and deeds. Per ADR 0007 this is a **separate `CityId`
(`broward`)**, not a division bolted onto Fort Lauderdale.

Fort Lauderdale municipal permits / 311 / SLA are frozen (sibling probe).
County GeoHub publishes a **live local-business-tax point extract** that
already contains ~20k Fort Lauderdale rows. It does **not** substitute for
municipal building permits. County last-sale-on-parcel is stale at row
level; the live Broward-shaped sales layer sits on **city of Fort Lauderdale
GIS**, not on this catalog.

| Family | Tier | Layer | Newest-row watermark | Geocode path |
|---|---|---|---|---|
| Permits | **3** | none registrable (building). Near-miss: `HCEDPossePermitsRef/FeatureServer/4` | ROW/utility `ISSUEDATE` **2026-08-26** (wrong family) | native point + `JOBADDRESS` |
| 311 | **3** | none | — | — |
| SLA | **1** | `BrowardLocalTaxBusinessesEmailPhone/FeatureServer/0` (twin `TaxDatabase2021/0`) | `Business_Start_Date` **2026-09-07** (future-dated start; 35 rows ≥ 2026-08-20) | native point (`outSR=4326`); 3.25% null-shape tail |
| Deeds | **3** | BCPA `PARCEL_POLY_BCPA_TAXROLL/0`; FDOR 2025 centroids `CO_NO=16` | last sale **2024-09-27** (BCPA); annual 2025 NAL (FDOR) | native polygon / centroid — snapshot, not a stream |

## Platform

Fingerprint (dead hosts confirmed once; not retried):

| Surface | Probe 2026-08-27 |
|---|---|
| `https://geohub-bcgis.opendata.arcgis.com/` | **LIVE** Hub HTML 200. Title "Broward County GeoHub". Org `JMAJrTsHNLrSsWf5` (`services.arcgis.com/JMAJrTsHNLrSsWf5`). |
| Hub search `/api/search/v1` | **LIVE** JSON 200. Dataset collection `numberMatched=123`; `all` collection **477**. |
| `/data.json` | HTTP **500** |
| `/api/feed/dcat-us/1.1.json` | HTTP 200, truncated / unparseable. Not used as evidence. |
| `/api/feed/dcat-ap/2.0.1.json` | HTTP **502** |
| `www.broward.org/OpenData` | **404** |
| `opendata.broward.org`, `data.broward.org` | **DNS fail** |
| `gis.broward.org` | **connection refused** |
| `bcgishub.broward.org` | **LIVE** ArcGIS Enterprise. Bare `curl` on `/server/rest/services` returns **403**; a browser `User-Agent` returns 200. Folders include `311` (empty), `BCPA`, `QAlert`, `POSSE`, `GeoHubDownloads`. POSSE site: `/posse/rest/services`. |
| Accela ePermits | `https://dpepp.broward.org/BCS/Default.aspx` HTML **200** — search UI, not a bulk FeatureServer. Org item "Building Permits" is this Web Mapping Application. |
| Socrata | `api.us.socrata.com` catalog for this Hub domain → **404**. Already a miss in `socrata-sweep.md`. |
| CKAN | `/api/3/action/status_show` **404**. |

Existing `ArcGISClient` covers every live layer. No fifth platform client.

## Method

1. Host fingerprint (table above).
2. Hub dataset collection (123 items, paginated) plus family keyword search
   on `dataset` and `all`.
3. Org search `orgid:JMAJrTsHNLrSsWf5` — this is how HCED POSSE and BCPA
   tax-roll layers showed up; they are **not** in the 123-item Open Data
   collection.
4. REST folder walk on `bcgishub.broward.org/server` and `/posse` (UA
   required). Family-named folders: `311`, `BCPA`, `QAlert`, `POSSE`,
   `HCED`, `CodeEnforcement`, `BCS`.
5. For every survivor: layer `?f=json` (fields, `editingInfo.lastEditDate`,
   geometry, WKID), `returnCountOnly`, `orderByFields=<watermark> DESC` with
   `outSR=4326` and `resultRecordCount=1`, plus a recent-window count.
   Newest-row dates are the evidence.

Hub keyword misses that are real absences on the **dataset** collection
(full catalog, not one query): `permit` / `building permit` / `building
permits` / `posse` / `accela` / `epermits` / `311` / `service request` /
`seeclickfix` / `qalert` / `complaint` / `open311` / `property sales` /
`assessor` / `inspection` / `code enforcement` all returned **0**.
`q=local business tax` hit the three SLA layers. `q=deed` hit only FDOR
statewide cadastral copies.

## Permits — Tier 3 (do not register as PERMITS)

No building-permit FeatureServer is published to GeoHub. County building
permits live behind Accela **ePermits** (`dpepp.broward.org/BCS`) — a search
UI. Municipalities issue their own building permits; this catalog does not
federate them. Fort Lauderdale `BuildingPermits/FeatureServer/0` is frozen
at `SUBMITDT` **2026-03-16** (sibling).

`bcgishub` POSSE folder `BCS` is **empty** (no services).

### Near-miss — HCED POSSE right-of-way / utility permits (live, wrong family)

- **URL:** `https://bcgishub.broward.org/posse/rest/services/HCED/HCEDPossePermitsRef/FeatureServer/4`
  (`HCEDPossePermits`). Org item `226bbd087fd64b15b3f8613720371295`.
  Description: POSSE permit table geocoded by an automated model. **Not** in
  the 123-item Open Data collection.
- **Rows:** 7,356. Point geometry, native SR WKID **2881** (NAD83 FL East ft);
  `outSR=4326` returns WGS84 (newest row −80.127, 26.123). `maxRecordCount`
  2000. `objectIdField=OBJECTID`.
- **Watermark:** `ISSUEDATE`. Newest **2026-08-26** (`PERMITNUM` `2026-140-TL`,
  `PERMITTYPE=Telephone`, directional-bore conduit on E Broward Blvd, Fort
  Lauderdale). 29 issued ≥ 2026-08-01; 65 ≥ 2026-07-01; **268** YTD 2026;
  633 ≥ 2025-01-01. Fort Lauderdale `CITY='FORT LAUDERDALE'`: **2,763**.
- **`PERMITTYPE` mix:** Telephone 2,914 / Electric Power 1,249 / Driveway 812 /
  Paving and Drainage 712 / Miscellaneous 672 / Water 476 / Gas 196 / … —
  **ROW and utility**, not structural building permits.
- **Ids / address:** `PERMITNUM`, `JOBADDRESS`, `WORKDESCRIPTION`, `FIJOBID`.
- Treat as a possible later **street-cut** companion (NYC `tqtj-sjs8`
  analogue), not Wave-3 PERMITS.

Sibling `PossePermitsLocated/FeatureServer/2` is the same family, **staler**:
6,722 rows, newest `ISSUEDATE` **2024-12-23**. Prefer the Ref layer if this
is ever wired as a companion.

### Other permit lookalikes

| Item | Finding |
|---|---|
| Accela ePermits UI | Search only. No public bulk REST. |
| `SWM_Licenses/0` | Surface-water management polygons, WCD 2/3/4/Cocomar. `lastEditDate` **2021-06-08**. 1,670 rows. Experience Builder "Surface Water Management License Public Map" wraps POSSE SWM, not building. |
| `MOT_Web/0` "MOT Active" | Modification-of-traffic. `lastEditDate` **2018-04-26**. **0** rows. Layer 1 Future also 0; layer 2 Expired = 284. |
| `EEPD_General_License/1` | Environmental POSSE points (seawalls / docks), not occupational SLA or building. 17,292 rows. Naive `ISSUEDATE DESC` returns nulls (2,422 null); `IS NOT NULL` newest is sentinel **2104-12-05**. 2 rows with `ISSUEDATE` in 2026. Wrong family. |
| `EEPD_WarnCitNot/3` | Environmental NOV points. Newest `VIOLATION_DATE` **2024-12-04**; 0 in 2026. Not 311. |

**Verdict:** do not register `FeedType.PERMITS`.

## 311 — Tier 3 (do not register)

Genuine absence of a public ticket table.

- Hub `dataset` searches `311`, `service request`, `seeclickfix`, `qalert`,
  `complaint`, `open311` → **0**. `all` collection `q=311` → **0**.
- **`bcgishub.broward.org/server/rest/services/311` is an empty folder** (no
  services). POSSE `CodeEnforcement` is also empty.
- Org `q=311` hits two **Power BI** apps only: Consumer Complaints and Child
  Care Complaints (`powerbi.broward.org`). Not REST.
- **Local Code Enforcement Agencies**
  (`experience/3f64e61cb7f64805af7983721659b993`) is a **jurisdiction lookup**
  (which municipality handles code at this address), not cases.
- `MunicipalCodeAppPts` / `MunicipalCodeAppCities` — 724,258 address points +
  89 city polygons, `lastEditDate` **2024-02-01**. Same lookup, not 311.
- Org `QAlert*` items are operated-facilities buffers, mosquito zones, and
  shelter polygons. Server folder `QAlert` has one service:
  `BMSDGarbageServiceDays` (pickup-day polygons). **No request layer.**

Fort Lauderdale city GIS `ServiceRequest` is frozen at `REQUESTDATE`
**2022-02-05** (sibling). SeeClickFix place `fort-lauderdale` is live but
thin / unofficial and is not a county feed.

**Verdict:** do not register live 311.

## SLA — Tier 1 (register)

County **Local Business Tax** (occupational license), not a municipal BTR.
Two hosted views of the same **111,263**-row extract, last edited
**2026-08-24**. Snapshot registry (NYC/LA/Miami-Dade LBT shape), not a daily
issuance stream.

### Primary — email/phone overlay

- **URL:** `https://services.arcgis.com/JMAJrTsHNLrSsWf5/arcgis/rest/services/BrowardLocalTaxBusinessesEmailPhone/FeatureServer/0`
- **Hub item:** `23a7d0e58f7748119a821ad4b62d75ab` ("Broward County Local Tax
  Businesses Contact Information").
- **Platform:** ArcGIS FeatureServer, `maxRecordCount=2000`,
  `geometryType=esriGeometryPoint`, `objectIdField=OBJECTID`. Native SR WKID
  **2881**; `outSR=4326` returns WGS84 inside Broward (newest row −80.200,
  26.049 — `5815 SW 39TH WAY`, Fort Lauderdale, `Account__=219102`).
- **Rows:** 111,263. `Account_Status`: Active **80,965** / Closed **17,993** /
  null **12,305**.
- **Watermark:** `Business_Start_Date` (`esriFieldTypeDate`). Newest row
  **2026-09-07** (future-dated start, same pattern as Miami-Dade `BUSSDATE`).
  35 rows ≥ 2026-08-20; **377** ≥ 2026-08-01; 1,162 ≥ 2026-07-01; **5,272** ≥
  2026-01-01. Filter `Business_Start_Date <= CURRENT_DATE` before taking a
  high watermark.
- **Do not watermark on `Year`.** Integer tax year, mixed 2024 (11,558) /
  2025 (91,944) / 2026 (7,753) / 2027 (8). A `Year DESC` read is not recency.
- **Ids:** `Account__` (integer). `Receipt_Num` is null on the newest page —
  do not use it as `id_keys`. `Receipt__` (`349-363351` on the newest row)
  is a companion, not unique-enough alone.
- **Columns worth mapping:** `Account__`, `Business_Name` / `DBA_Name`,
  `Owner_Name`, `Occupation_Desc_`, `Category_Name`, `Business_Start_Date`,
  `Account_Status`, `Business_Address_Line_1` + `Business_City` +
  `Business_Zip`, `Business_Email`, `Business_Phone`.
- **Geocoding:** native point. `SHAPE IS NULL` on **3,618 / 111,263
  (3.25%)**. `Business_Address_Line_1 IS NULL` on 12,419 (different tail).
  Register as native; optional address fallback for the null-shape subset
  is not required for Tier 1.
- **Cadence:** extract `lastEditDate` 2026-08-24T16:44Z; start dates through
  probe week plus a handful of future-dated 2026-09 rows.
  `ingestion_mode="snapshot"`. `expected_cadence_days=30`.
- **Fort Lauderdale share:** `Business_City = 'FORT LAUDERDALE'` →
  **20,109**; `CITYNAME = 'FORT LAUDERDALE'` → 18,436. Countywide coverage,
  not unincorporated-only.

### Twin — tax database (same rows, fewer columns)

- **URL:** `https://services.arcgis.com/JMAJrTsHNLrSsWf5/arcgis/rest/services/TaxDatabase2021/FeatureServer/0`
  (Hub item `269d9de41bee45b6bb71cdc054579e97`, "Local Business Tax Database").
  Layer 1 is `Non-Broward Business Address` (5,372 points) — skip.
- **lastEditDate:** 2026-08-24T15:19Z (email overlay 16:44Z the same day).
- Same 111,263 count, same `Business_Start_Date` newest **2026-09-07**, no
  `Account_Status` / email / phone. Prefer the overlay.

### Rejected SLA lookalikes

| Item | Why not |
|---|---|
| `Broward_RTT_Business/0` (`BrowardBiz_TaxRoll_Hyperlink`) | Parcel **join** of tax-roll polygons + business-tax attrs. 93,119 polygons. `Receipt_Application_Date` newest **2026-08-10**, 1,128 ≥ 2026-07-01 / 169 ≥ 2026-08-01 — live, but polygon-of-parcel not point-of-business, and no sale/deed fields. Inferior duplicate of the point SLA. |
| `SBDirectoryComplete/0` | 1,133 certified small businesses. `lastEditDate` **2025-01-29**. Newest `BUSINESSSTARTDATE` **2023-07-17**; newest `ENDDATE` 2025-12-20. Stale directory, not the tax extract. |
| `SBE_NAICS_Certs` layers 0–2 | `lastEditDate` **2022-03-28**. Dead. |

**Verdict:** register the email overlay as `FeedType.SLA`, native geocode,
snapshot mode.

## Deeds — Tier 3 (do not register)

No recorded-documents stream on GeoHub. What exists is **last-sale-on-parcel**
(the Seattle / PG-County snapshot class), and on **county** hosts even that
is stale at row level.

| Layer | Rows | lastEditDate | Newest sale | Verdict |
|---|---|---|---|---|
| `PARCEL_POLY_BCPA_TAXROLL/FeatureServer/0` | 554,358 | 2026-04-02 | `SALE_DATE_1` = **2024-09-27** (DRR, $0.70 stamp, Davie folio). **0** rows with `SALE_DATE_1` in 2025 or 2026; 28,267 in 2024 | Tax-roll republish; sale column frozen ~11 months before the edit stamp, ~23 months before probe |
| `QAlertBCPA_Parcel_TaxRoll/FeatureServer/3` | 781,388 | 2026-02-02 | `SALE_DATE_1` = **2020-03-26**. 0 in 2024–2026 | Older QAlert join, not a stream |
| `Real_Property_TEST/FeatureServer/11` | 2,441 | **2023-04-06** | `SALE_DATE_` = **2023-03-07**. 0 sales in 2026 | Named TEST; dead |
| `BCPA/Parcels/FeatureServer/0` (`bcgishub`) | 556,172 | (no editingInfo) | **no sale/deed fields** (7 cols) | Cadastral polygons only |
| `BCPA_Parcels/FeatureServer/53` | 553,909 | 2026-04-24 | no sale fields | Geometry only |
| `Parcels_FEMA_App/0` | 536,584 | 2026-06-10 | no sale/deed fields | Flood join |
| `BCPAParcelsVacant/11` | 12,549 | 2026-07-07 | no sale fields | Vacant-land inventory |
| FDOR `Florida_Statewide_Parcel_Centroid_Version/0` | title **FDOR Cadastral Centroids 2025**; `lastEditDate` 2026-06-09. **765,030** with `CO_NO=16` (Broward). `CO_NO=11` = 117,522 (Alachua — do **not** filter FIPS 011). Description: April PA GIS submissions exported **August 2025**. `SALE_YR1` year-equality counts timed out under load | Annual NAL snapshot, not a transaction stream |

`Broward_RTT_Business` has **zero** sale/deed columns — it is the SLA join
onto parcels, listed under SLA above.

### Live Broward-shaped sales live on Fort Lauderdale GIS, not this catalog

Sibling probe (do not rewrite that file): city GIS
`https://gis.fortlauderdale.gov/server/rest/services/TaxParcel/FeatureServer/0`
is a BCPA last-5-sales snapshot covering 19 municipalities, `SALEDATE1`
newest **2026-08-14**, **459** countywide in the 30 days to 2026-08-27.
Reconfirmed this probe: newest row `PARCELCITY=TAMARAC`, 459 in
`SALEDATE1 >= DATE '2026-07-28'`. That layer is **not** a Broward GeoHub
publish, mutates last-5 rather than appending a deed log, and is owned by
the Fort Lauderdale stream as a reason **not** to register FTL. Do not
import it here as a `broward` DEEDS feed either — last-5 mutation plus the
wrong host.

A live clerk O&R search was not hunted; GeoHub/org/REST follow-through does
not publish one.

**Verdict:** do not register deeds.

## REST folders that looked like hits and were not

| Folder | Finding |
|---|---|
| `server/311` | Empty. |
| `server/QAlert` | `BMSDGarbageServiceDays` only. |
| `server/BCPA` | Address + parcel geometry. Sale attrs live on the hosted tax-roll copies, which are stale. |
| `server/POSSE` | Empty (POSSE services are on the `/posse` site). |
| `posse/BCS` | Empty. Building Construction Services is Accela UI. |
| `posse/CodeEnforcement` | Empty. |
| `posse/HCED` | ROW/utility POSSE only (near-miss above). |
| `posse/EEP` | Environmental licenses / NOVs. |
| `server/GeoHubDownloads` | Boundaries, parks, GTFS, address points. `BCGIS_Q_BCPA_Parcel_TaxRoll` is the stale QAlert tax-roll MapServer twin. |
| `server/RealProperties` | `DaniaBeachParcels` subset, not county deeds. |
| `server/MunicipalData` | Empty. |

## Address substrate (not a feed)

`OpenDataAddressPoints/FeatureServer/0` (483,733) and
`GeoHubDownloads/GISAddressPoints/FeatureServer/0` (492,909) are county
site-address points. Useful if the SLA null-shape tail is geocoded later,
not a fourth family.

## Registration contract (`broward`, SLA only)

Spine is **not** applied in this stream. Sketch for the interlock holder.
City identity is Broward **County**; do not fold Fort Lauderdale municipal
feeds or Miami-Dade into this `CityId` (ADR 0007).

```python
# SLA — Tier 1 snapshot
DatasetSpec(
    endpoint="https://services.arcgis.com/JMAJrTsHNLrSsWf5/arcgis/rest/services/BrowardLocalTaxBusinessesEmailPhone/FeatureServer/0",
    platform="arcgis",
    watermark_col="Business_Start_Date",
    id_keys=["Account__", "OBJECTID"],
    producer_key="sla",
    ingestion_mode="snapshot",
    oid_field="OBJECTID",
    max_record_count=2000,
    expected_cadence_days=30,
    companion_endpoints={
        "tax_database_twin": "https://services.arcgis.com/JMAJrTsHNLrSsWf5/arcgis/rest/services/TaxDatabase2021/FeatureServer/0",
    },
    field_map={
        "license_id": ["Account__"],
        "dba": ["DBA_Name", "Business_Name"],
        "premises_name": ["Owner_Name"],
        "license_type": ["Occupation_Desc_", "Category_Name"],
        "effective_date": ["Business_Start_Date"],
        "address_street": ["Business_Address_Line_1"],
        "borough": ["Business_City"],
        "zipcode": ["Business_Zip"],
    },
)
```

Read-time notes (not spine in this stream): filter
`Business_Start_Date <= today` before watermarking; optionally
`Account_Status='Active'` if closed rows should not enter G8. Native
geocode — G8 null-H3 should track the 3.25% `SHAPE IS NULL` tail unless an
address fallback is added. Re-probe ≤72 h before build
(`expansion-roadmap-wave-3.md` §5.3).

Do **not** register permits, 311, or deeds on this evidence.

## Fort Lauderdale metro supplement?

**Yes, for SLA only.** County occupational-license points already sit on
Fort Lauderdale addresses (20,109 rows) and on the rest of the
municipalities. A Fort Lauderdale city registration that lacks SLA can lean
on this layer once `broward` is its own `CityId` (ADR 0007 shape 2 + later
`metro_group` presentation). It does **not** fill Fort Lauderdale building
permits or 311 — those remain municipal, frozen on city GIS, and unpublished
here.

## Wave-3-ready

**Yes — partial.** One live family on the existing ArcGIS client. Implementation
is a leaf `cities/broward.py` plus a serial spine hold (`CityId`, aliases,
`REGISTRY`, one endpoint setting, field map, dashboard `METRO_META`). Do not
wait on permits / 311 / deeds. Do not register anything from this stream.
