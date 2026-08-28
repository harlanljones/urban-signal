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

## Phase 2 result — §1.1 SeriesClient DONE (2026-08-28)

Leaf only. No spine files touched: series are national files keyed by
geography, not city feeds, so they live in their own `SERIES_REGISTRY` rather
than `CityRegistration.datasets` (a city holds at most one DatasetSpec per
FeedType, while one metro carries rent + value + forecast + HPI + FMR series
at once). Nothing is produced to Kafka — the output is an upsert.

Files: `src/spatial/geography_crosswalk.py`, `src/spatial/series_registry.py`,
`src/producers/series_client.py`, `src/features/macro_series_store.py`,
`tests/unit/test_series_client.py` (61 tests).

### Decisions
- **Crosswalk source: Census Gazetteer, not HUD.** The sweep suggests HUD's
  USPS ZIP crosswalk; `huduser.gov/hudapi/public/usps` returns **401** without
  a Bearer token (verified 2026-08-28), which would make the crosswalk — a
  dependency of *every* series feed — fail closed on a missing secret. The
  Gazetteer files are the same public-domain geography with no key:
  `2024_Gaz_zcta_national.zip` (33,791 ZCTA centroids) and
  `2024_Gaz_cbsa_national.zip` (935 CBSAs).
- **Metro names do not match across publishers.** The 2024 Gazetteer carries
  2023 OMB delineations; Zillow still ships the older titles. Exact matching
  loses most metros:
  `Houston-Pasadena-The Woodlands, TX` vs `Houston-The Woodlands-Sugar Land, TX`;
  `New York-Newark-Jersey City, NY-NJ` vs `New York, NY`;
  `Chicago-Naperville-Elgin, IL-IN` vs `…, IL-IN-WI`.
  Matching tries the full name, then falls back to (primary city, first
  state) — the two parts that survive redelineation. Ambiguous keys are
  logged and dropped, never guessed.
- **CBSA -> city is NOT centroid containment.** A CBSA spans whole counties,
  so its internal point sits outside the tighter bbox we register a metro
  with: Seattle-Tacoma-Bellevue's centroid lands in the Cascades, east of
  Seattle's `metro_bbox` entirely; Denver's and DC's do the same. Containment
  is right for a ZIP and wrong for a CBSA, so CBSAs resolve by primary city
  with containment only as a second pass. Pinned by a test.
- **Four CBSA-title spellings the registry's aliases lack** live in the
  crosswalk, not in spine ALIASES, because each is a title artifact and two
  are genuinely ambiguous as bare aliases: "washington" is also a state and
  "miami" is also the Miami, OK micro area (CBSA 33060). Keying on
  (city, state) is what makes them safe.
- **Coverage:** every registered city is reachable from a CBSA except
  `fort_worth`, `aurora` and `prince_georges`, which have no CBSA of their own
  (they are submarkets inside Dallas-Fort Worth, Denver-Aurora and
  Washington-Arlington-Alexandria). They get ZIP-level coverage instead, where
  smallest-bbox containment picks the more specific registration. Asserted by
  a test so a lost CBSA link fails loudly instead of emptying a series.
- **The store is not append-only.** Zillow and FHFA reissue and revise full
  history; a watermark append would freeze the first vintage of every revised
  month. `macro_series` upserts current values and writes displaced ones to
  `macro_series_vintages`; `max_period()` is a freshness signal, explicitly
  not an ingestion cursor.
- **Set-based upsert.** The first implementation read-then-wrote per row:
  **37s** for one Zillow release. Staging through a registered DataFrame and
  diffing in four statements is **0.7s** for the same 313,065 rows and 5.4s
  for ZHVI's 2,407,210. The PRIMARY KEY was measured rather than assumed —
  0.09s vs 0.28s to bulk-insert 313k — and kept.
- **Timezone/period normalization:** every period is stored as the first day
  of its period, so a publisher switching month-end to month-start labels
  cannot fork the key space.

### Live proof run (2026-08-28, all four keyless series)
```
zori_zip        313,065 obs   62 cities  2015-01..2026-07  fetch 1.1s  upsert 0.7s
fhfa_hpi_metro    7,242 obs   50 cities  1991-01..2026-04  fetch 2.6s  upsert 0.0s
zhvf_metro          219 obs   59 cities  2026-08..2027-07  fetch 0.2s  upsert 0.0s
zhvi_zip      2,407,210 obs   62 cities  2000-01..2026-07  fetch 6.3s  upsert 5.4s
re-apply identical release -> 0 inserted / 0 revised / 7,242 unchanged
perturb 100 values         -> 0 inserted / 100 revised / 0 unchanged
store total                -> 2,727,736 rows
```

### Gates
`pytest tests/unit/test_series_client.py` 61 passed; `pytest -m interlock`
24 passed / 0 failed.

### Note on the tree (2026-08-28 ~22:05)
Another session held the `city_registry.py` spine mid-run for the wave-5
city registrations, and the tree briefly carried a torn write
(`CityId.BUFFALO` + aliases with no registration, so `import city_registry`
raised). It cleared on its own. I did not touch that file during the hold.
Also: cutting this branch switched the working tree under that session, so
its wave-5 commits may land here; `git checkout main` refuses while its edits
are uncommitted, and stashing another agent's in-flight hold is not mine to
do. Separate with a cherry-pick of 0523e8d if the branches need untangling.

## Current step
Phase 2 committed. Starting the §5 event-schema spine decision.

## Next step
Decide generic `InfrastructureEvent` vs per-family once (§5 item 2), register
`StationChangeEvent` / `poi_change` / `insurance_loss` schemas in one hold,
then build SnapshotClient/GBFS, poi_diff_producer/FSQ, OpenFemaClient and
NrelAfdcClient.
