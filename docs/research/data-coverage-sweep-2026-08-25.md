# Data-coverage sweep — 2026-08-25

**Date of survey: 2026-08-25.** Four parallel research subagents probed
municipal open-data portals live (Socrata discovery API, ArcGIS Hub DCAT +
FeatureServer REST, CKAN datastore SQL, county auditor/register sites). Every
"register" verdict below is backed by a row-level or SQL-aggregate probe done
today; catalog `modified` metadata was never trusted alone (per the method in
`current-city-feed-gaps.md`). Prior research (`current-city-feed-gaps.md`,
`socrata-sweep.md`, `non-socrata-platforms.md`,
`nine-unidentified-metros-platform.md`, `mc311-geocode-evaluation.md`,
`metro-expansion-and-new-signals.md`, `deeds-watermark-audit.md`,
`new-orleans-austin-verification.md`) was read first and not duplicated; this
sweep closes the remaining README-matrix gap cells.

## Summary

| # | City | Feed | Verdict | Platform | Geocoding | Cadence |
|---|---|---|---|---|---|---|
| 1 | San Diego | 311 | register | CSV | native lat/lng 98% | daily |
| 2 | San Diego | Business Tax (SLA) | register | CSV | native lat/lng | daily snapshot |
| 3 | Cincinnati | Deeds | register | CSV | address-only → ADR 0004 | daily |
| 4 | Columbus | Deeds | register | ArcGIS | native point | annual snapshot |
| 5 | Baltimore / Montgomery / Prince George's | Deeds | register (one spine-hold) | Socrata (MD SDAT) | native lat/lng | monthly snapshot |
| 6 | Pittsburgh | Deeds | register | CKAN (WPRDC) | address-only | daily |
| 7 | Philadelphia | Deeds | register (upgrade) | CARTO | native point | where-filter `document_type='DEED'` |
| 8 | Nashville | 311 | register (upgrade) | ArcGIS | native lat/lng 71.5% | intraday |
| 9 | Pittsburgh | 311 | register (upgrade) | CKAN (WPRDC) | native lat/lng | intraday |
| 10 | Norfolk | Licenses | register (upgrade) | Socrata | native lat/lng 96% | daily |
| 11 | Kansas City | Licenses | register (upgrade) | Socrata | native point 96% | snapshot (~7mo lag) |
| 12 | Minneapolis | Licenses | register (upgrade) | ArcGIS | native lat/long | active |
| 13 | Austin | Licenses (TABC) | register (US-136, ADR 0004) | Socrata | none → geocode | daily |
| 14 | Boston | Licenses | register (US-137 Path A) | CKAN | State Plane EPSG:2249 → WGS84 | active |
| 15 | Milwaukee | Permits + Deeds | defer (lag + text watermark) | CSV | address-only | 2.3mo / yearly |
| 16 | Washington DC | Deeds | defer (parcel-join) | ArcGIS | non-spatial → join | batchy |
| — | Nashville, Kansas City, Charlotte, Baton Rouge, New Orleans, San Diego, Columbus, Milwaukee, PG, Denver | Deeds / 311 / Licenses | skip (confirmed absent) | — | — | — |

## Register findings

### 1. San Diego — 311 (Get It Done)

- **Endpoint:** `https://seshat.datasd.org/get_it_done_reports/get_it_done_requests_closed_2026_datasd.csv` (year-scoped; rolls `_2027_` per year, matching the permits `endpoint_by_year`). Companion open-queue: `get_it_done_requests_open_datasd.csv` (regenerated daily). Backfill: `get_it_done_requests_closed_<YYYY>_datasd.csv` 2016–2025.
- **Platform:** `csv` (`CSVClient`).
- **Schema (23 cols):** `service_request_id`, `date_requested` (watermark, ISO), `date_closed`, `status`, `service_name`/`service_name_detail`, `lat`, `lng`, `street_address`, `zipcode`, `council_district`, `comm_plan_name`.
- **id_keys:** `["service_request_id"]`.
- **Geocoding:** native `lat`/`lng` floats — 98.4% closed-2026, 98.9% open.
- **Freshness:** `date_requested` newest 2026-08-24 19:32 (closed) / 2026-08-24 23:58 (open); HTTP `Last-Modified` today.
- **Caveats:** closed-year file carries only Closed/Referred cases; the open file holds the freshest still-open new cases — wire the open file as `companion_endpoints`. `CSVClient` lowercases headers, so `field_map` columns must be lowercase.
- **Sketch:**
  - `config.py`: `csv_san_diego_311_endpoint = "https://seshat.datasd.org/get_it_done_reports/get_it_done_requests_closed_2026_datasd.csv"`.
  - `city_registry.py` `SAN_DIEGO.datasets[FeedType.COMPLAINTS_311]`: `platform="csv"`, `watermark_col="date_requested"`, `id_keys=["service_request_id"]`, `extra={"endpoint_by_year": {...}, "companion_endpoints": {"open": ".../get_it_done_requests_open_datasd.csv"}, "field_map": {"incident_id": ["service_request_id"], "created_date": ["date_requested"], "closed_date": ["date_closed"], "complaint_type": ["service_name","service_name_detail"], "latitude": ["lat"], "longitude": ["lng"], "incident_address": ["street_address"], "zipcode": ["zipcode"], "borough": ["council_district","comm_plan_name"]}}`.
  - `complaints_311_producer.py`: wire `CSVClient` (`self.csv = CSVClient()` + `"csv"` in `_client_for` — currently only `dob_permits_producer` has it); add a `service_request_id`/`sap_notification_number` → `san_diego` city-sniff branch.

### 2. San Diego — Business Tax Certificates (SLA)

- **Endpoint:** `https://seshat.datasd.org/business_tax_certificates/sd_businesses_active_datasd.csv` (active snapshot). Backfill: `sd_businesses_inactive_*` files; dictionary: `sd_businesses_dictionary_datasd.csv`.
- **Platform:** `csv`.
- **Schema (27 cols):** `account_key` (id, float-string — normalize `str(int(float(...)))`), `date_account_creation` (watermark), `date_cert_effective`, `date_cert_expiration`, `business_owner_name`, `dba_name`, `naics_sector`/`naics_code`/`naics_description`, `address_*`, `council_district`, `bid`, `lat`, `lng`.
- **id_keys:** `["account_key"]`.
- **Geocoding:** native `lat`/`lng`.
- **Freshness:** HTTP `Last-Modified` today; snapshot feed (judge by file refresh, not per-row dates — effective dates future-dated by design, like NYC SLA).
- **Caveats:** snapshot — full re-download each run, dedup on `account_key`; `ingestion_mode: "snapshot"`. NAICS 72 = hospitality for the LIMS SLA term (mirrors LA/SF business-registry scope).
- **Sketch:**
  - `config.py`: `csv_san_diego_licenses_endpoint = "https://seshat.datasd.org/business_tax_certificates/sd_businesses_active_datasd.csv"`.
  - `city_registry.py` `SAN_DIEGO.datasets[FeedType.SLA]`: `platform="csv"`, `watermark_col="date_account_creation"`, `id_keys=["account_key"]`, `extra={"ingestion_mode":"snapshot", "field_map": {"license_id":["account_key"], "effective_date":["date_cert_effective"], "expiration_date":["date_cert_expiration"], "license_type":["naics_description","naics_sector"], "dba":["dba_name"], "latitude":["lat"], "longitude":["lng"], "borough":["council_district","bid"]}}`.
  - `sla_licenses_producer.py`: wire `CSVClient` (verify not already wired).

### 3. Cincinnati — Deeds (Hamilton County Auditor)

- **Endpoint:** `https://www.hamiltoncountyauditor.org/download/transfer_dailysales_new.csv` (current month); prior month `transfer_priormonth_new.csv`; YTD `transfer_ytd_new.csv`; annual `transfer_files_ytd_<YYYY>.csv` 1998–2025.
- **Platform:** `csv` (static-file download; no REST API).
- **Schema:** `SaleAmount`, `MonthSale`/`DaySale`/`YearSale` (compose `SaleDate`), `PreviousOwner` (grantor), `OwnerName1`/`OwnerName2` (grantee), `ConveyanceNumber` (deed ref), `DeedType`, `PropertyNumber` (parcel), `House#`/`StreetName`/`StreetSuffix`, `LocationZipCode`, `Valid` (arms-length flag), `AppraisalArea`.
- **id_keys:** `["ConveyanceNumber","PropertyNumber"]` (multi-parcel sales share `ConveyanceNumber`).
- **Geocoding:** address-only → ADR 0004 (`House#`+`StreetName`+`StreetSuffix`+`LocationZipCode`+", Hamilton County, OH"). Deeds producer tolerates null lat/lng.
- **Freshness:** LIVE — current-month CSV has August 2026 sales; updated daily.
- **Caveats:** split-date composition (3 int cols → datetime); `$0`/`QC` non-market rows filtered by `Valid='Y'`; multi-parcel dedup needs `PropertyNumber`.
- **Sketch:**
  - `config.py`: `csv_cincinnati_deeds_endpoint = "https://www.hamiltoncountyauditor.org/download/transfer_dailysales_new.csv"`.
  - `city_registry.py` `CINCINNATI.datasets[FeedType.DEEDS]`: `platform="csv"`, `watermark_col="SaleDate"` (synthesized), `id_keys=["ConveyanceNumber","PropertyNumber"]`, `extra={"needs_geocode":True, "geocode_context":"Hamilton County, OH", "field_map": {"doc_id":["ConveyanceNumber"], "bbl":["PropertyNumber"], "document_amount":["SaleAmount"], "party1_grantor":["PreviousOwner"], "party2_grantee":["OwnerName1","OwnerName2"], "doc_type":["DeedType"], "incident_address":["House#","StreetName","StreetSuffix"], "zipcode":["LocationZipCode"], "borough":["AppraisalArea"]}}`.
  - `deeds_acris_producer.py`: wire `CSVClient`; add `ConveyanceNumber`/`PreviousOwner`/`OwnerName1`/`SaleAmount`/`DeedType` fallbacks; compose `SaleDate` client-side.

### 4. Columbus — Deeds (Franklin County Auditor)

- **Endpoint:** `https://services1.arcgis.com/7r2Wl09a1Apy459r/arcgis/rest/services/FCAO_Sales_Dashboard_Last_Years_Sales_Points/FeatureServer/0` (AGOL item `d2550387e1284da6a3704ba07b124b76`).
- **Platform:** ArcGIS FeatureServer (`ArcGISClient`, `outSR=4326` → WGS84).
- **Schema:** `PARCELID`, `SALEDATE` (epoch-ms, newest 2025-07-16), `SALEPRICE`/`Sale_Price`, `Transfer_Date` (NULL on recent), `Instrument_Number` (NULL on recent), `OWNERNME1` (grantor), `OWN1`/`OWN2` (grantee), `SITEADDRESS`, `ZIPCD`, point geometry, `LASTUPDATE`, `MUNINAME`/`NHBDNAME`.
- **id_keys:** `["PARCELID","Instrument_Number","OBJECTID"]` (effective `PARCELID`+`OBJECTID`).
- **Geocoding:** native point geometry via `outSR=4326`.
- **Freshness:** annual snapshot — `lastEditDate` 2026-07-31; layer name `DashboardSalesPtsJuly25`. G11 cadence = 365 days.
- **Caveats:** dual schema (old `OWNERNME1`/`SALEPRICE` vs new `OWN1`/`OWN2`/`Sale_Price`); `Instrument_Number`/`Transfer_Date` NULL on recent rows; 1,568 rows (validated subset).
- **Sketch:**
  - `config.py`: `arcgis_columbus_deeds_url = "https://services1.arcgis.com/7r2Wl09a1Apy459r/arcgis/rest/services/FCAO_Sales_Dashboard_Last_Years_Sales_Points/FeatureServer/0"`.
  - `city_registry.py` `COLUMBUS.datasets[FeedType.DEEDS]`: `platform="arcgis"`, `watermark_col="SALEDATE"`, `id_keys=["PARCELID","Instrument_Number","OBJECTID"]`, `extra={"expected_cadence_days":365, "oid_field":"OBJECTID", "max_record_count":2000, "field_map": {"doc_id":["Instrument_Number","PARCELID"], "bbl":["PARCELID"], "document_amount":["Sale_Price","SALEPRICE"], "recorded_date":["SALEDATE"], "party1_grantor":["OWNERNME1"], "party2_grantee":["OWN1","OWN2"], "incident_address":["SITEADDRESS"], "zipcode":["ZIPCD"], "borough":["MUNINAME","NHBDNAME"]}}`.

### 5. Baltimore + Montgomery + Prince George's — Deeds (MD SDAT)

One spine-hold (shared schema + shared `parse_watermark` `%Y.%m.%d` format prerequisite; all three touch `config.py`, `city_registry.py`, `deeds_acris_producer.py`, `watermarks.py`).

- **Endpoints (per-county SDAT "Real Property Assessments: Hidden Property Owner Names"):**
  - Baltimore: `https://opendata.maryland.gov/resource/3x3p-xk2v.json`
  - Montgomery: `https://opendata.maryland.gov/resource/kb22-is2w.json`
  - Prince George's: `https://opendata.maryland.gov/resource/w3eb-4mzd.json`
- **Platform:** Socrata (`opendata.maryland.gov` — NOT federated under `data.maryland.gov`; the real domain is `opendata.maryland.gov`). Statewide `ed4q-f8tm` has 241,619 Baltimore City parcels.
- **Schema:** `account_id_mdp_field_acctid` (parcel key), `sales_segment_1_consideration_mdp_field_considr1_sdat_field_90` (sale price, text), `sales_segment_1_grantor_name_mdp_field_grntnam1_sdat_field_80` (grantor), `sales_segment_1_transfer_date_yyyy_mm_dd_mdp_field_tradate_sdat_field_89` (watermark, text `YYYY.MM.DD`), `sales_segment_1_transfer_number_mdp_field_transno1_sdat_field_79` (transfer #), `mappable_latitude_and_longitude` (WGS84 Point), `mdp_latitude`/`mdp_longitude`, `county_name_mdp_field_cntyname`. Carries `sales_segment_2_*`/`_3_*` (prior two sales).
- **id_keys:** `["account_id_mdp_field_acctid","sales_segment_1_transfer_number_mdp_field_transno1_sdat_field_79"]`.
- **Geocoding:** native WGS84 Point — fully geocoded.
- **Freshness:** newest transfer 2026.07.24; `data_updated_at` 2026-08-05 (monthly snapshot).
- **Caveats:** per-parcel SNAPSHOT carrying last 3 sales (segment 1 = most recent) — NOT per-transaction; dedup across runs (a sale stays in segment 1 until superseded), `ingestion_mode: "snapshot"` (SF roll precedent). No grantee (SDAT records grantor only). **Text watermark `YYYY.MM.DD` — `parse_watermark` (`watermarks.py`) has no branch for this; a format addition is a prerequisite.** PG: this sidesteps the held `qzrv-2tnv` parcel table (MultiPolygon `the_geom` crash) entirely — the SDAT dataset is Point-geocoded and parses cleanly.
- **Sketch:**
  - `watermarks.py`: add a `%Y.%m.%d` format branch to `parse_watermark`.
  - `config.py`: `socrata_baltimore_deeds_endpoint`, `socrata_montgomery_deeds_endpoint`, `socrata_pg_deeds_endpoint` (the three URLs above).
  - `city_registry.py`: add `FeedType.DEEDS` `DatasetSpec` to each of `BALTIMORE`, `MONTGOMERY`, `PRINCE_GEORGES` — `platform="socrata"`, `watermark_col="sales_segment_1_transfer_date_yyyy_mm_dd_mdp_field_tradate_sdat_field_89"`, `id_keys=[...]`, `extra={"expected_cadence_days":30, "ingestion_mode":"snapshot", "field_map": {"doc_id":["account_id_mdp_field_acctid"], "bbl":["account_id_mdp_field_acctid"], "document_amount":["sales_segment_1_consideration_mdp_field_considr1_sdat_field_90"], "recorded_date":[...transfer_date...], "party1_grantor":[...grantor_name...], "latitude":["mappable_latitude_and_longitude.latitude"], "longitude":["mappable_latitude_and_longitude.longitude"]}}`.
  - `deeds_acris_producer.py`: city-sniff branches for the SDAT column presence; handle WKT Point string in lat/lng chain.
- **Note:** row-probe `kb22-is2w` and `w3eb-4mzd` before landing (Baltimore was row-sampled; Montgomery/PG share the statewide schema but were not per-county row-sampled today).

### 6. Pittsburgh — Deeds (WPRDC "Allegheny County Property Sale Transactions")

- **Endpoint:** `ckan://data.wprdc.org/5bbe6c55-bce6-4edb-9d04-68edeb6bf7b1` (package `real-estate-sales`, datastore-active, SQL enabled). Dump: `https://data.wprdc.org/datastore/dump/5bbe6c55-bce6-4edb-9d04-68edeb6bf7b1`.
- **Platform:** CKAN datastore (`CkanClient` — same as the registered Pittsburgh permits).
- **Schema:** `PARID` (parcel), `FULL_ADDRESS`, `PROPERTYHOUSENUM`/`PROPERTYADDRESSSTREET`/`PROPERTYCITY`/`PROPERTYSTATE`/`PROPERTYZIP`, `MUNIDESC` (municipality), `RECORDDATE` (watermark, ISO date), `SALEDATE`, `PRICE` (float), `DEEDBOOK`/`DEEDPAGE`, `SALECODE`/`SALEDESC` (validation), `INSTRTYP`/`INSTRTYPDESC`. Declared PK: `PARID, RECORDDATE, SALEDATE, DEEDBOOK, DEEDPAGE, INSTRTYP, PRICE, SALECODE`.
- **id_keys:** `["PARID","RECORDDATE","SALEDATE","DEEDBOOK","DEEDPAGE"]`.
- **Geocoding:** address-only / PARID-only (no lat/lng). Deeds producer tolerates null lat/lng (Cook County `wvhk-k5uv` precedent). Optional: PARID join to WPRDC parcel-assessments package for geometry (DC CAMA pattern).
- **Freshness:** `max(SALEDATE)=2026-08-24`, `max(RECORDDATE)=2026-08-24` (yesterday), `count=501,120`; ETL `last_etl_update` today. Daily.
- **Caveats:** `SALECODE` filter recommended ("H"=multi-parcel, "3"=love-and-affection are non-arm's-length); `PRICE` can be 0/1 on non-market; no grantor/grantee columns (parties null); recording lag after sale.
- **Sketch:**
  - `config.py`: `ckan_pittsburgh_deeds_endpoint = "ckan://data.wprdc.org/5bbe6c55-bce6-4edb-9d04-68edeb6bf7b1"`.
  - `city_registry.py` `PITTSBURGH.datasets[FeedType.DEEDS]`: `platform="ckan"`, `watermark_col="RECORDDATE"`, `id_keys=[...]`, `extra={"expected_cadence_days":7, "field_map": {"doc_id":["PARID","DEEDBOOK","DEEDPAGE"], "bbl":["PARID"], "document_amount":["PRICE"], "recorded_date":["RECORDDATE"], "doc_type":["INSTRTYP"], "borough":["MUNIDESC","PROPERTYCITY"], "address_street":["FULL_ADDRESS"]}}`.
  - `deeds_acris_producer.py`: Pittsburgh city-sniff branch (`"PARID" in row and "DEEDBOOK" in row`); `PRICE` to amount chain (or via field_map `document_amount`).

### 7. Philadelphia — Deeds (upgrade via where-filter, no source swap)

- **Endpoint:** unchanged — `carto://phl.carto.com/rtt_summary` (`config.py:423`).
- **Finding:** `rtt_summary` IS the price-bearing recorded-deeds source (Office of Realty Transfer Tax). The "mortgages → amount 0.0" caveat is a scope problem, not a source problem. `document_type='DEED'` = 1,100,426 rows, **95.3% with `total_consideration`** (vs. the current over-ingestion of mortgages/satisfactions with NULL price).
- **Schema:** unchanged (`document_type`, `total_consideration`, `recording_date` [watermark, already switched per `deeds-watermark-audit.md`], `document_date` [sentinel-poisoned, NOT watermark], `grantors`, `grantees`, `opa_account_num`, `the_geom` Point). id_keys `["document_id","cartodb_id","id"]` unchanged.
- **Sketch:**
  - `config.py`: no change.
  - `city_registry.py` PHILADELPHIA `FeedType.DEEDS` `DatasetSpec`: add `extra.where = "document_type = 'DEED'"` (CartoClient already applies `where`). Optionally `IN ('DEED','MISCELLANEOUS DEED','DEED SHERIFF','SHERIFF\'S DEED')` for completeness.
  - `deeds_acris_producer.py`: no change.
- **Acceptance:** the amount-0.0 mortgage noise drops from the stream; ~95% of DEED rows carry a real price.

### 8. Nashville — 311 (hubNashville, upgrades HJ-119 exclusion)

- **Endpoint:** `https://services2.arcgis.com/HdTo6HJqh92wn4D8/arcgis/rest/services/hubNashville_311_Service_Requests_Current_Year_view/FeatureServer/0` (AGOL item `7b7a79e0060e4f71b4e4de6abd9aff51`).
- **Platform:** ArcGIS Hub (FeatureServer, point, native WGS84 `wkid:4326`).
- **Schema:** `Request__` (id), `Latitude`/`Longitude`, `Date_Time_Opened` (watermark, epoch-ms), `Date_Time_Closed`, `Status`, `Request_Type`/`Subrequest_Type`, `Address`, `City`, `ZIP`, `Council_District`, `GlobalID`, `OBJECTID`.
- **id_keys:** `["Request__","GlobalID","OBJECTID"]`.
- **Geocoding:** native WGS84. 185,902 rows current-year; 52,997 (28.5%) `Latitude IS NULL` (no-location public-safety calls). With `where: Latitude IS NOT NULL` → 100% geocoded (Baltimore 311 precedent registers a 25% published gap).
- **Freshness:** `lastEditDate` today; newest `Date_Time_Opened` today. The registry comment "re-adjudicate before ever adding it" — this re-adjudication is positive (the Current_Year view now carries 2026 rows; the 2026-08-23 exclusion saw only a 2025 slice).
- **Sketch:**
  - `config.py`: `arcgis_nashville_311_url = "..."`.
  - `city_registry.py` `NASHVILLE.datasets[FeedType.COMPLAINTS_311]`: `platform="arcgis"`, `watermark_col="Date_Time_Opened"`, `id_keys=[...]`, `extra={"oid_field":"OBJECTID", "max_record_count":2000, "where":"Latitude IS NOT NULL", "field_map": {...}}`.

### 9. Pittsburgh — 311 (new WPRDC dataset, upgrades address-only-archive verdict)

- **Endpoint:** `ckan://data.wprdc.org/5202679a-d243-402e-b82a-63189995a942` (package `8069a170-92d1-4f5e-bc03-327bcf262545`, resource "311 Data"). Dump: `https://data.wprdc.org/datastore/dump/5202679a-d243-402e-b82a-63189995a942`.
- **Platform:** CKAN datastore.
- **Schema:** `unique_id` (id), `case_number`, `subject` (category), `created_date_utc` (watermark), `closed_date_utc`, `status`, `latitude`/`longitude` (text, 5-dec EXACT or 2-dec APPROXIMATE), `geo_accuracy`, `neighborhood`, `council_district`, `ward`, `street`, `city`.
- **id_keys:** `["unique_id","case_number"]`.
- **Geocoding:** native lat/lng; newest-window rows ~100% geocoded (legacy 2015–2025 rows have null coords).
- **Freshness:** `last_modified` today; newest `created_date_utc` today (intraday). 963,380 rows.
- **Caveats:** this NEW dataset was created 2025-12-19 after the city's 311 system transition; the OLD archive (`a8f7a1c2-…`/`29462525-…`) is frozen at 2025-02-04 — that dead archive is the source of the README's "address-only archive" verdict, now obsolete.
- **Sketch:**
  - `config.py`: `ckan_pittsburgh_311_endpoint = "ckan://data.wprdc.org/5202679a-d243-402e-b82a-63189995a942"`.
  - `city_registry.py` `PITTSBURGH.datasets[FeedType.COMPLAINTS_311]`: `platform="ckan"`, `watermark_col="created_date_utc"`, `id_keys=[...]`, `extra={"field_map": {...}}` (lat/lng text → `float()` cast, already done by producer).

### 10. Norfolk — Business Licenses (upgrades no-geometry verdict)

- **Endpoint:** `https://data.norfolk.gov/resource/dpi6-sct5.json` (Socrata).
- **Schema:** `trading_as_name`, `naics`, `primary_owner`, `location_address`, `business_opened_date` (watermark), `latitude`/`longitude`/`geocoded_point`, `census_tract`.
- **id_keys:** `["trading_as_name","primary_owner","business_opened_date"]`.
- **Geocoding:** native lat/lng. 7,256/10,100 (71.8%) carry coords; 2,558 (25.3%) are the placeholder `"NO NORFOLK ADDRESS REQUIRED 99999"` (special-event/no-fixed-premises). With `where: location_address != 'NO NORFOLK ADDRESS REQUIRED 99999'` → 96.2% geocoded. The city added these columns (its own geocoding of `location_address`) — the Wave G2 "no geometry" verdict is obsolete.
- **Freshness:** `rowsUpdatedAt` today; newest `business_opened_date` today.
- **Sketch:**
  - `config.py`: `socrata_norfolk_licenses_endpoint = "https://data.norfolk.gov/resource/dpi6-sct5.json"`.
  - `city_registry.py` `NORFOLK.datasets[FeedType.SLA]`: `platform="socrata"`, `watermark_col="business_opened_date"`, `id_keys=[...]`, `extra={"where":"location_address != 'NO NORFOLK ADDRESS REQUIRED 99999'", "field_map": {...}}`.

### 11. Kansas City — Business Licenses (upgrades no-endpoint verdict)

- **Endpoint:** `https://data.kcmo.org/resource/pnm4-68wg.json` (Socrata).
- **Schema:** `id`, `business_type`, `address`, `city`, `state`, `zipcode`, `business_name`, `dba_name`, `valid_license_for` (text `YYYYMMDD` expiration), `location` (point, 96.4% non-null).
- **id_keys:** `["id"]`.
- **Geocoding:** native `location` point at 96.4%.
- **Freshness:** `rowsUpdatedAt` 2026-01-15 (~7mo stale — likely a publishing lapse); metadata claims daily. `valid_license_for` distribution: 22,986 `20251231` (expired 2025), 1,599 `20261231` (current 2026).
- **Caveats:** snapshot feed — register `ingestion_mode: "snapshot"` (Baton Rouge businesses precedent); `expected_cadence_days: 90` given the lapse. The `scripts/rejection_recheck.py` `kc_sla` claim "location field only, no date column" is OBSOLETE — update watch_patterns to include `valid_license` or remove the entry.
- **Sketch:**
  - `config.py`: `socrata_kansas_city_licenses_endpoint = "https://data.kcmo.org/resource/pnm4-68wg.json"`.
  - `city_registry.py` `KANSAS_CITY.datasets[FeedType.SLA]`: `platform="socrata"`, `watermark_col=""`, `id_keys=["id"]`, `extra={"expected_cadence_days":90, "ingestion_mode":"snapshot", "field_map": {"license_id":["id"], "license_type":["business_type"], "expiration_date":["valid_license_for"], "dba":["dba_name"], "latitude":["location.latitude"], "longitude":["location.longitude"], "borough":["city"], "zipcode":["zipcode"]}}`.

### 12. Minneapolis — Liquor Licenses (upgrades no-endpoint verdict)

- **Endpoint:** `https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services/On_Sale_Liquor/FeatureServer/0` (AGOL item `5042131de56d44749f6e43c0b5738b21`). Companion: `Off_Sale_Liquor/FeatureServer/0`.
- **Platform:** ArcGIS FeatureServer (point, native lat/long).
- **Schema:** `licenseNumber` (id), `licenseType`, `licenseStatus`, `liquorType`, `issueDate` (watermark, epoch-ms), `expirationDate`/`expirationYear`, `licenseName`, `address`, `endorsements`, `ward`, `neighborhood`, `lat`/`long`, `lastUpdateDate`.
- **id_keys:** `["licenseNumber","OBJECTID"]`.
- **Geocoding:** native `lat`/`long`.
- **Freshness:** `lastEditDate` in August 2026 (actively maintained).
- **Caveats:** narrow scope (On/Off Sale liquor only, like Milwaukee's registered SLA — precedent set). Register `Off_Sale_Liquor` as `companion_endpoints` (Montgomery permits precedent).
- **Sketch:**
  - `config.py`: `arcgis_minneapolis_licenses_url = "..."`.
  - `city_registry.py` `MINNEAPOLIS.datasets[FeedType.SLA]`: `platform="arcgis"`, `watermark_col="issueDate"`, `id_keys=[...]`, `extra={"oid_field":"OBJECTID", "max_record_count":16000, "companion_endpoints":{"off_sale":".../Off_Sale_Liquor/FeatureServer/0"}, "field_map": {"license_id":["licenseNumber"], "license_type":["licenseType","liquorType"], "effective_date":["issueDate"], "expiration_date":["expirationDate"], "latitude":["lat"], "longitude":["long"], ...}}`.

## Defer findings (clear unblock path)

### 13. Austin — TABC (`7hf9-qc9f`)

- **Endpoint:** `https://data.texas.gov/resource/7hf9-qc9f.json`. Socrata, 126,457 rows statewide (Travis County subset 6,304).
- **Schema:** `license_id`/`master_file_id`, `license_type`, `current_issued_date` (watermark), `expiration_date`, `trade_name`, `owner`, `address`/`address_2`/`city`/`state`/`zip`/`county`. **No coordinate columns** (confirmed).
- **Implementation:** US-136 registers the Travis County slice with `where: county='Travis'`, `needs_geocode: True`, and `geocode_context: "TX"`. The shared SLA producer invokes the ADR 0004 geocoder for the address-only rows.

### 14. Boston — Licensing Board (`04dc653b`)

- **Endpoint:** `ckan://data.boston.gov/04dc653b-1789-4374-9669-b07df7233344` (registered by US-137). The live datastore reports 3,628 records and fields `license_num`, `license_category`/`license_type`, `issued`, `expires`, `business_name`/`dba_name`, `address`/`city`/`state`/`zip`, `gpsx`, and `gpsy`.
- **Coordinate verification:** live rows and the acceptance sample use Massachusetts Mainland State Plane US survey feet, EPSG:2249. `pyproj.Transformer.from_crs("EPSG:2249", "EPSG:4326", always_xy=True)` maps `gpsx=764720.25`, `gpsy=2940110.43` to approximately `(-71.0986, 42.3151)`. The earlier EPSG:26986-meter label was incorrect.
- **Implementation:** US-137 Path A transforms the source coordinates in `sla_licenses_producer.py`; the field map uses the live CKAN names and `expires` as the text watermark.

### 15. Milwaukee — Permits + Deeds

- **Permits** (`buildingpermits` CSV, 16,685 rows): `Date Issued` watermark (newest 2026-06-15 — ~2.3-mo lag, confirms prior research), address-only (`Address`), `Record ID` id. Sparse 9-col schema; `Construction Total Cost` is 0.00 on sampled rows.
- **Deeds** (`property-sales-data`, yearly CSV): 2025 file `armslengthsales_2025_valid_20260417.csv` (5,685 rows, newest `Sale_date` **12/31/2025** — corrects the prior `2025-09-09` lexicographic-max trap). `Sale_price` present; address-only; `Sale_date` is `M/D/YYYY` text (NOT lexicographically sortable — `CSVClient` string-compare breaks; needs date-aware compare or snapshot re-download). 2026 file won't publish until ~April 2027 (8–16mo stale).
- **Unblock path:** geocoding wave (ADR 0004) + `M/D/YYYY` watermark format + a decision to accept 90-day/365-day cadence exceptions. Permits is the better live signal of the two (2.3mo beats 8mo).

### 16. Washington DC — Deeds parcel-join (now fully specified)

- **CAMA sales (already registered):** layer 57 `PROPERTY SALES (CAMA)` table in `DCGIS_DATA/Property_and_Land_WebMercator/FeatureServer` (`https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Property_and_Land_WebMercator/FeatureServer/57`). Non-spatial; `SSL`, `SALE_DATE`, `SALE_PRICE`, `QUALIFIED`, `ROW_NUMBER`.
- **Parcel geometry (for the join):** layer 33 `Parcel Lots` polygon in the SAME service (`.../FeatureServer/33`). Fields: `SSL` (join key), `SQUARE`/`SUFFIX`/`LOT`/`QUADRANT`, `LOT_TYPE`, `STATUS`, polygon `SHAPE`, `OBJECTID`. `maxRecordCount: 2000`.
- **Join:** key = `SSL` (present on both layers). Layer 33 polygon → centroid (King County `PARCEL_SALES3YR_AREA_287` precedent in `arcgis_client`). Same service, one `ArcGISClient` serves both.
- **Sketch:** add `extra.parcel_join = {"parcel_layer": <layer 33 URL>, "join_key": "SSL", "geometry_source": "centroid"}`; flip `non_spatial` to `False` once wired; no field-map change. The current non-spatial registration stays valid under the deeds-precedent tolerance.

## Confirm-skip findings (no issue; update README/research where verdict changed)

- **Nashville deeds** — Hub catalog has only eBid surplus auctions + marriage records; no property deed sales. README accurate.
- **Kansas City deeds** — Zero AGOL property-sales results; city Socrata car-auction trap; county GIS not found. README accurate.
- **Charlotte deeds** — `gis.charlottenc.gov/arcgis/rest/services/CountyData/Parcels` is cadastral-only (no sales attrs); POLARIS is interactive-only; AGOL "Property Sales" is a 2012 web map. **Update README cell "Mecklenburg Hub unverified" → "verified — no sales feed".**
- **Baton Rouge deeds** — EBR Clerk of Court is paid-subscription (`clerkconnect.com`); EBR Assessor unreachable. LA-deeds-skip precedent. README accurate.
- **New Orleans deeds (price substitute)** — No price-bearing substitute on `data.nola.gov`; Sheriff Sales has `SaleAmount` but frozen at 2018 + foreclosure-only (worse than the live NORA feed). Orleans Assessor 403-unreachable → price-substitute `unverified`. NORA caveat-registration stays.
- **San Diego deeds** — No transaction-level sales at city/county/Assessor level. LA-deeds-skip precedent. README accurate.
- **Columbus 311** — 69-dataset Hub catalog + ArcGIS Server root have no 311/service-request; `311.columbus.gov` is a lookup app. README accurate.
- **Milwaukee 311** — CKAN `q=311` returns 2 irrelevant datasets. README accurate.
- **Prince George's licenses** — Socrata `q=license` returns Food Inspection + Day Cares only. README accurate.
- **Columbus licenses** — No license/business dataset in Hub or ArcGIS Server root. README accurate.
- **Charlotte licenses** — NBS folder has only StreetAdoption; CountyData has no license layer. README accurate.
- **Denver licenses** — `ODC_active_business_licenses/FeatureServer/31` is a non-spatial table with NO coordinates AND NO address field (fails G5/G8 by construction). **Update README cell "licenses lack issue dates" → "no coordinates AND no address (non-spatial reference table)".**

## Corrections to prior research

- **Milwaukee deeds newest sale date:** `nine-unidentified-metros-platform.md` says "newest sale 2025-09-09"; true newest is **12/31/2025** (lexicographic-max on `M/D/YYYY` text — the same trap `current-city-feed-gaps.md` documents for NYC `issuance_date`).
- **KC SLA `pnm4-68wg`:** `wave-2-city-candidates.md` / `rejection_recheck.py` rejection "location field only, no date column at all" is OBSOLETE — the feed now has `location` (96.4%) and `valid_license_for`.
- **Pittsburgh 311:** README "address-only archive" applied to the dead `a8f7a1c2-…` archive (frozen 2025-02-04); the new `5202679a-…` dataset (created 2025-12-19) is fully geocoded and intraday.
- **Norfolk SLA:** Wave G2 "no geometry" is obsolete — the city added `latitude`/`longitude`/`geocoded_point`.
- **Philly deeds:** README "mortgages → amount 0.0" is a scope problem (over-ingestion), not a source problem — `rtt_summary` is price-bearing for `document_type='DEED'`.

## Honesty / limits

Probed live 2026-08-25 via direct HTTP/SQL: MD SDAT (Baltimore row-sampled; Montgomery/PG share statewide schema, not per-county row-sampled — row-probe before landing), Pittsburgh WPRDC (SQL aggregates + samples), DC FeatureServer layers 57/33, Philly CARTO `document_type` distribution, NOLA catalog, San Diego County Socrata, Nashville/Pittsburgh/Norfolk/Austin/KC/Minneapolis/Denver/Boston metadata + samples, Columbus/Charlotte ArcGIS enumeration, Milwaukee CKAN.

Could NOT reach: Orleans Parish Assessor (HTTP 403 — NOLA price-substitute `unverified`); EBR Parish Assessor (transport error — skip stands on the paid Clerk alone); Franklin County Auditor website (403 — FeatureServer answered anonymously); Mecklenburg County GIS REST path (404 — joint Charlotte/Meck server `gis.charlottenc.gov` covers county data under `CountyData/`, no sales layer); statewide MD Comptroller / Ohio liquor / NC ABC (not probed — likely search portals, not bulk feeds).

Method limits consistent with `current-city-feed-gaps.md`: Socrata catalog metadata trusted for columns, never for freshness; every `register` is backed by a live row/SQL probe. Text-typed watermarks (`YYYY.MM.DD` MD SDAT, `M/D/YYYY` Milwaukee deeds, `YYYYMMDD` KC SLA) need format-aware handling — flagged per finding.
