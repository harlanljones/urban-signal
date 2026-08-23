# Stream log — city-detroit — 2026-08-23

## Claim

- **Stream id:** `city-detroit`
- **Leaf files I will create/edit:** `src/spatial/cities/detroit.py`, `tests/unit/test_producers_detroit.py`, `.streams/city-detroit.md`
- **Spine files I expect to need:** `src/spatial/city_registry.py` (CityId.DETROIT + ALIASES + REGISTRY entry + settings URLs — orchestrator applies after stream ends; registry tests red until then, expected)

## Intent

Register FOUR Detroit ArcGIS feeds (permits, 311, licenses, property sales — licenses INCLUDED, see verdict below) through the existing ArcGISClient, plus a `cities/detroit.py` spatial module (metro bbox, predicate, 6 division bboxes, 16 submarkets, division catalog) and an LA/NOLA-mirrored test file. Everything probed live first; DatasetSpec proposals recorded here for the orchestrator.

## Decisions

- 2026-08-23 ~probe start — Claim written; scope locked to three leaf files; no git; no client/producer edits.
- 2026-08-23 — **Hub search API shape**: `data.detroitmi.gov/api/search/v1/collections/dataset/items?q=…` returns a GeoJSON FeatureCollection (not the JSON `data[]` shape); item ids resolve via `properties.url` to `services2.arcgis.com/qvkbeam7Wirps6zC/arcgis/rest/services/<svc>/FeatureServer`.
- 2026-08-23 — **Resolved layer URLs (all layer id 0, all point geometry, all maxRecordCount 1000, all oidField `ObjectId`)**:
  - PERMITS: `https://services2.arcgis.com/qvkbeam7Wirps6zC/arcgis/rest/services/bseed_building_permits/FeatureServer/0` — 2026 count-to-date = 3,779 (matches research exactly). Fields: `record_id` (Accela id), `address`, `submitted_date`/`issued_date` (**esriFieldTypeDateOnly** → "YYYY-MM-DD" strings), `work_description`, `permit_type`, `construction_type`, `current_use_type`, `amt_permit_cost`, `amt_estimated_contractor_cost`, `neighborhood`, `council_district`, `zip_code`, street parts, `parcel_id`, `longitude`/`latitude` attrs + point geometry. Sample row captured (RES2026-02969, issued 2026-08-22, ObjectId 43090).
  - 311: `https://services2.arcgis.com/qvkbeam7Wirps6zC/arcgis/rest/services/improve_detroit/FeatureServer/0` — SeeClickFix-derived: `issue_id`, `request_type`, `status`, `created_at`/`acknowledged_at`/`updated_at`/`closed_at`/`reopened_at` (**esriFieldTypeDate**, epoch-ms → client converts), flat `longitude`/`latitude` attrs (geocoded even when `geometry` comes back null), `neighborhood`, `council_district`, `zip_code`. Newest row 2026-08-23-era created_at epoch 1787495436000.
  - LICENSES: `https://services2.arcgis.com/qvkbeam7Wirps6zC/arcgis/rest/services/bseed_active_business_licenses/FeatureServer/0` — **GEOCODING VERDICT: GEOCODED.** Research called this a non-spatial table; live probe shows `esriGeometryPoint` with `longitude`/`latitude` attrs populated on every sampled row. INCLUDE in registration scope (unlike LA precedent — nothing to exclude). Fields: `record_id` (BUS####-#####), `business_name`, `license_type`, `license_category`, `expiration_date` (DateOnly; ONLY date column on the feed), `neighborhood`, `council_district`, `zip_code`, `parcel_id`.
  - SALES: `https://services2.arcgis.com/qvkbeam7Wirps6zC/arcgis/rest/services/assessor_property_sales_view/FeatureServer/0` — genuine market sales: `sale_id`, `parcel_id`, `amt_sale_price`, `grantor`, `grantee`, `liber_page`, `term_of_sale`, `sale_instrument` (WD), `property_class_description`, `ecf_neighborhood`, `neighborhood`, `sale_date` (DateOnly), `longitude`/`latitude` attrs. Newest REAL sale_date = **2026-08-19** (fresher than research's 2026-03-26). **Sentinel alert: max sale_date overall = '2925-12-24'** (typo-year sentinel, like NOLA's future-dated rows) — watermark query should clamp `< CURRENT_DATE`; tolerated as skew otherwise.
- 2026-08-23 — **OID-field surprise: every Detroit layer's objectIdField is `ObjectId`** (camelCase, NOT King County's `OBJECTID`). ArcGISClient reads it from layer metadata (`objectIdField or "OBJECTID"`), so pagination works unchanged; DatasetSpec.extra must carry `oid_field="ObjectId"`.
- 2026-08-23 — **DateOnly quirk confirmed live** on permits (`submitted_date`,`issued_date`), licenses (`expiration_date`), sales (`sale_date`): values arrive as `"YYYY-MM-DD"` strings; client's `_epoch_ms_to_iso` short-circuits on str (no-op) — parser-friendly. 311's `created_at` family is true `esriFieldTypeDate` epoch-ms → converted to ISO by the client. Pinned in docstring + tests.
- 2026-08-23 — **311 geometry-flattening answer**: moot — Improve Detroit rows carry flat `longitude`/`latitude` ATTRIBUTES, so chains match without dotted-path maps; `_flatten_feature`'s setdefault lift only matters when attrs are absent (geometry was null on the sampled newest row anyway). No client change needed, none made.
- 2026-08-23 — **Parser-chain resolution matrix (chains only; production passes city_id="detroit" explicitly)**:
  - PERMITS: lat/lng DIRECT ✓; `permit_type`→job_type ✓ ("Alteration"→A2); `issued_date`/`submitted_date` in date chains ✓; zip/neighborhood ✓. `record_id` matches NO id-chain term (checked permit_number/permit_nbr/permit_/job__/job_number/job_filing_number/id/application_number) → **whole feed xfails today on the id guard** until map entry `job_id→record_id`. `amt_permit_cost` not in cost chain → cost parses 0.0 pending map `cost→amt_permit_cost`.
  - 311: lat/lng ✓; `request_type`→complaint_type ✓; `created_at`→created_date ✓; status/zip/neighborhood ✓. `issue_id` not in incident-id chain → xfail pending `incident_id→issue_id`. `closed_at` not in closed-date chain → map `closed_date→closed_at`.
  - SLA: `business_name`→dba ✓; `license_type` literal ✓; `expiration_date` in expiration chain ✓; lat/lng ✓. `record_id` not in license-id chain → xfail pending `license_id→record_id`. NO effective/start/issue date exists on the feed at all → effective_date stays None by design; watermark is renewal-driven (`expiration_date`) — weak, documented.
  - DEEDS: lat/lng attrs present (unlike KC!) → FULL H3 events ✓; lowercase `grantor`/`grantee` keys hit party chains directly ✓ (Detroit attrs are lowercase, not PascalCase like KC — KC sniffing irrelevant; autodetect falls through to nyc but production passes city_id explicitly); `sale_date` in recorded-date chain ✓ (DateOnly string parses). `sale_id` not in doc-id chain → xfail pending `doc_id→sale_id`; `amt_sale_price` not in amount chain → map `document_amount→amt_sale_price`; `parcel_id` → map `bbl→parcel_id`.
- 2026-08-23 — **Metro bbox validated against live extents**: Hub dataset extent (Building Permits) = lat 42.2562–42.4500, lng -83.2874–-82.9111; live sales extremes: max_lat 42.44996, maxLng -82.9116 (null-coordinate rows exist — producer emits null-H3 events for them, same as Cook County). Adopted DETROIT_METRO_BBOX = 42.25–42.49 / -83.35–-82.88: contains all sampled coords incl. far-east Jefferson-Chalmers (-82.9511 seen) and clamps any adjacent-community spill on the sales view.
- 2026-08-23 — Licenses watermark decision: `expiration_date` (only DateOnly column). Roadmap's "modified-date granularity" caveat noted; renewals move it slowly.

## Proposed DatasetSpec extras (for orchestrator spine)

```python
# PERMITS — bseed_building_permits/FeatureServer/0
DatasetSpec(endpoint=<URL above>, platform="arcgis", watermark_col="issued_date",
    id_keys=["record_id", "id"], topic=settings.topic_permits, interval_seconds=300.0,
    producer_key="permits",
    extra={"oid_field": "ObjectId", "max_record_count": 1000,
           "field_map": {"job_id": ["record_id"], "cost": ["amt_permit_cost"]}})
# COMPLAINTS_311 — improve_detroit/FeatureServer/0
DatasetSpec(..., platform="arcgis", watermark_col="created_at",
    id_keys=["issue_id", "ObjectId", "id"], producer_key="311", interval_seconds=180.0,
    extra={"oid_field": "ObjectId", "max_record_count": 1000,
           "field_map": {"incident_id": ["issue_id"], "closed_date": ["closed_at"]}})
# SLA — bseed_active_business_licenses/FeatureServer/0
DatasetSpec(..., platform="arcgis", watermark_col="expiration_date",
    id_keys=["record_id", "id"], producer_key="sla", interval_seconds=600.0,
    extra={"oid_field": "ObjectId", "max_record_count": 1000,
           "field_map": {"license_id": ["record_id"],
                          # the shared license_type chain has NO bare
                          # 'license_type' term (falls through to
                          # 'On-Premises Liquor' default) — map it, with
                          # license_category as backup
                          "license_type": ["license_type", "license_category"]}})
# DEEDS — assessor_property_sales_view/FeatureServer/0
DatasetSpec(..., platform="arcgis", watermark_col="sale_date",
    id_keys=["sale_id", "liber_page", "ObjectId"], producer_key="deeds", interval_seconds=600.0,
    extra={"oid_field": "ObjectId", "max_record_count": 1000,
           "field_map": {"doc_id": ["sale_id"], "bbl": ["parcel_id"],
                          "document_amount": ["amt_sale_price"]}})
```

Aliases proposal: `{"detroit", "detroit_mi", "detroit-mi"}`; job_suffix `"detroit"`; center `{"lat": 42.3314, "lng": -83.0458}`.

## Current step

Done. Spine applied by orchestrator; all gates green.


## Next step

None. Interlock 17/17; city suite + full suite 390/390. xfail markers stripped post-spine (now hard assertions). Platform-routing note: Detroit's ArcGIS specs exposed that only the deeds producer exposed an arcgis client — the interlock completeness gate caught it and permits/311/SLA producers gained the same _client_for routing.
