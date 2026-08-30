# Stream log — assess-noaa — 2026-08-30

## Claim

- **Stream id:** `assess-noaa`
- **Leaf files I will create/edit:**
  - `docs/research/noaa-climate-validation.md` (required deliverable)
  - `apps/api/src/spatial/noaa_climate.py` (leaf rollup/profiling helper, no spine imports)
  - `apps/api/tests/unit/test_spatial_noaa_climate.py`
  - `.streams/assess-noaa.md`
- **Spine files I expect to need:** none (`docs/agents/spine-manifest.txt` untouched)

## Intent

Produce a validation document (mirroring `epa-echo-validation.md` and
`zbp-validation.md`) that assesses NOAA NCEI Climate Data Online as a
disruption-context layer for five registered metros (Chicago, Houston, Miami-Dade,
Denver, Los Angeles), probing the token-gated v2 API, the no-token bulk GHCND
Daily / GSOD fallbacks, station metadata, freshness, and observation-time
conventions, and confirming that a spine-free leaf helper can select nearby
stations, profile per-variable missingness, and map daily observations onto the
repo's H3 res 7/8/9 units. Delivered verdict: ADOPT / DEFER / REJECT with
token, rate-limit, and station-density risks mapped.

## Decisions

- <2026-08-30> Live probes succeeded: CDO v2 API is token-gated (HTTP 400 "Token
  parameter is required." on `/datasets`, `/stations`, `/data`); no token present
  in env or settings. No-token bulk paths confirmed live: GHCND per-station CSVs
  under `.../global-historical-climatology-network-daily/access/` (LAX + ORD HTTP
  200, LAX data through 2026-08-27 ≈ 1–3-day lag), `ghcnd-stations.txt` inventory
  (129,657 stations), GSOD yearly archives (1929–2025). Docs page confirms 5
  req/s, 10,000 req/day limits.
- <2026-08-30> Five registered metros selected for the doc: Chicago, Houston,
  Miami-Dade, Denver, Los Angeles (diverse climate families). Airport GHCND IDs
  confirmed in inventory and inside each metro bbox.
- <2026-08-30> Verdict: **ADOPT (bulk path) / DEFER (API path)** — the token-gated
  v2 API is unsuitable as a primary automated ingest (rate limits), but the
  no-token GHCND per-station CSV fallback is verified live, fresh, and covers all
  ticket variables; integration still needs a spine decision (new context family).

## Current step

Done. Validation doc, leaf module, and unit test all written and passing.

## Next step

(No next step — stream complete. Report back to the ticket.)
