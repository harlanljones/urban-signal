# US-422: Ingest NHTSA FARS crash geocodes, FRA rail crossings, and OpenFEMA NFIP claims

## Summary

Adds two new Wave 1 leaf spatial modules from
`docs/research/national-environmental-infrastructure-signals-2026-08-30.md`
(§2.1, §2.3, §7 Ticket Specs 1–2): NHTSA FARS fatal-crash geocodes and FRA
highway-rail grade crossing inventory/incidents. Both follow the repo's
established "Wave 1 point-event, zero spine risk" leaf-module pattern
(`epa_echo.py`, `hpms_context.py`): pure geometry/severity helper functions
that map one record's lat/lng onto the H3 res 7/8/9 hierarchy via the
existing `H3SpatialIndexer`, with no changes to `config`, `city_registry`,
`geo_utils`, `submarkets`, or `producers`.

The third dataset in scope — OpenFEMA NFIP Redacted Claims — is **already
fully implemented** on `main` (US-363): `NfipProducer` + `OpenFemaClient` +
`NationalFeed.NFIP_CLAIMS` in `apps/api/src/spatial/national_feeds.py`
already ingest claim payouts at Census Tract / ZIP / Lat-Lon grain, resolve
`city_id` by point-in-metro-bbox, and emit `InsuranceLossEvent` with the
full H3 res 7/8/9 hierarchy attached per claim. No code changes were needed
for that leg of the ticket — see Notes.

## Changes

- **`apps/api/src/spatial/nhtsa_fars.py`** (new) — `FarsCrash` dataclass,
  `LightCondition` enum with per-condition pedestrian-risk priors,
  `map_crash_to_h3`, `pedestrian_fatality_ratio`,
  `accumulate_cell_fatal_stats`, `rolling_window_crashes` (3-year default
  window), `vision_zero_density` (fatalities/km² per H3 cell), and
  `pedestrian_vulnerability_index` (volume-scaled pedestrian-fatality share
  per cell).
- **`apps/api/tests/unit/test_nhtsa_fars.py`** (new) — coordinate-hierarchy
  consistency, invalid-coordinate guard, pedestrian ratio edge cases, cell
  accumulation, rolling-window filtering (including future-dated and
  boundary crashes), and density/vulnerability-index scaling.
- **`apps/api/src/spatial/fra_rail_crossings.py`** (new) — `RailCrossing` /
  `RailIncident` dataclasses, `WarningDeviceClass` / `CrossingType` enums
  with per-device barrier-friction priors, `map_crossing_to_h3` /
  `map_incident_to_h3`, `daily_train_movements`, `rail_severance_index`
  (train volume × track count × warning-device friction, private crossings
  scaled 0.4x), `incident_severity` (Form 57 fatalities/injuries,
  recency-decayed), and `accumulate_cell_weight`.
- **`apps/api/tests/unit/test_fra_rail_crossings.py`** (new) — coordinate
  hierarchy, invalid-coordinate guard, train-movement summation, severance
  index scaling (passive vs. gated, track count, public vs. private),
  incident severity (fatality weighting, future-date guard, recency decay),
  and cell accumulation.

## Testing

- `pytest apps/api/tests/unit/test_nhtsa_fars.py apps/api/tests/unit/test_fra_rail_crossings.py -q` — 26 passed.
- `pytest apps/api/tests/unit -k "spatial or fars or fra_rail or nfip or openfema" -q` — 279 passed, 1 pre-existing failure (`test_submarkets.py::TestSpatialDistanceAndBoroughs::test_get_city_for_coordinate`, an Oakland/SF bbox overlap issue unrelated to this change — reproduces identically on `main` before this branch's changes).

## Notes

- **Scope call**: The research doc's headline table marks FARS and FRA
  `ADOPT / REGISTER`, but its own Phase 1 architecture section (§6) and
  concrete ticket specs (§7, US-410/US-411) both say "Leaf modules in
  `apps/api/src/spatial/`... Zero spine risk" with exactly the target paths
  used here. Registering a live `FeedType` (producer + Kafka topic + avro
  schema + scheduler wiring) is a spine change explicitly deferred by the
  same pattern `epa_echo.py` and `hpms_context.py` already established for
  prior Wave-1-adjacent datasets — a future producer can build directly on
  these leaf helpers (mirrors `epa_echo`'s own stated intent). This matches
  how the ticket's third item (NFIP) already landed: **spine-registered**,
  because that dataset's Wave 1 rollout (US-363) went further than the leaf
  stage. If full spine registration (producer + `FeedType` + avro schema)
  for FARS/FRA is wanted now rather than as a follow-up, flag it and it can
  be scoped as a fast-follow ticket — NHTSA's Crash Data API and FRA's
  Master Web Service API details from the research doc are already captured
  in the leaf modules' docstrings for that follow-up to build from.
- No network calls are made by either leaf module or its tests — both are
  pure geometry/severity logic over caller-supplied records, matching the
  `epa_echo`/`hpms_context` convention. A future producer would add the
  NHTSA Crash Data API / bulk CSV client and FRA Master Web Service / bulk
  CSV client, following `OpenFemaClient`'s pagination pattern.
