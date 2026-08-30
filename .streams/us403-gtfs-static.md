# Stream log — us403-gtfs-static — 2026-08-30

## Claim

- **Stream id:** `us403-gtfs-static`
- **Leaf files I will create/edit:**
  - `apps/api/src/producers/gtfs_static_client.py`
  - `apps/api/tests/unit/test_gtfs_static_client.py`
- **Spine files I expect to need:**
  - `apps/api/src/producers/scheduler.py` (schedule quarterly refresh)
  - `apps/api/src/spatial/city_registry.py` (FeedType, per-city DatasetSpec)
  - `apps/api/src/schemas/models.py` (EnrichedH3Feature transit covariate fields)

## Intent

Build `GtfsStaticClient` — a thin client that queries the MobilityDatabase
catalog (keyless, 1,182 US GTFS-schedule feeds), downloads in-scope operators'
`google_transit.zip`, parses the five required GTFS files (stops, routes, trips,
stop_times, calendar), and emits per-H3 covariates (stop_density,
service_frequency, route_count). Quarterly refresh. Parsing uses the existing
`parse_gtfs_stops` from `ntd_transit.py` and H3SpatialIndexer for spatial
tagging. No new event schema — output is EnrichedH3Feature context covariate
dicts.

## Decisions

- 2026-08-30 — `service_frequency` computed as average daily departures per stop
  (sum over trips serving the stop of `days_of_week_active / 7`). If calendar.txt
  is missing, every service_id defaults to 7-day operation.
- 2026-08-30 — Bbox filtering is a data parameter (list of bbox dicts), not an
  import from city_registry. The caller (spine) passes the registered metros'
  bboxes.

## Current step

Phase 1 DONE — leaf files created and tested: `gtfs_static_client.py`
(`GtfsStaticClient` with catalog fetch, zip download, `parse_feed_zip`,
`compute_covariates`, `select_feeds_for_bboxes`) and `test_gtfs_static_client.py`
(17 tests). `pytest tests/unit/test_gtfs_static_client.py` green, ruff clean.

## Next step

Spine interlock hold: wire into scheduler, register per-city DatasetSpec, add
transit covariate fields to EnrichedH3Feature.