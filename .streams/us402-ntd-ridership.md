# Stream log — us402-ntd-ridership — 2026-08-30

## Claim

- **Stream id:** `us402-ntd-ridership`
- **Leaf files I will create/edit:**
  - `apps/api/src/producers/ntd_spec.py` (SeriesSpec dict)
  - `apps/api/tests/unit/test_ntd_spec.py`
- **Spine files I expect to need:**
  - `apps/api/src/spatial/series_registry.py` (register the spec)
  - `apps/api/src/producers/series_client.py` (add Socrata SODA profile branch)
  - `apps/api/src/producers/scheduler.py` (schedule weekly poll)

## Intent

Define a SeriesSpec-shaped plain dict for the FTA NTD Complete Monthly Ridership
SODA feed (`datahub.transportation.gov/resource/8bui-9xvu`). Keyless, weekly
refresh, ~2-month lag. The spec dict constructs as `SeriesSpec(**spec)` with zero
massaging; the spine phase wires it into `SERIES_REGISTRY` and adds a Socrata
profile branch to `SeriesClient.fetch`. The leaf field constants and the
`ntd_ridership_spec(measure)` factory support all four NTD measures
(UPT/VRM/VRH/VOMS).

## Decisions

- 2026-08-30 — Profile set to `PROFILE_SOCRATA = "socrata"` (new constant) rather
  than forcing the spec into an existing CSV/HUD/Census profile. Explicitly not
  recognized by the current `SeriesClient.fetch`; the spine phase adds the branch.
- 2026-08-30 — `geography_col="uza_name"` with `geography_level="metro"`. City
  resolution from UZA name requires a hand-authorable crosswalk entry per metro
  (the research doc names this as the integration path); the raw SeriesSpec
  declares the column, not the resolution.

## Current step

Phase 1 DONE — leaf files created and tested: `ntd_spec.py` (SeriesSpec dict +
`ntd_ridership_spec(measure)` factory, `PROFILE_SOCRATA` constant) and
`test_ntd_spec.py` (14 tests). `pytest tests/unit/test_ntd_spec.py` green,
ruff clean. Spec is NOT registered anywhere (leaf-first).

## Next step

Spine interlock hold: register the spec in `series_registry.py`, add the Socrata
profile dispatch in `series_client.py`, schedule in `scheduler.py`.