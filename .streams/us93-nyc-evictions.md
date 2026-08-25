# Stream log — us93-nyc-evictions — 2026-08-24

## Claim

- **Stream id:** `us93-nyc-evictions`
- **Leaf files I will create/edit:**
  - `apps/api/src/producers/evictions_producer.py` (new)
  - `apps/api/src/schemas/models.py` (EvictionEvent)
  - `apps/api/src/schemas/avro/eviction_event.avsc` (new)
  - `apps/api/src/features/pipeline.py` (raw_evictions + insert_evictions)
  - `apps/api/src/consumers/spatial_enrichment_worker.py` (topic_evictions branch)
  - `apps/api/tests/unit/test_producers_evictions.py` (new)
  - `apps/api/tests/unit/test_schemas.py` (avro roundtrip)
  - `apps/api/tests/unit/test_feed_staleness_probe.py` (NYC feed count 5→6)
  - `.streams/us93-nyc-evictions.md`
- **Spine files I expect to need:** `apps/api/src/config.py` (endpoint),
  `apps/api/src/spatial/city_registry.py` (NYC EVICTIONS spec),
  `apps/api/src/producers/scheduler.py` (wire evictions producer).

## Intent

US-93 (Signals S4): ingest NYC Marshals' executed evictions (`6z8x-wfk4`) as
a **NYC-only context/validation feature** — never a LIMS input (single-metro
asymmetry rule). Re-probed at claim time: the feed now carries `latitude`/
`longitude` (91.6% of newest-500, fresh to 2026-08-20, daily cadence), so the
ticket's geocoding constraint is moot and G5 passes (newest-window gap ≈
published gap). Register behind the EVICTIONS FeedType (US-72) with raw
ingestion + enrichment so the context signal is available; no LIMS term.

Done = producer + registration + enrichment + tests, interlock + full suite
green, US-93 resolved.

## Decisions

- 2026-08-24 (re-probe) — Ticket said "no lat/lon, geocoding required"; live
  probe shows the feed now publishes `latitude`/`longitude` (91.6% of newest
  500, gap = published gap, G5 passes). No geocoder dependency.
- 2026-08-24 — NYC-only per constraint #2: context/validation, NOT a LIMS
  input. Cross-city feature deferred until a second metro publishes evictions.
- 2026-08-24 — Feed is Socrata (single city, nyc); shared chains cover the
  spellings; field map for the NYC evictions column names.
- 2026-08-24 — id = `court_index_number` (docket_number fallback).

## Current step

DONE. Producer + NYC registration + enrichment + tests all in place;
interlock green except 2 failures owned by the concurrently-active US-81
stream (KeyError 'street_cut' — their REGISTRY spec landed, their scheduler
wiring is mid-write: import present, producers-dict entry pending). Full
suite: 779 passed / 2 failed (both US-81's) / 3 skipped. Working tree NOT
committed.

## Next step

Linear resolution on US-93.