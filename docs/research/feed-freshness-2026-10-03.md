# Feed freshness — 2026-10-03

The weekly `feed-staleness-monitor` run was cancelled at its 20-minute job
limit on each of its five scheduled runs from 2026-08-31 to 2026-09-28,
before it printed or paged anything; the last run that finished was on
2026-08-24. It read every registered feed in turn, a 1,000-row page of
every column with a 30-second timeout and three retries, without the feed's
own filter, and it had no client for the workbook and GBFS feeds.

This note is the census the reworked probe (`scripts/feed_staleness_probe.py`)
took of all 443 registered feeds on 2026-10-03, and what a weekly run costs.

## How the probe dates a feed

- **Through the poll's own filter.** A statewide table is dated by the rows
  its city reads. The probe asks for the watermark column alone.
- **Newest first.** A date or number column, or text written year first,
  is read newest first, 100 rows. A column the spec leaves untyped, and its
  layer does not type as a date or number, is also read by row id, a full
  page of 1,000 rows: NYC's permits write `2020-06-05` on old rows and
  `09/30/2026` on new ones, and a read by value stops in 2020. CKAN is
  always read by row id too: it takes no existence check, and a descending
  read there puts rows without a date first (read by date, Boston's first
  100 inspection results have none).
- **Month-first text by its dates.** `9/4/2026` sorts after `10/1/2026` as
  text, and a table's ids need not follow its dates: Worcester's newest
  permits hold its lowest object ids. Such a column is read as its poll
  reads it, by naming the dates (`text_date_window`): the last week, then
  windows doubling to ten years, until one holds rows.
- **Files whole.** A file feed is read with its poll's zip member,
  delimiter, column names and date format, and its source is dated by its
  `Last-Modified` header, read without the body. GBFS feeds are dated by
  their `last_updated` stamp.
- **Age and alarm.** A feed's age is the older of its newest row and its
  source's update time. It is stale past twice its declared cadence, and
  never sooner than the run's fallback of 7 days: a daily feed's newest
  permit on a Monday run is Friday's.

## The run

Live, from 00:16 to 00:28 UTC on 2026-10-03, a dry run (no page), with
24 hosts side by side, requests to any one host at least 2.2 seconds apart
(the weekly job does not pace), and one retry for a request that fails.
Six feeds on four hosts this census does not request were left out:
Scottsdale's three, Buffalo's and Modesto's licences, and El Paso's `311`.

| Platform | Feeds | Fresh | Stale | Stale, alarm-exempt | Not probed |
|---|---|---|---|---|---|
| arcgis | 301 | 260 | 34 | 2 | 5 |
| socrata | 89 | 77 | 7 | 4 | 1 |
| csv | 24 | 24 | 0 | 0 | 0 |
| ckan | 17 | 15 | 2 | 0 | 0 |
| carto | 4 | 3 | 0 | 1 | 0 |
| excel | 4 | 4 | 0 | 0 | 0 |
| gbfs | 4 | 4 | 0 | 0 | 0 |
| **All** | **443** | **387** | **43** | **7** | **6** |

## Stale feeds

Ages are days to the run. "Alarm after" is the feed's window: twice its
declared cadence, at least 7 days.

### Over 180 days old

| Feed | Newest row | Source updated | Age | Alarm after |
|---|---|---|---|---|
| tulsa `crime` | 2019-01-24 | 2019-01-25 | 2809 days | 14 days |
| eugene `311` | 2021-03-12 | 2024-01-06 | 2031 days | 7 days |
| columbus_ga `permits` | 2022-04-15 | – | 1632 days | 14 days |
| montgomery_al `permits` | 2024-03-01 | 2024-09-03 | 946 days | 14 days |
| bridgeport `deeds` | 2025-09-30 | 2026-08-12 | 368 days | 60 days |
| new_haven `deeds` | 2025-09-30 | 2026-08-12 | 368 days | 60 days |
| eugene `deeds` | 2026-01-05 | 2026-02-23 | 271 days | 7 days |
| lincoln `permits` | 2026-01-22 | – | 254 days | 7 days |
| spokane `sla` | 2026-06-30 | 2026-04-04 | 182 days | 14 days |

### 30 to 180 days old

| Feed | Newest row | Source updated | Age | Alarm after |
|---|---|---|---|---|
| boston `inspections` | 2026-05-11 | – | 144 days | 14 days |
| tempe `311` | 2026-06-12 | 2026-06-16 | 113 days | 60 days |
| nyc `crime` | 2026-06-30 | 2026-07-27 | 95 days | 60 days |
| peoria `deeds` | 2026-07-01 | – | 94 days | 60 days |
| spartanburg `sla` | 2026-07-08 | – | 87 days | 60 days |
| prince_georges `311` | 2026-07-17 | 2026-07-20 | 78 days | 60 days |
| glendale_az `311` | 2026-08-05 | – | 59 days | 7 days |
| anaheim `permits` | 2026-09-13 | 2026-08-06 | 57 days | 42 days |
| portland `permits` | 2026-08-10 | – | 54 days | 14 days |
| billings `permits` | 2026-08-11 | – | 53 days | 7 days |
| tallahassee `permits` | 2026-08-18 | – | 46 days | 14 days |
| vancouver_wa `permits` | 2026-08-27 | 2026-10-02 | 36 days | 7 days |
| durham `deeds` | 2026-08-27 | – | 36 days | 14 days |
| boise `crime` | 2026-09-01 | 2026-10-02 | 32 days | 14 days |
| tampa `sla` | 2026-09-02 | – | 30 days | 14 days |

### Under 30 days old

| Feed | Newest row | Source updated | Age | Alarm after |
|---|---|---|---|---|
| savannah `permits` | 2026-09-04 | – | 29 days | 14 days |
| topeka `permits` | 2026-09-04 | – | 29 days | 7 days |
| glendale_az `sla` | 2026-09-06 | – | 27 days | 7 days |
| virginia_beach `permits` | 2026-09-13 | 2026-09-14 | 20 days | 7 days |
| los_angeles `sla` | 2026-10-01 | 2026-09-15 | 17 days | 14 days |
| las_vegas `deeds` | 2026-09-16 | 2026-09-27 | 17 days | 14 days |
| tampa `street_cut` | 2026-09-18 | – | 15 days | 14 days |
| orlando `sla` | 2026-09-23 | 2026-10-02 | 10 days | 7 days |
| montgomery_al `311` | 2026-09-24 | – | 8 days | 7 days |
| aurora `sla` | 2026-09-25 | – | 8 days | 7 days |

### Unreadable

| Feed | Platform | What the probe got |
|---|---|---|
| bend `crime` | arcgis | ArcGIS error 499: token required |
| boston `deeds` | ckan | no watermark column, and the source gives no update time |
| denver `311` | arcgis | ArcGIS error 400: layer 66 not found |
| evansville `permits` | arcgis | ArcGIS error 500 (read again minutes later: newest 2026-08-31, stale either way) |
| inland_empire `permits` | arcgis | 403 Forbidden from `gis.countyofriverside.us` |
| ocala `deeds` | arcgis | no watermark column, and the source gives no update time |
| phoenix `sla` | arcgis | 500 Internal Server Error from `mapportal.phoenix.gov` |
| tulsa `311` | arcgis | no rows with a valid watermark |
| washington_dc `childcare` | arcgis | no watermark column, and the source gives no update time |

### Alarm-exempt

These page no one; their specs mark the source as accepted dead or
unmaintained.

| Feed | Newest row | Source updated | Age |
|---|---|---|---|
| chicago `energy_benchmark` | 2023-01-01 | 2025-02-05 | 1371 days |
| eugene `sla` | – | 2023-12-15 | 1022 days |
| kansas_city `sla` | – | 2026-01-15 | 260 days |
| nyc `energy_benchmark` | 2024-01-01 | 2025-11-25 | 1006 days |
| philadelphia `deeds` | 2026-08-11 | – | 53 days |
| san_francisco `deeds` | 2026-06-26 | 2026-06-26 | 98 days |
| stockton `sla` | 2026-09-11 | – | 22 days |

## What a weekly run costs

- **Requests.** 1,094 requests to 129 hosts, summing to 1,060 seconds.
  The busiest host, `services1.arcgis.com` (89 SNAP retailer feeds and 29
  others), took 174 requests summing to 111 seconds. With 16 hosts side by
  side and one request at a time per host, the requests take about two
  minutes.
- **Files.** The 28 file feeds are the slow part. Read one at a time
  (measured on 2026-10-02), they take 347 seconds, 254 of them CPU:
  Lakeland's 518 MB Polk County sales file 124 seconds (80 of CPU),
  Richmond's transfers workbook 65, Boulder's sales 21, Fort Collins' 19,
  Pierce County's sale file 18 for each of the two feeds that read it, and
  Alachua County's 15. Their parsing shares one interpreter, so a weekly
  run should take six to eight minutes, inside its 15-minute deadline.
- **Memory.** 1.4 GB at peak with the files read one at a time; 2.0 GB in
  the census, with them read side by side.

## Follow-ups

Each its own change.

- **Stopped sources.** Retire or replace Tulsa's crime reports (a display
  layer last loaded in January 2019), Eugene's `311` (the City's 2020-21
  camping work orders) and deeds, Columbus GA's and Montgomery AL's
  permits, Lincoln's permits, and Spokane's licences (newest renewal
  2026-06-30, source last updated 2026-04-04). Lincoln's residential
  new-construction layer holds 40 permits from December 2025, one each from
  January and April 2026, and none since; the probe dates it 2026-01-22
  because its spec leaves the month-first text column untyped and its ids
  do not follow its dates (read whole, the newest is 2026-04-14).
- **Cadences.** Connecticut's sales file (Bridgeport's and New Haven's
  deeds, `5mzw-sjtu`) was last updated on 2026-08-12 and its newest sale is
  from 2025-09-30: it is published about once a year, each update adding a
  year of sales that ends on 30 September. NYPD's complaint data (NYC
  `crime`, `5uac-w243`) ends on 2026-06-30 and was updated on 2026-07-27,
  quarterly. Both specs declare 30 days.
- **Behind their cadence.** Each feed in the 30-to-180-day table needs its
  source checked. Boston's inspections, for one, have nothing newer than
  2026-05-11 in a table of 904,046 rows.
- **NYC permits.** The probe dates the feed by row id (2026-09-30), but the
  poll compared the mixed-format `issuance_date` text with `>=`
  (`current-city-feed-gaps.md`), so after its first poll it read nothing.
  `dobrundate` cannot drive it: 3,897,736 rows carry 2026-10-01, the day the
  set was last reloaded. Declared month-first, the column is read by its
  dates, as Worcester's are.
- **Unreadable.** Denver's `311` layer 66 is gone, Phoenix's short-term
  rentals answered 500, Tulsa's `311` layer returns no rows, and Riverside
  County answered 403 from this network (the weekly job's own network may
  differ). Bend's calls for service ask for a token; that feed stays
  failing by decision.
- **No date at all.** Boston's and Ocala's deeds and DC's child care have
  neither a date column nor a source update time, so they always read
  stale: give each a date or mark it exempt.
- **Edit dates that lag.** An ArcGIS layer's `lastEditDate` can trail its
  rows. Anaheim's newest permit is from 2026-09-13, 20 days before the run,
  but its layer's edit date is 2026-08-06, so the feed reads 57 days old
  against its 42-day window and pages.
- **Frederick's deeds.** Maryland's portal answers the probe's read (the
  feed's filter with the existence check) with a block page (403) and
  answers the poll's own query; the feed reads fresh from its source's
  update time (2026-09-04).
