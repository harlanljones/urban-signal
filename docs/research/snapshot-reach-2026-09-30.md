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

Milwaukee `sla` (1,275 rows, cap 2,000) joined the full reads later the same
day. It was incremental on `GIS_DATETIME`, which each refresh stamps on every
row at once, so every poll re-read the same first 1,000 rows
(`feed-health-2026-09-30.md`).

Richmond `deeds` (Excel, 6,650 rows, cap 12,000) joined with the city's
registration. The assessor's workbook holds every transfer it has recorded
(439,398 rows), so the feed filters to the 365 days before each poll and
reads that year whole. A new workbook appears about monthly, and the daily
poll between releases gets a 304 and reads nothing
(`feed-health-2026-09-30.md`).

Richmond `crime` (1,249 rows, cap 2,500) joined with its registration.
Chesterfield County's offenses layer holds every offense since 2024-10-01
(25,653 rows), so the feed filters to the metro box and the 120 days before
each poll and reads that whole. An offense is dated by when it happened and
can be reported up to 118 days later, which a watermark would miss
(`probe-richmond.md`).

Denver, Hartford and Nashville `deeds` (2,445, 353 and 4,373 rows; caps
4,000, the default 1,000 and 7,000) joined with their registrations. Each
source holds one row per parcel with its last sale, so each feed filters to
sales dated in the 90 days before each poll and reads those whole
(`deeds-probe-2026-09-30.md`).

Chandler, Glendale, Phoenix, Scottsdale and Tempe `deeds` (1,573, 1,263,
9,224, 2,507 and 783 rows; caps 3,000, 2,500, 15,000, 5,000 and 2,000) joined
later the same day. The Maricopa County Assessor's parcel layer also holds one
row per parcel with its latest deed, so each feed filters to its own city and
the 90 days before each poll and reads those whole. Phoenix's leaves the known
gaps below.

Bend `deeds` (1,048 rows, cap 2,500) joined after them. Deschutes County's
sales table covers the county, so the feed reads the sales dated in the 90
days before each poll on the four township-ranges under Bend's metro box,
places each on its taxlot, and skips the 29 that land outside the box
(`metro_clip`, `deeds-probe-2026-09-30.md`).

Medford `deeds` (304 rows, default cap 1,000) reads Jackson County's sales
layer the same way the Maricopa feeds read theirs: the sales dated in the 90
days before each poll in the city (`SiteCity = 'MEDFORD'`), whole, each on
its own taxlot polygon.

Tacoma `deeds` (2,432 rows, cap 5,000) reads Pierce County's weekly sales
file once a day: one download a poll, filtered in memory to the sales dated
in the 90 days before it. The file covers the county, so each sale takes its
parcel's centroid only in the City of Tacoma's tax code areas, and the clip
skips the rest: 452 publish (`deeds-probe-2026-09-30.md`).

Pierce County `deeds` (2,432 rows, cap 5,000) reads the same file the same
way. Its metro is the whole county, so each sale takes its parcel's centroid
anywhere the county's parcel layer has one, and the clip skips only the 115
the layer cannot place: 2,317 publish.

Yakima `deeds` (453 rows, default cap 1,000) joined on 2026-10-02. The County
Assessor's parcels on the City GIS server hold a row per parcel and owner with
the parcel's latest sale, dated in text, so the server casts the dates and the
feed reads the 90 days before each poll county-wide, whole, each sale at its
parcel's centroid. The clip skips the 244 outside the metro box, and 208
publish (`two-family-depth-2026-09-30.md`).

Cape Coral `deeds` (6,765 rows, cap 17,000) joined the same day. Lee County's
parcel layer holds one row per parcel with its latest sale, so the feed reads
the sales dated in the 90 days before each poll county-wide, whole, newest
first, each at the parcel's own coordinates; the clip skips the 2,356 outside
the metro box, and 4,409 publish. The cap holds the 11,253 sales of March to
May 2026, the busiest window of the year so far.

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
| Frederick `deeds` (added 2026-09-30, mid-Atlantic deeds) | transfer date `DESC, :id` | 0 / 270 | 1,000 (default) |
| Providence `deeds` (same) | `SaleDate DESC, OBJECTID DESC` | 37 / 791 | 1,500 |
| Allentown `deeds` (same) | `SYEAR DESC, SMON DESC, OBJECTID DESC` | 2 / 304 | 1,000 (default) |
| Charleston WV `deeds` (same) | `Last_Sales_Date DESC, OBJECTID DESC` | 0 / 3 | 1,000 (default) |

Every window orders by the column the feed already tracks as its watermark
(Baton Rouge has none and uses its open date; Allentown has none and sorts by
sale year and month). The Maryland transfer date is `YYYY.MM.DD` text and
Asheville's `DeedDate` is `YYYYMMDD` text; both sort correctly as text.
Henderson's issue date is `MM/DD/YYYY` text, which does not, but the CSV
client sorts the declared watermark column as dates. Two windows need a
filter:

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
question about the source, not the window. Charleston WV's three are the
assessor's four-month posting lag (see the feed-health note).

## Known gaps

| Feed | Rows | Why it is not fixed here |
|---|---|---|
| Kansas City `sla` | 28,245 | no date to window on; `valid_license_for` is a text licence year shared by thousands of rows |
| Boston `deeds` | 184,552 | the configured id is the CKAN package, not a resource (404); the FY2026 resource has no coordinates and none of the mapped column names |

Henderson `sla` was on this list; the feed-repair change
([feed-health-2026-09-30.md](feed-health-2026-09-30.md)) fixed its field map
and made it a window. Reno `deeds` was too, since its only sale date is
`MM/DD/YYYY` text, which does not sort; a later change there ("Text-dated
polls") names the dates since its watermark, and it now polls incrementally.
Phoenix `deeds` was too, as a 61 MB zip of a 270 MB pipe-delimited file
(903,301 rows) whose spec named no zip member or delimiter; it now reads the
Assessor's parcel layer (above). Ocala `permits` and Orlando `permits` were
too: the statewide cadastral layer they read, under county codes 42 and 48,
held Jackson and Levy counties' parcels. Since 2026-10-02 Ocala registers no
permits and Orlando reads the City's own permit applications incrementally
([two-family-depth-2026-09-30.md](two-family-depth-2026-09-30.md)). Boston
needs more than a spec edit, as its row above says.

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
  date) would fix it. Fixed in a later change ("Incremental filters" in
  [feed-health-2026-09-30.md](feed-health-2026-09-30.md)) by a
  `composite_id` flag, which the Denver, Hartford and Nashville feeds use
  too.
- **Feed health.** A one-poll check of all 367 jobs on 2026-09-30 found 36 that
  fail outright (moved or retired endpoints, San Francisco's Socrata redirect,
  four Boston CKAN resources, two platforms with no client) and 16 that fetch
  rows but publish none. The repairs are in
  [feed-health-2026-09-30.md](feed-health-2026-09-30.md).
