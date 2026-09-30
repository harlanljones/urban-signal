# Stream log — backfill-args — 2026-09-30

## Claim

- **Stream id:** `backfill-args`
- **Leaf files created/edited:**
  - `scripts/backfill_loader.py`: the poll's client arguments, parcel joins,
    text-typed windows in the column's format, client-side windows for
    formats the server cannot order, snapshots in the spec's order
  - `apps/api/src/producers/ckan_client.py`: column names with spaces in
    filters and orders
  - `apps/api/src/producers/csv_client.py`: ISO filter literals on a column
    with a declared format
  - `apps/api/src/producers/watermarks.py`: `casts_text_watermark`, shared by
    the filter and the loader
  - corpus files `st_louis.yaml` (permits format), `san_antonio.yaml`
    (permits text watermark), `cincinnati.yaml` (deeds names no watermark
    column), and the St. Louis and San Antonio leaf docstrings and specs
  - tests: `test_backfill_loader.py`, `test_ckan_client.py`,
    `test_scheduler_boundaries.py`, `test_producers_st_louis.py`,
    `test_producers_san_antonio.py`, `test_producers_cincinnati.py`
  - `docs/research/feed-health-2026-09-30.md` ("Backfills"), product facts
    (`facts:export`), this file, `.streams/dispatch-log.md`
- **Spine files touched:** none.
- **Generated surfaces:** `apps/product/public/facts.json` and the affected
  cities' `cities/*.json`.

## Intent

Make a backfill read each feed the way its poll does. The loader built its
own query and handed the client only an order, so it read zipped CSVs,
workbooks, parcel-joined sales and text-dated columns differently from
`poll_job`, and fetched the name columns a `select` keeps on the server.

## Decisions

- 2026-09-30 — The loader takes `_PAGINATE_KWARGS` from the scheduler rather
  than a copy, and a test compares every job's backfill arguments with its
  poll's. Only the order differs.
- 2026-09-30 — A text-typed window starts in the column's format. A format
  that is not year first cannot be windowed or ordered on the server, so the
  backfill reads those six feeds whole and filters client-side; no cast
  expressions for ArcGIS or Socrata.
- 2026-09-30 — St. Louis permits keeps an untyped watermark with the export's
  new format; the CSV client parses an ISO literal when the format does not
  match it. Declaring the column text was tried first and was the wrong fix:
  the declared format itself was stale.
- 2026-09-30 — Cincinnati deeds drops its `SaleDate` watermark column, which
  the auditor's file does not have; the feed is a snapshot.
- 2026-09-30 — The polls of the six client-windowed feeds, which still compare
  text, are left for a later change.

## Current step

Done.

## Next step

Object-id cursors (or a client-side filter) for the six text-dated polls; the
`select` sweep for feeds that fetch owner and party names; Richmond's county
police layer.
