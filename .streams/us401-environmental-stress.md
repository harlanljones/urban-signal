# Stream log — us401-environmental-stress — 2026-08-30

## Claim

- **Stream id:** us401-environmental-stress
- **Leaf files I will create/edit:**
  - `apps/api/src/producers/environmental_stress_client.py` (create)
  - `apps/api/tests/unit/test_environmental_stress_client.py` (create)
- **Spine files I expect to need:** NONE — leaf-only phase
  - Confirmed: no edits to config.py, city_registry.py, series_registry.py, scheduler.py, or any spine-manifest file

## Intent

Build thin keyed/keyless HTTP clients for five environmental-stress data sources
(AirNow AQI, USDM drought, NOAA Storm Events, USGS NWIS stream gauges, NOAA
tide gauges), parse their responses into H3-tagged covariate observations, and
test parsing/H3-mapping logic with fixture data. All output is
`EnrichedH3Feature`-style context covariates; no new event schemas, no spine
edits. The Storm Events client reuses the CSVClient/SNAP bulk-CSV pattern from
sba_client.py. Tide gauges limited to coastal metros.

## Decisions

- 2026-08-30 — All five clients in one leaf module; no new event schemas, only covariate output
- 2026-08-30 — AirNow uses the API key from AIRNOW_API_KEY env var (not the existing airnow_signal.py which uses the free reportingarea.dat product)
- 2026-08-30 — StormEventsClient reuses _normalize_header from src.producers.csv_client, same pattern as sba_client.py
- 2026-08-30 — USDM uses the JSON endpoint (not shapefile); the live `usdm_current.json` is a GeoJSON FeatureCollection, one feature per DM category 0–4 (NOT county-keyed), so we do H3 areal intersection over the polygons via h3.h3shape_to_cells (zero new raster machinery)
- 2026-08-30 — NWIS bbox query per metro, parameter 00060 (streamflow), no key required; bBox order is west,south,east,north = min_lng,min_lat,max_lng,max_lat (verified live 200 on NYC box)
- 2026-08-30 — Tide gauges: coastal city_id → NOAA station id map; per-station datagetter API, water_level, datum=MSL, units=metric, time_zone=gmt (verified live on 9414290 SF)
- 2026-08-30 — AirNow zipCode current/forecast endpoints probed live: 401 without key, "Invalid API key" with a bogus key → key-gated confirmed; parsers written from documented shapes, live probes marked @pytest.mark.live
- 2026-08-30 — StormEvents CSV verified live: d2026_c20260819 URL 200, gzip, 51 cols with BEGIN_LAT/BEGIN_LON/EVENT_TYPE/DAMAGE_PROPERTY
- 2026-08-30 — Registered `live` pytest marker in apps/api/pyproject.toml (leaf file, not spine) so @pytest.mark.live doesn't warn

## Current step

DONE — all leaf work complete and verified.

## Next step

Spine-bound producer wiring (orchestrator's responsibility — out of scope for this leaf).