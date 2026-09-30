# Four-family depth pass — 2026-09-30

`docs/signal-roadmap.md` gate E3 splits results by metro tier (all four signal
families versus partial), and `docs/expansion-roadmap-wave-2.md` §1 puts coverage
depth before coverage breadth. A family is present when the metro's corpus file
carries a `datasets` key named `permits`, `311`, `sla` or `deeds`. On 2026-09-28,
16 metros had all four and 32 were exactly one family short.

This pass probed 13 of the 32 live (2026-09-29 23:10Z to 2026-09-30 03:20Z, curl
default User-Agent, a few requests per minute per host, no WAF response except
where noted). Two metros move up; eleven stay where they are.

| Tier (families) | Before | After |
|---|---|---|
| 4 | 16 | **18** (Columbus, Tallahassee) |
| 3 | 32 | 30 |
| 2 | 54 | 54 |
| 1 | 54 | 54 |
| 0 | 1 | 1 |

Denver, Hartford and Nashville joined the four-family tier later the same
day with deeds from their parcel records, which makes 21
([deeds-probe-2026-09-30.md](deeds-probe-2026-09-30.md)). Tempe followed with
deeds from the Maricopa County Assessor's parcel layer, which makes 22, and
Chandler, Glendale and Scottsdale gained a third family from the same layer.

## Registered

### Columbus, OH — `311`

- **Source:** City of Columbus ArcGIS Server 11.5,
  `maps2.columbus.gov/arcgis/rest/services/Applications/ServiceRequests/MapServer/1`
  ("All Service Requests - Last 3 Years"). It sits behind the City's "311 Service
  Requests" map app and is not in the open-data Hub, which is why the 2026-08-25
  coverage sweep recorded Columbus 311 as absent.
- **Shape:** 920,928 rows on 2026-09-29, a rolling three-year window (oldest
  2023-09-30). `DATAHUB_ID` is unique on every row; `CASE_ID` is not (one CRM case
  can spawn up to eight requests). 74.7% of rows carry `LATITUDE`/`LONGITUDE`, and
  99.99% of those fall inside the registered metro bbox. No requester name,
  contact or free text is in the schema.
- **Freshness:** loaded by one extract a day at about 05:00 ET; the newest
  `REPORTED_DATE` at measurement was 2026-09-29 04:57:53 ET. Over the 90 days to
  2026-09-28 the filtered layer (point present, "City Staff Requests" excluded)
  averaged 932 rows per weekday and at most 310 on a weekend day.
- **Watermark:** the server answers `REPORTED_DATE > '2026-09-29T00:00:00'` with
  error 400 and accepts `REPORTED_DATE > date '2026-09-29'` (read as Eastern midnight),
  so `maps2.columbus.gov` joins `ANSI_DATE_LITERAL_HOSTS`. Truncating the
  watermark to a date re-reads the early hours of a day, which the cross-run
  dedup drops.
- **Filter:** `LATITUDE IS NOT NULL AND REQUEST_CATEGORY <> 'City Staff Requests'`.
  Staff requests are call-centre notes rather than service locations.
- **Field map:** `incident_id` ← `DATAHUB_ID`; `created_date` ← `REPORTED_DATE`;
  `complaint_type` ← `REQUEST_TYPE`, then subcategory, then category; `status`,
  `incident_address` (`STREET`), `zipcode`, and `borough` (Columbus community,
  then council district). `closed_date` stays unmapped because `STATUS_DATE` is
  the last status change for every status, not a close time.
- **Poll cap:** the filtered daily volume passed 1,000 rows on 22 of the 64
  weekdays in the 90-day window (peak 1,227 on 2026-08-31), 1,651 rows above
  the cap in all.
  A newest-first poll capped at the scheduler default of 1,000 rows never reaches
  the oldest rows of a heavy extract, so `DatasetSpec` gains an opt-in
  `batch_limit` and this feed sets 5,000 (covers a missed extract as well).
- **Live check:** a 1,000-row poll of the registered spec through the real
  scheduler against the live layer published 1,000 of 1,000 rows with 0 DLQ
  routes and a watermark of 2026-09-29T08:57:53; the next poll sent
  `... AND REPORTED_DATE > date '2026-09-29'` and dropped the re-read rows as
  duplicates.

### Tallahassee, FL — `sla` (SNAP fallback)

- **Local source:** none. The City stopped requiring business licences in 2016,
  the Leon County Tax Collector publishes no business-tax roll, and neither the
  TLCGIS Hub nor the City and County ArcGIS servers carry a licence layer (the
  only candidate, a 128-point rooming-house registry, has no dates).
- **State candidate, held:** Florida DBPR's alcoholic-beverage licence extract
  (a CSV regenerated daily, 53,016 rows statewide; Leon County 687, all unique
  licence numbers, 105 effective dates in the last 12 months). It is
  address-only. Run through the production geocoder path, 105 of 120 sampled
  Leon addresses resolved (88%). The four misses with a `#` unit lost their city
  to the defect below and each resolved when resent with city and state, which
  would make 109 (91%). The other 11 miss with the state or ZIP too: two are not
  street addresses (a road intersection and an "INACTIVE" placeholder) and nine
  are addresses the Census geocoder does not match, six of them on Apalachee
  Parkway. Both results are under the 95% floor for geocoded feeds, so the
  extract stays a candidate.
- **Registered:** the statewide USDA SNAP retailer layer sliced to
  `State = 'FL'`, the same spec the other six Florida metros use. See the SNAP
  finding below before relying on it.

## Not now

| Metro (missing) | Why not | Re-check when |
|---|---|---|
| Chattanooga (`311`) | The only 311 artefact is a frozen GOGov CSV (newest 2025-10-28, nothing in 30 days, address-only). The replacement CRM, CHA 311, runs on Accela with no published extract. | A CHA 311 dataset appears on the City portal. |
| Durham (`311`) | Durham One Call runs on Accela; no public row feed. | A One Call dataset appears on the City Hub. |
| Las Vegas (`311`) | The City table is a graffiti-abatement log (about 6 a day) with no coordinates, address or request id. The City and Clark County take requests on SeeClickFix, Henderson and North Las Vegas on Comcate; none publishes rows. SeeClickFix's API answered 403 and was not probed further. | A request layer appears in a City or County ArcGIS org. |
| Lynchburg (`311`) | Requests go through a custom web form and TRAKiT; nothing is published. | Any request dataset appears on the City GIS. |
| Miami-Dade (`311`) | The county 311 extracts stopped on 2024-08-10 in every source checked (yearly tables end with 2023, `data_311_2024` still needs a token, the animal-services table's newest row is 2024-08-11). The public Citizen 311 view exposes only `OBJECTID`. Proxies examined and not registered: the Waste Collection enforcement-complaints table (live, 1,410 rows in 30 days, unique `COMPLAINT_NO`, but address-only, no complaint-type column, and owner and complainant phone columns in every row), bulky-waste pickup work orders (a scheduling stream rather than complaints, with owner phone columns), and EnerGov code cases (about 25 citizen complaints a month). | `data_311_2024` or a later table is published without a token. |
| Montgomery County (`311`) | MC311 (`xtyh-brr2`) is live (newest 2026-09-28) but still ZIP-only, schema unchanged since 2026-08-24. Noise complaints carry a ZIP in the address column on 99.5% of rows; housing-code violations have zero coordinates on 7,134 of 7,136 rows since 2026-03-30 and no unique id; illegal dumping (`d985-d2ak`) lists closed cases only, about one a day, 24% without a point. | MC311 gains an address or point column (`scripts/rejection_recheck.py` watches it). |
| Phoenix (`311`) | myPHX311 is a Dynamics 365 portal with no public API. The nearest CKAN datasets are police calls (hundred-block only) and property-maintenance cases with no date column. | A 311 package appears on phoenixopendata.com. |
| Spokane (`311`) | My Spokane 311 is vendor-hosted Salesforce with no API; the City portal serves a JavaScript challenge; the County GIS has no request layer. | A request layer appears on the County GIS. |
| Virginia Beach (`311`) | VB311 is Salesforce (portal and CRM). No request-level dataset exists in the Hub (0 results for 311), the 366-service AGOL org, the state CKAN harvest, or the on-premises `geo.vbgov.com` server, whose CRM_311 service holds reference layers only. Code-enforcement cases are closed-only, with no case id or coordinates. | A 311 item appears in the Hub or `geo.vbgov.com/.../Business_Systems`. |
| Eugene (`permits`) | Permits live in the City's in-house eBuild system; the only public export is a form-post report (PDF or Excel) carrying owner and contractor names and no coordinates. Springfield uses Accela Citizen Access. | A permits layer appears in the City AGOL org or DCAT feed. |
| Prince George's County (`permits`) | The Planning `MomentumPermitLocation` point layer (27,558 rows, native points, clean schema) is one bulk load dated 2026-04-02 whose newest issuance is 2026-03-31, with nothing since; the Socrata successor `245r-4wz8` stopped on 2025-07-28 and `weik-ttee` is a legacy tail of about 1%. | `DATE_LOADED_PPD` moves past 2026-04-02 (the host then needs `ANSI_DATE_LITERAL_HOSTS`). |

A new platform client would not unlock any of these on its own: Accela
(Chattanooga, Durham, Springfield), Salesforce (Spokane, Virginia Beach), Dynamics
(Phoenix) and SeeClickFix/Comcate (Las Vegas) all lack an anonymous row API for
these agencies.

## Findings outside this pass's scope

### SNAP licences cover a statewide sample, not the metro (54 metros)

`snap_sla_spec(state)` filters the national SNAP layer by state only, runs in
snapshot mode, and the ArcGIS client orders pages by `ObjectId`. Each poll is
capped at the scheduler's 1,000 rows, so every SNAP job fetches the same 1,000
lowest-`ObjectId` retailers in its state on every poll and tags them with its own
city. Measured 2026-09-30 for Florida: 14,138 retailers statewide, 242 inside
Tallahassee's bbox, and 19 of those among the 1,000 rows each poll returns. The
other 981 are elsewhere in Florida. Every SNAP-backed metro is affected: a
metro in a large state receives a fraction of its own retailers, and every metro
receives rows from elsewhere in its state. That is 54 metros, including five of
the 18 four-family metros (Cleveland, Columbus, Pittsburgh, Raleigh,
Tallahassee). The fix is to add each metro's bbox to its SNAP `where`
clause and to set `batch_limit` for any metro whose bbox holds more than 1,000
retailers. It touches 54 corpus files, so it belongs in its own change.

Fixed in that change (`snap-metro-scope-2026-09-30.md`): every SNAP spec now
reads its state inside its metro bbox, and 18 metros declare a higher cap. The
54 metros go from 5,694 of their 34,686 retailers to all of them.

### Geocoder normalization drops context (address-only feeds)

Both defects are in `normalize_address` (`apps/api/src/spatial/geocoder.py`) and
apply after `geocode_row_if_declared` appends a feed's `geocode_context`:

- `FL` is in `_UNIT_TOKENS` (as in "floor"), so any `FL` token after the first is
  dropped together with the token after it. `..., Tallahassee, FL` reaches the
  Census geocoder as `... TALLAHASSEE`, and `... Unincorporated FL 331751234`
  loses the state and ZIP. The Census oneline geocoder usually still resolves
  the street and city (105 of 120 Leon addresses did), so the damage is limited
  to addresses the city alone cannot place. Florida feeds that declare a
  context: Cape Coral, Miami-Dade and Port St. Lucie permits, and Orlando `sla`.
- Everything after a `#` is cut, which removes the appended context along with
  the unit. All four `#` addresses in the Leon sample missed as a result, and all
  four resolved once the state or ZIP was kept.

Either fix changes what `normalize_address` returns for some inputs, so it
needs a `NORM_VERSION` bump (the geocode cache is keyed on it). Not changed
here.

Fixed in a later change ("Addresses keep their place" in
`feed-health-2026-09-30.md`): normalization `v3` keeps `FL` as the state
where it ends a line or precedes a ZIP code, and a `#` drops only its value.
