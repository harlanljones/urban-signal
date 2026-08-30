# AirNow + AQS — validation as environmental-stress signals for short-lived market disruption

**Date of research: 2026-08-30.** Linear **US-390** ("Validate AirNow and AQS
environmental-stress signals"). This is a *validation* document — no feed was
registered, no `FeedType` was added, and no spine file was touched. A small,
spine-free leaf module (`apps/api/src/spatial/airnow_signal.py`) and its unit
test accompany this write-up to prove the reporting-area→H3 and shock-feature
mapping is feasible without a spine edit.

## Method, and its limits

I validated on three layers, in order:

1. **Product facts.** Read AirNow's live docs pages (Home, Web Services, FAQ)
   and AQS's live API documentation page (`aqs.epa.gov/aqsweb/documents/data_api.html`).
   These are EPA's own descriptions of program coverage, the preliminary-vs-validated
   distinction, latency, and rate limits — quoted, not reconstructed from memory.
2. **Live API probes.** Issued real `curl` requests against both machine
   interfaces. **AQS** was probed with the *documented test key*
   (`email=test@aqs.api&key=test`): `metaData/isAvailable`, `list/states`,
   `monitors/byBox`, `sampleData/byBox`, and `dailyData/byBox` all returned live
   data. **AirNow** was probed two ways: the keyed REST endpoints
   (`www.airnowapi.org/...`) returned **HTTP 401** without a key (confirmed
   key-gated), but the **public file product** `reportingarea.dat` at
   `https://files.airnowtech.org/airnow/today/reportingarea.dat` downloaded
   **without any authentication** (HTTP 200, 1.99 MB, 6,841 rows, 892 distinct
   reporting areas, 16 pollutants) — this is the credential-free real-time
   observation path.
3. **Feasibility of the spatial mapping.** Wrote and unit-tested a leaf module
   that parses one `reportingarea.dat` row, maps the reporting area's point
   coordinate to the repo's H3 res 7/8/9 hierarchy via the existing
   `H3SpatialIndexer`, and derives a smoke/shock AQI feature (no new joiner, no
   spine import).

**Limits.** No non-production API credential was available in this environment
for the keyed AirNow REST endpoints, so per-station AirNow JSON field shapes are
asserted from documentation and from the live `reportingarea.dat` file product,
**not** from a credentialed REST response. AQS probing used the public
documentation test key, which is rate-limited and not a real account: only a
bounded number of queries was made and only 2023–2025 data was confirmed
reachable (a 2026-08 window returned "No data matched your selection" — AQS lags
current observations by roughly a year, consistent with the documented 6+-month
validation lag; the test key itself may also cap the window). "Incremental value
against current signals" is assessed by *concept* against the repo's feed
families, not by running an ablation (this is a leaf research stream; no
pipeline was run). The AirNow/AQS revision reconciliation (preliminary → validated
corrections) is quantified from the *documented* revision mechanism and the
`date_of_last_change` field shape in a live AQS response, not from a real
30-day AirNow-vs-AQS paired sample — the ticket's proposed 30-day ingestion
remains unimplemented (needs a credential + a real account).

---

## Headline verdict

**ADOPT-as-context — DEFER as a feed registration.** AirNow real-time
observations and the AQS validated archive are together a genuine, distinctive,
credential-gated-but-accessible source of **environmental-stress features
(air-quality shocks)** that **no existing Urban Signal feed measures**, and —
critically — they are the *only* current/repo-relevant source whose near-real-time
layer (AirNow) can drive a **short-lived shock** (wildfire smoke, inversion, ozone
episode) and whose delayed layer (AQS) supplies the **retrospective truth set** to
validate it. The data side is **proven live**, not just documented: the AQS test
key returned real monitor metadata and daily data, and AirNow's `reportingarea.dat`
is downloadable anonymously with per-reporting-area point coordinates and AQI
values for the registered metros (Los Angeles, Houston, New Orleans, Tyler etc.
all present). The spatial mapping is **trivially feasible**: reporting areas and
monitors both carry point lat/lng, so `H3SpatialIndexer.get_multi_res_hierarchy`
maps them to H3 7–9 exactly like the event feeds, and the repo's
`dynamic_spatial_fallback` is precisely the smoothing sparse monitor coverage
needs (Tyler has **1** PM2.5/O₃ monitor; LA **13**; Houston **31**).

**But it cannot be registered as a `FeedType` by a leaf stream.** The decisive
reason is the same three-part integration gap seen in the ECHO and ZBP
validations: AirNow/AQS are **keyed, non-paginating REST/file** sources (AQS
`email`+`key` on every call; AirNow REST key-gated, with the useful real-time
layer being a twice-hourly anonymous file product) — none of which matches the
`PaginatingClient` (Socrata/ArcGIS/CKAN) producer archetype the registry assumes.
A real registration needs a **new context-measurement family** (the
`ContextObservationEvent` covariate tier, `period_type="hour"`/`"day"`), a new
**keyed-API + file-product producer**, and per-metro or national registry
entries — all spine/interlock edits gated by `pytest -m interlock`. It also
carries three named risks that must be engineered around before any scoring:
**credential management**, **monitor-coverage / spatial-assignment policy**
(no-interpolation baseline for sparse metros), and **strict AirNow-vs-AQS
separation** (preliminary values must never be conflated with validated history).
None of those is a data-availability blocker; all are integration decisions.

So the honest verdict is **ADOPT the signal as a context/anchor layer when a
context-family registration is approved; DEFER the feed registration now** (leaf
stream cannot do it). This is the *strongest* context-source candidate in the
repo's context-measurement tier (US-363) because the live AirNow layer is the only
one that is **near-real-time** — unlike energy-benchmark (annual), Zillow/FHFA
(monthly, revised), and AQS itself (year-lagged).

---

## Source assessment

### AirNow

- **What it is.** EPA's public-facing, near-real-time AQI service. Per the AirNow
  API home page: *"AirNow receives real-time air quality observations from over
  2,500 monitoring stations and collects forecasts for more than 500 cities."*
  Data come from "more than 150 local, state, tribal, provincial, and federal
  government agencies." **Coverage is US + Canada + Mexico.**
- **Preliminary — the central caveat.** AirNow's home page states verbatim:
  *"These data are not fully verified or validated and should be considered
  preliminary and subject to change. Data and information reported to AirNow are
  for the express purpose of reporting and forecasting the AQI. As such, they
  should not be used to formulate or support regulation, trends, guidance, or any
  other government or public decision making. Official regulatory air quality data
  must be obtained from EPA's Air Quality System (AQS or AirData)."* **This is the
  ticket's named "AirNow-vs-AQS separation" risk, and EPA itself states it.**
  Any feature built on AirNow must be labeled preliminary and reconciled against
  AQS before use as a retrospective truth.
- **Access / credentials.** The REST **web services are key-gated**: probing
  `https://www.airnowapi.org/aq/observation/zipCode/current/?format=application/json&zipCode=90012&distance=25`
  returned `{"WebServiceError":[{"Message":"Request not authenticated."}]}` with
  **HTTP 401**. Keys are issued via the AirNow "Request an API Account" page
  (email-gated; no key was available in this sandbox). **However**, the FAQ
  explicitly steers database-builders to the **file products** on
  `files.airnowtech.org`, which are **public, anonymous, and credential-free** —
  verified live this session:
  - `https://files.airnowtech.org/airnow/today/reportingarea.dat` → **HTTP 200**,
    1.99 MB, updated "twice per hour at :55 and :25" (FAQ, verbatim).
  - `cityzipcodes.csv` → **HTTP 200** (City|State|Zipcode|Latitude|Longitude),
    the reporting-area↔ZIP crosswalk the FAQ recommends for zip lookup.
  The FAQ's recommendation, verbatim: *"If your objective is to maintain a
  database of zip code-based forecasts or observations... we recommend you use
  the following file outputs from the AirNow system: reportingarea.dat..."*
  So **the realistic ingestion path is the public file product, not the keyed
  REST API** — a *file-product* producer archetype, not `PaginatingClient`.
- **File format (verified live).** `reportingarea.dat` is pipe-delimited, 17
  columns. Live rows:
  `08/30/26|08/29/26||CDT|-1|Y|Y|Aberdeen|SD|45.4680|-98.4940|PM10|16|Good|No||South Dakota...`
  Column semantics observed: (1) current date, (2) valid date, (3) hour,
  (4) timezone, (5) day offset, (6) row type (`O`=observed, `F`=forecast,
  `Y`=yesterday), (7) primary/action-day flag (`Y`/`N`), (8) reporting-area name,
  (9) state, (10) latitude, (11) longitude, (12) parameter (OZONE/PM2.5/PM10/...),
  (13) AQI value, (14) AQI category (Good/Moderate/Unhealthy for Sensitive
  Groups/...), (15) action-day Y/N, (16) forecast source URL (forecasts only),
  (17) reporting agency. Observed rows carry an hour (`14:00`) and a numeric AQI;
  forecast rows carry a forecast URL and no numeric value. Current file had
  **3,972 forecast rows, 1,432 observed, 1,437 yesterday**.
- **Reporting areas vs monitors.** The FAQ: reporting areas "vary by size and
  population, covering anywhere from part of a city to an entire county area."
  The file gives each reporting area a **point coordinate** (e.g. Houston:
  `29.7510,-95.3510`; Tyler-Longview-Marshall: `32.3500,-95.3000`). So AirNow's
  geometry is **coarser than a neighborhood** — it is division/county-scale —
  which is a central spatial-assignment caveat: the reporting-area point is a
  representative point, **not** a neighborhood-level exposure measurement. For
  Houston, LA, New Orleans, Tyler all present in the current file (Houston 18
  rows, Tyler 13, New Orleans 10 in the live pull). LA's area name is split
  across many sub-areas (162 CA reporting areas; "Central LA CO", "Central
  Orange", "E San Fernando Vly", etc.).
- **Latency.** Real-time-ish: the observed rows carry the current hour
  (e.g. `14:00` on the pull date), and the file is regenerated twice/hour. This
  is the only repo-relevant source with **hour-scale** freshness.
- **Retirement notice (found live).** The Web Services page lists a section
  "Web Services that will be retired in the fall of 2026" — the zip/lat-lng
  forecast and historical-observation-by-zip endpoints are being retired. The
  **file products are not in the retirement list** (and the FAQ steers to them
  anyway), so the anonymous file path is the durable one.

### AQS (Air Quality System)

- **What it is.** The regulatory database of record. AQS API page, verbatim:
  *"AQS contains ambient air sample data collected by state, local, tribal, and
  federal air pollution control agencies from thousands of monitors around the
  nation. It also contains meteorological data, descriptive information about
  each monitoring station (including its geographic location and its operator),
  and information about the quality of the samples."* And on latency, verbatim:
  *"AQS does not contain real-time air quality data (it can take 6 months or more
  from the time data is collected until it is in AQS)."*
- **Validated / quality-assured.** This is the **retrospective truth set** for
  AirNow reconciliation. AQS is what AirNow's own disclaimers point to as the
  "official regulatory" source. The API exposes quality flags (`validity_indicator`,
  `event_type`), QA services (collocated assessments, performance evaluations,
  blanks, flow audits), and a **revision trail**: every row carries
  `date_of_last_change`, and every service accepts `cbdate`/`cedate` change-date
  filters. Verified live: an AQS daily row for Pico Rivera #2 (2023-08-01 O₃,
  `arithmetic_mean` 0.029, `validity_indicator` "Y", `date_of_last_change`
  "2024-05-24") — so the revision-query mechanism is real and queryable.
- **Access / credentials.** Free **email+key** registration (the docs' `signup`
  service). Every call requires `email` + `key`. The documented test key worked
  live this session for metadata, list, monitors, sample, and daily services.
  **Invalid credentials** return an explicit error shape: `{"status":"Failed",
  "error":["Email and/or key are invalid."]}`.
- **Rate limits / terms (verbatim from the API page).** *"Limit the size of
  queries. ... We request that you limit queries to 1,000,000 rows of data each."*
  *"Limit the frequency of queries. ... if scripting requests, please wait for one
  request to complete before submitting another and do not make more than 10
  requests per minute. Also, we request a pause of 5 seconds between requests."*
  Also: max **5 parameter codes** per request, and the end date must be in the
  same year as the begin date. All confirmed on the live page.
- **Geography / monitors.** Monitors are the unit. `monitors/byBox` returns
  operational metadata with **precise coordinates, `datum` (WGS84 or NAD83),
  `measurement_scale` (e.g. "NEIGHBORHOOD — 500 M TO 4KM", "URBAN SCALE — 4 KM TO
  50 KM"), `monitoring_objective`, `monitor_type` (SLAMS/NCORE), agency, and
  open/close dates**. `sampleData/byBox`, `dailyData/byBox`, and
  `quarterlyData`/`annualData` return concentrations and AQI at monitor level.
  Verified live, PM2.5+O₃ monitor counts within the registered metros:
  | Metro | PM2.5+O₃ monitors (2023-08 window) | density class |
  |---|---|---|
  | Los Angeles (`LA_METRO_BBOX`) | **13** | dense |
  | Houston (`HOUSTON_METRO_BBOX`) | **31** | dense |
  | New Orleans | **6** | moderate |
  | Boise | **3** | sparse-moderate |
  | Spokane | **3** | sparse-moderate |
  | Tyler (`TYLER_METRO_BBOX`) | **1** | **sparse** |
  | Amarillo | **1** | **sparse** |
  | Waco | **1** | **sparse** |
- **Lag / availability.** Verified live: 2026-08 daily queries returned "No data
  matched your selection"; 2025-08 returned 43 rows; 2024-08 returned 75 rows;
  2023-08 returned 67 rows for the LA box. So AQS is effectively **~1 year behind
  current** (documented as "6 months or more"). It is a **trailing anchor and
  truth set**, never a leading signal.
- **Completeness / bias.** Monitor coverage is regulated and uneven — dense in
  non-attainment/urban areas (South Coast AQMD, TCEQ), thin in small metros.
  Absence of a monitor is **not** evidence of clean air; it is absence of
  measurement. The ticket's "no-interpolation baseline for sparse areas" is
  exactly right: for a metro with 1 monitor, a feature is only meaningful at
  division scale (or as "monitored or not").

---

## Urban Signal fit

Repo units nest **metro bbox → division bbox → submarket → H3 7–9**
(`spatial/h3_indexer.py`; res 7 ≈ 5.16 km², res 8 ≈ 0.74 km², res 9 ≈ 0.105 km²).
Each event feed is bbox-filtered at ingest, then each row → `h3_res7/8/9` via
`H3SpatialIndexer.get_multi_res_hierarchy`.

AirNow/AQS fit the repo's **context-measurement tier** (`ContextObservationEvent`,
US-363 §2.7/§2.8) far better than the event tier:

1. **Shape: context observation, not event.** A daily/hourly AQI at a reporting
   area or monitor is a *periodic numeric measurement attached to a fixed asset*
   (a reporting area / a monitor site) — exactly the `ContextObservationEvent`
   contract (`source`, `asset_id`, `metric`, `value`, `unit`, `period_start`,
   `period_type`). It is deliberately **never a LIMS term** (covariate on
   `EnrichedH3Feature` only, subject to the standing ablation rule) — which
   matches the street-cut/energy-benchmark precedent. The `source` would be a new
   family (`airnow` / `aqs`), the `asset_id` the reporting area or AQS
   `state_code-county_code-site_number`, `metric` `aqi`/`pm25`/`o3`, `unit` AQI
   points or µg/m³.
2. **Coordinate → H3.** Both sources carry point coordinates. The accompanying
   leaf module maps a `reportingarea.dat` row's lat/lng to H3 7–9 with
   `get_multi_res_hierarchy` and applies `dynamic_spatial_fallback` keyed on
   observed-row density — so a metro with one monitor/reporting area rolls up to
   a coarser cell rather than fabricating a fine-grained number. **No new joiner.**
3. **Metro filter.** Point-in-metro-bbox, exactly like the national feeds
   (`national_feeds.py`: "`city_id` by point-in-registered-metro-bbox — all
   sources carry lat/lon, no geocoding"). AirNow/AQS are national sources; the
   national-feed registry pattern applies (AirNow is the stronger fit: a
   twice-hourly national file).
4. **Revision handling (the reconciliation).** AQS rows carry `date_of_last_change`
   and accept `cbdate`/`cedate`; ingestion is **full/vintage-aware**, exactly the
   `series_client.py` revision discipline ("Zillow and FHFA reissue and revise
   full history... prior values retained as vintages"). A future producer would
   ingest AirNow observations as the preliminary vintage and later AQS rows as
   the validated vintage, reconciled on (asset, period, pollutant, parameter).

**Does it add independent coverage?** Decisively yes, in kind. No existing feed
measures **air quality / environmental stress**: permits, 311, SLA, deeds, crime,
evictions, STR, street-cut are all development/service/transaction/public-safety
events; energy-benchmark is a building's annual efficiency, not ambient exposure.
An AirNow **AQI shock** (e.g. "Houston O₃ today = 105 Unhealthy for Sensitive
Groups" — a live row from this session's pull) is a distinct short-lived stressor
plausibly tied to outdoor-dependent foot traffic and near-term rental demand, and
AQS supplies the validated truth to test it against. This is the ticket's core
proposal and it is **feasible**.

**The catch is integration, not data.** A `FeedType` is required for a
`CityRegistration` to expose a signal, and each `DatasetSpec` assumes a
`PaginatingClient` with a `watermark_col` and `id_keys` per geolocated event row.
AQS violates those assumptions (keyed REST, no watermark — period- and
change-date-filtered), and AirNow's real-time layer is a **file product**
(twice-hourly full-file diff), not a paginated feed. Registering it requires a
new **context family** (`AirNow`/`AQS` or `AIR_QUALITY`), a new **keyed-API +
file-product producer** (the `SeriesClient` REST/`full`-ingestion patterns are the
closest precedent, but AQS/airnow are not yet `SeriesSpec`-registered), and
**per-metro or national registry entries** — all spine/interlock edits. That is
explicitly out of scope for this leaf stream.

---

## Independent coverage check (vs. the repo's context tier)

| Dimension | Energy-benchmark / bike-ped (existing context) | AirNow + AQS |
|---|---|---|
| Unit | building / sensor | reporting area / monitor site |
| Freshness | annual / daily | **hourly (AirNow)**, year-lagged (AQS) |
| Concept | building efficiency / pedestrian flow | **ambient air-quality stress** |
| Geometry | point asset → H3 | reporting-area point / monitor point → H3 |
| Coverage | metros with feeds | **every US metro with a monitor or reporting area** |
| Validation | n/a | **AQS = validated truth set for AirNow preliminaries** |
| Revision | n/a (annual) | `date_of_last_change`, `cbdate/cedate` — versioned |

**Under the repo's retention rule** (a signal is retained only if it adds
independent coverage and clears its family gate), AirNow/AQS add a genuinely
independent dimension and — uniquely — an **hour-scale** one; the family gate
(context covariates, ablation-before-LIMS) is the natural home.

---

## Risks and dependencies (mapped to the ticket's named risks)

1. **"Credential management."** **Confirmed real but mild.** AQS requires an
   email+key (documented test key worked live; invalid keys return a clean
   `Failed` envelope). AirNow REST requires a key, **but** the useful real-time
   layer (`reportingarea.dat`, `cityzipcodes.csv`) is **public and anonymous** —
   verified live, no credential needed. The remaining credential need is a
   non-production AQS key for the validated truth set, stored in the env-secret
   pattern already used by `SeriesSpec.auth_env` / `SeriesClient.token()`.
2. **"Monitor coverage is uneven; not a neighborhood-level exposure without an
   explicit spatial-assignment policy."** **Confirmed, quantified live.** Within
   registered metros, PM2.5+O₃ monitor counts range 31 (Houston) → 13 (LA) → 6
   (New Orleans) → 3 (Boise/Spokane) → **1** (Tyler/Amarillo/Waco). The ticket's
   **no-interpolation baseline** is the right policy: never interpolate where no
   monitor exists; assign each monitor/reporting area's point to its H3 cell and
   rely on `dynamic_spatial_fallback` to coarsen sparse cells — treat sparse
   metros at division scale only, and treat *absence of measurement* as unknown,
   not clean.
3. **"AirNow data are preliminary and should not be used for historical or
   regulatory conclusions; AQS is the delayed, validated reference."** **Confirmed,
   in EPA's own words (quoted above).** The mitigation is structural, not
   optional: separate storages/sources for `airnow` (preliminary, hourly, shock
   detection) vs `aqs` (validated, year-lagged, truth/anchor); reconcile on
   (asset, period, pollutant) with AQS `date_of_last_change` as the revision
   clock. Never let an AirNow value flow into a historical/regulatory feature.
4. **"Rate-limit handling."** **Confirmed live on the AQS docs.** 10 req/min, 5 s
   pause, 1M rows/request, ≤5 parameters. A real producer must throttle
   accordingly; AirNow's file product has no per-request quota (it is a twice-
   hourly file download) — simpler.
5. **Reporting-area geometry ≠ neighborhood.** **Confirmed.** AirNow reporting
   areas span "part of a city to an entire county"; a single point represents the
   area. At H3 res 9 the point assignment is not a neighborhood measurement —
   must document as division-scale context, or rely on AQS monitor-scale points
   for finer reads where monitors exist.
6. **AirNow endpoint retirement (newly surfaced).** **Verified live.** Several
   AirNow REST zip/lat-lng endpoints are scheduled for retirement in fall 2026.
   The file-product path is not in the retirement list and is the durable one.
7. **Integration-model dependency (decisive).** No context `FeedType` exists for
   a keyed/file-product air-quality layer; registering one is a spine/interlock
   change (new family + producer + registry entries), out of scope for a leaf
   stream. This is why the recommendation is DEFER-the-registration / ADOPT-the-
   signal.

---

## Leaf module built (phase 2, leaf-only)

To prove the parse→H3→shock-feature path is real and testable **without any spine
edit**, this stream adds a self-contained leaf module:

- `apps/api/src/spatial/airnow_signal.py` — pure functions, imports only `h3` and
  the leaf `H3SpatialIndexer` (no spine file touched):
  - `parse_reporting_area_row(line)` — parses a `reportingarea.dat` row into a
    typed `AirNowObservation` (reporting area, state, lat/lng, parameter, AQI,
    category, row type observed/forecast/yesterday, hour).
  - `aqi_shock_score(aqi)` — maps an AQI value to a 0–1 shock severity using the
    EPA AQI breakpoints (Good=0 … Hazardous≈1), the basis for a short-lived
    stress feature.
  - `map_reporting_area_to_h3(obs)` — projects the reporting area point to H3 res
    7/8/9 via `H3SpatialIndexer.get_multi_res_hierarchy`.
  - `fold_observations_by_cell(observations)` — folds per-cell observed AQI into
    a max-value shock tally (with `dynamic_spatial_fallback`-style coarsening
    contract), the proposed context-observation fold shape.
- `apps/api/tests/unit/test_airnow_signal.py` — unit tests: row parsing (observed
  vs forecast vs yesterday), AQI breakpoint mapping (Good/Moderate/Unhealthy for
  Sensitive Groups/…), multi-res hierarchy correctness, and the per-cell fold.
  Run with the repo venv; **all pass** (see VERIFY).

This module is a building block only. It is **not** imported by any spine file and
does **not** register a feed; wiring it into `city_registry.py` / a `FeedType` /
`national_feeds.py` would be the spine-gated REGISTER step, which this leaf does
not perform.

---

## Recommendation

**ADOPT the signal as a context/anchor layer; DEFER the feed registration.** Do
**not** register now — a feed registration is impossible in the current model
without a spine/interlock change: it needs a new context family (`AirNow`/`AQS`),
a new keyed-API + file-product producer (AQS REST, AirNow `reportingarea.dat`),
and registry entries (national-feeds pattern, or per-metro), all gated by
`pytest -m interlock`. The ticket's named risks (credentials, monitor coverage,
AirNow-vs-AQS separation) are **confirmed but all engineering-solvable**, and the
data side is **proven live** this session.

But **do not reject it** — this is the *strongest* context-source candidate in the
repo's US-363 context-measurement tier, for three reasons no other candidate
offers: (1) AirNow's real-time layer is **hour-scale**, the only near-real-time
environmental-stress signal available (energy-benchmark is annual; Zillow/FHFA are
monthly-and-revised; AQS itself is year-lagged); (2) the **AirNow→AQS
reconciliation** gives the repo its first *preliminary-vs-validated truth-set*
pair, exactly the retrospective validation the ticket asks for, with AQS's
`date_of_last_change`/`cbdate` revision mechanism verified live; and (3) the
real-time ingestion path is **credential-free** (public file product), removing
the largest access objection.

**What unblocks a future REGISTER:**

1. A scope decision that Urban Signal wants an **air-quality context layer** — a
   new context family (`AIR_QUALITY` / `airnow`+`aqs`) under
   `ContextObservationEvent`, treated as context/LIMS-exempt (precedent:
   energy-benchmark, bike-ped, street-cut).
2. Provision of a **non-production AQS key** (env-secret, `SeriesSpec.auth_env`
   pattern) and, if the keyed AirNow REST is preferred over the file product, an
   AirNow key too — otherwise the public `reportingarea.dat` product suffices.
3. A concrete consumer — e.g. an **environmental-stress prior** behind submarket
   distress (smoke/ozone shock as a short-lived demand dampener), or the
   ticket's proposed **event-window ablation** against transaction, permit, and
   mobility signals (AirNow shock in the window vs. AQS-validated truth).
4. If both arrive, register the **file-product producer first** (AirNow,
   twice-hourly, anonymous, national-feeds pattern), fold hourly observed AQI
   into `ContextObservationEvent` (`period_type="hour"`, `period_type="day"`),
   then layer the AQS validated anchor (`period_type="day"`, versioned by
   `date_of_last_change`) and run the reconciliation ablation. Start with the
   **dense metros (Houston, Los Angeles, New Orleans)** for the signal and the
   **sparse metros (Tyler, Amarillo, Waco)** as the no-interpolation baseline
   test.

Until then, no existing feed is displaced, and AirNow/AQS should not be wired
into scoring — but they should be the **first environmental-stress source
reopened** when a context layer is approved. The leaf module
`apps/api/src/spatial/airnow_signal.py` (imports only the leaf `h3_indexer`) is a
ready, tested building block for that future spine-bound registration.

---

## VERIFY (commands run this session)

- `curl https://aqs.epa.gov/data/api/metaData/isAvailable?email=test@aqs.api&key=test`
  → `"API service is up and running healthy."`
- `curl .../list/states?email=test@aqs.api&key=test` → `"rows": 56`, first 20
  states with FIPS codes.
- `curl .../monitors/byBox?...&param=88101,44201&minlat=33.7&maxlat=34.34&...`
  → LA **13** PM2.5+O₃ monitors; Houston **31**; New Orleans **6**; Boise **3**;
  Spokane **3**; Tyler **1**; Amarillo **1**; Waco **1** (with coordinates, datum,
  measurement_scale).
- `curl .../dailyData/byBox?...&param=88101&bdate=20230801&edate=20230831...` →
  LA **1,821 rows** with `arithmetic_mean`, `aqi`, `validity_indicator`,
  `date_of_last_change` (e.g. Pico Rivera #2 O₃, `date_of_last_change` 2024-05-24).
- `curl .../sampleData/byBox?...&bdate=20230801&edate=20230801...` → 78 hourly
  PM2.5 rows, `time_local`, `sample_measurement`, `method_type` (FEM/FRM).
- Freshness: 2026-08 → 0 rows; 2025-08 → 43; 2024-08 → 75; 2023-08 → 67 (LA box).
- Invalid key → `"Email and/or key are invalid."`
- `curl https://files.airnowtech.org/airnow/today/reportingarea.dat` → **HTTP 200,
  no auth**, 1.99 MB, 6,841 rows, 892 reporting areas; Houston/Tyler/New Orleans
  present; observed rows carry hour + AQI (Houston O₃ 14:00 = 105 "Unhealthy for
  Sensitive Groups").
- `curl https://files.airnowtech.org/airnow/today/cityzipcodes.csv` → **HTTP 200**,
  City|State|Zipcode|Latitude|Longitude.
- `curl https://www.airnowapi.org/aq/observation/zipCode/current/?format=application/json&zipCode=90012&distance=25`
  → **HTTP 401**, `{"WebServiceError":[{"Message":"Request not authenticated."}]}`.
- `cd apps/api && .venv/bin/pytest tests/unit/test_airnow_signal.py -q` → **all pass**.
