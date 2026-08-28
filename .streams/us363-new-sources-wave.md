# Stream log — us363-new-sources-wave — 2026-08-28

## Claim
- **Stream id:** `us363-new-sources-wave`
- **Ticket:** US-363 — new data sources wave, 2026-08-27 sweep (8 register-now
  candidates). Evidence: `docs/research/new-sources-sweep-2026-08-27.md` §1–§5.
  §2.6 (SNAP) already shipped as US-364 — not re-done here.
- **Leaf files I will create/edit:**
  - `apps/api/src/producers/field_maps_energy_benchmark.py`
  - `apps/api/src/producers/field_maps_counters.py`
  - `apps/api/src/producers/context_observations_producer.py`
  - `apps/api/src/producers/series_client.py`
  - `apps/api/src/producers/snapshot_client.py`
  - `apps/api/src/producers/gbfs_producer.py`
  - `apps/api/src/producers/poi_diff_producer.py`
  - `apps/api/src/producers/openfema_client.py`
  - `apps/api/src/producers/nfip_producer.py`
  - `apps/api/src/producers/nrel_afdc_client.py`
  - `apps/api/src/producers/ev_charging_producer.py`
  - `apps/api/src/spatial/geography_crosswalk.py`
  - `apps/api/src/spatial/national_registry.py`
  - `apps/api/src/schemas/avro/{context_observation,station_change,poi_change,infrastructure,insurance_loss}_event.avsc`
  - `apps/api/tests/unit/test_producers_context_observations.py` and one test
    module per component above
- **Spine files I expect to need:**
  - `apps/api/src/config.py` (endpoints, topics, macro-series settings)
  - `apps/api/src/spatial/city_registry.py` (FeedType members + DatasetSpec
    entries on nyc / chicago / seattle / san_francisco)
  - `apps/api/src/producers/scheduler.py` (producer keys + platform clients)
  - `apps/api/tests/unit/test_interlock_gate.py` (FEED_TOPICS, KNOWN_PLATFORMS,
    PLATFORM_SCHEMES, SPINE_INVARIANTS — extend the gate before extending
    the spine, per parallel-streams.md)
  - `docs/agents/spine-manifest.txt` (national registry, if it lands as spine)

## Intent
Land all eight register-now candidates from the sweep: the two remaining
zero-machinery Socrata registrations (§2.7 energy benchmarking, §2.8 bike/ped
counters) and the four new ETL components (§1.1 SeriesClient, §1.2
SnapshotClient/GBFS, §1.3 poi_diff_producer/FSQ, §1.4 OpenFemaClient, §1.5
NrelAfdcClient), in the sweep's recommended order, with `pytest -m interlock`
green at every step boundary.

## Decisions
- 2026-08-28 — **Branch:** `harlanljones/us-363-...` cut from `main` @ 2a70e39.
  The tree carried 34 uncommitted files of in-flight wave-4/5 work; those are
  left alone and never staged. Only US-363 paths are committed.
- 2026-08-28 — **Live re-probe of all six §2.7/§2.8 endpoints (2026-08-28), all 200:**
  - NYC LL84 `5zyy-y8am`: max `report_year` **2024**, n=103,259 (2024 cohort
    39,090). **253 columns.** `latitude`/`longitude` ARE present (sweep doc
    correct) — 1,354 / 39,090 = 3.5% null lat in the 2024 cohort. Numeric
    columns carry the string sentinel `"Not Available"`, which must be
    coerced to null, not 0.
  - Chicago `xq83-jr8c`: max `data_year` **2023** (lags, as documented),
    n=28,329; native `latitude`/`longitude` + `location` container;
    `chicago_energy_rating`, `reporting_status`, `community_area`.
  - Seattle `teqw-tu6e`: max `datayear` **2024**, n=34,699; lat/lng,
    `energystarscore`, `siteeui_kbtu_sf`, `totalghgemissions`,
    `ghgemissionsintensity`, `compliancestatus`, `demolished` (bool).
  - NYC counts `ct66-47at`: max `timestamp` **2026-08-27T05:00** (same-day
    freshness confirmed), n=**21,016,786** 15-minute rows. Carries NO
    geometry — `sensor_id` joins the sensor registry `6up2-gnw8`
    (`lat`/`lon`, `firstdata`/`lastdata`, `travelmodes`, `directional`).
  - Seattle Fremont `65db-xm6k`: max `date` **2026-07-31T23:00** (~4-week lag,
    as documented), n=121,211 hourly rows, columns `fremont_bridge`,
    `fremont_bridge_nb`, `fremont_bridge_sb`. NO geometry and no sensor
    registry — it is one fixed structure, so the coordinate is a constant.
- 2026-08-28 — **§2.8 is not one-event-per-row.** 21M 15-minute rows cannot
  become 21M Kafka events for a feature that is "flow intensity per hex".
  The producer aggregates to one observation per (sensor, travel mode, day)
  before producing.
- 2026-08-28 — **Event-shape decision for §2.7/§2.8.** The sweep (§5.1, §6.3.1)
  says "no new event" for these two, but neither maps onto an existing event —
  a benchmarked building is not a license, permit, deed or complaint. They are
  both *periodic per-asset measurements*, so they share ONE new typed event,
  `ContextObservationEvent` (`source`, `asset_id`, `metric`, `value`, `unit`,
  `period_start`/`period_end`, `category`, lat/lng, h3). One shape, not two,
  and it is the same shape round two's context tier (HRSA, IMLS/IPEDS, FRA
  crossings) will reuse — which is what §6.3's "bound the new-event count"
  rule is actually protecting.

- 2026-08-28 — **Two live findings the sweep doc does not carry**, both of
  which change how a counter day is summed:
  - `ct66-47at.status` is raw / modified / **deleted** (18,579,562 /
    2,435,656 / 1,568). `deleted` = retracted observation → filtered
    server-side by the spec's `where`, never summed.
  - **A sensor carries two live flows per direction.** Every
    sensor/mode/direction on 2026-08-26 had exactly two distinct `flowid`s,
    and they are not copies: sensor 100009425 (Prospect Park West) reported
    NB 71 and 1,682, SB 1,358 and 222, each over a full 96-row day. Separate
    parallel series, so the rollup sums all flows (~3.3k bikes/day for PPW is
    the plausible magnitude); de-duplicating to one flow per direction would
    halve it.
- 2026-08-28 — **Naive-timestamp bug caught by test.** Socrata publishes
  floating timestamps; leaving them naive let `astimezone` reinterpret them in
  the host timezone, moving a 22:00 row onto the next calendar day on a
  US-Pacific box. `_parse_datetime` now stamps UTC on naive values (the repo's
  convention for every other municipal feed) and a regression test pins it.

## Phase 1 result — §2.7 + §2.8 DONE (2026-08-28)
- Leaves: `field_maps_energy_benchmark.py` (240), `field_maps_counters.py`,
  `context_observations_producer.py` (~510),
  `schemas/avro/context_observation_event.avsc`,
  `tests/unit/test_producers_context_observations.py` (47 tests).
- Spine: `config.py` (+1 topic `raw.context.observations`, +6 endpoints),
  `city_registry.py` (FeedType.ENERGY_BENCHMARK / BIKE_PED, 5 DatasetSpecs on
  nyc / chicago / seattle), `scheduler.py` (2 producer keys, 1 shared
  instance per key), `schemas/models.py` (ContextObservationEvent + 9
  EnrichedH3Feature context keys), `enriched_h3_feature.avsc`,
  `test_interlock_gate.py` (FEED_TOPICS +2).
- Reconciled 2 pre-existing pins my registration moved:
  `test_feed_staleness_probe` nyc feed count 6 -> 8, `test_producers_seattle`
  registration shape +2 feeds.
- **Gates:** `pytest -m interlock` 24 passed / 0 failed. Full suite **2072
  tests, 1 failure, 0 errors, 3 skipped** — the single failure is the
  pre-existing spine-owned leaf-count pin
  (`test_city_leaf_naming::test_all_expected_leaf_modules_present`, `== 62`
  vs the 68 leaf modules the uncommitted wave-5 work adds). It is red on this
  tree before any US-363 edit and is not mine to move.

## Current step
Phase 1 committed. Starting the §5 event-schema spine decision, then
`SeriesClient` (§1.1).

## Next step
Decide generic `InfrastructureEvent` vs per-family once (§5 item 2), register
`StationChangeEvent` / `poi_change` / `insurance_loss` schemas in one hold, and
build SeriesClient + the geography crosswalk.
