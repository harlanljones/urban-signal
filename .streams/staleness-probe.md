# Stream log — staleness-probe — 2026-10-02

## Claim

- **Stream id:** `staleness-probe`
- **Leaf files created/edited:**
  - `scripts/feed_staleness_probe.py` (the weekly freshness probe)
  - `apps/api/tests/unit/test_feed_staleness_probe.py`
  - `docs/research/feed-freshness-2026-10-03.md` (the census this probe
    took of every registered feed)
  - this file and `.streams/dispatch-log.md`
- **Spine files touched:** none.
- **Generated surfaces:** none.

## Intent

Let the weekly `feed-staleness-monitor` run finish inside its job's
20-minute limit, and have it page for the feeds that are stale and no
others.

## Decisions

- 2026-10-02 — Probe hosts side by side and each host's feeds one at a
  time, rather than every feed in turn: the run went through 443 feeds one
  after another, with a 30-second timeout and three retries per request,
  and was cancelled at 20 minutes on every scheduled run since at least
  2026-08-31, before it printed or paged anything. One request at a time
  per host keeps the load on any one server where it was.
- 2026-10-02 — Read each feed through its poll's own filter, newest first,
  asking for the watermark column alone: a statewide table is dated by the
  rows its city reads, and a 100-row read replaces a 1,000-row page of
  every column. A text column the spec leaves untyped is also read by row
  id, since text dates need not sort by date (NYC's permits mix
  `2020-06-05` and `09/30/2026`).
- 2026-10-02 — Read a month-first text date by naming the dates, as its
  poll does (`text_date_window`): the last week, then windows doubling to
  ten years, until one holds rows. The first census read such columns by
  their newest 1,000 object ids, and Worcester's permits and licences came
  back as last issued in 2015 and 2016: the newest rows hold the lowest ids
  there. Named, the dates were 2026-09-26 and 2026-09-21.
- 2026-10-02 — Parse a file's dates in its declared format whatever the
  type, as the CSV client compares them: Boulder's sales
  (`9/15/2026 12:00:00 AM`) read no dates without it.
- 2026-10-02 — Give the run a 15-minute deadline after which no feed
  starts, and stop waiting two minutes later; feeds not reached are
  reported as not probed and never page. Each result is logged as it
  lands, so a cut-off run still leaves its census.
- 2026-10-02 — Floor every feed's alarm window at the run's fallback
  (7 days): a daily feed's newest permit on a Monday run is Friday's, and
  `2 × 1` days paged every weekday-only feed every week.
- 2026-10-02 — Date file feeds from their `Last-Modified` header without
  downloading the body, read zipped files with their poll's member,
  delimiter and column names (the gap the held-sources stream left), read
  the four workbook feeds with the Excel client, and date the four GBFS
  feeds from their `last_updated` stamp. The probe had no client for
  either platform, so all eight read as stale.
- 2026-10-02 — Keep the age as the older of the source's update time and
  its newest row, as the probe has always computed it, and leave any change
  to its own PR: an ArcGIS layer's `lastEditDate` can lag its newest row
  (Anaheim's permits), which makes such a feed read older than its rows.
- 2026-10-02 — Do not send the existence check (`IS NOT NULL`) to CKAN:
  it moves every read to `datastore_search_sql`, which WPRDC refuses with
  a 403; the row-id read covers rows without a date there.
- 2026-10-03 — Read CKAN by row id whatever the column's type: without the
  existence check, a descending read there puts rows without a date first,
  and the newest 100 of Boston's inspection results by date had no result
  date at all.
- 2026-10-03 — Make the row-id read behind a column the spec leaves untyped
  a full page (1,000 rows), not 100: ids drift from dates. Lincoln's
  permits keep a month-first text date the spec leaves untyped; their
  newest 100 by object id end on 2025-12-23 and their newest 1,000 reach
  2026-01-22. Their newest permit (2026-04-14) is the 1,800th by object id,
  so only a spec that names the column's text format, as Worcester's do,
  is read by its dates.
- 2026-10-03 — Retry a failed request once, as intended: a client's
  `max_retries` counts every attempt, so the `1` the probe first passed
  made one attempt and no retry, and a single timeout read a feed as
  unreadable (Charleston WV's deeds).

## Current step

Done.

## Next step

The stale and unreadable feeds the census found, each in its own change
(listed in the research note).
