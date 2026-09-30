# Feed health — 2026-09-30

On 2026-09-30 every registered poll job (367, GBFS and national feeds aside)
was polled once through the real scheduler and clients, 50 rows each, with
Kafka mocked. 36 jobs failed outright, 8 fetched nothing, and 16 fetched rows
but published none. This change repairs the ones a spec, endpoint or small
client fix can reach, retracts one feed that has no public source, moves two
licence feeds whose source holds no rows for their city to the SNAP retailer
fallback, and lists the rest with the reason.

| | Jobs | Repaired here | Left, with reason below |
|---|---|---|---|
| Failed outright | 36 | 14, and Madison `permits` retracted | 21, 14 of them mid-Atlantic `deeds` |
| Fetched rows, published none | 16 | 8, and Milwaukee `deeds` was fine on a full read | 7 |
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
| Lynchburg `deeds` | the sales table has no coordinates and declares a `parcel_join`, but only the standalone producer applies it, not `poll_job`; its id is the parcel, so a parcel's earlier sales collapse (250 of 300 rows) | the parcel join in `poll_job`, and the document number as the id |
| Bend `crime` | the layer now answers 499 Token Required; the public replacement lists each offense's exact address, where the old feed gave block ranges | a decision on publishing exact offense addresses; left failing |
| Lincoln `permits`, Sioux Falls `permits` | each city's permit service fails every query, even a bare count: Lincoln with 400 "Unable to complete operation", Sioux Falls with 500 and a stopped Java web application behind the service | a restart on the city's side; no other public permit source was found for either |
| El Paso `311` | Cloudflare answers 403 to this network | a check from the production network |
| Chicago, NYC, Seattle `energy_benchmark`; NYC, Seattle `bike_ped` | the context-observation producer has no per-row hook: an energy row fans out into several metrics and counter rows fold into one observation per sensor-day, so `poll_job` dead-letters every row | a batch hook in `poll_job`, or running these through the producer's own stream |

### Mid-Atlantic deeds: the next stacked change

The 14 cities of the 2026-09-06 mid-Atlantic wave were registered with only a
`deeds` feed, and all 14 fail. None of the registered URLs ever pointed at a
live sales source: three hosts have no DNS (Allentown, Dover, Wilmington DE);
seven paths sit on city websites with no ArcGIS Server behind them (Albany,
Burlington, Harrisburg, Huntington, Providence, Richmond, Roanoke); two name
ArcGIS Online services or organizations that do not exist (Frederick,
Manchester); and two point at the wrong place (Charleston WV at a Charleston,
SC service; Portland ME at a layer id the service does not have). The
interlock gate checks a spec's shape, not whether its endpoint answers.

| City | Replacement | Rows | Newest sale |
|---|---|---|---|
| Frederick | Maryland SDAT assessments (Socrata `gx8c-a963`), city filter | 56,256 | 2026-08-06 |
| Providence | the city's parcel layer with its assessor's last sale | 35,421 with a sale date | 2026-09-20 |
| Burlington | Vermont's property-transfer returns (VCGI), town 114 | 6,788 | posted 2026-09-18 |
| Allentown | the city's assessed parcels, sale year and month | 34,234 with a sale month | 2026-09 |
| Charleston WV | Kanawha County Assessor parcels, county-wide | 88,853 with a sale date | complete to 2026-05 |
| Roanoke | the city's transfer-history table, no geometry | 214,121 dated | 2026-09-28 |
| Richmond | the assessor's monthly transfers workbook (.xlsx, 72 MB) | 439,398 | 2026-09-22 |

Roanoke needs the parcel join in `poll_job` (as Lynchburg does), and Richmond
needs a reader for `.xlsx` files and their monthly changing URL. Albany, Dover,
Harrisburg, Huntington, Manchester, Portland ME and Wilmington DE publish no
sale dates or prices anywhere public: their county and state parcel layers
carry deed book and page only, and the sales searches that exist are
interactive sites.


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

These cut across many feeds and need scheduler changes, so they are the next
change rather than part of this one.

- **The watermark advances from the event's date, not the filter's column.**
  `poll_job` stores the newest `issuance_date`, `created_date`,
  `effective_date` or `recorded_date` of the published events and falls back to
  the watermark column only when an event has none. Where the two differ, the
  next filter compares the column against the wrong date. The Connecticut
  `sla` feeds filter on the refresh date but store the permit's effective date,
  which runs into the future: a live poll logged `ignoring future watermark
  2026-11-06`.
- **Record ids take the first id key that has a value, not all of them.**
  Boston inspections list `licenseno` then `_id`; a licence number repeats on
  every row of an inspection and on every later inspection, so a first poll of
  1,000 rows published 17. Lynchburg deeds, the parcel-keyed deeds in the
  snapshot-reach note, and St. Louis permits (special-cased in the scheduler)
  have the same shape.
- **170 of 274 incremental feeds are not ordered by their watermark column.**
  A capped poll then reads the first rows by object id newer than the
  watermark, and the watermark jumps to the newest date among them, so rows
  dated in between that sit past the cap are never read. It bites on a cold
  start or after an outage longer than one cap's worth of rows.
- **Date-only watermarks lose the boundary day.** A feed whose dates carry no
  time stores `2026-09-28T00:00:00`, and `>` then skips rows published later
  with that same date. From `2026-09-01T00:00:00`, Baton Rouge fetched 632 of
  the 671 permits issued since 1 September.
- **ArcGIS polls read every column.** The ArcGIS client ignores `select`, so
  owner, applicant and contractor names ride along with each row and are kept
  in the DLQ payload of any row that fails to parse.
- **`maps.cityofmadison.com` refuses ISO date strings** like the three hosts
  above. No feed polls it today; a future Madison spec should add the host to
  `ANSI_DATE_LITERAL_HOSTS`.
