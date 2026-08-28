# Stream log — west-long_beach — 2026-08-28

## Claim

- **Stream id:** `west-long_beach`
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/long_beach.py`
  - `apps/api/src/producers/field_maps_long_beach.py`
  - `apps/api/tests/unit/test_producers_long_beach.py`
- **Spine files I expect to need:** NONE (spine hold for CityId.LONG_BEACH is a
  separate dispatch; this leaf prepares evidence + FEED_SPECS for it)

## Intent

Live-probe official Long Beach, CA open-data feeds (OpenDataSoft
datalongbeach.opendatasoft.com per US-224; also check cityoflongbeach.gov),
verify 1-4 feeds with row counts + watermarks + geometry, then build the three
leaf files (city module, field maps, producer tests) matching the
DatasetSpec/greenville patterns. No spine edits, no commits.

## Decisions

- 2026-08-28 — US-224's cited portal `datalongbeach.opendatasoft.com` is DEAD: live probe returns Huwise branded "This domain could not be found" page (HTTP 404, both /api/explore/v2.1 and /api/v2 paths). OpenDataSoft rebranded to Huwise; the domain was decommissioned. The portal MIGRATED to `https://data.longbeach.gov/explore/` (same ODS/Huwise platform, custom domain) — that is the official door now.
- 2026-08-28 — IMPORTANT SPINE FACT: `city_registry.py:798-799` currently aliases `"long_beach"` and `"long beach"` to `CityId.LOS_ANGELES`. The future spine hold must REMOVE those two aliases when adding `CityId.LONG_BEACH` to CityId + REGISTRY (otherwise `normalize_city("long_beach")` still resolves to LA). Recommended Linear comment must call this out.
- 2026-08-28 — SPINE-PIN FACT: `tests/unit/test_city_leaf_naming.py::test_all_expected_leaf_modules_present` pins `len(_LEAF_MODULES) == 97`; branch currently has 101 leaf modules (pre-existing failure from concurrent waves — NOT caused by this leaf). Adding long_beach.py makes it 102. Test is NOT interlock-marked (interlock baseline today: 24 passed). Spine should bump the pin when registering. This leaf does not touch the spine file.
- 2026-08-28 — SPINE FACT: no OpenDataSoft/Huwise client exists in `src/producers/` (clients: arcgis, socrata, ckan, csv, carto, excel, snapshot, ...). The verified 311 feed cannot be ingested at leaf. Platform-gap follow-up recommended to spine.

## Phase A — probe results (2026-08-28, all live)

### VERIFIED FEED 1 — SLA: Business Licenses (ArcGIS)
- Endpoint: `https://services6.arcgis.com/yCArG7wGXGyWLqav/arcgis/rest/services/Business_Licenses_Public_View/FeatureServer/0` (layer 0 "BusinessLicenses_DailyUpdate"; org `arcgis_clb` = City of Long Beach; item 54d45ca9c4554062a02df49ec1ea2b2a)
- Platform: arcgis (hosted FeatureServer, maxRecordCount 2000)
- Rows: 178,826 total (MILESTONEDATE non-null n=178,802); OUTSIDECITY='No' 133,946 / 'Yes' 44,878
- Watermark: `MILESTONEDATE` (esri Date, epoch-ms) — newest verbatim `1787817600000` = 2026-08-27T08:00:00+00:00; 1,337 rows with MILESTONEDATE >= date '2026-08-20' → daily cadence
- `ISSDTTM` is FUTURE-DATE SENTINEL-POISONED (max `38886854400000` = year 3202; min 1800) — never the watermark
- Columns: OBJECTID(OID), LICENSENO, LICCATDESC, LICSTATUS, DBANAME, ISSDTTM(Date), INACTVDTTM(Date), MILESTONEDATE(Date), MILESTONE, FULLNAME, SITELOCATION, ZIP, COMPANYTYPE, NUMEMP, NUMUNITS, PRINTPRODUCTTYPES, HOMEBASED, INDCNTR, CLASSDESC, BLLICEXEMPT, OUTSIDECITY, BID_NAME(_1, _12), COUNCIL_NUMBER(Integer), TRACT, CDBG, MILESTONE_SIMPLE
- Geometry: native point; outSR=4326 lifts clean WGS84 for in-city rows (fixtures: -118.201/33.806, -118.148/33.764, -118.193/33.853). Some rows carry junk off-map geocodes (x≈-138, y≈27 — off Baja) and ~0.1% null geometry (2/2000 sampled) → ADR-0004 geocode on SITELOCATION. Downstream metro scoping handles junk-coord rows (Greenville/SNAP precedent).
- Where-queryable: `MILESTONEDATE >= date '2026-08-20'` works; composes with `OUTSIDECITY='No'` (3,867 rows since 08-01)
- PII: FULLNAME is the license-holder name — not mapped.

### VERIFIED FEED 2 — CRIME: LBPD Crime Mapping (ArcGIS)
- Endpoint: `https://services6.arcgis.com/yCArG7wGXGyWLqav/arcgis/rest/services/Police_Crime_Mapping/FeatureServer/0` (layer 0 "CrimeData"; item db3defed7a894a6088b98ec16b4b5dfa)
- Platform: arcgis (hosted FeatureServer, maxRecordCount 2000)
- Rows: 11,012 (≈6-month rolling window: min ReportedDateTimeDate 2026-02-18T08:44:07+00:00)
- Watermark: `ReportedDateTimeDate` (esri Date epoch-ms) — newest verbatim `1787106060000` = 2026-08-19T02:21:00+00:00 (probe day 2026-08-28 → ~9d publish lag; 265 rows since 2026-08-10 → batched publishing)
- `ReportedDateTime` is a plain string ("08/18/2026 07:21 PM") — not the watermark
- Columns: OBJECTID(OID), DR(report number), Type, Category, CrimeType, ReportedDateTime(String), ReportedDateTimeDate(Date), Address(block string), Division, Beat, ReportingDistrict, DaysOld(Integer), DayOfWeek, HourOfDay(SmallInteger)
- Geometry: native point WGS84 (newest fixtures: -118.146/33.828, -118.180/33.793, -118.173/33.783) — **ADR-0004 crime gate satisfied by native coordinates**; needs_geocode stays false
- IDs: DR + OBJECTID

### VERIFIED FEED 3 (not registrable at leaf) — 311: service-requests (OpenDataSoft/Huwise)
- Endpoint: `https://data.longbeach.gov/api/explore/v2.1/catalog/datasets/service-requests`
- Rows: 346,300; watermark `createddate` newest verbatim `2026-08-28T17:50:01+00:00` (intraday-fresh)
- Columns: casenumber, type, status, createddate, closeddate, citydistrict_c, zipcode_c, geolocation (geo_point_2d native lat/lon), days_to_close, age_open, escooter_issue_c, escooter_operator_c, observed_time
- BLOCKER: no OpenDataSoft client in repo; CSV export route is semicolon-delimited (CSVClient is comma dialect) and full-file (~346k rows) per pull. Spine follow-up: an ODS client or a where-parameterized export path.

### REJECTED / SKIPPED (evidence)
- PERMITS: no live permit register exists publicly. `Bldg_Permits_5th_Cycle_RHNA_2020` FeatureServer = RHNA compliance aggregate; `Development_Projects_(Public)` = 61-row planning snapshot (layer `ProjectInfo_5_2026_Geocoded`, manually maintained). Both skipped (aggregates/snapshots rule).
- DEEDS (LA County recorder): `data.lacounty.gov` HTML-reachable but its Socrata API endpoints 404 (catalog/API dead); `lavote.gov` records-services has no open-data API. No verifiable recorded-deeds feed. Partial registration without deeds is acceptable per ticket.
- `Cannabis_BusinessLicenses` (6 layers, 74-218 rows each): sub-slice of the general BL feed — skipped.
- Stale mirrors: none used; `datalongbeach.opendatasoft.com` dead domain documented above.

## Current step

DONE — all phases complete. Stream ready for closeout/dispatch review.

## Next step

None for this leaf. Spine hold (separate dispatch) should execute the
Spine delta below.

## Outcome

**REGISTER (partial, 2 feeds) — recommend.** Ticket's portal hint was dead
(datalongbeach.opendatasoft.com → Huwise 404; official portal migrated to
`data.longbeach.gov`), so the probe re-dered the city on its hosted ArcGIS
org (`services6.arcgis.com/yCArG7wGXGyWLqav`, owner `arcgis_clb`) and the
new portal. No stale mirror used anywhere.

Feeds verified live 2026-08-28 (full evidence in Decisions/Phase A above):

| Feed | Endpoint | Rows | Watermark (newest verbatim) | Geometry |
|---|---|---|---|---|
| SLA | `.../Business_Licenses_Public_View/FeatureServer/0` | 178,826 (133,946 in-city via `OUTSIDECITY='No'`) | `MILESTONEDATE` = `1787817600000` (2026-08-27T08:00:00+00:00) | native point WGS84; ~0.1% null → ADR-0004 geocode |
| CRIME | `.../Police_Crime_Mapping/FeatureServer/0` | 11,012 (~6-mo rolling window) | `ReportedDateTimeDate` = `1787106060000` (2026-08-19T02:21:00+00:00) | native point WGS84 (ADR-0004 natively satisfied) |

Not registered (evidence recorded): 311 `service-requests` on
data.longbeach.gov — feed VERIFIED (346,300 rows, `createddate` newest
`2026-08-28T17:50:01+00:00`, native lat/lon) but no OpenDataSoft client
exists in-repo and the CSV export route is semicolon-dialect full-file;
PERMITS — only RHNA compliance aggregate + 61-row Development Projects
snapshot exist; DEEDS — LA County recorder publishes no queryable API
(data.lacounty.gov Socrata endpoints 404; lavote.gov no API);
Cannabis_BusinessLicenses — sub-slice of the BL feed.

Leaf build (all ruff-clean, all spine-stable):
- `apps/api/src/spatial/cities/long_beach.py` — metro bbox, 8 divisions /
  10 submarkets (Downtown Shoreline, East Village, Belmont Shore, Belmont
  Heights, Naples, Cambodia Town, Wrigley, Bixby Knolls, California
  Heights, North Long Beach), LONG_BEACH_FEED_SPECS, get_long_beach_dataset,
  REGISTRATION. Docstring = full registration evidence.
- `apps/api/src/producers/field_maps_long_beach.py` — SLA_FIELD_MAP +
  CRIME_FIELD_MAP; FULLNAME dropped as PII; no native-coordinate candidates
  (geometry lift only).
- `apps/api/tests/unit/test_producers_long_beach.py` — 49 tests, 3
  byte-verbatim SLA fixtures + 3 CR fixtures through the real
  ArcGISClient._flatten_feature → producer parse path.

Verification (2026-08-28, from apps/api):
- `pytest tests/unit/test_producers_long_beach.py -q` → **49 passed**
- `pytest -k long_beach -q` → **51 passed**
- `pytest -m interlock -q` → **24 passed** (unchanged)
- `ruff check` on all three files → clean
- test_city_leaf_naming: canonical-constants for long_beach pass; the
  97-pin `test_all_expected_leaf_modules_present` failure is PRE-EXISTING
  (was 101-vs-97 before this leaf; now 102-vs-97) — spine bump required.

## Spine delta (exact edits for the spine hold)

1. **CityId member** (city_registry.py enum, append after TUCSON):
   `LONG_BEACH = "long_beach"`
2. **Aliases** — REMOVE the two LA aliases at city_registry.py:798-799
   (`"long_beach": CityId.LOS_ANGELES`, `"long beach": CityId.LOS_ANGELES`)
   and ADD a `# Long Beach, CA` block:
   `"long_beach"`, `"long beach"`, `"lb_ca"`, `"lbc"` → `CityId.LONG_BEACH`.
   Without the removal, `normalize_city("long_beach")` keeps resolving to LA.
3. **Imports** (city_registry.py):
   `from src.producers.field_maps_long_beach import CRIME_FIELD_MAP, SLA_FIELD_MAP`
   and `from src.spatial.cities.long_beach import (LONG_BEACH_DIVISIONS,
   LONG_BEACH_DIVISION_BBOXES, LONG_BEACH_METRO_BBOX, LONG_BEACH_SUBMARKETS)`.
4. **Registry entry**: CityRegistration(city_id=CityId.LONG_BEACH,
   name="Long Beach", state="CA", center={"lat": 33.7695, "lng": -118.1930},
   metro_bbox=LONG_BEACH_METRO_BBOX, division_bboxes=LONG_BEACH_DIVISION_BBOXES,
   submarkets=LONG_BEACH_SUBMARKETS, divisions=LONG_BEACH_DIVISIONS,
   job_suffix="long_beach", datasets={FeedType.SLA: DatasetSpec(endpoint=
   LONG_BEACH_SLA_ENDPOINT, platform="arcgis", watermark_col="MILESTONEDATE",
   id_keys=["LICENSENO","OBJECTID"], topic=settings.topic_sla,
   interval_seconds=600.0, producer_key="sla", expected_cadence_days=3,
   needs_geocode=True, geocode_context="Long Beach, CA", oid_field="OBJECTID",
   max_record_count=2000, order_by="MILESTONEDATE DESC",
   where="OUTSIDECITY='No'", field_map=SLA_FIELD_MAP), FeedType.CRIME:
   DatasetSpec(endpoint=LONG_BEACH_CRIME_ENDPOINT, platform="arcgis",
   watermark_col="ReportedDateTimeDate", id_keys=["DR","OBJECTID"],
   topic=settings.topic_crime, interval_seconds=1800.0, producer_key="crime",
   expected_cadence_days=14, oid_field="OBJECTID", max_record_count=2000,
   order_by="ReportedDateTimeDate DESC", field_map=CRIME_FIELD_MAP)})
   — or copy LONG_BEACH_FEED_SPECS verbatim per the greenville pattern.
5. **cities/__init__.py**: export the long_beach module symbols (existing pattern).
6. **config.py**: NO new endpoint settings needed (endpoints are leaf
   constants; topics exist). 
7. **test_city_leaf_naming.py**: bump the module-count pin 97 → current
   count (102 after this leaf; re-count at spine time — concurrent waves
   are also adding modules).
8. **Dashboard (same spine hold, city-registration rule)**: METRO_META
   entry (metro chip + `?city=long_beach` deep link), snapshot export
   coverage, res-5 grid-tile coverage in the published manifest, and the
   byte-synced `apps/dashboard/public/index.html` static copy. NOTE: that
   file is currently modified by another stream — rebase the byte-sync.
9. **Follow-up ticket (not this spine hold)**: OpenDataSoft client for
   `data.longbeach.gov` (or where-parameterized export path) to register
   the verified 311 service-requests feed (346,300 rows, intraday-fresh,
   native geolocation).

**Recommended Linear comment (US-224):** register as partial (SLA + CRIME);
flag that the ticket's datalongbeach.opendatasoft.com URL is dead (Huwise
migration → data.longbeach.gov); the 311 feed is verified but blocked on a
missing ODS client; permits exist only as aggregates; LA County deeds have
no open API; and the spine hold MUST delete the two `long_beach` →
LOS_ANGELES aliases when adding CityId.LONG_BEACH.
