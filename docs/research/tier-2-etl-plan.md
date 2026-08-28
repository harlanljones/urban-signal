# Tier 2 ETL — parcel H3, county/city/state fusion, seasonality

**Plan stamp: 2026-08-28.** Decomposition of the "Tier 2 ETL" work item into
sequenced, leaf-shaped tickets. This is a plan, not an implementation: every
component touches spine files (`h3_indexer.py`, `feature_aggregation_worker.py`,
`geography_crosswalk.py`, `lims_calculator.py`) and must go through the
interlock hold with `pytest -m interlock` green.

## Today (Tier 1)

Events flow: producer → `spatial_enrichment_worker` (H3-tags at res 7/8/9 from a
**point**; geocodes address-only rows via ADR 0004) → `feature_aggregation_worker`
(keyed `city_id:h3`) → `feature_store_h3` → `features/` (`lims_calculator`,
`shift_dynamics`, `time_decay`) → alert dispatch. Series observations land in
`macro_series_store` (SeriesClient: zillow/fhfa/hud/census/fred profiles).

Three limitations motivate Tier 2:
1. **Point, not parcel.** H3 cells are tagged from event lat/lng (or geocoded
   address point). A parcel polygon's boundaries (or a multi-parcel deed) do not
   participate in the H3 assignment. `parcel_join` machinery exists only inside
   `deeds_acris_producer` (DC SSL / Denver PARID, ADR 0004 §"out of scope").
2. **City-centric geography.** `geography_crosswalk` resolves a point → one
   city; the DC-metro spread (Montgomery + DC + Prince George's = one product
   metro, ADR 0007 "metro_group") has no fusion layer; county and state layers
   are not merged into a resolved geography.
3. **No seasonality.** `lims_calculator` / aggregation treat January and July
   alike; northern metros' winter construction troughs and liquor-license
   seasonality are unmodeled.

## Components (sequenced)

### T2-A: Parcel → H3 join (parcel-polygon tagging)

- Promote `parcel_join` out of `deeds_acris_producer` into shared
  `spatial_enrichment_worker` so ANY event family (permits, 311, SLA, deeds)
  with a parcel id can join a parcel layer once and tag res-7/8/9 H3 from the
  parcel centroid/polygon instead of the event point.
- Shape: `parcel_join` already exists on `AcquisitionSpec`/`DatasetSpec`
  (`apps/api/src/producers/acquisition.py:98`) — the spine change is moving the
  join out of the deeds producer into enrichment, gated behind the same
  `spec.parcel_join` contract.
- New work: `ParcelJoinClient` (parcel layer lookup by `join_key`, polygon →
  representative point), unit tests with the DC/Denver parcel layers already
  proven in `deeds_acris_producer` tests.
- **Gate note:** `h3_indexer` and `spatial_enrichment_worker` are spine — the
  interlock gate needs an invariant that a parcel-joined spec yields cells
  inside the parcel's metro bbox.

### T2-B: county + city + state fusion

- Introduce the ADR 0007 `metro_group` concept (deferred there by design):
  a registry-level grouping of `CityId`s surfaced as one product metro.
  First group: DC metro (Montgomery + DC + PG) and the Texas I-35 corridor
  (Austin + Dallas + Fort Worth + Houston + San Antonio) — the TABC slices
  registered in this same hold make the I-35 corridor genuinely multi-source.
- `geography_crosswalk` gains a resolution cascade: point → parcel → county →
  city → CBSA → state, returning the full chain so a consumer can ask "which
  metro, which city, which county, which state" without re-deriving.
- **Gate note:** the ADR 0007 consequence says a `metro_group` "must extend the
  gate's coverage (a grouping resolving to registered CityIds)" — new interlock
  invariant required.

### T2-C: seasonality adjustment

- Factor store: per-(metro, feed-family, month) seasonality multipliers fed by
  macro series (FRED LAUS/CPI, FHFA HPI) and/or a rolling 12-month in-house
  baseline from `feature_store_h3`.
- Apply at the feature layer: `lims_calculator` / `shift_dynamics` consume a
  de-seasonalized input (dividing observed counts by the month factor) so
  January's construction trough doesn't read as a contraction signal.
- Deliverable is a `seasonality.py` feature module + `SeasonalityStore`
  (mirroring `macro_series_store`), ablation-gated before LIMS per US-72's rule
  (a seasonality factor entering LIMS is a model change — needs an ablation run).

## Sequencing

1. **T2-A** first (enrichment is upstream of everything; deeds parcel evidence
   already exists). 
2. **T2-B** second (fusion is ingestion-level; the I-35 corridor now has real
   multi-city SLA data to fuse).
3. **T2-C** last (consumes the fused geography + FRED macro series from item 5's
   key).

Each is a spine hold with its own interlock delta; all three are larger than a
single session's silent edit and should be dispatched as Linear tickets
(parent: this plan) with the leaf/spine split per `docs/agents/parallel-streams.md`.

## Dependencies

- T2-A depends on nothing new (parcel layers already live: DC SSL, Denver
  PARID).
- T2-B depends on T2-A's joined parcel geometry for the county layer.
- T2-C depends on the FRED key (item 5) for LAUS/CPI/HPI series and on T2-B's
  metro grouping for metro-level factors.
