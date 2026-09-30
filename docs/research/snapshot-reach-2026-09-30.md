# Snapshot feeds reach their rows — 2026-09-30

A snapshot poll re-reads its source and stops at the job's `batch_limit`
(1,000 rows unless the spec declares more), in the source's table order: the
ArcGIS object id, the Socrata row id, or the file's own order. On 2026-09-30,
33 of the 38 non-SNAP snapshot feeds (GBFS aside) held more rows than that
cap, so each poll handed them the same first 1,000 rows and never the rest.
The SNAP retailer feeds had the same defect and were fixed separately
(`snap-metro-scope-2026-09-30.md`).

Each feed now reaches its rows in one of two ways, and the ones that cannot
yet are listed with the reason.

| | Feeds | Before | After |
|---|---|---|---|
| Full read | 15 | 2 saw every row; the other 13 saw their first 1,000 (tables of 1,078 to 10,585 rows) | a cap of at least 1.5 times the table on the 14 that need one, so every poll reads every row |
| Newest-first window | 16 | 5 already read newest first; 11 read their first 1,000 rows in table order (parcels and licences from as far back as 1900) | order by the feed's own date, newest first, with a window holding at least 1.5 times the rows dated in the last 90 days |
| Known gap | 7 | | unchanged; reasons below |

Across the 31 feeds read in full or newest first, a cold start reads 102,455
rows instead of 30,204, and requests go from about 2,700 a day to about 3,900
(see Costs).

## How the two shapes work

**Full read.** A table that fits under its cap is read whole on every poll,
so every new row is seen on the next poll. `test_snapshot_reach.py` pins each
table's measured size and checks the cap clears it by half again; a table
that outgrows its cap now logs `snapshot poll stopped at its N-row cap` on
every poll.

**Newest-first window.** A table too large to read whole is read newest
first, so a new row enters at the top and is seen on the next poll. The
window has to span the source's update rhythm: the Maryland assessment
tables publish monthly and their newest transfer is about five weeks old, and
Baltimore's newest 1,000 transfers cover only 5 to 26 August. Each window
therefore holds at least 1.5 times the rows dated in the 90 days before
measurement, so it reaches back past those 90 days. Windows
that read more than one page break date ties with the object id (ArcGIS) or
`:id` (Socrata); paging a sort on a shared date is not stable otherwise.

## Full reads

| Feed | Rows in table | Rows read before | Cap after |
|---|---|---|---|
| Bend `sla` | 5,981 | 1,000 (newest by expiration) | 9,000 |
| Cincinnati `deeds` (CSV) | 1,078 | 1,000 | 2,000 |
| Eugene `sla` | 752 | 752 | 2,000 |
| Fort Collins `permits` | 2,183 | 1,000 | 4,000 |
| Inland Empire `sla` (CSV) | 10,585 | 1,000 | 16,000 |
| Milwaukee `deeds` (CSV) | 5,685 | 1,000 (January to March 2025 only) | 9,000 |
| Modesto `sla` | 4,574 | 1,000 | 7,000 |
| Montgomery County `sla` | 1,084 | 1,000 | 2,000 |
| NYC `childcare` | 2,752 | 1,000 | 5,000 |
| Oakland `sla` (CSV) | 5,103 | 1,000 | 8,000 |
| Portland `sla` | 6,079 | 1,000 | 10,000 |
| Santa Rosa `sla` (CSV) | 4,979 | 1,000 | 8,000 |
| St. Louis `sla` (CSV) | 1,799 | 1,000 | 3,000 |
| Stockton `sla` | 1,369 | 1,000 (newest first) | 3,000 |
| Washington, DC `childcare` | 452 | 452 | 1,000 (default) |

Eugene's 752 rows fit today, but not with half again to spare. Portland's
dates are `MM/DD/YYYY` text, which does not sort, so it is read whole.
Bend and Stockton already read newest first and are small enough to read
whole instead. Milwaukee's source is the city's 2025 arm's-length sales file
(`expected_cadence_days: 365`); reading it whole publishes all of 2025, and a
2026 file needs a new endpoint.

## Newest-first windows

| Feed | Order | Rows dated in last 30 / 90 days | Window after |
|---|---|---|---|
| Asheville `deeds` | `DeedDate DESC, objectid DESC` | 848 / 2,653 | 4,000 |
| Baltimore `deeds` | transfer date `DESC, :id` | 0 / 2,459 | 4,000 |
| Baton Rouge `sla` | `topendate DESC, :id` | 131 / 344 | 1,000 (default) |
| Chattanooga `deeds` | `SALE1DATE DESC, OBJECTID DESC` | 249 / 1,661 | 3,000 |
| Cleveland `deeds` | `last_transfer_date DESC, OBJECTID DESC` | 1,068 / 3,509 | 6,000 |
| Durham `deeds` | `PKG_SALE_DATE DESC, OBJECTID_1 DESC` | 0 / 574 | 1,000 (default) |
| Miami-Dade `sla` | `BUSSDATE DESC, OBJECTID DESC` | 474 / 2,128 | 4,000 |
| Montgomery County `deeds` | transfer date `DESC, :id` | 0 / 2,042 | 4,000 |
| Oxnard–Ventura `sla` | `DATEISSUE DESC, OBJECTID DESC` (was `DATEISSUE DESC`) | 339 / 3,839 | 6,000 (was 1,000) |
| Prince George's County `deeds` | transfer date `DESC, :id` | 0 / 1,231 | 2,000 |
| Raleigh `deeds` | `SALE_DATE DESC, OBJECTID DESC` | 546 / 3,240 | 5,000 |
| San Diego `sla` (CSV) | `date_account_creation DESC` | 841 / 2,275 | 4,000 |
| Anaheim `sla` | `applicationdate DESC` (unchanged) | 38 / 322 | 1,000 (default) |
| Aurora `sla` | `Issue_Date DESC` (unchanged) | 79 / 238 | 1,000 (default) |
| Glendale, AZ `sla` | `IssuedOn DESC` (unchanged) | 33 / 518 | 1,000 (default) |
| Henderson `sla` (CSV) | `original_issue_date DESC` (added with the feed repair) | 140 / 579 | 1,000 (default) |
| Tucson `sla` | `DT_START DESC` (unchanged) | 2 / 2 | 1,000 (default) |

Every window orders by the column the feed already tracks as its watermark
(Baton Rouge has none and uses its open date). The Maryland transfer date is
`YYYY.MM.DD` text and Asheville's `DeedDate` is `YYYYMMDD` text; both sort
correctly as text. Henderson's issue date is `MM/DD/YYYY` text, which does not,
but the CSV client sorts the declared watermark column as dates. Two windows
need a filter:

- **Raleigh** sorts null sale dates first, so its window filled with parcels
  that never sold. It now filters `SALE_DATE IS NOT NULL` (358,251 of 438,805
  parcels).
- **Cleveland** could not sort 162,874 parcels by transfer date with full
  attributes inside the client's 30-second timeout (41.7 seconds for 500 rows;
  the tiebreak variant failed outright). It now filters
  `last_transfer_date >= CURRENT_DATE - INTERVAL '180' DAY` (7,114 parcels),
  and each 1,000-row page returns in about 3 seconds. A backfill of Cleveland
  deeds now reads 180 days, since the backfill keeps each feed's filter.

Tucson's layer holds only two rows dated in the last 90 days, which is a
question about the source, not the window.

## Known gaps

| Feed | Rows | Why it is not fixed here |
|---|---|---|
| Kansas City `sla` | 28,245 | no date to window on; `valid_license_for` is a text licence year shared by thousands of rows |
| Reno `deeds` | 194,124 | the only sale date is `MM/DD/YYYY` text, which does not sort |
| Phoenix `deeds` (CSV) | 903,301 | the endpoint is a 61 MB zip of a 270 MB pipe-delimited file; the spec names no zip member or delimiter, and the CSV client holds the whole file and every kept row in memory |
| Boston `deeds` | 184,552 | the configured id is the CKAN package, not a resource (404); the FY2026 resource has no coordinates and none of the mapped column names |
| Ocala `permits`, Orlando `permits` | 283,399 / 488,959 | the Florida statewide cadastral polygon layer now answers 499 Token Required, and the county codes select Jackson (42) and Levy (48) counties instead of Marion (52) and Orange (58) |

Henderson `sla` was on this list; the feed-repair change
([feed-health-2026-09-30.md](feed-health-2026-09-30.md)) fixed its field map
and made it a window. Phoenix, Boston, Ocala and Orlando need more than a spec
edit and are described there.

## Scheduler and backfill changes

- **Seen-set per snapshot job.** The scheduler kept one 100,000-id seen-set for
  every feed. A snapshot re-reads its table every poll and emits only ids it
  has not seen, so once other feeds' new ids pushed a snapshot's ids out, its
  next poll re-published unchanged rows as new. Each snapshot job now keeps its
  own seen-set, sized to twice its cap (and grown when a poll passes a larger
  explicit limit); incremental feeds keep the shared one.
- **A full cap is logged.** A table-order snapshot poll that fills its cap
  logs a warning naming the job and cap. A poll whose order starts with a
  `DESC` term is a window and fills its cap by design, so it does not warn.
- **Backfills keep each feed's filter.** `scripts/backfill_loader.py` built
  its query from the watermark alone and dropped every spec's `where`, so a
  backfill of a SNAP metro read the national layer under one city's id, and a
  county-sliced CSV read the whole state. Both windowed and snapshot backfills
  now start from the registry's `where`, as `poll_job` does.

## Costs

- **Requests.** Windows and full reads of more than 1,000 rows read several
  pages a poll. The nine that polled more often than every 30 minutes now poll
  every 30 minutes (Bend, Montgomery County `sla`, Portland, Stockton,
  Baltimore, Miami-Dade, Montgomery County `deeds`, Oxnard–Ventura and
  Prince George's County; none of their sources updates more than daily).
  Across the 31 feeds above, requests go from about 2,700 a day to about
  3,900; without the slower polls it would have been about 8,200.
- **Cold starts.** The seen-sets live in memory, so after a restart every
  snapshot job re-publishes its whole table or window once. The scheduler
  sleeps `rate_limit_delay` (0.2 seconds) per new row and runs jobs one at a
  time, so the replay across the 31 feeds above grows from 30,204 rows (about
  1.7 hours) to 102,455 (about 5.7 hours); Inland Empire alone takes 35 minutes
  on its first poll. The SNAP feeds add 34,686 rows. Only NYC's four legacy jobs
  are enabled in `docker-compose.yml` today, so this does not bite yet;
  persisting the snapshot seen-sets would remove the replay.

## Evidence

All live, 2026-09-30, at a spacing of 1.5 to 3 seconds per request.

- Table sizes: `returnCountOnly` (ArcGIS), `$select=count(*)` (Socrata), and a
  full download counted client-side (CSV), each under the feed's `where`.
- Rows dated in the last 30 and 90 days, and rows dated after today: the same
  counts with a date condition on each window's column. Future-dated rows are
  3 (Miami-Dade) and 30 (Baton Rouge); every other window has none.
- Each window paged through the real scheduler clients: two pages of 500 under
  the planned order and filter. Dates never rise, no nulls lead, and no id
  repeats across the page boundary except where one id key covers several rows
  (Miami-Dade accounts with several receipts, Durham parcels with several
  deeds). Two 1,000-row pages return within 6 seconds on every ArcGIS window.
- Before: a `poll_job` of each of the 33 larger feeds at its old cap, Kafka
  mocked: every one fetched exactly 1,000 rows; Milwaukee's were all dated
  January to March 2025, and Chattanooga's parcels reached back to 1900.

## Not covered here

- **Parcel-layer deeds keep one id per parcel.** Cleveland, Chattanooga, Durham,
  Raleigh, Asheville, Reno and the three Maryland feeds take their record id
  from the parcel or account, so a parcel that sells again while its id is still
  in the job's seen-set is not re-published. A composite id (parcel plus sale
  date) would fix it.
- **Feed health.** A one-poll check of all 367 jobs on 2026-09-30 found 36 that
  fail outright (moved or retired endpoints, San Francisco's Socrata redirect,
  four Boston CKAN resources, two platforms with no client) and 16 that fetch
  rows but publish none. The repairs are in
  [feed-health-2026-09-30.md](feed-health-2026-09-30.md).
