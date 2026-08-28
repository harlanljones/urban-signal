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

## Phase 3 result — event schemas + §1.2 GBFS + §1.4 client (2026-08-28)

### The §5 event-schema decision, made once
Four new Avro types, matching §6.3's budget:
1. `StationChangeEvent` — GBFS. Kept separate from the generic shape because a
   bikeshare station carries dock-level state (capacity, docks available) that
   a charger or a small cell does not.
2. `PoiChangeEvent` — POI deltas. **Never** an `SLALicenseEvent`: a license is
   a government authorization with an issuing body and a legal effective date;
   a POI detection is a vendor observation with a confidence and a release
   date. Conflating them corrupts the license move-in/out semantics that the
   S1 flow features rest on.
3. `InfrastructureEvent` — **generic**, as §5 suggested. `category` ∈
   {ev_station, small_cell, grid_capacity}; `unit_count` carries whatever the
   family counts (ports, antennas, megawatts). Three near-identical schemas
   would have cost three consumers and three feature-key sets for no analytic
   gain.
4. `InsuranceLossEvent` — NFIP claims.
FEMA **disaster declarations** deliberately earn no type: county-level, no
loss amount, no point geometry. They ride the existing
`ContextObservationEvent` — context around claims, not a sited event.

### Where national feeds live
`src/spatial/national_feeds.py`, not `CityRegistration.datasets`. A city holds
at most one DatasetSpec per FeedType and these feeds have no per-city
endpoint; registering one national file 62 times would make 62 jobs poll the
same URL, and the city gate's per-city invariants are meaningless for them.
GBFS is the exception and stays city-shaped: one system, one metro.

### §1.2 GBFS — live proof run, four systems
```
nyc            bkn      v2.3  2,508 stations   98 pre-activation (is_installed=0)
chicago        chi      v2.3  2,050 stations    1 pre-activation
san_francisco  bay      v2.3    633 stations    0
washington_dc  dca-cabi v1.1    866 stations    0
```
Second poll on warm state: 0 added / 0 removed on every system. 6,057 stations
under management; both the v2.x `data.<lang>.feeds` and the v3 flat dialect are
handled, and the v1.1 path is exercised for real by Capital Bikeshare.

**Two findings that changed the design:**
- **`gbfs.lyft.com/gbfs/2.3/dca/` is a live-but-empty stub.** HTTP 200, fresh
  `last_updated`, `"stations": []`. The real Capital Bikeshare system is
  `dca-cabi` on GBFS **1.1** with 866 stations, reached through
  `gbfs.capitalbikeshare.com/gbfs/gbfs.json`. Registering the stub would have
  seeded an empty store and then emitted 866 spurious installs.
- Therefore **an empty station set is a failed poll, not a snapshot**
  (`EmptySnapshotError`): never seed or overwrite state from one. Likewise a
  first poll emits nothing — with no prior state every station looks new, and
  the install date of a pre-existing station simply is not knowable from a
  feed that publishes no history.

### §1.3 FSQ — the source moved
The anonymous S3 bucket the sweep recorded (`fsq-os-places-us-east-1`) now
holds **only LICENSE.txt and NOTICE.txt**; every release partition is gone.
Foursquare moved the dataset to a **gated Hugging Face repo** (anonymous
download 401, access auto-granted on request). Layout is unchanged —
`release/dt=<date>/{places,deltas,categories}/parquet/`, 21 releases, latest
**dt=2026-08-11** with 10 delta partitions. Apache-2.0 still applies and
NOTICE.txt attribution must travel with any derivative, so the spec carries
the attribution string. Registered with `auth=bearer`/`HF_TOKEN`; it is not
schedulable until the token exists.
This is exactly the failure mode the sweep warned about ("FSQ did exactly that
in Oct 2025") — re-probing before registering is what caught it.

### §1.4 OpenFEMA — verified live
`NfipClaims` **v3**: `$inlinecount=allpages`, `$filter`, `$orderby`,
`$select`, `$top`/`$skip` all behave (NY since 2024-01-01 → count **1,443**).
`DisasterDeclarationsSummaries` is v2-only; v3 404s.
- **The published coordinate is unusable.** FEMA truncates claim lat/lng to
  0.1° (~11 km) — wider than a res-7 hexagon, and capable of naming the wrong
  city. Tagging goes `censusGeoid` → tract centroid → H3, ZIP centroid as
  fallback, DLQ otherwise, with `geometry_source` recorded on the event. The
  live Harris County example: FEMA publishes (29.9, −95.4); the tract centroid
  is (29.935, −95.305), over 9 km away.
- **Tracts split between censuses.** Harris County's `48201222700` became
  `...01`/`...02` in the 2020 tabulation, so a claim filed under the old id
  matches no Gazetteer tract exactly. The crosswalk falls back to the parent's
  first child, which always lies inside the old tract.
- **NFIP paid amounts go negative** (a NY claim at −8,627.72, found live when
  a `ge=0` constraint rejected it): recoveries and subrogation reverse earlier
  payments. Clamping to zero would understate exactly the hexes with the most
  complicated claim histories. The constraint is gone and the reason is
  recorded on the model.

### §1.5 NREL — cannot be verified from here
`developer.nrel.gov` and `afdc.energy.gov` do **not resolve** from this
network (DNS failure) — the same block the research sweep hit, so nothing
about this feed has been confirmed live by anyone. Registered with
`verified=False`, which keeps it out of `schedulable_feeds()` until someone
spot-verifies `developer.nrel.gov/terms/` and one live response.

### Gates
`pytest -m interlock` 24 passed / 0 failed. My modules'' tests: 151 passed
(context observations 47, series 61, gbfs+national 37, plus the concurrent
agent''s snapshot/openfema tests, which pass against my clients unchanged).

## ⚠ Collision — a second agent is working this same ticket
Discovered 22:22–22:25 while writing §1.4. Another session is writing US-363
files in the same tree and **overwrote `src/producers/nfip_producer.py`** with
its own implementation, and has added `src/producers/nrel_afdc_client.py`,
`src/producers/ev_charging_producer.py` and five test modules
(`test_nfip_producer.py`, `test_openfema_client.py`, `test_snapshot_client.py`,
`test_nrel_afdc_client.py`, `test_ev_charging_producer.py`). Its tests pass
against *my* `snapshot_client.py` and `openfema_client.py` unchanged, so the
two efforts are compatible where they meet — but there is no stream claim for
it in `.streams/`, which is what would have prevented this.

I have stopped writing shared paths and committed only my own files. Not mine
and not touched by me: `nfip_producer.py`, `nrel_afdc_client.py`,
`ev_charging_producer.py` and the five test modules above.

## Current step
Phase 3 committed. **Stopped pending direction** — §1.3 `poi_diff_producer`
is the only component neither agent has built, and §1.4/§1.5 need the two
implementations reconciled before either is trustworthy.

## Next step
Reconcile with the other agent''s §1.4/§1.5 work (or have one of us drop it),
then build `poi_diff_producer` against the gated Hugging Face channel.
