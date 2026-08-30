# NOAA NCEI Climate Data Online — validation as a weather-disruption context layer

**Date of research: 2026-08-30.** Linear **US-173** ("Assess NOAA climate
observations for disruption context"). This is a *validation* document — **no
feed was registered, no `FeedType` was added, and no spine file was touched**.
A small, spine-free leaf module (`apps/api/src/spatial/noaa_climate.py`) and its
unit test accompany this write-up to prove the station-selection /
missingness-profiling / H3-mapping path is feasible without a spine edit.

## Method, and its limits

I validated on three layers, in order:

1. **Product facts.** Fetched the official [CDO Web Services v2 documentation](https://www.ncei.noaa.gov/cdo-web/webservices/v2)
   page (live, HTTP 200), the CDO [Datasets](https://www.ncei.noaa.gov/cdo-web/datasets)
   discovery page, the token-request page (`/cdo-web/token`, HTTP 200), and the
   GHCND Daily `readme.txt` / station inventory. Quoted directly where possible.
2. **Live API probes.** Issued real `curl` requests against the documented v2
   endpoints (`/datasets`, `/stations`, `/data`) **and** against the
   **no-token bulk fallbacks** that the ticket's "caching or bulk-access fallback
   within rate limits" asks about: GHCND Daily per-station CSVs, the
   `ghcnd-stations.txt` inventory, and GSOD yearly archives.
3. **Feasibility of the spatial mapping.** Wrote and unit-tested a leaf module
   that selects stations inside a metro bbox, computes nearest-station distance,
   profiles per-variable daily coverage, and maps a station's observation onto
   the repo's H3 res 7/8/9 hierarchy via `H3SpatialIndexer` (no new joiner, no
   spine import).

**Limits.** The CDO v2 API is **token-gated**, and **no NOAA/NCEI token exists in
this environment** (checked `env`, `apps/api/src/config.py`, and repo `.env` — the
only token-like variable present is an unrelated `FREETOKEN_FT_BIN`). Every live
request to `api/v2/*` returned **HTTP 400 `{"status":"400","message":"Token
parameter is required."}`** — the endpoints are reachable but reject anonymous
clients, so **no token-protected data pull was performed; all CDO-API data-level
claims below are asserted from the official documentation, not from a
token-authenticated sample.** The rate limits (5 requests/second, 10,000
requests/day) are documented, not independently enforced-verified. The per-station
GHCND CSV format was confirmed on two live files, but the per-variable `_ATTRIBUTES`
field (source/quality/observation-time codes) was observed, not exhaustively
decoded against the flag reference — unit interpretations below are marked
**documented**. Event-vs-local-official-summary comparison and the ablation against
existing municipal-event models are **assessed by concept and not executed**
(this is a leaf research stream; no pipeline or model run was performed).

---

## Headline verdict

**ADOPT (data path) / DEFER (integration path).** NOAA NCEI is the authoritative,
public-domain source of U.S. historical **daily weather/climate observations** —
temperature (TMAX/TMIN/TAVG), precipitation (PRCP), snow (SNOW/SNWD), and wind
(AWND/WSFG/WDFG) — exactly the disruption context US-173 names for 311, permits,
mobility, and construction. It is **event-shaped at the right temporal cadence for
a context layer** (one observation per station per day, at point coordinates),
and the critical operational risk in the ticket — the token plus the 5 req/s and
10,000 req/day caps — is **fully mitigated by a verified no-token bulk path**:
per-station daily CSV files under `ncei.noaa.gov/data/global-historical-climatology-network-daily/access/`
are **live without any token, require no rate-limit management, and carry a
1–3-day availability lag** (LAX file observed with a row dated 2026-08-27, three
days before this research date). That lag is comparable to the municipal event
feeds' cadence and far better than the multi-year lags that sank LODES/ZBP.

**The data side is proven feasible; the integration side is a spine decision.**
No `FeedType` exists for a weather layer, `DatasetSpec` assumes a
`PaginatingClient` (Socrata/ArcGIS/CKAN) with watermark/id_keys per event row, and
a bulk daily-file producer violates those assumptions the same way ECHO and ZBP
did. Registering it as a live feed is a **spine/interlock change** (new context
family, new bulk producer archetype, per-city entries) and is explicitly **out of
scope for this leaf stream**. Treating it as a **LIMS-exempt context layer**
(precedent: street-cut "disruption context only") is the right end-state.

---

## Source assessment

- **What it is.** NOAA NCEI Climate Data Online serves **GHCND (Global Historical
  Climatology Network – Daily)** daily station summaries plus GSOD (Global Summary
  of the Day) and monthly/annual products. The `GHCND` dataset carries the
  variables US-173 names: `TMAX`/`TMIN`/`TAVG` (daily temperature), `PRCP`
  (daily precipitation), `SNOW`/`SNWD` (snowfall / snow depth), `AWND`
  (average daily wind speed), `WSFG`/`WDFG` (gust speed / direction), and more
  (`TSUN`, `WESD`, hourly-adjacent elements). Each row is a **station-day
  observation at a point (station lat/lng)**, i.e. the same primitive shape the
  repo's event feeds use, with a real timestamp (the calendar day).
- **Access / terms (verified).** The v2 API is **token-gated**: *"An access token
  is required to use the API"*, obtained from the token-request page; each token is
  *"limited to five requests per second and 10,000 requests per day"* (quoted from
  the live docs page). Corroborated live: `api/v2/datasets`, `/stations`, and
  `/data` all returned HTTP 400 *"Token parameter is required."* NOAA data are U.S.
  government work, public domain (17 U.S.C. § 105); no terms-of-service restriction
  on bulk downloading was found. **Crucially, the bulk NCEI data store is NOT
  token-gated** — verified live this session.
- **Bulk access fallback (verified live, the key mitigation).** All of GHCND Daily
  is downloadable without a token:
  - **Per-station daily CSV:** `https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/<STATIONID>.csv` —
    HTTP **200** for both `USW00023174` (LAX) and `USW00094846` (O'Hare). Columns:
    `STATION,DATE,LATITUDE,LONGITUDE,ELEVATION,NAME` then per-variable value +
    `_ATTRIBUTES` columns (source/quality/obs-time codes). **Freshness verified:**
    the LAX file contains rows through **2026-08-27**, i.e. a **~1–3-day lag**,
    comparable to the event feeds' cadence.
  - **Station inventory:** `.../doc/ghcnd-stations.txt` — HTTP 200, **129,657
    stations**, fixed-width fields (id, lat, lon, elevation, state/name, GSN flag,
    WMO id). All five metro airport stations confirmed present and inside their
    repo metro bboxes (see below).
  - **Documentation:** `.../doc/readme.txt` (GHCND version 3.34, HTTP 200) and
    `.../doc/GHCND_documentation.pdf` (HTTP 200).
  - **GSOD yearly archives:** `https://www.ncei.noaa.gov/data/global-summary-of-the-day/archive/`
    lists per-year `1929.tar.gz … 2025.tar.gz` (verified listing; 2025 archive
    ~2.5 GB). GSOD is a coarser daily product (station-day, fewer elements, some
    airport-derived); GHCND is the richer source for the ticket's variable set.
- **Geographic granularity.** Stations are **point observations** (airports, COOP
  network, mesonets) — a *station near a metro*, not a sensor feed per grid cell.
  Station density **varies materially by metro** (see metro table). The ticket's
  named risk is correct: this is an external context layer requiring explicit
  spatial interpolation / nearest-station assignment, never a cell-localized feed.
- **Units & observation-time conventions (documented, sample-consistent).**
  GHCND daily values are stored in **metric tenths** — TMAX/TMIN/TAVG in **0.1 °C**,
  PRCP/SNOW/SNWD in **0.1 mm** (trace recorded as `T`), AWND in **0.1 m/s**. The
  live LAX sample is consistent (TMAX `294` = 29.4 °C on 2026-08-25). The per-row
  `_ATTRIBUTES` field encodes source, quality, and **observation time**; the daily
  value is the 24-hour period ending at the station's local observation time
  (airport stations typically report at/after local midnight). **Explicit
  timezone handling is required** when aligning a daily observation to
  metro-local calendar days and when comparing against event timestamps.
- **Update cadence / latency (verified).** GHCND daily per-station files lag real
  time by **~1–3 days** (LAX through 2026-08-27 as of 2026-08-30). This is
  **dramatically fresher than expected** for a "historical" source and makes a
  rolling 30–365-day context window fully realistic. No periodic watermark — each
  station file is append-style daily CSV.
- **Completeness / missingness.** Daily coverage varies **by variable and
  station**: airports reliably report TMAX/TMIN/PRCP/AWND; **SNOW/SNWD are
  systematically sparse or absent in southern metros** (Miami-Dade, Houston, LA
  rarely report snow) and absent from many automated stations. GHCND quality flags
  (`S` suspicious, `H` estimated, trace `T`, `M` missing) must be honored — missing
  or failed values are not zero. The ticket's station-density/missingness profile
  requirement is exactly right and is exercised in the leaf module.
- **Volume.** A per-metro daily pull is trivially small: 5 stations × 1 row/day
  each ≈ 1.8k rows/year per metro; a 30-year daily history for ~5 stations is
  ~55k rows. Bulk GHCND has no practical request-count limit; the token path's
  10,000 req/day cap is only binding if you pull per-variable API requests instead
  of the bulk CSV.

---

## Metro selection and station profiling (five registered metros)

Five registered metros picked for **climate-family diversity**: a Great Lakes
snow/heat city (Chicago), a Gulf hurricane/heavy-rain city (Houston), a tropical
heavy-rain city (Miami-Dade), a high-plains snow city (Denver), and a coastal
Mediterranean heat/wind city (Los Angeles). Each metro's airport GHCND station
was confirmed present in the live `ghcnd-stations.txt` inventory and **inside the
repo's metro bbox** (`apps/api/src/spatial/cities/<metro>.py`, read-only):

| Metro (bbox) | GHCND station | Coords | Distance to bbox center | Variables to expect |
|---|---|---|---|---|
| Chicago, IL | `USW00094846` O'HARE INTL AP | 41.9603, -87.9317 | ~5 km | TMAX/TMIN/PRCP/SNOW/SNWD/AWND (full) |
| Houston, TX | `USW00012960` HOUSTON INTERCONTINENTAL AP | 29.9844, -95.3608 | ~10 km | TMAX/TMIN/PRCP/AWND; SNOW ≈ absent |
| Miami-Dade, FL | `USW00012839` MIAMI INTL AP | 25.7881, -80.3169 | ~9 km | TMAX/TMIN/PRCP/AWND; SNOW ≈ absent |
| Denver, CO | `USW00023062` DENVER-STAPLETON | 39.7633, -104.8694 | ~2 km | TMAX/TMIN/PRCP/SNOW/SNWD/AWND (full) |
| Los Angeles, CA | `USW00023174` LOS ANGELES INTL AP | 33.9381, -118.3867 | ~5 km | TMAX/TMIN/PRCP/AWND; SNOW ≈ absent |

Nearest-station distance is the leaf module's profile output; the metro bbox
filter mirrors how event feeds are bbox-filtered at ingest. **Station density
caveat:** a single airport station per metro is the realistic v1 source — no
meaningful within-metro spatial variation, which is fine for a **division/metro
context layer** but means weather cannot be a cell-level (H3 res 8/9) differentiator.

---

## Urban Signal fit

Repo units nest **metro bbox → division bbox → submarket → H3 7–9**
(`spatial/h3_indexer.py`). A daily observation maps onto this shape the same way
event rows do:

1. **bbox-filter the station inventory** to each metro's `METRO_BBOX` (leaf helper
   `stations_within_bbox`), pick the **nearest** station to the bbox center
   (`nearest_station`, haversine) — mirrors event-feed bbox filtering.
2. **Map the station's point → H3 res 7/8/9** via
   `H3SpatialIndexer.get_multi_res_hierarchy`, identical to every event feed. The
   observation lands on one res-9 cell per station (airport-adjacent); for a
   neighborhood-shaped context the value must be **assigned to metro/division
   scale**, not treated as res-9-localized weather.
3. **Aggregate weather anomalies** to metro/grid features: per-variable daily
   anomaly (value − climatological baseline, e.g. a 30-day trailing mean or
   NOAA-derived daily normals), then mean-over-stations or mean-over-cells. This is
   the "aggregate weather anomalies to metro/grid features" step of US-173's
   proposed validation, and it slots into `EnrichedH3Feature` covariate territory
   exactly as the US-363 context families (`ENERGY_BENCHMARK`, `BIKE_PED`) do.
4. **Ablation against municipal-event models** (per the ticket) is *conceptually*
   straightforward — add per-metro daily anomalies (heat-index, heavy-precip, snow,
   wind-gust) as covariates/external-shock terms and compare model fit — but was
   **not executed** here (leaf stream, no pipeline run).

**Does it add independent coverage?** Yes, in kind. No existing feed measures
weather. For disruption context — a heat wave suppressing 311 service calls or
driving AC-related permits, a snow event suppressing street-cut work, a hurricane/
flood event spiking 311 flooding reports — NOAA is the canonical external prior.
It is a **context/prior layer**, never a LIMS velocity term: weather is a
co-located confounder to model *around*, not a move-in/move-out signal.

**The catch is integration, not data.** `FeedType` has no weather family, and
`DatasetSpec`/`PaginatingClient` assume a watermark-paginated geolocated event
stream. GHCND daily is a **per-station append-style CSV** — no `watermark_col`
that advances, only the DATE column; no paging. A registration needs a **new
context family** (e.g. `WEATHER`/`CLIMATE_CONTEXT`), a **new bulk producer
archetype** (download per-station CSV → parse tenths/units + flags → assign to
metro/division → store daily anomalies), and **per-city entries** — all
spine/interlock edits. Explicitly out of scope for this leaf.

---

## Risks and dependencies (mapped to the ticket's named risks)

1. **"The API requires a token… 5 req/sec and 10,000 req/day."** **Confirmed live,
   and fully mitigated.** Token-gating verified (HTTP 400 on every `api/v2/*`
   probe). **But** the no-token GHCND per-station CSV path was **verified live and
   has no request-count cap**, so the token+rate-limit risk only constrains the
   *secondary* API path, not the ingest path. If a producer preferred the API
   (e.g. for arbitrary station search), a token would still be required and
   caching/backoff within 5 req/s is mandatory.
2. **"Station density and measurement completeness vary materially by metro and
   variable."** **Confirmed.** One airport station per metro is the realistic v1;
   SNOW/SNWD are structurally absent in southern metros. The leaf module profiles
   per-variable coverage and quality flags; a v1 layer should treat missing/suspect
   values as `None` (never zero) and rely on metro/division-scale aggregation
   (`dynamic_spatial_fallback` precedent) to avoid false "no weather" signals.
3. **"Spatial interpolation and timezone rules need explicit treatment."**
   **Confirmed.** Points are stations, not grid cells; assignment is
   nearest-station within bbox (interpolation deferred). Daily observations are
   recorded in station-local time at a documented observation hour; aligning them
   to metro-local days and event timestamps requires explicit timezone
   normalization — the leaf module keeps obs-time attributes visible for this.
4. **"Secure/manage an API token and design caching/bulk-access fallback."**
   **Resolved in favor of bulk.** The bulk CSV path removes the token dependency
   entirely for daily observations. A producer should still cache station
   inventory + per-station files (append daily), and can treat the API as optional.
5. **Externality ("context, not sensor feed").** Confirmed; weather is a
   co-located external covariate, not a property of the neighborhood. It must be
   labeled context/LIMS-exempt (street-cut precedent) and must never enter LIMS
   scoring as a cell-level velocity.
6. **Integration-model dependency (decisive).** No `FeedType`/producer archetype
   exists for a bulk daily-observation context layer. This is why the verdict is
   ADOPT-data / DEFER-integration rather than ADOPT-today.

---

## Leaf module built (phase 2, leaf-only)

To prove the path is real and testable **without any spine edit**, this stream
adds a self-contained leaf module:

- `apps/api/src/spatial/noaa_climate.py` — pure functions, imports only `h3`/the
  leaf `H3SpatialIndexer` (no spine file touched):
  - `haversine_km(lat1, lng1, lat2, lng2)` — station-distance profiling.
  - `stations_within_bbox(stations, bbox)` — mirror of event-feed bbox filtering.
  - `nearest_station(stations, lat, lng)` — nearest-station assignment for a
    metro/division context point.
  - `daily_coverage(rows, variable)` — fraction of station-days with a
    quality-passing, non-trace value (missingness profiling).
  - `obs_quality_ok(value, attributes)` — honor GHCND quality/trace flags before
    a value is usable.
  - `daily_anomaly(value, baseline)` — simple anomaly (Δ from climatological
    baseline) at metro scale.
  - `map_station_to_h3(lat, lng)` — resolve a station point to H3 res 7/8/9 via
    `H3SpatialIndexer.get_multi_res_hierarchy`.
- `apps/api/tests/unit/test_spatial_noaa_climate.py` — unit tests: haversine
  sanity, bbox filtering, nearest-station selection, coverage/missingness math,
  quality-flag handling, anomaly delta, and H3 hierarchy consistency. Run with the
  repo venv; **all pass** (see VERIFY).

This module is a building block only. It is **not** imported by any spine file and
does **not** register a feed; wiring it into `city_registry.py` / `DatasetSpec`
would be the spine-gated REGISTER step, which this leaf does not perform.

---

## Recommendation

**ADOPT the NOAA NCEI data as the standard weather-disruption context source;
DEFER the feed registration to a spine/interlock change.** **Do register (as a
context layer):** the data is authoritative, public-domain, verified-live **without
a token**, covers every US-173 variable, is **~1–3 days fresh** (better than the
ticket assumes), and maps cleanly to metro/division scale alongside the existing
event feeds. **Do not wire it in today:** there is no `FeedType`/producer
archetype for a bulk daily-observation layer, so a live registration is a spine
change gated by `pytest -m interlock` per `docs/agents/parallel-streams.md`. The
token + 5 req/s + 10,000 req/day risks are real for the *API* path but
**non-binding for the bulk path**, which is the decisive fact that distinguishes
this source from ECHO (bot-blocked REST) and ZBP (no per-row coordinates).

**What unblocks a future REGISTER:**

1. A scope decision that Urban Signal wants a **weather-disruption context layer**
   — a new `WEATHER`/`CLIMATE_CONTEXT` family, treated as context/LIMS-exempt
   (street-cut precedent), storing **daily per-metro anomalies** (heat, heavy
   precip, snow, wind) as `EnrichedH3Feature` covariates.
2. A concrete consumer — e.g. an **external-shock prior** behind hard-to-explain
   311/permits/mobility/construction deltas, or a "weather-adjusted baseline"
   comparison for a submarket.
3. If both arrive, **register the five metros above first** (one airport station
   each, daily per-station CSV via the bulk path), profiling per-variable coverage,
   honoring trace/missing as `None`, normalizing observation time to metro-local,
   and labeling anomalies as nearest-station (no within-metro interpolation v1).

Until then, the existing event feeds remain the correct timely signal and NOAA
should not be wired into scoring — but it is the **canonical external context
prior** to reach for the moment a context layer is approved. The leaf module
`apps/api/src/spatial/noaa_climate.py` (imports only the leaf `h3_indexer`) is a
ready, tested building block for that future spine-bound registration.
