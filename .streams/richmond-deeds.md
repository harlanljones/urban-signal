# Stream log — richmond-deeds — 2026-09-30

## Claim

- **Stream id:** `richmond-deeds`
- **Leaf files created/edited:**
  - `richmond.yaml` (the deeds block) and its mirror `richmond.py`
  - clients outside the spine: `xlsx_reader.py` (new), `excel_client.py`
    (the monthly link, streamed `.xlsx`, conditional GET), `csv_client.py`
    (`CURRENT_DATE - INTERVAL 'N' DAY` resolved client-side),
    `arcgis_client.py` (`IN` lists split by encoded length)
  - tests: `test_xlsx_reader.py` (new), `test_excel_client.py` (new),
    `test_producers_richmond.py` (new), `test_scheduler_boundaries.py`,
    `test_dc_parcel_join.py`, `test_snapshot_reach.py`
  - `docs/research/feed-health-2026-09-30.md`,
    `docs/research/snapshot-reach-2026-09-30.md`,
    `docs/research/probe-richmond.md`, product facts (`facts:export`), this
    file, `.streams/dispatch-log.md`
- **Spine files touched (one hold):** `apps/api/src/producers/scheduler.py`
  (`link_pattern` forwarded to the Excel client; the parcel join reads the
  row's own key name), `apps/api/src/spatial/city_registry.py`
  (`DatasetSpec.link_pattern`), `apps/api/src/config.py` (Richmond's deeds
  endpoint is the media page), `apps/api/src/producers/deeds_acris_producer.py`
  (the producer carries an Excel client).
- **Generated surfaces:** `apps/product/public/facts.json` and
  `cities/richmond.json`.

## Intent

Make Richmond's registered `deeds` feed publish. Its ArcGIS URL never pointed
at a service; the assessor's monthly transfers workbook is the live source
(feed-health note, "Mid-Atlantic deeds").

## Decisions

- 2026-09-30 — A standard-library streaming reader rather than openpyxl: no
  new dependency, and 41 seconds and about 60 MB for the 439,398-row file.
- 2026-09-30 — The spec registers the media page plus a `link_pattern`; the
  greatest matching file name is the newest, since the names carry the date.
- 2026-09-30 — The client remembers `ETag` and `Last-Modified` only after a
  complete, uncapped read, so a short poll reads the file again.
- 2026-09-30 — A 365-day window, read whole each poll (cap 12,000), rather
  than the whole history: the feed exists for recent sales, and a cold start
  replays one year.
- 2026-09-30 — `doc_id` is the parcel id, as Durham's is; the record id is the
  composite of parcel, date, deed book and page, unique across the year.
- 2026-09-30 — `IN` lists split at 1,400 encoded characters as well as 100
  values: Richmond's ArcGIS Online host answers 404 past about 2,000.

## Current step

Done.

## Next step

The SNAP retailer `sla` slice for the metros with no SLA-grade feed, Richmond
among them.
