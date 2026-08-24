# Stream log — city-dc — 2026-08-23

## Claim

- **Stream id:** `city-dc`
- **Leaf files I will create/edit:**
  - `src/spatial/cities/washington_dc.py`
  - `tests/unit/test_producers_dc.py`
  - `.streams/city-dc.md`
- **Spine files I expect to need:** `src/feeds/city_registry.py` (orchestrator applies; registration tests red until then — expected)

## Intent

Wave C3 (HAR-20): register Washington DC as city_id `"washington_dc"` with FOUR ArcGIS FeatureServer feeds over maps2.dcgis.dc.gov (PERMITS, COMPLAINTS_311 year-sliced; SLA licenses, DEEDS sales non-spatial). Deliver the spatial module (bbox, is_in, 7–8 divisions, 15–18 submarkets) and unit tests mirroring detroit/austin discipline. All endpoints probed live first.

## Decisions

- 2026-08-23T12:00Z — **Live probes (all URLs `https://maps2.dcgis.dc.gov/dcgis/rest/services/…`, probed 2026-08-23):**
  - `FEEDS/DCRA/FeatureServer?f=json` — currentVersion 11.5, maxRecordCount **2000**. Year layers: 2026=18, 2025=17, 2024=16, 2023=15 (+ older back to 2009; layer 4 = Last 30 Days, ignored). Layer 13 = Basic Business License *Points* (not used; we use table 0).
  - `DCGIS_DATA/ServiceRequests/FeatureServer?f=json` — maxRecordCount **1000**. Year layers: 2026=21, 2025=18, 2024=16, 2023=15, 2022=14 (older to 2009; 13=Last 90 Days, 17=Snow, 19=Current FY — ignored).
  - `DCGIS_DATA/Property_and_Land_WebMercator/FeatureServer/57` — "PROPERTY SALES (CAMA)", non-spatial table, OBJECTID OID, maxRecordCount 2000. Fields: SSL, SALE_DATE, SALE_PRICE, QUALIFIED, SALE_CODE, SALE_CURR_OWNER, ROW_NUMBER, GIS_LAST_MOD_DTTM. **No coordinates of any kind — SSL parcel key only** (parcel-join limitation documented in registry comment).
  - Layer metadata: `FEEDS/DCRA/FeatureServer/18` point, `…/0` table (INITIALISSUEDATE, LICENSESTARTDATE/ENDDATE, LICENSETYPE, CUSTOMERNUMBER, PREMISEADDRESS, PREMISEINDC), `ServiceRequests/21` point (ADDDATE, RESOLUTIONDATE, SERVICEREQUESTID, SERVICECODEDESCRIPTION, SERVICEORDERSTATUS, LATITUDE/LONGITUDE uppercase).
- 2026-08-23T12:10Z — **Recency verified newest-first** (`orderByFields=<col> DESC`, resultRecordCount=1): permits-2026 ISSUE_DATE→2026-08-17; 311-2026 ADDDATE→2026-08-23T23:41Z; DEEDS SALE_DATE→2026-08-12 ($496k, SSL 6093 0808); SLA INITIALISSUEDATE (where IS NOT NULL)→2026-08-05. Confirmed quirks: `returnCountOnly=true` → 400 "Query with count request failed"; naive python urllib requests with unencoded spaces also 400 ("Unable to perform query operation") — curl `-G --data-urlencode` works; pagination/order supported per advancedQueryCapabilities.
- 2026-08-23T12:15Z — **SLA coordinates are NOT usable**: fields LATITUDE/LONGITUDE exist but newest rows carry NULL or placeholder junk (live row: LATITUDE=39, LONGITUDE=-77 — not in DC!). Plus PREMISEINDC="No" out-of-state licenses exist (Randallstown MD row). Null-coords Cook County precedent confirmed and strengthened: events carry null lat/lng/H3; recommend PREMISEINDC='Yes' filtering upstream.
- 2026-08-23T12:20Z — **Year maps locked** (each entry probed with a DESC-order sample):
  - PERMITS endpoint_by_year: {"2023": …/FEEDS/DCRA/FeatureServer/15, "2024": …/16, "2025": …/17, "2026": …/18}
  - COMPLAINTS_311 endpoint_by_year: {"2022": …ServiceRequests/FeatureServer/14, "2023": …/15, "2024": …/16, "2025": …/18, "2026": …/21}
- 2026-08-23T12:25Z — **Proposed DatasetSpecs** (city_id WASHINGTON_DC/"washington_dc", state "DC", job_suffix "dc"; platform arcgis ×4; oid_field OBJECTID ×4):
  - PERMITS: endpoint=https://maps2.dcgis.dc.gov/dcgis/rest/services/FEEDS/DCRA/FeatureServer/18, watermark_col="ISSUE_DATE", id_keys=["PERMIT_ID","DCRAINTERNALNUMBER","OBJECTID"], topic=settings.topic_permits, interval 300, producer_key "permits", extra={"oid_field":"OBJECTID","max_record_count":2000,"endpoint_by_year":{above},"field_map":{"job_id":["PERMIT_ID"],"latitude":["LATITUDE"],"longitude":["LONGITUDE"],"issuance_date":["ISSUE_DATE"],"job_type":["PERMIT_TYPE_NAME","PERMIT_SUBTYPE_NAME"],"cost":["FEES_PAID"],"borough":["WARD"],"zipcode":["ZIPCODE"]}}
  - COMPLAINTS_311: endpoint=…/DCGIS_DATA/ServiceRequests/FeatureServer/21, watermark_col="ADDDATE", id_keys=["SERVICEREQUESTID","GLOBALID","OBJECTID"], interval 180, producer_key "311", extra={"oid_field":"OBJECTID","max_record_count":1000,"endpoint_by_year":{above},"field_map":{"incident_id":["SERVICEREQUESTID"],"latitude":["LATITUDE"],"longitude":["LONGITUDE"],"complaint_type":["SERVICECODEDESCRIPTION"],"created_date":["ADDDATE"],"closed_date":["RESOLUTIONDATE"],"status":["SERVICEORDERSTATUS"],"incident_address":["STREETADDRESS"],"borough":["WARD"],"zipcode":["ZIPCODE"]}}
  - SLA: endpoint=…/FEEDS/DCRA/FeatureServer/0, watermark_col="INITIALISSUEDATE", id_keys=["CUSTOMERNUMBER","GLOBALID","OBJECTID"], interval 600, producer_key "sla", extra={"oid_field":"OBJECTID","max_record_count":2000,"field_map":{"license_id":["CUSTOMERNUMBER"],"license_type":["LICENSETYPE"],"effective_date":["LICENSESTARTDATE"],"expiration_date":["LICENSEENDDATE"],"borough":["WARD"]}} — NON-SPATIAL: no lat/lng/H3 (Cook County precedent); LATITUDE fields exist but are null/sentinel garbage.
  - DEEDS: endpoint=…/DCGIS_DATA/Property_and_Land_WebMercator/FeatureServer/57, watermark_col="SALE_DATE", id_keys=["SSL","ROW_NUMBER","OBJECTID"], interval 600, producer_key "deeds", extra={"oid_field":"OBJECTID","max_record_count":2000,"field_map":{"doc_id":["ROW_NUMBER"],"bbl":["SSL"],"document_amount":["SALE_PRICE"],"recorded_date":["SALE_DATE"],"doc_type":["QUALIFIED"]}} — NON-SPATIAL, SSL parcel key only; H3 needs a future join to Parcel Lots (layer 33); registry comment must say so.
- 2026-08-23T12:30Z — Spatial module authored: DC_METRO_BBOX 38.79–38.995 / -77.12 – -76.909 (all four live samples contained: permit 38.9260,-77.0765; 311 38.9509,-77.0696; plus ward coverage). 8 divisions, 18 submarkets (see washington_dc.py).

## Current step

Done. Spine applied by orchestrator; all gates green; dashboard map wired per the city registration rule.


