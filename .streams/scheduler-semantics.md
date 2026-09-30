# Stream log — scheduler-semantics — 2026-09-30

## Claim

- **Stream id:** `scheduler-semantics`
- **Leaf files created/edited:**
  - dataset blocks in `allentown`, `asheville`, `baltimore`, `boston`,
    `bowling_green`, `canton`, `charleston_wv`, `chattanooga`, `cleveland`,
    `durham`, `frederick`, `indianapolis`, `las_vegas`, `lynchburg`,
    `milwaukee`, `montgomery`, `phoenix`, `prince_georges`, `providence`,
    `raleigh`, `reno`, `roanoke` and `washington_dc` `.yaml`
  - leaf mirrors: `allentown.py`, `boston.py`, `bowling_green.py`,
    `charleston_wv.py`, `frederick.py`, `las_vegas.py`, `lynchburg.py`,
    `phoenix.py`, `providence.py`, `roanoke.py`
  - clients outside the spine: `watermarks.py` (28 hosts, exact `timestamp`
    literals, the layer's zone), `arcgis_client.py` (the zone from
    `dateFieldsTimeReference`, numeric `IN` lists), `acquisition.py`
    (docstring)
  - tests: `test_scheduler_boundaries.py` (new), `test_scheduler.py`,
    `test_watermarks.py`, `test_arcgis_client.py`, `test_dc_parcel_join.py`,
    `test_acquisition.py`, `test_backfill_loader.py`, `test_snapshot_reach.py`,
    `test_rollover_drill.py`, and the Boston, Bowling Green, Chattanooga,
    Cleveland, Columbus, Dayton, Des Moines, Lynchburg, Milwaukee, Phoenix,
    Raleigh and Reno producer tests
  - `docs/research/feed-health-2026-09-30.md`,
    `docs/research/snapshot-reach-2026-09-30.md`, product facts
    (`facts:export`), this file, `.streams/dispatch-log.md`
- **Spine files touched (one hold):** `apps/api/src/producers/scheduler.py`
  (the incremental filter's boundary, stall guard and zone; the watermark from
  the filter column; composite ids; the parcel join in `poll_job`),
  `apps/api/src/spatial/city_registry.py` (`DatasetSpec.composite_id`),
  `apps/api/src/config.py` (Roanoke's deeds endpoint).
- **Generated surfaces:** `apps/product/public/facts.json` and the affected
  cities' `cities/*.json`.

## Intent

Fix the filter an incremental poll sends. The feed-health census polled every
job once, from no watermark, so no incremental filter was ever exercised; its
"Found along the way" list named the watermark source, first-key record ids
and date-only boundaries. Poll every incremental ArcGIS feed twice and repair
what the second poll shows.

## Decisions

- 2026-09-30 — ANSI hosts get `timestamp 'YYYY-MM-DD HH:MM:SS'`, exact to the
  second, not `date 'YYYY-MM-DD'`: every incremental ANSI host answered it,
  and a date re-read the watermark's day forever when the day outgrew the cap.
- 2026-09-30 — A layer's `dateFieldsTimeReference` decides the zone a literal
  is written in. The client reads it with the metadata it already fetches for
  paging; a layer that declares none, or UTC, gets UTC.
- 2026-09-30 — A watermark on a whole hour is a date and keeps its boundary
  with `>=`; the dedup drops the rows already seen. A full page that leaves the
  watermark where it was steps past the boundary until the watermark moves
  (`>` on a date, `>=` the next second on a timestamp); newest-first reads
  never step past.
- 2026-09-30 — The watermark is the filter column's newest value; the event's
  date stands in only for an empty column.
- 2026-09-30 — `composite_id` is opt-in per spec rather than a change to every
  feed's record id, so feeds whose later keys are fallbacks keep their ids.
- 2026-09-30 — Milwaukee `sla` becomes a snapshot: each refresh restamps all
  1,275 rows with one `GIS_DATETIME` that the server holds finer than it
  returns, so no filter on it can page.
- 2026-09-30 — A row the dedup skips still does not move the watermark. Only
  Milwaukee `sla` needed it in the survey, and it is now a snapshot.

## Current step

Done.

## Next step

Richmond `deeds` (an `.xlsx` reader and its monthly URL), or the object-id
ordering of the incremental feeds the feed-health note lists.
