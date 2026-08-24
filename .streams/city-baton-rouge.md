# Stream log — city-baton-rouge — 2026-08-24

## Claim

- **Stream id:** city-baton-rouge
- **Leaf files I will create/edit:** `src/spatial/cities/baton_rouge.py`, `tests/unit/test_producers_baton_rouge.py`
- **Spine files I expect to need:** `src/config.py`, `src/spatial/city_registry.py`, `src/spatial/cities/__init__.py`, `src/serving/dashboard.py`, `apps/dashboard/public/index.html`, `README.md`, `src/export/snapshot_builder.py`, `tests/unit/test_export_snapshot.py`

## Intent

Register Baton Rouge / East Baton Rouge Parish's verified Socrata permits, 311, and business-registry feeds, including snapshot ingestion for the license registry, then wire the city through the dashboard and program scorecard with the interlock gate green.

## Decisions

- 2026-08-24 — Use `brla` as the job suffix and register only the three verified feeds; no market-sales feed was found.
- 2026-08-24 — Use one parish-wide Baton Rouge Core division because the verified contract is parish-scale and does not provide an authoritative submarket roster.
- 2026-08-24 — Business licenses use `extra={"ingestion_mode": "snapshot"}` and no watermark column, as required by D4.

## Current step

Spine wiring is complete; focused contract, snapshot, interlock, and dashboard-copy checks are green.

## Next step

Completed — HAR-22 verification comment posted and Linear issue marked Done.
