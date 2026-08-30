# Stream log — us400-noaa-weather — 2026-08-30

## Claim

- **Stream id:** `us400-noaa-weather`
- **Leaf files I will create/edit:**
  - `apps/api/src/producers/noaa_weather_client.py` (create)
  - `apps/api/tests/unit/test_noaa_weather_client.py` (create)
- **Spine files I expect to need:** NONE — leaf-only phase
  - Confirmed: no edits to config.py, city_registry.py, series_registry.py, scheduler.py, or any spine-manifest file

## Intent

Build two thin HTTP clients (GhcnDailyClient, NwsWeatherClient) for NOAA weather
sources — GHCN-D daily station summaries (TMAX/TMIN/PRCP, keyless JSON via
`access/services/data/v1`) and NWS api.weather.gov (forecast + alerts per
gridpoint). Both parse responses into H3-tagged covariate observations, using
the existing `noaa_climate.py` station-selection/H3-mapping helpers. No new
event schemas, no spine edits. Unit tests use fixture data (live endpoints may
not be reachable from the sandbox).

## Decisions

- <2026-08-30> Both clients defined in one leaf module; output is a
  `WeatherObservation` dataclass with H3 hierarchy + source + weather fields.
- <2026-08-30> GhcnDailyClient uses `access/services/data/v1?dataset=daily-summaries`
  (keyless JSON, verified live in US-173 research). The per-station CSV path is
  the fallback; the client exposes `station_csv_url` for callers who prefer it.
- <2026-08-30> NwsWeatherClient resolves lat/lon → gridpoint via
  `/points/{lat},{lon}`, then follows the `forecast` and `alerts/active` links.
  Both are keyless.
- <2026-08-30> Station→H3 crosswalk reuses `map_station_to_h3` from
  `noaa_climate.py` directly. No duplicate H3 logic.
- <2026-08-30> Tests use httpx.MockTransport for fixture responses; no live
  network calls.
- <2026-08-30> Live probes confirmed the shapes the fixtures trim: GHCN-D
  daily-summaries (O'Hare 2026-08-20..27) is a JSON list of padded-string
  tenths (TMAX 256 = 25.6 °C); `ghcnd-stations.txt` is 132,501 fixed-width
  lines (ID 1-11, lat 13-20, lon 22-30, elev 32-37, name 42-71); NWS
  `/points/{lat},{lon}` carries the `forecast` URL; `/alerts/active?point=`
  works and carries `event`/`severity`. The daily-summaries JSON has no
  `_ATTRIBUTES` columns, so the quality-flag gate reads them when present and
  passes otherwise.
- <2026-08-30> NWS sends an identifying `User-Agent` (NWS policy) on every
  request; GHCN-D is plain. Both raise a single readable `WeatherFetchError`.
- <2026-08-30> Covariate shape: `WeatherCovariate` dataclass — GHCN fills
  tmax_c/tmin_c/prcp_mm, NWS fills forecast_max_temp_f/precip/periods +
  alert_count/max_severity/events; fields a source doesn't measure stay
  None/0 so the two folds merge additively.

## Current step

DONE. Leaf module + tests written, ruff clean, 30/30 tests pass.

## Next step

(No next step — stream complete. Report back to the ticket; work left
uncommitted for the orchestrator's spine wiring.)