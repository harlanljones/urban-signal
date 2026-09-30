# Stream log — text-windows — 2026-09-30

## Claim

- **Stream id:** `text-windows`
- **Leaf files created/edited:**
  - `apps/api/src/producers/watermarks.py`: `text_sorts_as_dates`,
    `text_date_window`, and `watermark_comparison` sending the window to an
    ArcGIS or Socrata server for a text format that is not year first
  - `apps/api/src/producers/arcgis_client.py`: a query URL past 2,000
    characters goes as a form POST
  - `scripts/backfill_loader.py`: the backfill's text window is the poll's;
    the client-side window is gone
  - corpus file `reno.yaml` (deeds `ingestion_mode: incremental`)
  - tests: `test_watermarks.py`, `test_arcgis_client.py`,
    `test_backfill_loader.py`, `test_producers_reno.py`
  - `docs/research/feed-health-2026-09-30.md` ("Text-dated polls"),
    `docs/research/snapshot-reach-2026-09-30.md` (Reno leaves the known gaps),
    this file, `.streams/dispatch-log.md`
- **Spine files touched:** none. `scheduler.py` already builds its filter
  through `watermark_comparison`, and `AccelaClient` inherits the POST.
- **Generated surfaces:** none.

## Intent

Make the polls of Reno and Rochester `deeds`, Virginia Beach and Worcester
`sla`, Worcester `permits` and Honolulu `311` read the rows since their
watermark. Their dates are text in a format that is not year first, so the
filter compared text and read old rows.

## Decisions

- 2026-09-30 — Name the dates rather than cast the column, and rather than an
  object-id cursor: none of the six layers has a date column, casts are not
  portable across ArcGIS servers and Socrata, and object ids do not follow
  sale or issue dates on parcel and licence layers.
- 2026-09-30 — Each day is written padded and unpadded: the declared format
  does not say which the feed writes, and Reno and Worcester differ.
- 2026-09-30 — The window ends today (UTC), so a row dated in the future is
  read on its day; whole months and years inside the window are `LIKE`
  patterns, which keeps the list to at most two part-months of days.
- 2026-09-30 — Decide by endpoint shape (an ArcGIS layer or a Socrata `.json`
  resource) that the server evaluates the filter, as the module already does
  for ANSI hosts and the CKAN cast; CSV and workbook clients compare the
  declared format themselves and keep the old comparison.
- 2026-09-30 — Long queries go as a POST in the ArcGIS client rather than
  capping the window, as Esri's clients do; short ones stay GETs.

## Current step

Done.

## Next step

Richmond crime from Chesterfield County (decision card on point precision);
the owner and party names in `deeds` (decision card).
