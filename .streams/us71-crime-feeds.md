# Stream log — us71-crime-feeds — 2026-08-24

## Claim

- **Stream id:** `us71-crime-feeds`
- **Leaf files I will create/edit:**
  - `apps/api/src/producers/crime_incidents_producer.py` (new)
  - `apps/api/src/schemas/models.py` (CrimeEvent)
  - `apps/api/src/schemas/avro/crime_event.avsc` (new)
  - `apps/api/src/features/pipeline.py` (raw_crime table + insert_crime)
  - `apps/api/src/consumers/spatial_enrichment_worker.py` (topic_crime branch)
  - `apps/api/tests/unit/test_producers_crime.py` (new)
  - `apps/api/tests/unit/test_schemas.py` (crime avro roundtrip)
  - `.streams/us71-crime-feeds.md`
- **Spine files I expect to need:** `apps/api/src/config.py` (4 crime
  endpoints), `apps/api/src/spatial/city_registry.py` (CRIME specs for
  NYC/CHI/SF/SEA), `apps/api/src/producers/scheduler.py` (wire crime producer).

## Intent

US-71 (Signals S2): register the crime incident feeds for Chicago `ijzp-q8t2`,
San Francisco `wg3w-h783`, Seattle `tazs-3rd5`, and NYC `5uac-w243` (YTD),
making them ingestible end-to-end (raw topic -> producer -> Kafka -> enrich ->
raw_crime). LA stays out (NIBRS-transition gap). Modeling constraints are
carried, not yet built: Part-1/Part-2 offense class is carried on the event so
Part-2 noise can be dropped later, and NOTHING feeds LIMS (ablation rule).
NYC's monthly feeds get the G11 cadence declaration (expected_cadence_days=30).

Done = 4-city registration + producer + enrichment + tests, interlock + full
suite green, US-71 resolved.

## Decisions

- 2026-08-24 — Live-probed all four Socrata feeds (2026-08-24) for real column
  names: CHI `id`/`primary_type`/`latitude`; SEA `offense_id`/
  `nibrs_offense_code_description`/`latitude`; SF `incident_number`/
  `incident_category`/`latitude`(+`point`); NYC `cmplnt_num`/`ofns_desc`/
  `latitude`(+`lat_lon`). Shared parse chains cover these; per-city field maps
  are unnecessary.
- 2026-08-24 — NYC registers the current-year YTD feed only (`5uac-w243`);
  the historic `qgea-i56i` set is a backfill/validation corpus, not a live
  signal. G11: `expected_cadence_days=30` (monthly cadence, alarm at 60d).
- 2026-08-24 — CrimeEvent carries `offense_class` (PART1/PART2) computed by a
  UCR Part-1 keyword classifier over offense text — the hook for the ticket's
  Part-2 noise filtering at the model stage. Best-effort, documented.
- 2026-08-24 — Ablation: crime events flow to `raw_crime` in the DuckDB
  pipeline for offline experiments; no `feature_store_h3` column, no LIMS
  term, no model input. Promotion waits on an ablation showing lift.
- 2026-08-24 — No LA registration; no county-bonus (Santa Clara/Alameda)
  registration — those are context-feature work outside this ticket.

## Current step

DONE. Producer + 4-city registration + enrichment + tests all in place;
interlock green; full suite green (730 passed, 0 failures). Working tree NOT
committed (awaiting instruction).

## Next step

Linear resolution on US-71. If resumed: commit, then run an ablation using
`raw_crime` (Part-1 filtered, own decay window) before any LIMS promotion.