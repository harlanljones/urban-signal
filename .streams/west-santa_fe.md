# Stream log — west-santa_fe — 2026-08-28

## Claim

- **Stream id:** west-santa_fe
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/santa_fe.py`
  - `apps/api/src/producers/field_maps_santa_fe.py`
  - `apps/api/tests/unit/test_producers_santa_fe.py`
- **Spine files I expect to need:** NONE

## Intent

Probe Santa Fe, NM for 1-4 official open-data feeds (permits, 311, SLA, deeds), verify live, build leaf files (city module, field maps, tests) if verified feeds exist. If no verifiable feeds, REJECT with evidence.

## Decisions

- 2026-08-28 — Phase A discovery: City of Santa Fe ArcGIS org `p0Gk2nDbPs7KEqSZ` (org name "City of Santa Fe", slug prefix "TheCityDifferent"), open data site `data-thecitydifferent.opendata.arcgis.com`. City site (santafenm.gov) is a CivicPlus site; no Socrata; `santafenm.maps.arcgis.com`/`santafe.maps.arcgis.com`/`data.santafenm.gov` all 404/transport-error (dead hints).
- 2026-08-28 — VERIFIED FEED (Tier 1): `CRM_Report_A_Problem_New_Public/FeatureServer/0` — 2,765 rows, point geometry, native WGS84 (outSR=4326 returns -105.99x/35.64x etc.), live watermark `CreationDate` (esriFieldTypeDate). Newest watermark on probe: `1787949766476` = 2026-08-28T20:42:46.476000+00:00 (today). Date range min 2026-04-10T14:01:42Z (1775829702327) → max 2026-08-28T20:42:46Z. 0 null geometries in full layer. Fields: objectid, globalid, problemtype, problem2, status, resolved_on (STRING — not a date field, always null), CreationDate, field_notes. problemtype domain (15 coded values): abandonedvehicle, arroyoriver, transit, encampments, graffiti, dumping, parking, parks, property, roads, streetlights, trash, utilities, weeds, other. status values: Submitted(34), Received(673), cs_only_resolved(2040), In progress(15), null(3). Status is a coded-value STRING; resolved_on is esriFieldTypeString (always null — not mapped). maxRecordCount 1000, no declared supportsOrderBy (orderByFields works — verified DESC query returns newest rows).
- 2026-08-28 — REJECTED city org feeds: `service_06e888807858433c8c54132d4465b54b` (old CRM feed, 37,870 rows) is the pre-2026 archive — stale (newest CreationDate 2026-08-24T18:46:15Z), no geometry on newest rows, redundant with New Public view. `ShortTermRentals2024_1` (1,239 rows) is an annual 2024 STR-license snapshot with no date/watermark column (Business_3 = year 2024 only) — static snapshot, not a live SLA feed (Greenville BusinessLicenses precedent). `ParcelsCity_1` (63,289 polygon parcels) and `Developments_Public_view` (80 polygon master-plan rows, PermitID mostly blank) are basemap/master-plan layers, not transactional. No building-permit feature layer exists in the org (searched permit/building/construction/complaint/case/application — only footprints, zoning, road closures).
- 2026-08-28 — Santa Fe County org `OrtlXpzQGtgBGqsz` (santafecountynm): 88 items, NO deeds/sales/assessor/permit/plat/recorded/license/inspection feeds found (all zero matches). No recorded-deeds feed reachable. Deeds NOT registered (partial without deeds is fine per ticket).
- 2026-08-28 — CONCLUSION: Santa Fe is a ONE-FEED PARTIAL metro: COMPLAINTS_311 only (the CRM "Report a Problem" public service-request surface). No permits feed, no SLA feed, no deeds feed in either city or county org.
- 2026-08-28 — Leaf files written: santa_fe.py (city module), field_maps_santa_fe.py (field maps), test_producers_santa_fe.py (33 tests). Tests pass, ruff clean, interlock stays 24 passed.

## Current step

Leaf build complete. Writing final outcome.

## Outcome

**Feeds verified: 1**
- **COMPLAINTS_311** (CRM_Report_A_Problem_New_Public): 2,765 rows, point geometry, native WGS84, 0 null geometries, watermark `CreationDate` (esriFieldTypeDate), newest = 2026-08-28T20:42:46Z. ArcGIS FeatureServer/0 hosted on `services7.arcgis.com/p0Gk2nDbPs7KEqSZ`, maxRecordCount=1000, orderByFields=CreationDate DESC.

**REJECTED:**
- Building permits: no feature layer in org (footprints only)
- SLA/STR: ShortTermRentals2024 is an annual snapshot, no watermark (Greenville precedent)
- Deeds: no feeds in city or county ArcGIS orgs

**Leaf files:**
- `apps/api/src/spatial/cities/santa_fe.py` — metro bbox, 6 divisions, 10 submarkets, FEED_SPECS w/ DatasetSpec-shaped dict, get_santa_fe_dataset()
- `apps/api/src/producers/field_maps_santa_fe.py` — COMPLAINTS_311_FIELD_MAP with incident_id, complaint_type, created_date, status; no borough/address/zip (Omaha discipline)
- `apps/api/tests/unit/test_producers_santa_fe.py` — 33 tests, 3 byte-verbatim live fixtures through real ArcGISClient flatten path

**Tests:** 33 passed, interlock 24 passed, ruff clean

## Spine delta

**Recommendation for spine registration:**
- `CityId.SANTA_FE` = "santa_fe" (new member)
- `ALIASES`: "santa_fe", "santa-fe", "santafe", "santa fe nm"
- `REGISTRY`: one entry `FeedType.COMPLAINTS_311` → DatasetSpec (endpoint, platform=arcgis, watermark_col=CreationDate, id_keys=["globalid"], topic=settings.topic_311, producer_key="311", interval_seconds=300, oid_field=objectid, max_record_count=1000, order_by="CreationDate DESC", needs_geocode=False, geocode_context="Santa Fe, NM", field_map=COMPLAINTS_311_FIELD_MAP)
- `METRO_META`: `{"city_id": "santa_fe", "name": "Santa Fe", "region": "West", "state": "NM", "lat": 35.6869, "lng": -105.9372, "zoom": 12, "county": "Santa Fe County"}`
- `config.py`: `endpoints.santa_fe_311 = "https://services7.arcgis.com/p0Gk2nDbPs7KEqSZ/arcgis/rest/services/CRM_Report_A_Problem_New_Public/FeatureServer/0"`
- Dashboard byte-sync per city-registration rule

## Next step

NONE — leaf build complete. Spine registration is FORBIDDEN here (concurrent spine agents in flight).