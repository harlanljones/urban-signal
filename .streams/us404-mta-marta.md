# Stream log — us404-mta-marta — 2026-08-30

## Claim

- **Stream id:** `us404-mta-marta`
- **Leaf files I will create/edit:**
  - `apps/api/src/producers/mta_gtfs_rt_client.py`
  - `apps/api/src/producers/marta_spec.py` (DatasetSpec dict)
  - `apps/api/tests/unit/test_mta_gtfs_rt_client.py`
  - `apps/api/tests/unit/test_marta_spec.py`
- **Spine files I expect to need:**
  - `apps/api/src/spatial/city_registry.py` (FeedType, DatasetSpec per city)
  - `apps/api/src/producers/scheduler.py` (schedule MTA/MARTA polls)
  - `apps/api/src/schemas/models.py` (EnrichedH3Feature transit covariate fields)

## Intent

Two leaf modules:

1. **MTA GTFS-RT client** — thin protobuf poll of MTA NYC subway service alerts
   (`api-endpoint.mta.info`, keyless). Decodes GTFS-RT protobuf via dynamically
   constructed descriptors (no `gtfs-realtime-bindings` dependency). Computes
   per-station service reliability index from alert severity weights (planned=1,
   delay=2, partial=3, full=5) and disruption impact (POI count within 800m of
   affected stations). Uses the installed `protobuf` runtime only.

2. **MARTA spec** — DatasetSpec-shaped plain dict for the Atlanta station
   entrances/exits Socrata feed (`data.atlantaga.gov/resource/nwqk-3q5y`).
   Keyless, weekly refresh. Zero new machinery (SocrataClient + DatasetSpec).

Both → EnrichedH3Feature context covariates. No new event schema.

## Decisions

- 2026-08-30 — MTA protobuf: descriptor built dynamically in `_gtfs_rt_descriptor()`
  and cached. This avoids a `gtfs-realtime-bindings` dependency while using the
  already-installed `protobuf` runtime. Only the subset of the GTFS-RT schema
  needed for alerts (FeedMessage → FeedEntity → Alert → TimeRange,
  EntitySelector, TranslatedString) is included.
- 2026-08-30 — MARTA spec: `watermark_col=""` with `ingestion_mode="snapshot"`
  — the feed has no `:updated_at` watermark. Full pull, churn via snapshot diff.
  Freshness rides Socrata `rowsUpdatedAt`.

## Current step

Phase 1 DONE — all four leaf files created and tested:
- `mta_gtfs_rt_client.py` (dynamic GTFS-RT protobuf descriptor, `MtaGtfsRtClient`
  with fetch→decode→classify→reliability→index pipeline, ~290 lines)
- `marta_spec.py` (DatasetSpec-shaped plain dict for Atlanta MARTA Socrata feed)
- `test_mta_gtfs_rt_client.py` (7 tests: decode, severity weights, per-station
  classification, reliability index)
- `test_marta_spec.py` (7 tests: construct-as-DatasetSpec, keyless, snapshot,
  weekly cadence, endpoint)
`pytest tests/unit/test_mta_gtfs_rt_client.py tests/unit/test_marta_spec.py`
green, ruff clean.

## Next step

Spine interlock hold: register MARTA DatasetSpec in city_registry, add MTA client
to scheduler, add transit covariate fields to EnrichedH3Feature.