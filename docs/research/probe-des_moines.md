# Wave 3 Phase-0 probe — Des Moines, IA

**Date of probe: 2026-09-29** (reads made about 02:55–07:50Z; Des Moines is on
CDT, UTC−5). Row-level reads only: `query` ordered by watermark DESC,
windowed `returnCountOnly`, and `outStatistics` min/max over row columns.
Catalog, item and DCAT "modified" dates were ignored. Two layer-level
`editingInfo` timestamps are quoted below, each labelled as a hint and never
used as evidence of freshness.

**Verdict: REGISTER (partial — one feed, `sla`).** The City's Rental License
layer is registerable at Tier 1: native points on every row, a per-licence
`IssuedDate` watermark that is 4 days old at the probe, weekday-continuous
issuance. Everything else was probed to the row and did not qualify, for five
different reasons (details and re-probe triggers below): permits are live but
Tyler EnerGov has no platform client; 311 has no public row API; deeds are live
but their geometry needs a parcel join the current `parcel_join` contract
cannot express; crime is a 29-day-old batch of unproven cadence; code-enforcement
cases are live but the `violations` feed type cannot ingest through the
scheduler today (a pre-existing defect, not a Des Moines one). Des Moines is the
first Iowa metro in the registry.

Platform: **ArcGIS Server 10.91** at `https://maps.dsm.city/p2/rest/services`
(City-run; resolves straight to an address record, no CDN CNAME), plus the City's AGOL org `HT7H9QGiZQoRJDpJ`
(`data.dsm.city` is its ArcGIS Hub). Not Socrata, not CKAN. The other families
sit on vendor systems: Tyler EnerGov Self-Service (permits, business licences),
CitySourced and Tyler Portico (311), Tyler Data & Insights (police, auth-gated),
and Polk County's ArcGIS Enterprise 11.5 (deeds and parcels).

---

## Method, and its limits

1. Hostname fingerprint. DNS-over-HTTPS lookups (`dns.google`) to separate
   NXDOMAIN from egress denial, then HTTP: the City site (`www.dsm.city`,
   `www.dmgov.org`), the Hub `data.dsm.city`, `maps.dsm.city`, and every vendor
   host linked from `www.dsm.city` (EnerGov, CitySourced, Portico, the police
   "LERM" map).
2. Hub DCAT (`data.dsm.city/api/feed/dcat-us/1.1.json`, 65 datasets: zoning,
   sewers, neighborhoods, wards, building footprints, census geographies,
   facilities, and 2023 police summary tables) and the full AGOL org item
   search (398 public items) plus the org's services directory (82 services: 77
   FeatureServer, 5 SceneServer). No permits, 311, licence or deed layer. The only
   transactional hosted layer is `PSDP_Crime_Layer_View`.
3. City ArcGIS Server walk from `/p2/rest/services`: folders `External` (32
   services), `EXTSecure` (HTTP 499 "Token Required"), `Utilities` (2
   GPServer), plus 15 GeocodeServers at the root. The `/arcgis`, `/server`,
   `/gis` and `/rest` roots on `maps.dsm.city` all redirect to the City's map
   page; `/portal/sharing/rest` returns only `{"currentVersion":"9.2"}`. Every
   External service's layer list was read; every survivor was read at row level.
4. Vendor systems, fingerprinted from links on `www.dsm.city`: EnerGov
   (`css.dmgov.org`), CitySourced and Portico (311), Tyler Data & Insights (PD).
5. Polk County: `maps.polkcountyiowa.gov/portal/sharing/rest/portals/self`
   helperServices point at the REST root `gis4.polkcountyiowa.gov/server/rest/services`
   (ArcGIS Enterprise 11.5, 21 folders). Service lists read for every folder; layer lists
   read for `Auditor`, `Public`, `PublicWorks` and `Sheriff`.
6. Iowa statewide: `data.iowa.gov`, `geodata.iowa.gov`, `iowalandrecords.org`,
   `govconnect.iowa.gov`.
7. Geography for the registration (metro bbox, divisions, submarkets) was authored
   from Census TIGERweb place extents, the Census geocoder (City Hall anchor) and the
   City's own Neighborhoods layer. See `cities/des_moines.py`.

Limits:

- EnerGov's search API ignores its date-range criteria, so its windowed counts
  are bucketed locally from the newest 4,600 rows (23 pages of 200). The 90-day
  window is exact only because the sample reaches back to 2026-06-23.
- Anonymous access only. No credentialed surface was tried (`EXTSecure`, Portico,
  the PD Socrata tenant, Iowa Land Records). CitySourced's same-origin proxy
  `pages/ajax/callapiendpoint.ashx` was located in the app bundle and not called:
  it is the app's own session proxy, not a documented API.
- The Rental License layer's reload schedule cannot be derived from one day of
  reads; see the SLA section.
- Polk County's Akamai edge answered "Access Denied" partway through an early
  burst of 82 windowed counts in about a minute (03:14Z). I backed off and made no
  attempt to evade it. One default-User-Agent request at about 03:16Z (the
  2,000-row deed page) then succeeded, but the next six requests to that host
  (five at 03:17Z, one at 03:30Z), which carried a descriptive research
  User-Agent instead of curl's default, all came back empty or refused (the 03:30Z
  reply is HTTP 403 "Access Denied"). Whether the block was rate-based,
  User-Agent-based or both was not isolated. The first request at 04:18Z succeeded
  (HTTP 200), and every Polk read from then on was a single spaced request with the
  default curl User-Agent. For that reason the Polk windowed counts below are
  bucketed from one 2,000-row page rather than queried per window.

---

## Headline table

| Family | Endpoint | Newest row (watermark) | Geocoding | Recent window | Tier |
|---|---|---|---|---|---|
| **SLA** (registered) | `maps.dsm.city/p2/rest/services/External/EXTDynamicCodeCaseRentalLicense/MapServer/1` (Rental License) | `IssuedDate` = **2026-09-25** (Fri); 2 future-dated rows (2026-11-20, 2026-12-05) | native points on 15,475 of 15,475 rows (`outSR=4326`) + `RentalAddress` | 7d **95** rows / **70** licences; 30d **503** / **312**; 60d **811** / **511**; 90d **1,207** / **750**; total **15,475** rows / **9,866** licences | **1** |
| **PERMITS** | Tyler EnerGov Self-Service `css.dmgov.org/EnerGov_Prod/SelfService` (anonymous JSON search) | `IssueDate` = **2026-09-28T16:27:25** (PLMR-2026-002494) | address text only (`AddressDisplay`) | 7d **351**; 30d **1,363**; 60d **2,725**; 90d **4,265**; total permits **383,212** | **2** by data; **not registrable** (no `energov` platform client) |
| **311** | CitySourced app / Tyler Portico: no public row API | n/a | n/a | n/a | **3** |
| **DEEDS** | Polk County Auditor `Parcel` table `gis4.polkcountyiowa.gov/server/rest/services/Public/Polk_County_Parcels/FeatureServer/2` | `LastDeededDate` = **2026-09-24T19:38:24Z** | none on the table (parcel key only) | 7d **160**; 30d **1,390**; total **220,002** | live but **deferred** (`parcel_join` contract) |
| Crime (extra) | `services.arcgis.com/HT7H9QGiZQoRJDpJ/arcgis/rest/services/PSDP_Crime_Layer_View/FeatureServer/0` | `reported_date` = **2026-08-31** | native anonymized points | 7d **0**; 30d **161**; 60d **2,836**; 90d **5,633**; total **122,243** | **3** as probed (29 d old, cadence unproven) |
| Code cases (extra) | `.../EXTDynamicCodeCaseRentalLicense/MapServer/0` (Code Case) | `DateOpened` = **2026-09-25** (Fri) | native points | 7d **190**; 30d **795**; 60d **1,843**; total **33,061** | **1** by data; **deferred** (scheduler defect) |

Windows are calendar windows through 2026-09-29 on the watermark column
(7d = on or after 09-22, 30d = 08-30, 60d = 07-31, 90d = 06-30; EnerGov's 90d
starts 07-01, Polk's 30d is counted from 08-31 because 08-30 was a Sunday). The
SLA licence counts in the windows are distinct `LicenseNumber` on owner rows (any-row
counts: 60d 512, 90d 751); the 9,866 total is distinct on any row.

---

## SLA — Tier 1 (REGISTERED)

`External/EXTDynamicCodeCaseRentalLicense/MapServer` layer 1 `Rental License`
(same map service as the Code Case layer; `maxRecordCount` 2000).

- **Grain.** One row per licence and contact: 15,475 rows, **9,866** distinct
  `LicenseNumber`, `Status` = `Issued` on every row. `ContactType`: Property Owner
  11,569, Management Agent 3,905, null 1. 4,934 licences have more than one row,
  1,508 have more than one Property Owner row, 2 have none (RENT-2025-011792 has
  an agent row only; RENT-2026-007277 has a single row with a null `ContactType`).
- **Columns.** `OBJECTID`, `LicenseNumber`, `ParcelNumber`, `IssuedDate`, `ExpDate`,
  `RentalAddress`, `Unit`, `ContactType`, `ContactName`, `ContactAddress`,
  `CityStateZip`, `Remark`, `DataOwner`, `PKID`, `created_date`, `created_user`,
  `last_edited_date`, `last_edited_user`, `ExtID`, `GlobalID`, `Status`,
  `Hyperlink`, `ContactEmail`, `Shape` (point).
- **Watermark `IssuedDate`** (date-typed, stored at local midnight: `T05:00:00Z`
  is 00:00 CDT). Newest non-future row: RENT-2026-006646, 5825 URBANDALE AVE
  (OBJECTIDs 1319041/1319042, two owner rows), **2026-09-25**. 17 rows carry that
  date; none carry 09-26 through 09-28.
- **Recent windows** (all-contact-type rows / distinct licences counted on owner
  rows; owner-only row counts in brackets): 7d 95 / 70 (78); 30d 503 / 312 (356);
  60d 811 / 511 (586); 90d 1,207 / 750 (886). Counting a licence on any row instead,
  the 60d and 90d distinct figures are 512 and 751. From 2026-07-01: 878 owner rows,
  **742** distinct licences on owner rows (743 on any row); 742 is the number behind
  the registration's `sla` seeds.
- **Weekly distinct licences** (Mon-start weeks): Jun 8 **29** · Jun 15 **75** ·
  Jun 22 **27** · Jun 29 **26** · Jul 6 **54** · Jul 13 **98** · Jul 20 **23** ·
  Jul 27 **46** · Aug 3 **53** · Aug 10 **15** · Aug 17 **66** · Aug 24 **58** ·
  Aug 31 **129** · Sep 7 **38** · Sep 14 **55** · Sep 21 **90** (through Fri
  Sep 25) · Sep 28 **0** (not loaded yet). Issuance is weekdays only and lumpy
  (Sep 21–25: 23, 2, 37, 39, 17 rows).
- **Cadence (the honesty clause).** Registered with `expected_cadence_days: 7`, so
  the staleness alarm fires at 14 days. Evidence: (1) the longest gap between two
  consecutive issue days over the last 12 months is 6 days (2026-08-11 to
  2026-08-17); (2) on both layers `created_date` and `last_edited_date` are a single
  value on every row (Rental License 2026-09-27 06:00:03 CDT, Code Case
  06:00:00 CDT, written by a service account), the signature of a full-table
  reload rather than row edits; (3) that reload is **not proven daily**: the
  Monday 2026-09-28 06:00 CDT slot passed without a new reload (`created_date`
  still 09-27, 15,475 rows and newest issue day 09-25 when re-read at 04:25Z and
  again at 07:48Z on 09-29), so the newest issue day can trail by a weekly cycle.
  One snapshot cannot resolve the schedule. Re-read `created_date` after the next
  Sunday: if it moves daily, tighten the cadence to 2–3 days; if it stays weekly,
  7 stands.
- **Date boundary.** The server rejects ISO string comparisons and accepts ANSI
  literals: `IssuedDate > '2026-09-25T05:00:00'` returns 400 "Unable to complete
  operation", while for the same day `> date '2026-09-25'` returns 2 (the two
  future-dated rows), `>= date` returns 19 and `= date` returns 17. So
  `maps.dsm.city` joins `ANSI_DATE_LITERAL_HOSTS`. The scheduler's `>` on a
  day-precision column would miss a row that lands late for an already-ingested
  day; the one observed reload (06:00 CDT, before the business day) makes that
  unlikely, and it is a property of every date-only watermark, not of this city.
- **Geocoding.** Native points on all 15,475 rows (0 null, 0 at 0/0); native
  spatial reference is Iowa State Plane South (102676), the client requests
  `outSR=4326`. Extent lng −93.7084…−93.5016, lat 41.5094…41.6582, all inside the
  four city divisions. No ADR 0004 dependency.
- **id_keys** `["LicenseNumber", "OBJECTID"]`. `LicenseNumber` repeats across a
  licence's contact rows by design; the scheduler's record id
  (`sla_des_moines:<LicenseNumber>`) collapses them.
- **Label decision.** `SLALicensesProducer.parse_socrata_row` falls back to
  "On-Premises Liquor" when `license_type` is unmapped, and this layer has no
  licence-category column. So `license_type` reads `ContactType`, and the feed
  filters `ContactType = 'Property Owner'` to keep one owner row per licence
  (management-agent rows are 145 of the newest 500). Two licences with no owner
  row are excluded (2 of 9,866).
- **Data-quality notes.** `ExpDate` carries a 2999-01-01 sentinel on one row
  (RENT-2026-007423, 1200 LOCUST ST); kept, expiry is not the watermark. Two rows
  are future-dated in `IssuedDate` (RENT-2025-015015, 119 E KIRKWOOD AVE,
  2026-11-20; RENT-2025-014477, 1221 LEWIS AVE, 2026-12-05); the scheduler's
  future-watermark guard (US-111) stops them from pinning the watermark, but the two
  events themselves are still published with their future dates, and they are
  re-read, then deduplicated, on each poll. The licence-number year differs
  from the issue year on 3,079 of 9,866 licences, so `LicenseNumber` says nothing
  about recency.
- **PII.** `ContactName`, `ContactAddress`, `CityStateZip` and `ContactEmail`
  identify individual landlords. The field map never reads them and the test
  fixtures replace them with `REDACTED`. But the ArcGIS client requests
  `outFields=*` (arcgis specs have no `select`), so raw rows carrying those
  columns pass through the client and would be written to the DLQ payload if a
  row failed to parse (0 of the newest 500 did). Platform-wide, not specific to
  Des Moines; flagged for the owner.
- **Precedent.** Boulder registers its Rental Housing Licenses layer as `sla` in
  the same shape.

## Permits — Tier 2 by data, NOT registered (no platform client)

Tyler **EnerGov Self-Service** v2025.3.1.25, `https://css.dmgov.org/EnerGov_Prod/SelfService`
(linked from the City's Permit & Development Center page). Anonymous JSON API,
base `https://css.dmgov.org/EnerGov_Prod/selfservice/api`:

- `GET /energov/search/criteria` (headers `tenantId: 1`, `Tyler-Tenant-Culture:
  en-US`) returns the default request model; `POST /energov/search/search` (same
  headers plus an empty `Tyler-TenantUrl`) with `SearchModule` 1, `FilterModule` 2
  (permits), `PermitCriteria.SortBy` `IssueDate`, `SortAscending` false, page size
  200 works. Date-range criteria are ignored, so an incremental poll would
  page newest-first and stop at its stored watermark.
- Newest non-future permit: **PLMR-2026-002494**, Plumbing (Residential) - Other,
  `IssueDate` 2026-09-28T16:27:25, 4300 ASHBY AVE DES MOINES IA 50310. One
  future-dated row in the sample (ROWP-2026-002230, 2026-10-19).
- Windows (IssueDate on or after 09-22 / 08-30 / 07-31 / 07-01): **351 / 1,363 /
  2,725 / 4,265**. Daily counts, newest first: Sep 28 76 · 25 63 · 24 55 · 23 57 ·
  22 100 · 21 68. Weekday-continuous.
- Module totals (anonymous search, 2026-09-29): permits 383,212; plans 28,307;
  inspections 813,010; licences 232,707 (animal licences, vacant-structure
  registrations and similar); projects 83,089; code cases 0; requests 0.
- Mix: the permit stream is trades and right-of-way as much as building. Newest 90
  days: Plumbing (Residential) - Other 923, ROW - Excavation or Obstruction 688,
  Mechanical (Residential) - Other 568, Electrical (Residential) - Other 348,
  Residential Other Building Permit 302, Sidewalk and Approach 236, Fence Permit
  155. A registration would need a type filter to stay building-shaped.
- Geocoding: address text only (`AddressDisplay`, formatted like
  "4300 ASHBY AVE DES MOINES IA 50310"); 120 of 4,600 sampled rows (2.6%) carry no
  address, so a Tier 2 G5 floor of 95% is reachable.
- **Blocker.** `KNOWN_PLATFORMS` has no EnerGov adapter. Adding one (client,
  `acquisition.py` adapter, platform closure) is a spine change outside this
  stream's leaf-only lane. Licence-module rows expose applicant names, so a licence
  feed would need the same redaction care as the rental contacts.

## 311 — Tier 3

The City's request app (myDSMmobile) is **CitySourced**,
`https://desmoinesia.citysourced.com` (customer id `DesMoinesIa`, Cloudflare-fronted
single-page app, bundle v4.29.11). `/open311/v2/services.json` and
`/api/open311/v2/requests.json` return IIS 404. The bundle talks to a same-origin
proxy (`/pages/ajax/callapiendpoint.ashx`) and has a `/servicerequests/nearby`
route; neither is a documented public row API, and the proxy was not exercised.
`cityofdesmoinesia.tylerportico.com` is a Tyler Portico launcher whose `TIM/Portal`
is the authenticated Incident Management portal. `www.dsm.city/departments/city_manager-311`
is a 404. No platform client (`socrata`, `arcgis`, `carto`, `ckan`, …) covers
CitySourced either way. No feed.

## Deeds — live signal, DEFERRED

Polk County Auditor table `Public/Polk_County_Parcels/FeatureServer/2` (`Parcel`),
`https://gis4.polkcountyiowa.gov/server/rest/services/Public/Polk_County_Parcels/FeatureServer/2`.
220,002 rows, one per parcel (220,002 distinct `ParcelNumber`), 206,413 with a
`LastDeededDate`, all tax year 2025. (`Auditor/Auditor_Export` layer 147 is a `Parcel`
table with a superset schema; its rows were not counted.)

- Newest `LastDeededDate` **2026-09-24T19:38:24Z** (ParcelNumber 792328302029, book
  20669 page 522). Daily counts from the newest 2,000 rows, newest first: Sep 24
  55 · 23 53 · 22 52 · 21 92 · 18 54 · 17 63 · 16 114 · 15 76 · 14 108 · 11 65 ·
  10 74 · 9 83 · 8 130; oldest row in that page 2026-08-19. 7d = **160**, 30d =
  **1,390**. Nothing dated Sep 25 or Sep 28, so the table trails by about 5 days.
- Columns (15): `OBJECTID`, `ParcelNumber`, `ParcelNumberFormatted`,
  `AlternateParcel`, `Year`, `AcresDeeded`, `SquareFeet`, `FullLegal`,
  `LastDeededDate`, `LastDeededBook`, `LastDeededPage`, `LastContractDate`,
  `LastContractBook`, `LastContractPage`, `IsCoOp`. No geometry, no address, no sale
  amount. One row per parcel means `LastDeeded*` holds only each parcel's latest
  deed; earlier deeds are not in the table, so it is a state table, not an event log.
- Geometry only through a parcel join, and the key name differs per source in the
  same service: `ParcelNumber` on this table, `parcel_number` on layer 0 "Parcel
  Point", `Parcel_Number` on layer 1 "Cadastral Parcels". The registry's
  `parcel_join` takes ONE `join_key` and uses it on both the deed rows and the parcel
  layer (`deeds_acris_producer.py` lines 497–503 into
  `ArcGISClient.fetch_centroid_index`, where it is also the layer-side `select` and
  `IN` field), so it cannot express this. The service does declare one-to-one
  relationships from the table to `SDE_LOADER.Tax_Parcel_Points` and
  `SDE_LOADER.Tax_Parcels` (key field `ParcelNumber`), so the join exists
  server-side; the platform's contract just cannot use it.
- The Akamai edge (see Limits) makes a per-poll parcel lookup fragile.
- Statewide alternative: `iowalandrecords.org` is an account-based search UI ("REQUEST AN
  ACCOUNT | ILR LOGIN") for all 99 counties; its landing page describes no API or
  bulk download. UI only, not probed past the landing page.

## Crime (extra family) — Tier 3 as probed

`PSDP_Crime_Layer_View` (item "PSDP Crime View": "Map View of Production Crime Layer
for Public Safety Data Portal"), 122,243 rows, native anonymized points
(`case_latitude_anonymized`/`case_longitude_anonymized`, block-level
`case_address_anonymized`, 0 null geometry). Columns include `case_number` (not
unique per row: one case carries several offences), `reported_date`,
`reported_hour_of_day`, `police_district`, `police_beat`, `crime_code`,
`crime_category`, `nibrs_offense`, `offense_category`.

- Newest `reported_date` **2026-08-31**, 29 days old. Month counts: Jun **2,797**,
  Jul **2,812**, Aug **2,725**, Sep **0**; oldest row 2023-01-01.
- Cadence unproven. The schema has no per-row load timestamp. Layer-level
  `editingInfo.dataLastEditDate` reads 2026-09-28T11:34Z, which I quote as a hint
  only: it is not a row-level read, and rows already stop at 08-31. A monthly-batch
  exception (`expected_cadence_days: 30` exists for several registered feeds, for
  example Albany, Baltimore, Chicago) needs row-level evidence of two successive
  month-boundary loads, which I could not obtain. DEFER.
- Other PD surfaces: the LERM map (`lerm.dsm.city`) is Socrata (now Tyler Data & Insights); eight
  dataset IDs on `desmoinesia-pd.data.socrata.com` return HTTP 403
  `authentication_required` at both `/resource/<id>.json` and `/api/views/<id>.json`
  (the ninth is a non-tabular logo file). The Hub carries only 2023 summary tables.

## Code cases (extra family) — Tier 1 by data, DEFERRED (scheduler defect)

Layer 0 `Code Case` of the same map service: 33,061 rows, native points,
`DateOpened` newest **2026-09-25**, 0 future rows, 7d **190**, 30d **795**, 60d
**1,843**, weekday-continuous. Columns: `CaseNumber`, `CaseType`, `ParcelNumber`,
`DateOpened`, `DateClosed`, `Status`, `Address`, `Unit`, `Description`, `Vacant`,
`FireDamage`, `FloodDamage`, `NuisanceStruc`, `Remark`, plus editor columns.

It would be the `violations` feed, and it is **not registered** because that feed
type cannot ingest through the scheduler today (pre-existing, unrelated to Des
Moines): `scheduler.py` `poll_job` calls `producer.parse_socrata_row(...)`
(line 868) but `ViolationsProducer` and `InspectionsProducer`
(`enforcement_signals_producer.py`, lines 79 and 221) only define `parse_row`, and
`ViolationEvent` carries `status_date` while the scheduler reads only
`issuance_date`, `created_date` or `effective_date` for its watermark (lines
904–906). A mock `poll_job` run on `violations_boston` produced 0 events and one
DLQ route ("'ViolationsProducer' object has no attribute 'parse_socrata_row'").
Registering Code Case would only feed the DLQ. Fix (spine): give both producers a
`parse_socrata_row` and add `status_date` to the watermark attributes. Code
enforcement is also not 311 (Lynchburg, Scottsdale and Wichita precedents in this repo).

## Other layers read (not families, or not live)

| Layer | Row-level result |
|---|---|
| `External/EXTDynamicRoadClosure/0` | 84 rows, `StartDate` up to 2026-12-08 (forward-dated closures, not transactions) |
| `External/EXTDynamicRoadTrailClosure/0`, `/2` | 50 and 9 rows, closure windows |
| `External/EXTDynamicProjectsCDM/1` Street Use Events | 51 rows, `StartDate` 2026-05-02…2027-06-12 (forward-dated events) |
| `External/EXTDynamicProjectsCDM/0` Projects and CIP | 152 rows, both date columns null |
| `External/EXTDynamicEcoDev/0` ProjectEcoDev | 7 rows, every date column 2015-03-30 |
| `External/EXTDynamicPoliceHomelessResponse/0` | 255 rows, `created_date` 2025-07-18…2026-09-18 (operational log, not a family) |
| `External/EXTDynamicTrafficVisionZero/0` Crashes | 28,046 rows, `crash_date` 2017-01-01…2021-12-31, single load 2023-07-28 |
| `External/EXTDynamicBenchmarkingDSM/0` | 807 rows, last edit 2024-07-03; `BenchmarkingDSMEnergyReport` table 1,404 rows, `reportyear` 2018–2022 |
| Polk `PublicWorks/OpenGov_MAT/3` Building Permits | service-area polygons only (four columns, no permit attributes) |
| Polk `Sheriff/Sheriff_Public/0` | PCSO zones |
| `snap_retailer_location_data` (USDA, the repo's usual fallback `sla` shape) | 250,628 national rows; 2,888 in Iowa; 202 with `City = 'DES MOINES'`; no authorization-date fields. Not used: a federal retailer roster, and the City's own licence layer has a real issuance watermark |

---

## Hostnames tried (negatives)

| Surface | Result |
|---|---|
| `data.dsm.city` | ArcGIS Hub (AGOL org `HT7H9QGiZQoRJDpJ`); DCAT 65 datasets, reference layers and 2023 police summaries |
| `dsm.opendata.arcgis.com`, `desmoines.opendata.arcgis.com` | resolve to the shared Hub wildcard, prove nothing |
| `opendata.dsm.city`, `open.dsm.city`, `api.dsm.city`, `datahub.dsm.city`, `311.dsm.city`, `permits.dsm.city`, `gis.dsm.city` | NXDOMAIN |
| `opendata.dmgov.org`, `data.dmgov.org` | NXDOMAIN |
| `data.desmoinesia.gov`, `opendata.desmoinesia.gov`, `desmoines.socrata.com`, `opendata.iowa.gov`, `open.iowa.gov` | resolve with no address record |
| `cityofdesmoines.opendatasoft.com`, `desmoinesia.opendatasoft.com`, `iowa.opendatasoft.com` | wildcard DNS; `/api/explore/v2.1/catalog/datasets` returns 404 "domain could not be found" |
| `maps.dsm.city` | **live**; REST root is `/p2/rest/services` (other roots redirect to the map page) |
| `lerm.dsm.city` | redirects to `dmmdatahub-transparency.connect.socrata.com` ("Law Enforcement Response Map") |
| `desmoinesia-pd.data.socrata.com` | PD tenant, datasets auth-gated (403); its public catalog lists one logo file |
| `dmmdatahub-letrms.connect.socrata.com`, `dmmdatahub-transparency.connect.socrata.com` (catalog API) | "Domain not found" |
| `css.dmgov.org` | Tyler EnerGov Self-Service, anonymous search live |
| `desmoinesia.citysourced.com` | CitySourced app; Open311 paths 404 |
| `cityofdesmoinesia.tylerportico.com` | Tyler Portico launcher; `TIM/Portal` authenticated |
| `data.polkcountyiowa.gov`, `opendata.polkcountyiowa.gov`, `gis.polkcountyiowa.gov`, `data.wdm.iowa.gov`, `opendata.wdm.iowa.gov`, `data.ankenyiowa.gov`, `data.urbandale.org`, `data.dmmpo.org` | NXDOMAIN |
| `maps.polkcountyiowa.gov`, `gis4.polkcountyiowa.gov` | live behind Akamai; REST root `gis4.../server/rest/services` |
| `data.iowa.gov` | "Iowa Data Hub" (Next.js), no longer Socrata (`/resource/*.json` 404, catalog API "Domain not found"); no row API |
| `geodata.iowa.gov` | state GIS Hub, DCAT 275 datasets; permit-like layers are state DNR environmental permits and facilities only |
| `data.iowadot.gov` | Hub DCAT reachable (1.07 MB); Iowa DOT, outside the four families, not mined |
| `iowalandrecords.org` | account-based search UI; landing page only |
| `govconnect.iowa.gov` | state portal; cookie-check landing page, nothing row-level reachable anonymously |
| `EXTSecure` folder | HTTP 499 "Token Required" |

## Registration sketch (summary)

`cities/data/des_moines.yaml` `datasets.sla`: `platform: arcgis`, endpoint
`https://maps.dsm.city/p2/rest/services/External/EXTDynamicCodeCaseRentalLicense/MapServer/1`,
watermark `IssuedDate`, `id_keys: [LicenseNumber, OBJECTID]`, `order_by: IssuedDate
DESC, OBJECTID DESC` (the tiebreak keeps paging total-ordered, since a bulk day
shares one timestamp), `where: ContactType = 'Property Owner'`, `oid_field:
OBJECTID`, `max_record_count: 2000`, `interval_seconds: 1800`,
`expected_cadence_days: 7`, `needs_geocode: false`, `ingestion_mode: incremental`,
field map: `license_id` ← `LicenseNumber`, `license_type` ← `ContactType`, `status`
← `Status`, `effective_date` ← `IssuedDate`, `expiration_date` ← `ExpDate`,
`address_street` ← `RentalAddress`. Contact columns are never mapped. Settings field
`arcgis_des_moines_rental_licenses_url` in `config.py`; `CityId.DES_MOINES`;
`maps.dsm.city` added to `ANSI_DATE_LITERAL_HOSTS`. `permits`, `311`, `deeds` and
`crime` are unregistered, so `get_dataset()` raises for them.

Geography (`cities/des_moines.py`): center City Hall (Census geocoder match for
400 Robert D Ray Dr, 41.588722, −93.616145); metro bbox 41.44–41.81 N, −93.90…−93.42 E
(union of ten Census TIGERweb place extents, rounded outward); six divisions that
tile the bbox exactly (four city, two suburban); 14 submarkets anchored on the City's
Neighborhoods layer (51 polygons) and TIGERweb place points. **Seeds are not all
measured:** `sla` is the measured licence count (742 licences issued
2026-07-01…2026-09-29, nearest anchor; 0 for the four suburban submarkets because the
feed covers the City only), while `base_lims`, `capex`, `permit_vel` and
`shift_ratio` are one neutral illustrative value on every submarket, so no ranking is
implied (no permits, 311 or scored feed is registered for Des Moines).

## G5 live parse-rate (2026-09-29)

`scripts/backfill_probe.py --city des_moines --count` (first run about 04:14Z, re-run
07:48Z with identical results), newest 500 rows of the registered feed through the
production client and parser: **500 / 500 parsed
(100%), 0 dropped**, source count 15,475. Separate measurement on the same 500 rows
(point-geocoded floor 99%, address floor 95%): points **500 / 500 (100%)**, all 500
inside the metro bbox, addresses **500 / 500 (100%)**, division resolved 500 / 500.
The probe orders by `IssuedDate DESC` and ignores the spec's `where`, so its sample
includes management-agent rows (355 owner, 145 agent, oldest 2026-09-01) and the
future-dated row (`watermark_seen` 2026-12-05). Re-run in the production shape
(spec `where` and `order_by`): 500 / 500 parsed, points 500 / 500, addresses 500 /
500, 500 owner rows, oldest 2026-08-17.

## Re-probe triggers

- **Permits**: an `energov` platform client lands (or the City publishes permits to
  ArcGIS/Socrata). Re-probe `IssueDate` at most 72 h before the build; register at
  Tier 2, cadence 7, with a type filter.
- **311**: an Open311 GeoReport v2 endpoint, a public 311 layer on `maps.dsm.city` or
  the Hub, or a documented anonymous CitySourced request feed.
- **Deeds**: `parcel_join` gains a layer-side key distinct from the deed-side key (or a
  server-side relationship join); then re-probe `LastDeededDate` (lag today about 5
  days) and decide how to treat last-deed-per-parcel semantics.
- **Crime**: 2026-10-31 (September should be complete if the release is monthly). A
  September load within about five weeks of month end, on top of the Jun–Aug
  month-complete counts, is the second boundary event needed for a 30-day cadence; or
  the PD publishes a weekly or daily feed.
- **Code cases**: after the `violations` scheduler fix above; the ANSI host and
  ordering notes already apply to layer 0.
- **SLA staleness**: newest non-future `IssuedDate` older than 14 days, or
  `created_date` moving daily (tighten the cadence).

These are prose only. `scripts/rejection_recheck.py`'s manifest is wave-2 scoped, so
these deferrals are not machine-watched (the same deliberate gap as the other wave-3
rejections).

Stamp: 2026-09-29.
