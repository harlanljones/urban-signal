# US-362 — NYC TLC trip-record prototype

## Decision

The TLC dataset is viable for a bounded NYC mobility analytics prototype, but it should remain a separate monthly analytical source rather than a municipal event feed or a registered Urban Signal city feed.

The source publishes monthly Yellow Taxi, Green Taxi, FHV, and High-Volume FHVV Parquet files on CloudFront. The prototype uses Yellow and HVFHV because they provide zone-to-zone trip records with pickup/dropoff times, location IDs, distance, and fare fields. The official taxi-zone lookup is a CSV keyed by `LocationID`.

Official source: [TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page). The page states that files are monthly, typically delayed by about two months, and may have minor schema changes across years and datasets. It also warns that source submissions may not be fully accurate or complete.

## Implemented prototype

- `apps/api/src/features/tlc_trip_analysis.py` — read-only DuckDB analysis module.
- `scripts/tlc_trip_analysis.py` — CLI that reads official URLs or local paths and emits JSON.
- `apps/api/tests/unit/test_tlc_trip_analysis.py` — deterministic Parquet/CSV fixtures.

Run a bounded smoke test against official files:

```bash
.venv/bin/python scripts/tlc_trip_analysis.py \
  --year 2025 --month 1 --row-limit 10000 \
  --output /tmp/us-362-tlc-report.json
```

For a full month, omit `--row-limit`. For reproducibility and offline validation, pass local paths with `--yellow-path`, `--hvfhv-path`, and `--zones-path`.

## Canonical contract

| Canonical field | Yellow | HVFHV |
| --- | --- | --- |
| pickup/dropoff timestamp | `tpep_*_datetime` | `pickup_datetime` / `dropoff_datetime` |
| pickup/dropoff zone | `PULocationID` / `DOLocationID` | same |
| distance | `trip_distance` | `trip_miles` |
| duration | derived from timestamps when `trip_time` is absent | derived when absent |
| fare | `fare_amount` | `base_passenger_fare` |
| total | `total_amount` | sum of published fare components when absent |

The module uses `union_by_name=true` so additive Parquet columns do not break the read. Required structural fields are fail-closed. Unknown or additive columns are preserved in the schema profile but are not silently interpreted as new analytics fields.

## Quality checks

The report records null counts and flags:

- non-positive or over-24-hour durations;
- negative or over-500-mile distances;
- negative or over-$2,000 fares/totals;
- pickup/dropoff IDs absent from the official zone lookup.

Only rows with usable timestamps, valid zone IDs, non-negative bounded distance, positive bounded duration, and bounded fare are used in the prototype aggregates. Invalid rows remain visible in the quality report rather than being silently discarded.

## Product signal tested

The prototype emits:

1. valid monthly trip, fare, distance, and duration totals;
2. top pickup zones with borough/zone labels and destination diversity;
3. top origin-destination pairs with trip count, distance, duration, and fare totals;
4. an optional comparison against manually supplied TLC aggregate totals.

This is enough to evaluate demand heatmaps, airport/corridor concentration, temporal travel patterns, and fare distributions before investing in production storage, H3 enrichment, or dashboard wiring.

## Risks and next step

This is NYC-regulated taxi/FHV activity, not a complete mobility layer: transit, walking, cycling, private vehicles, and unregulated trips are absent. Monthly publication lag and source revisions make it unsuitable for real-time catalyst alerts without a separate freshness/revision contract. The next decision should be whether the zone/OD outputs demonstrate product value; only then should the team define a production table, H3 mapping, monthly refresh state, and dashboard surface.
