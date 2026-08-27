# Wave 3 feed-expansion drafts (US-196)

**Probed:** 2026-08-27T19:31Z (row-level; catalog `modified` unused).
**Stream:** `.streams/feed-expansion-geocode.md` (leaf-only; no REGISTRY / city-module / spine edits).
**Ticket:** Linear US-196 — unlock already-identified address-only feeds on *registered* metros via ADR 0004.
**Method:** newest-row-by-watermark (nulls and dirty values excluded), column list, geocode/address fields, recent-window count. ArcGIS `returnCountOnly` used where the server accepts it; Socrata `$select=count(*)` + `$where`.

This file is the application contract for a later **serial interlock hold**. Drafts below are literals of `DatasetSpec(...)` as declared in `apps/api/src/spatial/city_registry.py` (typed fields, not the retired `extra=` dict).

## Verdict board

| Feed | Live? | Newest watermark (clean) | Geocode path | Verdict |
|---|---|---|---|---|
| Sacramento PERMITS `BldgPermitIssued_CurrentYear` | yes, **monthly batch** | `Status_Date` **2026-07-30** (text); layer `lastEditDate` 2026-08-01 | address-only `Address`+`ZIP` → ADR 0004 | **GO (companion, do not replace county)** |
| Norfolk 311 `nbyu-xjez` | yes, intraday | `creation_date` **2026-08-26T23:13Z** | address string `location` → already `needs_geocode=True` | **GO — already registered** |
| Norfolk SLA `dpi6-sct5` | yes, same-day | `business_opened_date` **2026-08-25** | **native** lat/lng (placeholder `where` already on spec) | **GO — already registered** |
| DC SLA Basic Business Licenses | yes, same-day | `INITIALISSUEDATE` **2026-08-27** | `PREMISEADDRESS` → already `needs_geocode=True` | **GO — already registered** |
| DC DEEDS CAMA sales | yes (CAMA lag) | `SALE_DATE` **2026-08-18**; `GIS_LAST_MOD_DTTM` 2026-08-27 | **no address**; SSL → Parcel Lots centroid (already `parcel_join`) | **GO — already registered** |
| Denver SLA active licenses | table live, **unusable** | no arrival-ordered date | **no address and no coords** | **NO-GO** |
| Denver DEEDS sales/transfers | yes | `RECEPTION_DATE` **20260825** (yyyymmdd int) | **PARID only — no address** | **NO-GO** (parcel-join would be a new ADR) |
| Chicago CDOT `pubx-yq2d` | yes, same-day | `applicationissueddate` **2026-08-26T22:32Z** | native lat/lng on **93.4%** recent; street-range fallback | **GO (companion / optional swap)** |
| Chicago CDOT `hr8i-6s6s` | yes, same-day | `applicationissueddate` **2026-08-26T22:32Z** | native lat/lng on **95.9%** recent; **33.6%** overall | **NO-GO as primary** (subset of `pubx-yq2d`) |
| Chicago CDOT `jdis-5sry` (already STREET_CUT) | yes | `applicationissueddate` recent window 3,971 | native lat/lng **99.97%** recent | **already registered — keep as primary** |
| NYC DOT `tqtj-sjs8` | yes, same-day | `permitissuedate` **2026-08-26T14:20Z** | house+street **34.5%**; on-street+from **99.6%** (intersection) | **GO with G5 risk** |

**Apply in the serial hold (net-new):** Sacramento city permits companion, Chicago `pubx-yq2d`, NYC `tqtj-sjs8`.
**Do not apply:** Denver SLA, Denver DEEDS, Chicago `hr8i-6s6s` as a second primary.
**Already on `REGISTRY`:** Norfolk 311+SLA, DC SLA+DEEDS, Chicago `jdis-5sry`. Re-probe confirms still live; no DatasetSpec write required unless the orchestrator wants comment/docstring refresh (city modules are still a serial-hold surface).

---

## 1 · Sacramento PERMITS — `BldgPermitIssued_CurrentYear`

### Probe

| | |
|---|---|
| Platform | ArcGIS **Table** (no `geometryType`) |
| Endpoint | `https://services5.arcgis.com/54falWtcpty3V47Z/arcgis/rest/services/BldgPermitIssued_CurrentYear/FeatureServer/0` |
| Live? | Service 200; **stale relative to a daily feed**. `editingInfo.lastEditDate` = **2026-08-01T11:16Z**. Zero rows with `Status_Date LIKE '08/%/2026'`. |
| Rows | 11,775 |
| Watermark col | `Status_Date` — `esriFieldTypeString`, values `MM/DD/YYYY` (ADR 0005 text watermark). Lexicographic DESC is unsafe; newest-by-`OBJECTID` agrees with max observed date **07/30/2026**. |
| Recent window | 1,608 rows `Status_Date LIKE '07/%/2026'`; 0 in August 2026. |
| Geocode fields | `Address` **11,775/11,775**, `ZIP` **11,775/11,775**, `Site_Location` 902/11,775, `Parcel_No`. No lat/lon, no geometry. |
| Contrast | Registered county PERMITS `services1.arcgis.com/5NARefyPVtAeuJPU/.../Permits/FeatureServer/0` is a **point** layer, `ISSUED_DATE` epoch, **2,602** rows since 2026-07-28. Different org, different permit-number scheme (`RES-2615946` vs `RRZR2024-02038`). |

Newest row: `Application=CF-2606380`, `Address=5500 ENRICO BLVD`, `ZIP=95820`, `Status_Date=07/30/2026`, `Current_Status=Issued`.

### Proposed DatasetSpec (literal)

Do **not** replace the registered county spec. Add as `companion_endpoints` **or** a producer dual-parse only if city-issued rows are wanted on top of county points. Schemas do not match (text `Status_Date` vs epoch `ISSUED_DATE`; table vs point), so a naive companion URL reuse will not parse.

```python
DatasetSpec(
    endpoint=(
        "https://services5.arcgis.com/54falWtcpty3V47Z/arcgis/rest/services/"
        "BldgPermitIssued_CurrentYear/FeatureServer/0"
    ),
    platform="arcgis",
    watermark_col="Status_Date",
    id_keys=["Application", "OBJECTID"],
    topic=settings.topic_permits,
    interval_seconds=3600.0,
    producer_key="permits",
    expected_cadence_days=45,
    oid_field="OBJECTID",
    max_record_count=2000,
    needs_geocode=True,
    geocode_context="Sacramento, CA",
    watermark_type="text",
    watermark_format="%m/%d/%Y",
    field_map={
        "job_id": ["Application", "OBJECTID"],
        "issuance_date": ["Status_Date"],
        "job_type": ["Type", "Sub_Type", "Category"],
        "cost": ["Valuation"],
        "status": ["Current_Status", "Rpt_Status"],
        "address_street": ["Address", "Site_Location"],
        "zipcode": ["ZIP"],
        "bbl": ["Parcel_No"],
        "borough": ["Council_Dist", "Comm_Plan_Area"],
    },
)
```

`dob_permits_producer` already calls `geocode_row_if_declared` on `address_street`. Compose the Census query as `{Address}, Sacramento, CA {ZIP}` via `geocode_context` (ZIP is not auto-appended today — application may want `address_street` to include ZIP in the map by concatenating in the producer, or rely on context).

### G5 / G8

- Address present on 100% of rows → G5 floor is geocoder recovery, not source gap. Staging probe of newest 500 required before hold (R2).
- G8 null-H3 = geocode miss; document it. Wave-3 address-geocode G5 = 95%.
- Staleness: treat as monthly. If `Status_Date` is still 2026-07-30 at the spine hold after 2026-09-15, **reclassify NO-GO stalled**.

### Spine files later

- `apps/api/src/config.py` — new `arcgis_sacramento_city_permits_url` (do not clobber `arcgis_sacramento_permits_url`).
- `apps/api/src/spatial/city_registry.py` — companion or second parse path on `CityId.SACRAMENTO` `FeedType.PERMITS`.
- `apps/api/src/producers/dob_permits_producer.py` — only if dual-schema companion needs an explicit branch (geocode hook already exists).
- Tests under `apps/api/tests/unit/` (leaf). **Do not edit** `cities/sacramento.py`.

---

## 2 · Norfolk 311 `nbyu-xjez`  (already on REGISTRY)

### Probe

| | |
|---|---|
| Platform | Socrata `data.norfolk.gov` |
| Endpoint | `https://data.norfolk.gov/resource/nbyu-xjez.json` |
| Live? | **yes**. `rowsUpdatedAt` 2026-08-27T11:01Z |
| Rows | 1,162,847 |
| Watermark | `creation_date` calendar_date; newest **2026-08-26T23:13:11Z** |
| Recent window | 16,973 since 2026-07-28; 16,848 of those have `location` (99.3%) |
| Geocode | `location` is **text** (`4260 HEUTTE DRIVE, NORFOLK, VA`), not a point. No lat/lng columns. |

Registered spec (confirm-live; do not rewrite unless comments drift):

```python
FeedType.COMPLAINTS_311: DatasetSpec(
    endpoint=settings.socrata_norfolk_311_endpoint,
    platform="socrata",
    watermark_col="creation_date",
    id_keys=["service_request_number", "id"],
    topic=settings.topic_311,
    interval_seconds=600.0,
    producer_key="311",
    expected_cadence_days=7,
    needs_geocode=True,
    geocode_context="Norfolk, VA",
    field_map={
        "incident_id": ["service_request_number"],
        "complaint_type": ["service_request_type", "service_request_category"],
        "created_date": ["creation_date"],
        "status": ["status"],
        "incident_address": ["location"],
    },
)
```

### G5 / G8

Already passing Wave G2 (ADR 0004). Re-probe does not change the contract. `cities/norfolk.py` module docstring still says 311/SLA are deferred — stale relative to `REGISTRY`; fix only in a serial hold if touched.

### Spine files later

None for this feed.

---

## 3 · Norfolk SLA `dpi6-sct5`  (already on REGISTRY)

### Probe

| | |
|---|---|
| Platform | Socrata |
| Endpoint | `https://data.norfolk.gov/resource/dpi6-sct5.json` |
| Live? | **yes**. `rowsUpdatedAt` 2026-08-27T11:14Z |
| Rows | 10,105 |
| Watermark | `business_opened_date`; newest **2026-08-25** |
| Recent window | 1,137 opened since 2026-01-01 |
| Geocode | **native** `latitude`/`longitude`/`geocoded_point`. 7,260/10,105 (71.8%) have lat. Placeholder `NO NORFOLK ADDRESS REQUIRED 99999` = **2,559 (25.3%)**. Filtered remainder is ~96% native-geocoded. |

Wave-3 ticket text ("address-only, deferred") is **obsolete**. City geocodes `location_address` itself. Keep the registered `where` + native lat/lng map; do **not** flip `needs_geocode=True` (would be redundant and would skip native points only if lat is missing).

```python
FeedType.SLA: DatasetSpec(
    endpoint=settings.socrata_norfolk_licenses_endpoint,
    platform="socrata",
    watermark_col="business_opened_date",
    id_keys=["trading_as_name", "primary_owner", "business_opened_date"],
    topic=settings.topic_sla,
    interval_seconds=600.0,
    producer_key="sla",
    expected_cadence_days=7,
    where="location_address != 'NO NORFOLK ADDRESS REQUIRED 99999'",
    field_map={
        "license_id": ["trading_as_name", "primary_owner"],
        "dba": ["trading_as_name"],
        "premises_name": ["primary_owner"],
        "license_type": ["naics"],
        "effective_date": ["business_opened_date"],
        "address_street": ["location_address"],
        "latitude": ["latitude"],
        "longitude": ["longitude"],
    },
)
```

### G5 / G8

G8′ null-H3 ceiling holds on the filtered set. No spine work.

---

## 4 · Washington DC SLA — Basic Business Licenses  (already on REGISTRY)

### Probe

| | |
|---|---|
| Platform | ArcGIS Table `FEEDS/DCRA/FeatureServer/0` |
| Endpoint | `https://maps2.dcgis.dc.gov/dcgis/rest/services/FEEDS/DCRA/FeatureServer/0` |
| Live? | **yes**. Newest `INITIALISSUEDATE` **2026-08-27** (epoch-ms). `DATAREFRESHEDON` same day. 1,179 issued since 2026-07-28. |
| Rows | 277,705 |
| Geocode | `PREMISEADDRESS` on premise rows. Native `LATITUDE`/`LONGITUDE` exist (**209,258** non-null) but newest-window samples include **integer degrees** (`LATITUDE=39`, `LONGITUDE=-77`) — too coarse for H3-7. Keep ADR 0004 on `PREMISEADDRESS`; do **not** trust native lat/lng without a precision audit. |
| Filter | `PREMISEINDC = 'Yes'`: 216,601 rows. |

Registered spec (confirm-live):

```python
FeedType.SLA: DatasetSpec(
    endpoint=settings.arcgis_dc_licenses_url,
    platform="arcgis",
    watermark_col="INITIALISSUEDATE",
    id_keys=["CUSTOMERNUMBER", "GLOBALID", "OBJECTID"],
    topic=settings.topic_sla,
    interval_seconds=600.0,
    producer_key="sla",
    expected_cadence_days=7,
    oid_field="OBJECTID",
    max_record_count=2000,
    needs_geocode=True,
    geocode_context="Washington, DC",
    where="PREMISEINDC = 'Yes'",
    field_map={
        "license_id": ["CUSTOMERNUMBER"],
        "license_type": ["LICENSETYPE"],
        "effective_date": ["LICENSESTARTDATE"],
        "expiration_date": ["LICENSEENDDATE"],
        "borough": ["WARD"],
        "address_street": ["PREMISEADDRESS"],
    },
)
```

Nulls sort first on `INITIALISSUEDATE DESC` — scheduler `where` already requires a usable watermark in practice; keep `INITIALISSUEDATE IS NOT NULL` in mind if incremental polls ever go silent.

### G5 / G8

Already registered under Wave G3. Out-of-DC premises (~24% historically) must not get a forced `, Washington, DC` suffix — `geocoder.py` already guards on a state token. No spine work.

---

## 5 · Washington DC DEEDS — Property Sales CAMA  (already on REGISTRY)

### Probe

| | |
|---|---|
| Platform | ArcGIS Table `Property_and_Land_WebMercator/FeatureServer/57` |
| Endpoint | `https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Property_and_Land_WebMercator/FeatureServer/57` |
| Live? | **yes**. Newest `SALE_DATE` **2026-08-18T04:00Z**; `GIS_LAST_MOD_DTTM` **2026-08-27T09:16Z** (same CAMA batch cadence as `deeds-watermark-audit.md`). 843 sales with `SALE_DATE >= 2026-07-28`. |
| Rows | 422,303 |
| Geocode | **Zero address-like fields.** Keys: `SSL`, `ROW_NUMBER`, `SALE_DATE`, `SALE_PRICE`, `QUALIFIED`. Spatial path is the existing SSL → Parcel Lots layer 33 centroid join — **not** ADR 0004. |

```python
FeedType.DEEDS: DatasetSpec(
    endpoint=settings.arcgis_dc_sales_url,
    platform="arcgis",
    watermark_col="SALE_DATE",
    id_keys=["SSL", "ROW_NUMBER", "OBJECTID", "id"],
    topic=settings.topic_deeds,
    interval_seconds=600.0,
    producer_key="deeds",
    expected_cadence_days=7,
    oid_field="OBJECTID",
    max_record_count=2000,
    parcel_join={
        "parcel_layer": (
            "https://maps2.dcgis.dc.gov/dcgis/rest/services/"
            "DCGIS_DATA/Property_and_Land_WebMercator/FeatureServer/33"
        ),
        "join_key": "SSL",
        "geometry_source": "centroid",
    },
    field_map={
        "doc_id": ["ROW_NUMBER"],
        "bbl": ["SSL"],
        "document_amount": ["SALE_PRICE"],
        "recorded_date": ["SALE_DATE"],
        "doc_type": ["QUALIFIED"],
    },
)
```

### G5 / G8

G8 null-H3 = parcel-join miss, already documented (US-139). Ticket's "non-spatial → geocode" is the wrong lever; address geocoding cannot run. No spine work.

---

## 6 · Denver SLA — Active Business Licenses  **NO-GO**

### Probe

| | |
|---|---|
| Platform | ArcGIS Table `ODC_active_business_licenses/FeatureServer/31` |
| Endpoint | `https://services1.arcgis.com/zdB7qR0BtYrg0Xpl/arcgis/rest/services/ODC_active_business_licenses/FeatureServer/31` |
| Live? | Table **refreshes** (`lastEditDate` 2026-08-27T10:24Z) but is not an activity feed. |
| Rows | 41,986, all `License_Status='License Issued - Active'` |
| Columns | `OBJECTID, License_Num, License_Type, License_Sub_Type, License_Status, Entity_Name, Trade_Name, Expiration_Date, B1_Access_By_ACA` |
| Watermark | **None usable.** Only date is `Expiration_Date` (term-length; century typos 2200/8099 still present). |
| Geocode | **No address, no coords, no parcel key.** |

Confirms US-73 / `test_producers_denver.py` descope. Wave-3 "address keys" does not match the live schema. Snapshot ingestion cannot satisfy G5 (0% locatable). **Do not draft a registrable spec.**

### Spine files later

None. Leave `CityId.DENVER` without `FeedType.SLA`.

---

## 7 · Denver DEEDS — Real Property Sales and Transfers  **NO-GO** (ADR 0004)

### Probe

| | |
|---|---|
| Platform | ArcGIS Table `ODC_real_property_sales_and_transfers/FeatureServer/60` |
| Endpoint | `https://services1.arcgis.com/zdB7qR0BtYrg0Xpl/arcgis/rest/services/ODC_real_property_sales_and_transfers/FeatureServer/60` |
| Live? | **yes** after excluding dirty `RECEPTION_DATE` values. |
| Rows | 309,947 |
| Watermark | `RECEPTION_DATE` **integer yyyymmdd**. Dirty first in raw DESC: `50250305`, `20281113`, `20261230` (same US-73 set). Clean newest **20260825**. |
| Recent window | 171 with `20260728 <= RECEPTION_DATE < 20260901`; 10,846 in 2026 before Sep. |
| Geocode | Columns: `PARID, RECEPTION_NUM, INSTRUMENT, SALE_YEAR, SALE_MONTHDAY, RECEPTION_DATE, SALE_PRICE, GRANTOR, GRANTEE, CLASS, MKT_CLUS, D_CLASS, D_CLASS_N, NBHD_1, NBHD_1_CN`. **No address, no lat/lng.** Neighborhood name is not geocodable at house precision. |

ADR 0004 explicitly left **parcel-join geocoding (Denver `PARID`) out of scope**. Registering as address-geocoded is impossible. Registering as Cook-County-style 100% null-H3 would fail Wave-G G8′ ("a feed registered *because of* Wave G that lands above 5% null-H3 is reverted") — already the US-73 outcome. Wave-3's loosened G8 applies to **address-geocoded** feeds, not PARID-only tables.

Candidate spec preserved for a future parcel-join ADR (also pinned in `test_producers_denver.py`); **do not apply**:

```python
DatasetSpec(
    endpoint=(
        "https://services1.arcgis.com/zdB7qR0BtYrg0Xpl/arcgis/rest/services/"
        "ODC_real_property_sales_and_transfers/FeatureServer/60"
    ),
    platform="arcgis",
    watermark_col="RECEPTION_DATE",
    id_keys=["RECEPTION_NUM", "PARID", "OBJECTID"],
    topic=settings.topic_deeds,
    interval_seconds=600.0,
    producer_key="deeds",
    expected_cadence_days=7,
    oid_field="OBJECTID",
    max_record_count=2000,
    watermark_type="text",
    watermark_format="%Y%m%d",
    watermark_exclude=["50250305", "20281113", "20261230"],
    needs_geocode=False,
    non_spatial=True,
    field_map={
        "doc_id": ["RECEPTION_NUM"],
        "bbl": ["PARID"],
        "document_amount": ["SALE_PRICE"],
        "recorded_date": ["RECEPTION_DATE"],
        "doc_type": ["INSTRUMENT"],
        "borough": ["NBHD_1_CN"],
        "party1_grantor": ["GRANTOR"],
        "party2_grantee": ["GRANTEE"],
    },
)
```

### Spine files later

None until a PARID→parcel-centroid ADR exists.

---

## 8 · Chicago street-cut `pubx-yq2d`  **GO**

### Probe

| | |
|---|---|
| Platform | Socrata `data.cityofchicago.org` |
| Endpoint | `https://data.cityofchicago.org/resource/pubx-yq2d.json` |
| Title | Transportation Department Permits |
| Live? | **yes**. `rowsUpdatedAt` 2026-08-27T06:52Z |
| Rows | 2,305,113 |
| Watermark | `applicationissueddate` (calendar_date). Raw DESC is poisoned by **`2115-03-11`** (2 rows) then real newest **2026-08-26T22:32:52Z**. Always constrain `< 2030-01-01`. |
| Recent window | 12,547 issued since 2026-07-28; **11,719 (93.4%)** have `latitude`. Lifetime lat fill 2,002,884 (86.9%). |
| Geocode | Native `latitude`/`longitude`/`location` **now present** — the 2026-08-24 "master, no coordinates" reading is **obsolete**. Street-range: `streetnumberfrom`+`direction`+`streetname`+`suffix`. |

Registered STREET_CUT remains `jdis-5sry` (street **closures**, 3,971 recent, 3,970/3,971 lat). `pubx-yq2d` is the CDOT **permit master** (occupy ROW, public-way opening, closures, …). Same column family as `jdis` / `hr8i`; `_chicago_row` would parse native-coord rows today and **drop** the 6.6% miss until a geocode hook is added.

### Proposed DatasetSpec (literal)

Keep `jdis-5sry` as primary (closure semantics, 99.97% coords). Unlock `pubx-yq2d` as companion **or** as a documented swap if product wants all CDOT permits instead of closures-only. One `FeedType.STREET_CUT` per city — cannot register both as primaries without duplicate H3 events.

```python
# Primary stays settings.socrata_chicago_street_cut_endpoint (jdis-5sry).
# NEW setting for the master:
# socrata_chicago_cdot_permits_endpoint = "https://data.cityofchicago.org/resource/pubx-yq2d.json"

DatasetSpec(
    endpoint=settings.socrata_chicago_cdot_permits_endpoint,  # NEW
    platform="socrata",
    watermark_col="applicationissueddate",
    id_keys=["uniquekey", "applicationnumber", "id"],
    topic=settings.topic_street_cut,
    interval_seconds=600.0,
    producer_key="street_cut",
    expected_cadence_days=7,
    needs_geocode=True,  # fallback for the ~6.6% recent miss
    geocode_context="Chicago, IL",
    where="applicationissueddate IS NOT NULL AND applicationissueddate < '2030-01-01T00:00:00'",
    field_map={
        "permit_id": ["uniquekey", "applicationnumber"],
        "permit_type": ["applicationtype", "applicationdescription"],
        "work_type": ["worktypedescription", "worktype"],
        "status": ["applicationstatus", "currentmilestone"],
        "street_name": ["streetname"],
        "address": ["streetnumberfrom", "direction", "streetname", "suffix"],
        "latitude": ["latitude"],
        "longitude": ["longitude"],
        "issued_date": ["applicationissueddate"],
        "start_date": ["applicationstartdate"],
        "end_date": ["applicationenddate"],
        "fees": ["totalfees"],
        "borough": ["ward"],
    },
)
```

If keeping `jdis-5sry` as `endpoint` and adding the master as companion:

```python
companion_endpoints={
    "cdot_permits_master": "https://data.cityofchicago.org/resource/pubx-yq2d.json",
}
```

`StreetCutPermitsProducer.run_stream` currently pages **only** `spec.endpoint`. Companion pagination is application work (leaf producer; not on the spine manifest). The producer also does **not** yet call `geocode_row_if_declared` — required for G5 on the 6.6% miss (and for NYC below). `street_cut_permits_producer.py` is a **leaf**.

### G5 / G8

Native 93.4% recent + address-range geocode on the remainder should clear 95% **if** the geocoder recovers street ranges. Staging probe of newest 500 (with `applicationissueddate < 2030`) before the hold. G8 null-H3 = remaining miss.

### Spine files later

- `apps/api/src/config.py` — new endpoint setting (and optional `where` lives on the spec).
- `apps/api/src/spatial/city_registry.py` — `CityId.CHICAGO` `FeedType.STREET_CUT` companion or endpoint swap + `needs_geocode` + `field_map`.
- Leaf: `apps/api/src/producers/street_cut_permits_producer.py` (geocode hook + compose `address` + optional companion loop).
- `apps/api/src/producers/scheduler.py` — only if the job is not already emitted from `datasets.items()` (it is, for the existing STREET_CUT).

---

## 9 · Chicago street-cut `hr8i-6s6s`  **NO-GO as primary**

### Probe

| | |
|---|---|
| Platform | Socrata |
| Endpoint | `https://data.cityofchicago.org/resource/hr8i-6s6s.json` |
| Title | Transportation Department Permits - Current and Future |
| Live? | **yes**. Same `rowsUpdatedAt` as `pubx-yq2d`. Newest real issued **2026-08-26T22:32Z** (same `DOT2282460` row). One `2115-03-11` poison date. |
| Rows | 53,491 |
| Recent window | 9,353 issued since 2026-07-28; **8,972 (95.9%)** have lat. |
| Lifetime lat | 17,961 / 53,491 = **33.6%** — matches the 2026-08-24 "~32% coordinates" reading. The current/future slice is well-geocoded; the tail is not. |
| Schema | Same CDOT columns as `pubx-yq2d` / `jdis-5sry` (no `ward` on this view). |

This is a **rolling window over the same permit family** as `pubx-yq2d`, not a new signal. Registering both primaries duplicates events. Prefer `pubx-yq2d` for history or this view for a small current-only payload — not both.

Optional companion-only (if product wants current/future and **not** the 2.3M master):

```python
companion_endpoints={
    "cdot_current_future": "https://data.cityofchicago.org/resource/hr8i-6s6s.json",
}
```

Same producer caveats as §8. **Recommendation: skip.**

---

## 10 · NYC street-cut `tqtj-sjs8`  **GO with G5 risk**

### Probe

| | |
|---|---|
| Platform | Socrata `data.cityofnewyork.us` |
| Endpoint | `https://data.cityofnewyork.us/resource/tqtj-sjs8.json` |
| Title | Street Construction Permits (2022 - Present) |
| Live? | **yes**. `rowsUpdatedAt` 2026-08-26T23:07Z. Newest `permitissuedate` **2026-08-26T14:20:54Z** (`permitissuedate IS NOT NULL`; raw DESC is null-first and 2017-shaped). |
| Rows | 3,845,920 |
| Recent window | 58,045 issued since 2026-07-28; 453,219 in 2026. |
| Geometry | `wkt` / `locationgeometry` are **State Plane LINESTRINGs**, present on **128 / 453,219** 2026 rows (0.03%). Unusable for H3. |
| Address | `boroughname` 58,045/58,045. `onstreetname`+`fromstreetname` **57,824 (99.6%)**. `permithousenumber` **20,052 (34.5%)**. Typical miss is a block face: `onstreetname=EAST 69 STREET`, `fromstreetname=3 AVENUE`, `tostreetname=LEXINGTON AVENUE`, `boroughname=MANHATTAN`. |

`StreetCutPermitsProducer._nyc_row` already knows the column names but **returns None** without lat/lng. Unlock = `needs_geocode=True` + compose an address (`{house} {onstreet}, {borough}, NY` or `{onstreet} and {fromstreet}, {borough}, NY`) + geocode hook. Config comment currently says this feed stays deferred.

### Proposed DatasetSpec (literal)

```python
FeedType.STREET_CUT: DatasetSpec(
    endpoint=settings.socrata_nyc_street_cut_endpoint,  # NEW
    platform="socrata",
    watermark_col="permitissuedate",
    id_keys=["permitnumber", "applicationtrackingid"],
    topic=settings.topic_street_cut,
    interval_seconds=600.0,
    producer_key="street_cut",
    expected_cadence_days=7,
    needs_geocode=True,
    geocode_context="New York, NY",
    where="permitissuedate IS NOT NULL",
    field_map={
        "permit_id": ["permitnumber", "applicationtrackingid"],
        "permit_type": ["permittypedesc", "permitseriesshortdesc"],
        "work_type": ["permitpurposecomments"],
        "status": ["permitstatusshortdesc", "permitstatusid"],
        "street_name": ["onstreetname", "fromstreetname"],
        "address": ["permithousenumber", "onstreetname", "fromstreetname", "tostreetname"],
        "borough": ["boroughname"],
        "issued_date": ["permitissuedate"],
        "start_date": ["issuedworkstartdate"],
        "end_date": ["issuedworkenddate"],
    },
)
```

New config:

```python
socrata_nyc_street_cut_endpoint: str = Field(
    default="https://data.cityofnewyork.us/resource/tqtj-sjs8.json",
    description="NYC DOT street construction permits (address/intersection geocoded, ADR 0004)",
)
```

Producer must compose the geocode string (field_map lists cannot concatenate). Suggested:

1. If `permithousenumber` and `onstreetname`: `{house} {onstreet}, {borough}, NY`
2. Else if `onstreetname` and `fromstreetname`: `{onstreet} and {fromstreet}, {borough}, NY`

Census intersection match may land below `geocode_confidence_floor` (0.9). That is the G5 risk.

### G5 / G8

Wave-3 G5 for address-geocoded feeds = **95% of newest 500 emit events with a resolved coordinate**. House numbers cover only 34.5% of the recent window; the rest depend on intersection geocoding. **Do not apply this spec until a staging probe of 500 newest `permitissuedate IS NOT NULL` rows reports recovery ≥ 95% (or an accepted documented gap).** If intersection recovery is ~50–80%, either drop to a `permithousenumber IS NOT NULL` `where` (keeps ~20k/30d, likely clears G5) or leave unregistered.

G8 null-H3 = geocode miss; expected and documented if G5 passes.

### Spine files later

- `apps/api/src/config.py` — `socrata_nyc_street_cut_endpoint`; drop the "stay deferred" comment.
- `apps/api/src/spatial/city_registry.py` — `CityId.NYC` `FeedType.STREET_CUT` (new key on an existing city).
- `apps/api/src/producers/scheduler.py` — auto-picks `producer_key="street_cut"` from `datasets.items()`; confirm `StreetCutPermitsProducer` is already in `self.producers`.
- Leaf: `apps/api/src/producers/street_cut_permits_producer.py` (geocode + address compose; `_nyc_row` currently drops).
- Tests (leaf). **Do not edit** `cities/nyc.py` (no bbox change).

---

## Spine-delta checklist (application hold)

Files on `docs/agents/spine-manifest.txt` the orchestrator will touch **once**, after this leaf. City geometry modules stay untouched.

| File | Delta |
|---|---|
| `apps/api/src/config.py` | Add Sacramento city permits URL; Chicago `pubx-yq2d` URL (if not swapping); NYC `tqtj-sjs8` URL. Do not remove county Sacramento or `jdis-5sry` unless product explicitly swaps. |
| `apps/api/src/spatial/city_registry.py` | Sacramento PERMITS companion / dual spec; Chicago STREET_CUT `needs_geocode` + `field_map` + companion or swap; NYC `FeedType.STREET_CUT` spec. Norfolk/DC: **no-op** (already registered). Denver: **no-op**. |
| `apps/api/src/spatial/cities/__init__.py` | none |
| `apps/api/src/spatial/geo_utils.py` | none |
| `apps/api/src/spatial/submarkets.py` | none |
| `apps/api/src/producers/scheduler.py` | Confirm STREET_CUT job for `nyc` appears; no new producer class. |
| `apps/api/src/producers/dob_permits_producer.py` | Only if Sacramento dual-schema companion needs a branch. |
| `apps/api/src/producers/complaints_311_producer.py` | none |
| `apps/api/src/producers/sla_licenses_producer.py` | none |
| `apps/api/src/producers/deeds_acris_producer.py` | none |

**Leaf (same hold, not spine):** `street_cut_permits_producer.py` geocode hook; unit tests; optional `norfolk.py` docstring if that module is opened for any reason (it should not be).

**Gates:** `pytest -m interlock` then full suite. No new `CityId`, no `METRO_META` / dashboard wiring (no new metro). City registration rule does not fire.

**Do not:** git-commit from the research stream; edit `docs/expansion-roadmap-wave-3.md`; mark US-196 completed until the hold lands.

---

## Already-registered vs ticket text

The Wave-3 §4.3 list was written as if Norfolk 311/SLA and DC SLA/DEEDS were still deferred. `REGISTRY` on 2026-08-27 already has all four, plus Chicago STREET_CUT as `jdis-5sry`. This re-probe is the ≤72 h freshness stamp for those four plus the still-open unlocks (Sacramento city permits, Chicago `pubx-yq2d`, NYC `tqtj-sjs8`). Denver remains the US-73 descope.

## Limits

- No Census/Nominatim recovery sample was run (geocoder backends are environment-dependent; G5 numbers above are **address-present**, not **geocode-success**).
- Sacramento August-empty table may be a monthly batch or a stall; stamp again before the hold.
- Chicago `pubx-yq2d` `$select=count(*)` without a where timed out on the first pass; the 2,305,113 figure is from a later count that succeeded.
- DC `LATITUDE=39` integer-degree rows were observed, not exhaustively counted.
