# Feed health — 2026-09-30

On 2026-09-30 every registered poll job (367, GBFS and national feeds aside)
was polled once through the real scheduler and clients, 50 rows each, with
Kafka mocked. 36 jobs failed outright, 8 fetched nothing, and 16 fetched rows
but published none. This change repairs the ones a spec, endpoint or small
client fix can reach, retracts one feed that has no public source, moves two
licence feeds whose source holds no rows for their city to the SNAP retailer
fallback, and lists the rest with the reason. A second stacked change repairs
five of the mid-Atlantic `deeds` feeds and retracts seven whose cities publish
no sales (see "Mid-Atlantic deeds"). A third fixes the filter an incremental
poll sends, which a second poll of every affected feed showed was failing on
32 feeds and reading the wrong rows on others (see "Incremental filters"). A
fourth reads Richmond's sales from the assessor's monthly workbook (see
"Richmond's transfers workbook"). A fifth makes a backfill read each feed the
way its poll does, and repairs three feeds' polls that the check turned up
(see "Backfills"). A sixth makes the polls of six text-dated feeds read the
rows since their watermark (see "Text-dated polls").

| | Jobs | Repaired here | Left, with reason below |
|---|---|---|---|
| Failed outright | 36 | 21 (seven of them mid-Atlantic `deeds`: Roanoke's in the third change, Richmond's in the fourth), and eight retracted: Madison `permits` and seven mid-Atlantic `deeds` | 7 |
| Fetched rows, published none | 16 | 9 (Lynchburg `deeds` in the third change), and Milwaukee `deeds` was fine on a full read | 6 |
| Fetched nothing | 8 | 5, and Lexington and Seattle `sla` moved to SNAP | 1, Tulsa `311` (an outage) |

Three feeds that did publish were repaired too: New Haven and Bridgeport `sla`
published private individuals' names as premises, and Henderson `permits`
dropped 38% of its rows.

## How it was measured

- **Census.** One `poll_job` per enabled job at a 50-row limit, real HTTP
  clients, Kafka and the DLQ mocked. Feeds that declare geocoding had the
  geocoder stubbed to the metro centre, so the check measures ids, fields and
  addresses rather than the geocode cache. A job with no stored watermark reads
  its source's first rows in the default order, which for several feeds means
  their oldest rows (see "What the census overstates").
- **Repairs.** Each repaired feed was polled again the same way at 300 to
  20,000 rows, and, where the feed is incremental, a second time from a recent
  watermark so the filter the scheduler sends was exercised as well.
- Requests were spaced at least 2 seconds apart per host, with the default
  client User-Agent.

## Repairs

### Endpoints that moved or were never right

| Feed | Why it failed | Fix | After |
|---|---|---|---|
| San Francisco `permits`, `311`, `crime`, `deeds`, `sla` | `data.sfgov.org` now answers `301` to `data.sf.gov`, and the client does not follow redirects | endpoints on `data.sf.gov`; unit and storey counts now arrive as `"2.0"`, so the permit parse coerces them instead of dropping the row | 463 of 500, 193 of 200, 170 of 200, 200 of 200, 198 of 200 |
| Lakeland `permits` | the on-premises iMS MapServer resets every connection; its empty field map had also dead-lettered every row, since `PERMIT_NO` is not in the producer's default id chain | the city's hosted `IMS_Projects_Permits` view, watermark `APPROVED` (`ISSUED` stops at 2025-06-25), `TYPE = 'Permit'`, and a field map that never reads `APPLICANT_NAME` | 500 of 500 |
| Peoria `deeds` | `endpoint_by_year` named last year's layer id; layer ids shift each January | the year map is gone: layer 5 is always Current Year Sales | 479 of 500 (21 rows share a document number with another parcel of the same sale) |
| Boston `crime`, `inspections`, `violations` | each id was the CKAN package, which `datastore_search` answers with 404 | the current resource ids; the text timestamps keep their own format as the watermark (below); inspections' watermark moves to `resultdttm`, since `status_date` is null on 55% of rows since August | 852 of 1,000 (148 with no coordinates in the source), 17 of 1,000 (see id keys under "Found along the way"), 994 of 1,000 |

Boston's timestamps are text (`2026-09-27 01:40:00+00`). Stored as ISO, a
watermark's `T` sorts after the space, so rows from the watermark's own day
compared lower and were never read: `> '2026-09-26T12:00:00'` matched 7 rows
where `> '2026-09-26 12:00:00'` matched 100. The three feeds now declare
`watermark_type: text` with their format (ADR 0005), and an incremental poll
from `2026-09-26 12:00:00+00` fetched those 100.

### Queries the server rejected

| Feed | Why it failed | Fix | After |
|---|---|---|---|
| Augusta `permits` | the table has no object id, and the client's default `OBJECTID` sort returns 400 | `order_by: DATE_ISSUE DESC,PERMITNUMBER ASC,PARID ASC` | 500 of 500 |
| Dayton `311` | the MapServer layer omits `objectIdField`, so the same default sort returns 400 | `order_by: SERVNO ASC`; the service request number is the id | 500 of 500 |

The Augusta, Dayton and Peoria hosts also refuse ISO date strings in a
watermark filter (400) and accept `date 'YYYY-MM-DD'` literals, so they join
`ANSI_DATE_LITERAL_HOSTS`.

### Platforms the scheduler could not route

Spokane `permits` (`excel`) and Madison `permits` (`accela`) raised `has no
client registered` on every poll: the scheduler's routing table stopped at
`csv`. Both now route. Spokane's workbook is not in date order (22,845 of
48,466 adjacent rows step back in time), so the poll sorts it by issue date,
and it polls hourly instead of every 5 minutes since the file is re-downloaded
whole each time: 20,000 of 20,000. Madison's Accela page has no API behind it
(next section).

### Retracted: Madison permits

The Accela Citizen Access page registered as Madison's permits feed answers
every API call with a redirect to an HTML error page, and Accela's Construct
API needs a registered App ID. No other public source of City of Madison
building permits exists: the city's SSRS reports export only through a session
postback, Dane County's zoning permits cover unincorporated towns and stop at
2026-07-23, and none of the nine "Madison" permit layers on ArcGIS Online is
Madison, WI. The feed is removed, and Madison gets the SNAP retailer `sla`
fallback that 54 other cities use: 303 of 303.

### A file the CSV client misread

Milwaukee `permits` ends its lines with a bare carriage return, which the
client read as one line with returns inside unquoted fields. It now opens the
text with `newline=""`: 990 of 1,000. The feed polls every 30 minutes instead
of 5, since the 3 MB file is downloaded whole each time, and its newest issue
date is 2026-06-15: the city has not updated it since.

### Field maps that matched nothing

| Feed | Why no row published | Fix | Before | After |
|---|---|---|---|---|
| Hartford `sla` | the map named columns the state table does not have, so every row was dropped for a missing licence id | the Connecticut liquor map (below) | 0 of 50 | 500 of 500 |
| New Haven, Bridgeport `sla` | they published every state credential in the city, pharmacists and contractors included, with the holder's name as the premises name | filtered to liquor permits; `name` is never read | | 500 of 500 each |
| Henderson `sla` (CSV) | the client normalizes headers (`Original Issue Date` becomes `original_issue_date`), and the map named the raw headers | normalized names, watermark `original_issue_date`, read newest first | 0 of 50 | 300 of 300 |
| Henderson `permits` | rows without coordinates had only the house number to geocode | the composed street address is read first | 31 of 50 | 456 of 500 |
| Cape Coral `permits` | `Addr1` is only the house number, and the geocoder refused it | a leaf composer joins number, direction, street, type and the row's own city; rows dated in the future (33, up to the year 2610) are filtered out | 0 of 50 | 500 of 500 |
| Cleveland `permits` | `PERMIT_NUMBER`, `STATUS` and `ADDRESS` no longer exist | `PERMIT_ID`, `CURRENT_TASK_STATUS`, `PRIMARY_ADDRESS` | 0 of 50 | 500 of 500 |
| Fort Worth `permits` | the address candidate was the house number column | `Address` | 0 of 50 | 500 of 500 |
| Seattle `permits` | an empty field map | a real one (`permitnum`, `issueddate`, `originaladdress1`, ...) | 0 of 50 | 426 of 426 |
| Tampa `street_cut` | outside NYC the street-cut producer read only Chicago's column names and stamped every row `chicago`; the map also used permit-producer keys | the producer reads the city's map first and stamps the row's own city; street-cut keys | 0 of 50 | 500 of 500 |
| Cincinnati `permits` | the id candidates did not exist and rows carry no coordinates | `permitnum`, geocoding on the address | 0 of 50 | 587 of 644 (57 repeat an id) |

The Connecticut feeds read `data.ct.gov` `ngch-56tr`, which holds every
credential the Department of Consumer Protection issues: 247,564 for Hartford
alone, most of them individuals. `src/producers/ct_liquor_specs.py` lists the
54 permanent permit types for premises that sell, serve or make alcohol
(temporary, event, caterer, out-of-state and label registrations are left
out), and the three feeds filter on them: 1,554 Hartford rows. On an
individually held permit `name` is the permittee, a person, so the map never
reads it; `businessname` and `dba` hold the premises.

Permit parsing gained one generic hook along the way: a city leaf may define
`compose_permit_address(row)` for layers that split the address across
columns. Albuquerque's special case now uses it, and Cape Coral and Henderson
do too.

## Not repaired here

| Feed | Why | What it needs |
|---|---|---|
| Phoenix `deeds` (CSV) | the endpoint is a 61 MB zip of a 270 MB pipe-delimited file (903,301 affidavits); the spec names no zip member or delimiter | a streaming zip reader in the CSV client, which today holds the whole file and every kept row in memory |
| Boston `deeds` | the id is the CKAN package; the FY2026 assessment resource (`ee73430d-...`, 184,552 rows) has none of the mapped column names and no coordinates, and a new resource appears every fiscal year | a field map on the uppercase columns, coordinates from a join to the SAM address points on `GIS_ID` (the CKAN client has no join) or geocoding, and `endpoint_by_year` |
| Ocala `permits`, Orlando `permits` | the Florida statewide cadastral polygon layer now answers 499 Token Required; its centroid twin is anonymous. The specs' county codes select Jackson (42) and Levy (48) counties: FDOR numbers Marion 52 and Orange 58 | the centroid layer, corrected county codes (and the 01-67 county map behind them), and an object-id band in the filter, since un-banded Orange queries time out. Orlando also has a real permit feed, Socrata `ryhf-m453`, whose recent rows need geocoding |
| Bend `crime` | the layer now answers 499 Token Required; the public replacement lists each offense's exact address, where the old feed gave block ranges | a decision on publishing exact offense addresses; left failing |
| Lincoln `permits`, Sioux Falls `permits` | each city's permit service fails every query, even a bare count: Lincoln with 400 "Unable to complete operation", Sioux Falls with 500 and a stopped Java web application behind the service | a restart on the city's side; no other public permit source was found for either |
| El Paso `311` | Cloudflare answers 403 to this network | a check from the production network |
| Chicago, NYC, Seattle `energy_benchmark`; NYC, Seattle `bike_ped` | the context-observation producer has no per-row hook: an energy row fans out into several metrics and counter rows fold into one observation per sensor-day, so `poll_job` dead-letters every row | a batch hook in `poll_job`, or running these through the producer's own stream |

## Mid-Atlantic deeds

The 14 cities of the 2026-09-06 mid-Atlantic wave were registered with only a
`deeds` feed, and all 14 failed. None of the registered URLs ever pointed at a
live sales source: three hosts have no DNS (Allentown, Dover, Wilmington DE);
seven paths sit on city websites with no ArcGIS Server behind them (Albany,
Burlington, Harrisburg, Huntington, Providence, Richmond, Roanoke); two name
ArcGIS Online services or organizations that do not exist (Frederick,
Manchester); and two point at the wrong place (Charleston WV at a Charleston,
SC service; Portland ME at a layer id the service does not have). The
interlock gate checks a spec's shape, not whether its endpoint answers.

The second stacked change repairs five and retracts seven. Each repaired feed
was polled live through `poll_job` on 2026-09-30 at its production cap:

| City | Source and filter | Mode | Rows | Newest sale | Published |
|---|---|---|---|---|---|
| Frederick | Maryland SDAT assessments, Frederick County view (Socrata `gx8c-a963`); postal city FREDERICK | snapshot, newest first | 56,256 | 2026-08-06 | 1,000 of 1,000 |
| Providence | the city's Parcels with CAMA layer (`Parcel_Zoning_FL`); rows with a sale date | snapshot, 1,500 newest | 35,421 | 2026-09-20 | 1,496 of 1,500 (4 parcels drawn as two polygons) |
| Burlington | Vermont Property Transfers (VCGI); town code 114 | incremental on `postedDate` | 6,788 | posted 2026-09-18 | 1,000 of 1,000, and 26 from a 2026-09-10 watermark |
| Allentown | the city's Tax Parcels Assessed layer; rows with a sale year and month | snapshot, newest first | 34,234 | 2026-09 | 1,000 of 1,000 |
| Charleston WV | Kanawha County Assessor parcels (`Parcel_Line_Layer/MapServer/1`); tax districts 09 to 14 | snapshot, newest first | 23,171 | complete to 2026-05 | 992 of 1,000 (8 parcels drawn as two polygons) |

- **No party names.** No feed maps an owner, grantor or buyer column. The four
  ArcGIS feeds list their columns in `select`, which the ArcGIS client now
  sends as `outFields`, so those columns stay on the server. Frederick's SDAT
  view hides owner names but still carries the grantor's; it is read and never
  mapped.
- **Allentown** records a sale's year and month but not its day. The leaf's
  `compose_deed_date` stamps the first of the month: the deeds producer calls a
  leaf composer when `recorded_date` is unmapped, and Cincinnati's split sale
  date moved onto the same hook.
- **Burlington** polls on the date a return was posted, because about 30% of
  returns post more than a month after closing and a closing-date cursor would
  skip them. The recorded date is still the closing date.
- **Charleston WV.** The assessor posts sales about four months late (80 sales
  county-wide from June to September 2026, against about 500 a month before),
  so the feed expects a new sale every 180 days. The layer has no city column;
  districts 09 to 14 hold about 94% of the parcels inside the metro box. The
  host rejects ISO date literals, so it joins `ANSI_DATE_LITERAL_HOSTS` in case
  the feed goes incremental.
- **Providence** has one sale dated 2026-10-08, a typo at the source. It is
  published as dated; the scheduler already refuses a future date as a
  watermark.

Seven cities publish no sale date or price anywhere public, so their `deeds`
feed is retracted and each gets the SNAP retailer `sla` slice instead (stores
inside the metro box, polled live on 2026-09-30):

| City | Why there is no source | SNAP stores published |
|---|---|---|
| Albany | city, county and state parcel layers stop at deed book and page; New York's RP-5217 sales sit behind the ORPTS Sales Web search | 133 |
| Dover | Kent County's parcel layer has a deed book and page reference only; its sales history is in the per-parcel PRIDE site | 67 |
| Harrisburg | the city's parcel snapshots carry a purchase date frozen at 2022-12-30 and no price; Dauphin County's sales search has no export | 144 |
| Huntington | Cabell County's parcel layer and the state parcel tables carry deed book and page only | 59 |
| Manchester | the assessor publishes through a per-property Vision site; the state's PA-34 sales go to municipalities only | 124 |
| Portland ME | the parcel layers have no sale fields; the one deed-dated layer has seven dated rows, the newest from 2005 | 92 |
| Wilmington DE | New Castle County's `PropertySales` MapServer could not be checked (its host answers HTTP 472 to this network), and its ArcGIS Online records describe yearly layers for 2013 to 2019 only | 144 |

Two cities needed more than a spec edit. Roanoke's replacement needed the
parcel join in `poll_job`, which the third change adds (see "Incremental
filters"), and Richmond's needed a workbook reader, which the fourth adds (see
"Richmond's transfers workbook"):

| City | Replacement found | Rows | Newest sale | What it needs |
|---|---|---|---|---|
| Roanoke | the city's transfer-history table, no geometry | 214,121 dated | 2026-09-28 | done in the third change: each sale sits at its parcel's centroid |
| Richmond | the assessor's monthly transfers workbook (.xlsx, 72 MB) | 439,398 | 2026-09-22 | done in the fourth change: the Excel client streams the workbook, keeps a year of sales, and places each at its parcel's centroid |


## Feeds that fetched nothing

Five of the eight are repaired, two move to the SNAP fallback, and Tulsa `311`
is an outage on the city's side.

Five were registered at an ArcGIS service root, a `.../FeatureServer` URL with
no layer index: Boise `crime`, Las Vegas `crime`, and Louisville `crime`,
`permits` and `street_cut`. A service root answers `/query` at HTTP 200 with
its own description, which the client read as an empty page, so every poll
reported SUCCESS with zero rows. They were the only 5 of 239 ArcGIS endpoints
without a layer index. The client now raises on a page with no `features`, and
a registry test requires every ArcGIS endpoint to name a layer. A layer index
alone was not enough for three of them:

| Feed | Behind the service root | Fix | After |
|---|---|---|---|
| Boise `crime` | the right layer | `/0` | 300 of 300; the newest offense is 2026-09-01, since Boise holds recent offenses back |
| Las Vegas `crime` | an archive whose newest call is 2024-02-29 | the daily 30-day calls-for-service view, whose columns are CamelCase, read newest first with a 4,000-row cap (about two days of calls) | 300 of 300 |
| Louisville `crime` | the closed 2025 table | the 2026 table, with `endpoint_by_year` so each January moves to the next one | 237 of 300 (52 repeat a multi-offense incident, 11 have no usable address; geocoder stubbed) |
| Louisville `permits` | the right layer, read from 2014 forward | `/0`, newest first | 296 of 300 |
| Louisville `street_cut` | the right layer, but the map used `job_id` where the street-cut producer reads `permit_id` | `/0`, newest first, street-cut keys, and the producer change above | 266 of 266 |

The Las Vegas view gives addresses as hundred blocks and intersections, as the
archive did.

Lexington and Seattle `sla` fetched nothing because their sources hold no rows
for the city. Lexington's Kentucky ABC layer is published by Louisville Metro
and holds Jefferson County only (5,523 rows, none in Fayette), and no public
Fayette licence layer was found. Seattle's Liquor and Cannabis Board table is
a statewide log of applications awaiting a local reply: it held 23 rows on
2026-08-23 and none on 2026-09-30, and its spec never mapped a field; the
board's renewal tables stopped updating in April. Both feeds move to the SNAP
retailer fallback, which holds 254 stores in Lexington's box and 1,103 in
Seattle's; a 300-row poll published every row it read. A current licence table
for either city should replace SNAP.

Tulsa `311` reads a 30-day view of the city's case system, and the system has
opened no case since 2026-08-27, so the view is empty. No fresher public source
exists. The spec stays, and its host joins `ANSI_DATE_LITERAL_HOSTS`: it
answers an ISO watermark filter with a 400, so the second poll after the city
recovers would fail.

## What the census overstates

A job with no stored watermark reads its source's first rows in the default
order, so the one-poll census judged several incremental feeds on their oldest
rows. Baton Rouge `permits` published 1 of 50: its 2019 rows have no
coordinates. From a September watermark it publishes 618 of 632. Milwaukee
`deeds` published 1 of its first 50 rows and 5,497 of 5,685 on a full read. The 11 feeds
that dead-lettered more than 30% of their first 50 rows (Baltimore, Denver,
Hartford, Pittsburgh and San José `311`; Baton Rouge, Chicago, Hartford,
Henderson, Norfolk and San Diego `permits`) were not re-checked one by one.

## Found along the way

These cut across many feeds and need scheduler changes, so they were left to
the next change. The third change fixes the first, second and fourth (see
"Incremental filters"); the rest stand.

- **The watermark advances from the event's date, not the filter's column.**
  `poll_job` stores the newest `issuance_date`, `created_date`,
  `effective_date` or `recorded_date` of the published events and falls back to
  the watermark column only when an event has none. Where the two differ, the
  next filter compares the column against the wrong date. The Connecticut
  `sla` feeds filter on the refresh date but store the permit's effective date,
  which runs into the future: a live poll logged `ignoring future watermark
  2026-11-06`. Fixed in the third change.
- **Record ids take the first id key that has a value, not all of them.**
  Boston inspections list `licenseno` then `_id`; a licence number repeats on
  every row of an inspection and on every later inspection, so a first poll of
  1,000 rows published 17. Lynchburg deeds, the parcel-keyed deeds in the
  snapshot-reach note, and St. Louis permits (special-cased in the scheduler)
  have the same shape. Fixed in the third change by a `composite_id` flag;
  St. Louis keeps its special case.
- **170 of 274 incremental feeds are not ordered by their watermark column.**
  A capped poll then reads the first rows by object id newer than the
  watermark, and the watermark jumps to the newest date among them, so rows
  dated in between that sit past the cap are never read. It bites on a cold
  start or after an outage longer than one cap's worth of rows. The third
  change reorders Canton `deeds`, whose second poll showed the jump; the rest
  stand.
- **Date-only watermarks lose the boundary day.** A feed whose dates carry no
  time stores `2026-09-28T00:00:00`, and `>` then skips rows published later
  with that same date. From `2026-09-01T00:00:00`, Baton Rouge fetched 632 of
  the 671 permits issued since 1 September. Fixed in the third change.
- **ArcGIS polls read every column a spec does not name.** The ArcGIS client
  ignored `select` until the mid-Atlantic deeds change, which sends it as
  `outFields`. Only those four feeds declare one so far, so owner, applicant
  and contractor names still ride along with other feeds' rows and are kept in
  the DLQ payload of any row that fails to parse.
- **`maps.cityofmadison.com` refuses ISO date strings** too. No feed polls it
  today; a future Madison spec should add the host to
  `ANSI_DATE_LITERAL_HOSTS`.

## Incremental filters

The census polled each job once, from no watermark, so it never sent an
incremental filter. The third stacked change polled every incremental ArcGIS
feed a second time, from the watermark its first poll stored, and fixed what
that showed.

- **32 feeds failed every poll after their first.** Their hosts answer an ISO
  date string with a 400 ("Unable to complete operation"), and 28 of the hosts
  were not in `ANSI_DATE_LITERAL_HOSTS`: Aurora, Billings, Boulder, Bozeman,
  Canton, Cape Coral, Columbus GA, Durham, Evansville, Fort Worth, Glendale AZ,
  Hartford (permits), Houston, Huntsville, Indianapolis, Las Cruces, Melbourne,
  Memphis, Montgomery AL, Nampa, Omaha, Phoenix (two hosts), Portland, Tampa,
  Toledo, Wichita and Wilmington NC. They join the list.
- **ANSI literals compared whole days.** The literal was `date 'YYYY-MM-DD'`,
  which re-read the watermark's day on every poll and never let a day with
  more rows than the cap go. It is now `timestamp 'YYYY-MM-DD HH:MM:SS'`,
  exact to the second; every incremental ANSI host answered it on 2026-09-30.
- **Layers read literals in their own time zone.** A layer whose
  `dateFieldsTimeReference` names a zone reads every literal, ISO or ANSI, as
  local time there, while the scheduler stores UTC. 25 incremental feeds
  declare one, DC's four among them. Under the date
  literal, a DC watermark between 8 PM and midnight Eastern, whose UTC date is
  already the next day, sent that next day, and the requests filed before
  midnight were skipped; an exact literal without the zone would start four
  hours late. The client now reads the zone from the layer's metadata, which it
  already fetched for paging, and the literal is written in local time.
  Greenville and Baltimore `sla` take ISO strings but read them as local, so
  they get local ISO strings.
- **Date-only watermarks keep their day.** A watermark on a whole hour is taken
  as a date: the filter keeps the boundary with `>=`, and the dedup drops the
  rows already seen. From `2026-08-18T00:00:00`, Tallahassee `permits` found a
  permit applied for that same day that its first poll had not seen. A
  timestamp keeps a strict `>`.
- **A boundary that fills the cap is stepped past.** When a poll fills its cap
  without moving the watermark, the next poll steps past the boundary (`>` on a
  date, `>=` the next second on a timestamp) until the watermark moves, and
  logs it. A newest-first read never steps past, since a newer row would have
  come first.
- **The watermark follows the filter column.** It is the newest value of the
  column the filter compares; the event's own date stands in only when that
  column is empty.
- **Sales keep one id each.** A `composite_id` flag joins every id key into the
  record id, where the first key with a value used to win. 18 `deeds` feeds
  key a sale by parcel and date, document, or book and page, and Boston
  `inspections` by licence and result time.
- **Parcel joins run in `poll_job`.** Lynchburg's and Roanoke's sales tables
  have no geometry and declare a `parcel_join`, which only the standalone
  producer applied. `poll_job` now looks up each batch's parcel centroids, with
  numeric keys sent as numbers. Roanoke moves to the city's transfer-history
  table; Lynchburg's feed reads newest first and names only the columns it
  maps, so buyer and seller names stay on the server.

### Checked live

On 2026-09-30, 78 feeds were polled twice through `poll_job` at 200 rows,
Kafka mocked: every incremental ArcGIS feed on an ANSI host or with a declared
zone, Baltimore `sla`, Greenville `permits`, Boston `sla` and `inspections`,
and every `deeds` feed whose id changed. 77 succeeded on both polls
(Tallahassee `permits` on a second try, after one query came back without
features); Sioux Falls `permits` fails every query (above). Lynchburg and Roanoke published 199
and 200 of their newest 200 sales. The second polls' duplicates had three
sources: the boundary day re-read under `>=`; source rows that repeat an id
within one poll (one Medford permit spans 174 taxlot rows); and a timestamp's
fraction of a second, which the JSON drops, so the watermark row came back
once more.

The survey also caught four feeds this change repairs:

| Feed | What the second poll showed | Fix | After |
|---|---|---|---|
| Chattanooga `deeds` | the new composite key named a `PIN` column the layer does not have, so every sale on a date shared one id: 16 of 200 published | key on `GISLINK` and the sale date; `bbl`, which named the same missing column, reads `TAX_MAP_NO` | 191 of 200 (9 rows repeat a parcel's sale) |
| Raleigh `deeds` | the same, with Wake County's `PIN_NUM`: 9 of 200 | key and `bbl` on `PIN_NUM` | 200 of 200 |
| Canton `deeds` | keyed by parcel alone, so a parcel's next sale was a duplicate, and read in object-id order, which does not follow the transfer date: the second poll jumped from 2026-07-31 to 2026-09-29 | key by parcel and instrument number, read newest first | the newest 200 rows hold 114 sales; a sale's row can repeat up to six times |
| Milwaukee `sla` | each refresh stamps one `GIS_DATETIME` on all 1,275 rows, and the server holds it finer than the JSON returns (`> 01:23:59` matches every row, `>= 01:24:00` none), so every poll re-read the same first 1,000 rows | read the whole layer as a snapshot every 30 minutes, cap 2,000 | 1,274 of 1,275 (one row has no coordinates) |

Left as is: a row the dedup skips does not move the watermark, so a layer that
restamps every row at each refresh keeps re-reading one refresh. Milwaukee
`sla` was the only such layer in the survey. The Socrata feeds that filter on
a refresh date (the Connecticut and Texas `sla` feeds) were not part of it.


## Richmond's transfers workbook

Richmond's assessor publishes every recorded property transfer, 439,398 rows
on 2026-09-23, as one Excel workbook re-released each month under a new name
(`Assessor_Transfers_2026-09-23.xlsx`). The file is 72 MB and its worksheet
XML 400 MB, so pandas would hold gigabytes, and xlrd no longer opens `.xlsx`.
The fourth stacked change reads it without new dependencies:

- **A streaming reader.** `xlsx_reader.py` walks the worksheet a row at a time
  with the standard library's `iterparse` and keeps the shared strings in one
  buffer: 41 seconds and about 60 MB for the whole file. Date-formatted cells
  come back as dates (Excel's 1900 and 1904 calendars), and the Excel client
  hands them on as ISO strings, as the ArcGIS and CSV clients do.
- **The monthly link.** The spec registers the city's media page
  (`rva.gov/media/53946`) and a `link_pattern`; each poll reads the page and
  takes the newest file it links whose name matches.
- **A 304 between releases.** The client keeps the workbook's `ETag` and
  `Last-Modified` once a poll has read it in full, so the daily poll asks
  whether it changed and reads nothing until a new file appears. A poll that
  stopped short reads the file again next time.
- **A year of sales.** The feed keeps transfers since the same day a year
  before (`CURRENT_DATE - INTERVAL '365' DAY`, which the CSV and Excel clients
  now resolve to a date): 6,650 on 2026-09-30, 1,425 of them in the last 90
  days, under a cap of 12,000. A sale is its parcel, date, deed book and page,
  which no two rows in that year share. $0 and non-market transfers are kept,
  as elsewhere.
- **Coordinates from the parcel.** The workbook has none, so each sale takes
  its parcel's centroid from the city's Parcels layer by `PIN`. The row's
  lower-cased `pin` is named by the join's new `row_key`.
- **Long parcel lists.** 100 quoted 11-character PINs made a 2,155-character
  query URL, and Richmond's ArcGIS Online host answers 404 past about 2,000.
  The client now splits each `IN (...)` list at 1,400 encoded characters as
  well as 100 values. Numeric keys (Lynchburg, Roanoke) still send 100 a
  request; DC's space-padded `SSL` values now send about 47.
- **No party names.** `GRANTEE` and `GRANTOR` never leave the client: the
  spec's `select` names only the columns the feed reads.
- **Backfills.** `scripts/backfill_loader.py` handed a client only its own
  `order_by`, so a Richmond backfill read the media page as a workbook and
  failed. The fifth change passes the `select`, `link_pattern` and parcel join
  to backfills too (see "Backfills").

Polled live through `poll_job` on 2026-09-30, Kafka mocked: 6,650 sales
fetched and published, none dead-lettered, 6,647 placed at a parcel centroid
inside the metro box (three found no parcel), dated 2025-09-30 to
2026-09-22. The parcel lookups took 100 requests at 2 seconds apart. A second
poll got a 304 and read nothing. A cold start publishes the whole year once,
about 22 minutes at the scheduler's 0.2 seconds a row; after that, a new
workbook brings its month's new sales.

## Backfills

`scripts/backfill_loader.py` loads a feed's history through the scheduler's
clients, producers, dedup filter and DLQ, but it built each query itself and
handed the client nothing but an order. The fifth stacked change makes a
backfill read each feed the way `poll_job` does:

- **The poll's client arguments.** A backfill now hands the client what
  `poll_job` hands it: a spec's `select`, which keeps owner and party names on
  the server; Richmond's `link_pattern`; a zipped CSV's member and delimiter;
  a Carto keyset column; a CSV's fallback endpoints and typed watermark column.
  A test polls and backfills every job with a mocked client and compares the
  two. Only the order differs: a window pages newest first on its watermark
  column.
- **Parcel joins.** A sales table without geometry takes each parcel's
  centroid, as `poll_job` places it.
- **Text-typed windows in the column's format.** A text-typed watermark
  (ADR 0005) compares as text, and the window started from an ISO literal.
  Las Vegas `deeds` answered that with a 400; Virginia Beach `permits`
  (`2026/09/10`) and Henderson `sla` (`08/20/2026`) matched nothing. The
  window now starts in the column's own format, as a poll's stored watermark
  does; San Jose's CKAN filter casts both sides to timestamps.
- **Formats the server can't order are windowed client-side.** Text sorts as
  dates only when its format is year first. No literal selects a window on
  `MM/DD/YYYY` or Honolulu's `September 7, 2026 at 1:27 PM`: from
  `07/02/2026`, Reno and Rochester `deeds` each read 200 sales made on a
  December 31, from 2018 and from 1990 to 2025, and Worcester `permits` read
  173 September rows of past years among its 200. A
  backfill of those six feeds reads the table without the window and keeps
  the rows inside it; the report's `outside_window` counts the rest. A CSV
  already compares in the declared format. Such a column is not in date
  order on the server either, so these feeds and San Jose's keep their
  spec's order instead of paging newest first. The sixth change sends these
  windows to the server as dates (see "Text-dated polls").
- **Snapshots keep their own order.** A backfill of a feed without a
  watermark column reads it in the spec's order, as the poll does.

### Checked live

On 2026-09-30 the 49 jobs whose backfill query changed were backfilled twice,
with the old loader and the new, from 90 days back at 200 rows each, Kafka
mocked, geocoding stubbed to the metro centre, requests 2 seconds apart. The
feeds whose result changed:

| Feed | Old loader | New loader |
|---|---|---|
| St. Louis `311`; Inland Empire, Oakland and Santa Rosa `sla` | read nothing: the zipped CSV's member never reached the client | 198, 186, 159 and 164 published |
| Richmond `deeds` | failed on the media page | 200 published, all placed at a parcel centroid |
| Lynchburg and Roanoke `deeds` | fetched party names; none placed | no names; 199 and 186 placed |
| Burlington, Charleston WV and Providence `deeds` | fetched owner and seller columns | only the `select` columns |
| Chattanooga `permits` | failed on the primary endpoint's 500 | 200 through its fallback |
| Philadelphia `permits`, `sla` and `deeds` | 0 published, 0 placed and 0 placed | 199 published, 190 placed and 182 placed |
| Las Vegas `deeds` | 400 | 200 published |
| Virginia Beach `permits`, Henderson `sla` | read nothing | 172 and 200 published, inside the window |
| Boston `sla` | 62 | 65 (rows from the window's first day) |
| Milwaukee `deeds` | 200 sales from 2025 | none: the file holds only 2025 |

San Jose `311`, read in full with the fixed CKAN client, shows the cast: the
old loader's text window read 228,536 rows, 142,333 of them before the
window; the new one reads 86,202, all inside it (44,526 published; the rest
are `0,0` points the parser drops, as documented).

The six client-windowed feeds were read in full with the new loader, again
from 90 days back:

| Feed | Rows read | Inside the window | Published | Dated |
|---|---|---|---|---|
| Honolulu `311` | 2,186 | 2,186 | 2,126 | 2026-08-31 to 2026-09-29 |
| Worcester `sla` | 15,776 | 48 | 48 | 2026-07-06 to 2026-09-21 |
| Virginia Beach `sla` | 42,135 | 606 | 556 | 2026-07-03 to 2026-08-31 |
| Worcester `permits` | 53,271 | 1,301 | 1,301 | 2026-07-03 to 2026-09-26 |
| Rochester `deeds` | 64,709 | 373 | 373 | 2026-07-03 to 2026-08-14 |
| Reno `deeds` | 194,122 | 2,690 | 2,687 | 2026-07-06 to 2026-09-28 |

### Repaired along the way

- **St. Louis `permits`** was registered with `ISSUEDATE` as month-name text
  (`August, 07 2026 00:00:00`); by 2026-09-30 the export wrote
  `2026-09-18 00:00:00.0` in every row. The CSV client compares the column in
  the declared format, and the old one parsed no row, so every poll after the
  first read nothing. The format is now the export's, and the CSV client also
  reads a filter literal written as ISO, as a stored watermark is. Polled
  twice, the second from 2026-09-20, it fetched 95 rows; a backfill publishes
  199 of 200.
- **Laredo and San Antonio `permits`** filter on CKAN columns whose names hold
  spaces and a dot (`PERMIT ISS. DATE`, `DATE ISSUED`). The client passed the
  unquoted name through, and every filtered poll was a 409 syntax error. It
  now quotes a name with spaces, in the filter and in the order (an order
  on `DATE ISSUED` was sent as `"DATE"`). Polled twice,
  the second from 2026-09-15 and 2026-09-25, they fetched 29 and 200 rows.
  San Antonio's column is `YYYY-MM-DD` text, now declared so (ADR 0005): an
  ISO watermark compared as text sorted each date below its own midnight.
- **Cincinnati `deeds`** named a `SaleDate` column the auditor's file does
  not have (the sale date is split across three columns), so a backfill
  windowed on it read nothing. The feed is a snapshot and its poll never
  filtered on the column; it now names none, and a backfill reads the file:
  1,131 valid sales, 936 published, one per conveyance (59 sales span
  several parcels, one of them 104).

### Found, not fixed

- **Milwaukee `permits`** has not changed since 2026-06-21; its newest permit
  was issued 2026-06-15.
- **Cincinnati `deeds` publishes no coordinates.** Its address is split
  across three columns, and the deeds producer geocodes a single address
  column (`address_street`), which the feed does not map. A leaf address
  composer, like the permits producer's, needs a spine edit.
- **DC `deeds`** places none: condominium lots (`0016    2033`) are not in the
  Parcel Lots layer the join reads.
- **Philadelphia `311`**: the newest requests have no coordinates yet, and a
  row geocoded later is never read again. **Baton Rouge `sla`**: read newest
  first, as its poll reads it, 5 of 200 rows are placed (143 of the oldest
  200).
- **Owner and party names.** 16 `deeds` specs map grantor or grantee
  columns into their events, Asheville, Miami-Dade, Philadelphia and Phoenix
  among them, and Virginia Beach `sla` names each premises by its
  `Owner_Name`. Las Vegas, Reno and DC `deeds` fetch owner-name columns they
  never map, with no `select` to keep them on the server; a row that fails to
  parse goes to the DLQ whole, and Phoenix `deeds` dead-letters every row.
- **`source_mode`.** A backfill does not mark its events as backfilled
  (ADR 0008, US-115).

## Text-dated polls

Six feeds keep their date as text in a format that is not year first: Reno
and Rochester `deeds`, Virginia Beach and Worcester `sla` and Worcester
`permits` write `MM/DD/YYYY` (Worcester without zero padding), and Honolulu
`311` writes `September 29, 2026 at 10:17 PM`. As text,
`SALEDATE > '09/21/2026'` reads September 22 to December 31 of every past
year, and Worcester's `9/9/2026` sorts above `9/30/2026`, so each poll read
old rows and could fill its cap before it reached new ones. Reno `deeds` was a
snapshot for this reason, and each poll re-read the same first 1,000 of its
194,122 sales. The sixth stacked change:

- **Names the dates.** An ArcGIS or Socrata filter on such a column lists
  each day from the watermark's to today, written padded and unpadded, with
  whole months and years as `LIKE` patterns:
  `SALEDATE IN ('09/28/2026', '9/28/2026', ...) OR SALEDATE LIKE '10/%/2026'`.
  A time of day matches any text, so Honolulu reads
  `date_created LIKE 'September 29, 2026 at %'` and the dedup drops the rows
  of that day it has seen. A CSV already compares in the declared format and
  San Jose's CKAN filter casts both sides, so neither changes, and a
  year-first format still compares as text.
- **Posts a long query.** ArcGIS Online answers 404 to a GET past about 2,000
  characters (a list of 85 dates measured 2,272; 70 measured 1,898 and
  passed), and a window that spans two part-months lists up to 120 dates. The
  ArcGIS client now sends a query that long as a form POST, as Esri's own
  clients do.
- **Reno `deeds` polls incrementally.**
- **Backfills use the same window** instead of reading these feeds whole and
  filtering client-side.

### Checked live

On 2026-09-30 each feed was polled twice through `poll_job` from a set
watermark, Kafka mocked, requests 2 seconds apart. Every row read was dated
inside the window, and each second poll read only the new watermark's day,
whose rows the dedup dropped:

| Feed | Watermark | First poll | Second poll |
|---|---|---|---|
| Reno `deeds` | `09/21/2026` | 211 rows dated 09/21 to 09/28, 211 published | 24 rows (09/28), none published |
| Rochester `deeds` | `08/03/2026` | 55 rows, 08/03 to 08/14, 55 published | 1 row, none published |
| Virginia Beach `sla` | `08/03/2026` | 296 rows, 08/03 to 08/31, 273 published | 9 rows, none published |
| Worcester `permits` | `8/2/2026` | 931 rows, 8/2 to 9/26, 931 published | 1 row, none published |
| Worcester `sla` | `8/20/2026` | 13 rows, 8/20 to 9/21, 13 published | 1 row, none published |
| Honolulu `311` | `September 26, 2026 at 3:15 PM` | 298 rows, September 26 to 29, 292 published | 85 rows (September 29), none published |

A 58-day window (116 dates) went as a POST to Worcester `permits` on ArcGIS
Online and to Reno's MapServer, which returned 834 and 2,013 rows over one
and three pages.

Rochester's newest sale is dated 2026-08-14 and Virginia Beach's newest
licence 2026-08-31: both layers are refreshed in batches, so their windows
run from that date until the next batch lands.
