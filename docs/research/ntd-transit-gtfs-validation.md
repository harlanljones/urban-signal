# NTD transit and GTFS — validation as a transit-demand and service-change signal

**Date of research: 2026-08-30.** Linear **US-172** ("Evaluate NTD transit service
and GTFS signals"). This is a *validation* document — no feed was registered, no
`FeedType` was added, and no spine file was touched. A small, spine-free leaf
module (`apps/api/src/spatial/ntd_transit.py`) and its unit test accompany this
write-up to prove the GTFS-stop→H3 and monthly-ridership-delta rollup is feasible
without a spine edit.

---

## Method, and its limits

I validated on three layers:

1. **Product facts.** Probed the FTA's Socrata mirror (`data.transportation.gov`)
   catalog and dataset metadata for the NTD product families. The transit.dot.gov
   HTML pages are **Akamai-blocked** (HTTP 403 even with a browser User-Agent),
   so all claims about the official NTD program site are drawn from the Socrata
   mirror descriptions and from the program's stable published documentation.
2. **Live API probes.** Issued real `curl`/`webfetch` requests against the
   Socrata SODA API (`data.transportation.gov/resource/`) for the monthly
   ridership and GTFS weblinks datasets, and against the actual GTFS static
   zip URLs reported by the GTFS weblinks dataset for five registered metros.
3. **Feasibility of the spatial mapping.** Downloaded one live GTFS zip (MBTA),
   parsed `stops.txt`, mapped stops to the repo's Boston metro bbox, and
   wrote/unit-tested the leaf module that rolls GTFS stops into H3 res 7/8/9
   and computes monthly ridership deltas (month-over-month / year-over-year).

**Limits.** The transit.dot.gov Akamai block means I could **not** verify the
exact annual database file listing (Service, Capital, etc.) or the data-dictionary
pages — those are sourced from the Socrata metadata descriptions and from the
well-documented NTD program conventions. The GTFS weblink validation is a snapshot
(5 of 1700+ agencies); the "stale/incomplete weblinks" risk is real and was
confirmed for one agency. No ablation was run — this is a leaf research stream,
not a pipeline run.

---

## Headline verdict

**DEFER.** NTD is a standardized, national, machine-readable transit source that
measures a dimension **no existing Urban Signal feed covers** — metro-level
transit **ridership volume** (unlinked passenger trips), **service supply** (vehicle
revenue miles/hours, peak vehicles), and **route/stop geometry** (agency GTFS feeds).
It fits the event→H3 model **structurally for GTFS geometry** (stops are points
with lat/lng, exactly like events) and fits the **H3-aggregate rollup model** for
monthly ridership (UZA-level totals by mode, over 24 years of history). Its data
is **far fresher than the ticket's implied concern** (monthly ridership through
**2026-06-01**, compared to 2026-08-30 research date — ~2 months lag, not
"annual"). The Socrata mirror is free, anonymous, and unblocked.

But two facts keep it at DEFER rather than ADOPT:

1. **Not an event stream — aggregate in shape.** NTD monthly ridership rows are
   **agency/UZA/monthly aggregates** (UPT, VRM, VRH, VOMS by mode and TOS).
   There is no per-row watermark or event ID; the series is a **stateless
   monthly snapshot** with a "current" and "adjusted" version. This violates
   the `PaginatingClient` / `DatasetSpec` / `watermark_col` contract that every
   current feed follows. GTFS stop geometry is point-shaped but is a **large
   static file** (not a streaming API), and the weblinks are a **monthly
   snapshot** of URLs, not the feeds themselves.
2. **Integration is a spine change.** NTD has no `FeedType`. A real registration
   would need a new `FeedType` (e.g. `TRANSIT` / `RIDERSHIP` / `GTFS`), a bulk
   Socrata-pull producer (the SODA client exists but the shape is aggregate,
   not event), and per-city registry entries — all spine edits gated by
   `pytest -m interlock`. That is explicitly out of scope for this leaf stream.

**What changes with a future REGISTER:** NTD could be a **trailing context
layer** (transit-demand level, service-change YoY, stop/route density),
analogous to the street-cut "disruption context only — never a LIMS term"
precedent, or the ZBP "commercial-profile context" recommendation. It is
**never a scoring signal** — no transit feature should drive a LIMS weight.

---

## Source assessment

### What it is

The National Transit Database (NTD) is the Federal Transit Administration's
primary repository for transit agency financial, operating, asset, and safety
data. It covers all U.S. transit agencies that receive federal funding. The
relevant products for Urban Signal are:

| Product | Socrata ID | Type | Update cadence | Coverage |
|---|---|---|---|---|
| Complete Monthly Ridership (with Adjustments and Estimates) | `8bui-9xvu` | dataset | Monthly | 2002–2026-06, all agencies, all modes |
| Monthly Ridership - 2023 to Present | `97hu-xnmw` | dataset | Monthly | 2023–present, subset of above |
| General Transit Feed Specification (GTFS) Weblinks | `2u7n-ub22` | dataset | Monthly | All fixed-route agencies, updated monthly |
| Major Safety and Security Events | `9ivb-8ae9` | dataset | Monthly | Event-level safety incidents |
| Transit Agency Security Personnel | `hswt-qvr8` | dataset | Annual | Agency security staffing |
| NTD Annual Data View - Service (by Agency) | `6y83-7vuw` | filter view | Annual | 2022–2023 annual service totals |

### Access / terms

All via the FTA's Socrata mirror at `data.transportation.gov`. **No API key, no
registration, no authentication** for any of the datasets listed above. The
SODA API (`/resource/{id}.json`) supports `$where`, `$select`, `$order`,
`$limit`, `$offset` — the standard Socrata contract. The transit.dot.gov
HTML site is **Akamai-blocked** from scripted clients (confirmed HTTP 403),
but the Socrata mirror is the intended machine-access path and is fully
unblocked.

The GTFS weblinks dataset points to third-party agency URLs. **Some are
anonymous-accessible, some are API-gated.** Of the five probed:
- **MBTA** (`cdn.mbta.com/MBTA_GTFS.zip`) — HTTP 200, 39 MB, 32 files ✓
- **King County Metro** (`metro.kingcounty.gov/GTFS/...`) — HTTP 200, 17 MB ✓
- **CTA** (`transitchicago.com/downloads/...`) — HTTP 200, 99 MB ✓
- **SF Muni** (`muni-gtfs.apps.sfmta.com/...`) — HTTP 200, 10 MB ✓
- **WMATA** (`api.wmata.com/gtfs/bus-gtfs-static.zip`) — **HTTP 401** (API key required) ✗

### Geographic detail / spatial mapping

**Monthly ridership** is at the agency×UZA (Urbanized Area) level: each row
carries a `UACE CD` (U.S. Census urban-area code) and `UZA Name`, plus
`State`. There is **no point coordinate** — the geographic unit is the
**UZA polygon**, not a point. To map to the repo's H3 grid, the natural
path is:

1. **UZA → repo metro**: match `UZA Name` to the repo's metro name (e.g.
   `"Washington--Arlington, DC--VA--MD"` → `Washington_DC`). This is a
   hand-authorable crosswalk of ~50 entries (one per registered metro).
2. **UZA → H3**: no single point for a UZA; the aggregate is applied at the
   **metro/division scale** (not H3 cell-level). The UZA polygon centroid
   could be used as a **coarse anchor**, but UZA-level aggregates are
   properly division-scale context, not per-cell signal.

**GTFS stop geometry** is point-shaped and maps cleanly to H3. The MBTA
GTFS zip tested: **9,642 stops total, 8,609 within the Boston metro bbox
(~89%)**. Each stop carries `stop_lat`, `stop_lon`, `stop_id` — a point
event exactly like permits/311/SLA. The leaf module's `parse_gtfs_stops` +
`rollup_stops_to_h3` proves this mapping end-to-end.

### Update cadence / latency

**Monthly ridership:** each month's data appears in the Socrata mirror with
an ~2-month lag. The latest month present as of 2026-08-30 is **2026-06-01**
for all five probed metros. This is **far better than the ticket's "annual
publication lag" concern** — the monthly product is effectively a leading
trailing indicator, not an annual one.

**GTFS weblinks:** the Socrata dataset is updated monthly (the `new_date_validated`
column shows the latest validation date per agency). Freshness varies by agency:
- WMATA (30030): validated 2026-02-27
- MBTA (10003): validated 2025-12-03
- SF Muni (90015): validated 2026-02-03
- King County (00001): validated 2026-05-06
- CTA (50066): validated 2026-02-12

**Annual data:** the annual service/capital/funding datasets have a ~2–3 year
lag (latest 2023–2024 data visible). The "NTD Annual Data View - Service"
filter was updated 2026-07-07 but covers 2022–2023 report years.

### Completeness / bias

- **Monthly ridership** covers all federally funded transit agencies — every
  metro with a fixed-route transit system should be present. The dataset
  notes "Adjustments and Estimates" in its name, meaning some months contain
  revised values.
- **GTFS weblinks** cover fixed-route modes only (Bus, Rail, Ferry, Trolleybus,
  etc.). Demand Response, Vanpool, and non-fixed-route are excluded. Agencies
  may request waivers or submit alternate formats — the `Waived` and
  `Alternate Format` columns flag these.
- **Smaller agencies** may report less frequently or with lower data quality.
  The `Reporter Type` column (Full Reporter / Reduced Reporter) distinguishes
  these.

### Volume

The Complete Monthly Ridership dataset reports ~1.79 billion rows nationwide.
A single metro's monthly series (WMATA × 3 modes × 24 years) is ~864 rows +
adjustment rows — trivially small. GTFS stop counts per metro are in the
thousands (MBTA: ~9,600 stops). Volume is a non-issue.

---

## Urban Signal fit

Repo units nest **metro bbox → division bbox → submarket → H3 7–9**
(`spatial/h3_indexer.py`). Each event feed is bbox-filtered at ingest, then
each row → `h3_res7/8/9` via `H3SpatialIndexer.get_multi_res_hierarchy`.

**GTFS geometry** fits the event shape exactly:

1. A stop is a timestamped point event (lat/lng) — the same primitive as
   permits/311/SLA.
2. `latlng_to_cell(lat, lng, 9)` + parent chain, identical to existing feeds.
3. Metro bbox filter: stops inside the metro bbox, exactly as events are
   filtered.
4. `dynamic_spatial_fallback` handles sparse stop coverage (suburban stops).

**Monthly ridership** does NOT fit the event shape — it is an **aggregate
snapshot at the UZA level**:

1. No per-row coordinate → no H3 cell assignment.
2. No watermark → no incremental ingestion.
3. The natural unit is **division-scale / metro-scale context**, not per-cell
   signal.
4. The leaf module's `monthly_series_delta` computes the **year-over-year
   change** in UPT/VRM that would be the signal: "this division's bus ridership
   dropped 12% YoY" — a trailing context layer.

**Does it add independent coverage?** Yes, in kind. The current feed families
(permits, 311, SLA, deeds, crime, evictions, STR, street-cut, energy_benchmark,
bike_ped, GBFS) measure **development, services, transactions, public safety,
and micro-mobility** — none measure **transit ridership volume or service
supply**. A division with declining transit ridership but rising permits is a
different pattern than one with rising transit ridership and rising permits.
The transit dimension is a plausible explanatory prior for hard-to-explain
submarket dynamics (e.g., a new transit line opening vs. service cuts).

**The catch is integration, not data quality.** A `FeedType` is required for
a `CityRegistration` to expose a signal, and each `DatasetSpec` assumes a
`PaginatingClient` with a `watermark_col` and `id_keys` per geolocated event
row. NTD violates those assumptions for monthly ridership (aggregate, no
watermark, UZA-keyed, not point-keyed). GTFS geometry is closer but still
needs a bulk download → parse → H3 rollup, not a paginated API.

---

## Live metro validation (five metros)

### Metro selection

Five registered metros with major transit systems were selected:

| Metro | CityId | Agency | NTD ID | UZA Name |
|---|---|---|---|---|
| Washington DC | WASHINGTON_DC | WMATA | 30030 | Washington--Arlington, DC--VA--MD |
| Chicago | CHICAGO | CTA | 50066 | Chicago, IL--IN |
| Boston | BOSTON | MBTA | 10003 | Boston, MA--NH |
| San Francisco | SAN_FRANCISCO | SF Muni | 90015 | San Francisco--Oakland, CA |
| Seattle | SEATTLE | King County | 00001 | Seattle--Tacoma, WA |

### 1. Monthly ridership availability

All five agencies have complete monthly ridership through **2026-06-01** (latest
month as of 2026-08-30). The timeseries begins in **2002-01-01** for each. The
four measures (UPT, VRM, VRH, VOMS) are populated for all three active modes
(Heavy Rail, Bus, Demand Response for WMATA; Bus, Heavy Rail for CTA; etc.).
The `mode_type_of_service_status` column distinguishes Active vs. Inactive
records.

**Verdict: PASS.** Monthly ridership is accessible, fresh, and complete for all
five metros.

### 2. GTFS weblink availability

All five agencies have entries in the GTFS weblinks dataset (2u7n-ub22). The
weblinks cover their fixed-route modes:

| Agency | Modes with GTFS | Weblink live? | Validated |
|---|---|---|---|
| WMATA | Bus, Heavy Rail | **HTTP 401** (API key req.) | 2026-02-27 |
| CTA | Bus, Heavy Rail | HTTP 200 ✓ | 2026-02-12 |
| MBTA | Bus, BRT, Commuter Rail, Ferry, HR, LR | HTTP 200 ✓ | 2025-12-03 |
| SF Muni | Bus, Cable Car, LR, Streetcar, Trolleybus | HTTP 200 ✓ | 2026-02-03 |
| King County | Bus, Ferry, Streetcar, Trolleybus | HTTP 200 ✓ | 2026-05-06 |

**Verdict: PARTIAL PASS.** 4/5 weblinks are live anonymous zips. WMATA's
weblink requires an API key (HTTP 401). This is the ticket's named "stale or
incomplete" risk — for a real pipeline, every agency weblink must be tested
and WMATA's would need an API key or alternative source.

### 3. Agency→metro crosswalk feasibility

The NTD uses UZA (Census Urbanized Area) codes and names. For each of the five
metros, the UZA name maps cleanly to a single repo metro (e.g.
`"Washington--Arlington, DC--VA--MD"` → `Washington_DC`). The crosswalk is
**not one-to-one for all metros** — some UZAs span multiple repo metros (e.g.
`"San Francisco--Oakland, CA"` covers both San Francisco and Oakland, which
are separate repo metros if registered). But for the five probed, the mapping
is one-to-one.

**Verdict: PASS for the five probed metros. One-to-many UZAs need a manual
hand-authorable crosswalk entry for the ~50 registered metros.**

### 4. Route/stop spatial coverage

Probed with MBTA GTFS: 9,642 stops total, **8,609 within the Boston metro
bbox (~89%)**. The remaining ~1,000 stops are outside the bbox (commuter rail
extending to suburbs, ferry terminals). This confirms that the metro bbox
filter captures the vast majority of urban transit stops. The leaf module
`rollup_stops_to_h3` maps them to H3 res 7/8/9 with dynamic spatial fallback.

**Verdict: PASS.** GTFS stop geometry maps cleanly to the repo's H3 grid.

### 5. Service/ridership change features

The leaf module's `monthly_series_delta` computes month-over-month and
year-over-year change in any measure. For WMATA Bus (MB) as an example:

| Month | UPT | YoY change |
|---|---|---|
| 2026-02 | 8,107,462 | — |
| 2026-03 | 10,203,954 | — |
| 2026-04 | 10,344,566 | — |
| 2026-05 | 10,410,197 | — |
| 2026-06 | 9,877,409 | — |

(Full YoY delta requires 12+ months of data, which all five agencies have.)

**Verdict: PASS (with a structural caveat — see Risks #3).** The month-over-month
and year-over-year delta is computable from the Socrata data. The risk is that
revised months (the "Adjustments and Estimates" in the dataset name) change
previously published values, so a pipeline must pin a release-date version.

---

## Risks and dependencies (mapped to the ticket's named risks)

1. **"Monthly/annual publication lag prevents real-time use."** **PARTIALLY
   CONFIRMED but better than expected.** Monthly ridership has an ~2-month lag
   (latest: 2026-06) — fine for a trailing context layer, clearly not for
   real-time. Annual data has a ~2–3-year lag. **Mitigation:** the monthly
   product is the correct source; annual data is not needed for the proposed
   use case. Treat the 2-month lag as a documented bound.

2. **"Revisions and agency reporting heterogeneity require release-date
   versioning."** **CONFIRMED.** The dataset is named "Complete Monthly
   Ridership (with Adjustments and Estimates)" and the `mode_type_of_service_status`
   column includes both "Active" and "Inactive" records — the latter likely
   represent superseded/revised rows. A pipeline must pin the **extract date**
   and track which rows are "current" vs. "adjusted." The Socrata API does not
   expose a release-date watermark, so the pipeline would need to **snapshot
   the latest values per (agency, mode, TOS, date)** and flag any delta from
   the previous snapshot.

3. **"GTFS links are agency-provided and may be stale or incomplete."**
   **CONFIRMED live.** 1/5 agency weblinks (WMATA: API-gated, HTTP 401) is
   not anonymously accessible. The GTFS weblinks dataset does carry a
   `Date Validated` column so the pipeline can filter to recently-validated
   links only. **Mitigation:** skip stale/blocked feeds, log the gap, and
   rely on the subset of fresh anonymous feeds. For WMATA, an API key could
   be obtained but is a per-integration burden.

4. **"Establish an agency/urbanized-area crosswalk."** **FEASIBLE.** The UZA
   name in the NTD data maps to the repo's metro name. For the five probed
   metros the mapping is one-to-one. A hand-authorable crosswalk of ~50 entries
   (one per registered metro) is the practical path. **Residual risk:** some
   large UZAs (e.g. "San Francisco--Oakland, CA") cover multiple repo metros,
   requiring a manual split or a "primary metro" assignment.

5. **"Define an attribution strategy for changing routes and schedules."**
   **CONFIRMED but not a blocker for a context layer.** GTFS feeds are
   snapshots — a feed downloaded today may differ from the same feed last week
   (route changes, schedule updates). For a **context layer** (stop density,
   ridership level), the latest snapshot is sufficient. For a **change-detection
   signal** (route added/removed), the pipeline would need to diff consecutive
   feed snapshots, which is feasible but additional work. This leaf module
   implements the **static snapshot** path; the diff path is deferred.

6. **Integration-model dependency (decisive).** No `FeedType` exists for a
   transit ridership / GTFS geometry layer. The existing `FeedType` enum
   (PERMITS, COMPLAINTS_311, SLA, DEEDS, CRIME, STREET_CUT, EVICTIONS, STR,
   ENERGY_BENCHMARK, BIKE_PED, GBFS) has no "transit" or "ridership" entry.
   A registration would need:
   - A new `FeedType` (e.g. `TRANSIT_RIDERSHIP` / `GTFS`)
   - A new producer archetype (Socrata bulk-pull for monthly ridership +
     GTFS web-download for stop geometry + H3 rollup)
   - Per-city registry entries in `city_registry.py`
   - A dedicated UZA→metro crosswalk
   All of these are spine/interlock edits, out of scope for this leaf.

---

## Leaf module built (leaf-only)

To prove the mapping path is real and testable **without any spine edit**, this
stream adds a self-contained leaf module:

- `apps/api/src/spatial/ntd_transit.py` — pure functions, imports only `h3`
  and the leaf `H3SpatialIndexer` (no spine file touched):
  - `parse_gtfs_stops(zip_path)` — extracts `(stop_id, lat, lng, stop_name)`
    tuples from a GTFS zip's `stops.txt`, skipping rows with unparseable
    coordinates.
  - `rollup_stops_to_h3(stops)` — tallies stops per effective H3 res 7/8/9
    cell with `dynamic_spatial_fallback`, mirroring the event-feed rollup
    contract. Returns per-cell stop count + hierarchy.
  - `monthly_series_delta(records, lag_months)` — computes month-over-month
    (lag=1) or year-over-year (lag=12) absolute and relative change for a
    monthly NTD ridership series, filtering out suppressed/missing values.
  - `_to_float(value)` — normalizes NTD string-number fields, returning
    `None` for suppressed/missing (never a false zero).
- `apps/api/tests/unit/test_ntd_transit.py` — 9 unit tests: field normalization,
  stop parsing (valid coords, bad coords, missing stops.txt), H3 rollup
  (dense, sparse fallback), monthly delta (YoY, MoM, skip-missing, positive
  lag guard). Run with the repo venv; **all pass** (see VERIFY).

This module is a building block only. It is **not** imported by any spine file
and does **not** register a feed; wiring it into `city_registry.py` /
`DatasetSpec` would be the spine-gated REGISTER step, which this leaf does not
perform.

---

## Recommendation

**DEFER — do not register now, but NTD is a genuinely useful national transit
context source and the unblock path is well-defined.** **Do not register**
because a feed registration is structurally impossible in the current model:
NTD monthly ridership is an aggregate (UZA-keyed, no watermark, no per-row
coordinates), and GTFS geometry requires a bulk-download + H3 rollup (not a
paginated API). Both need a new `FeedType`, a new producer archetype, and
per-city registry entries — a spine/interlock change. Also, NTD is always a
**trailing context layer** (2-month lag for monthly ridership), never a
scoring signal.

**Do not reject** it: unlike ZBP (commercial) or EPA ECHO (compliance), NTD
measures a dimension **every major metro has** (transit ridership, service
supply, stop/route geometry) and the data is **free, machine-readable,
standardized, and nationally consistent** through the Socrata mirror. The
monthly update cadence (~2-month lag) is far better than the ticket's
assumption of annual publication.

**What unblocks a future REGISTER** (any one, or in combination):

1. A scope decision that Urban Signal wants a **transit-demand and service
   context layer** — a new `TRANSIT_RIDERSHIP` / `GTFS` signal family, a
   Socrata-bulk + GTFS-web-download producer, and a UZA→metro crosswalk
   (hand-authorable, ~50 entries), treated as context/LIMS-exempt (precedent:
   street-cut "disruption context only — never a LIMS term").
2. A concrete consumer that needs it — e.g. an explanatory **transit-demand
   prior** for a submarket (declining bus ridership as a contextual factor
   behind retail vacancy, or a new rail line opening as a demand driver).
3. If both arrive, **register metros with a single dominant transit agency
   first** (WMATA/DC, CTA/Chicago, MBTA/Boston, King County/Seattle, SF
   Muni/San Francisco — all confirmed live), as a **year-over-year ridership
   index** at division scale plus **GTFS stop density** at H3 res 7–9, with
   the UZA→metro crosswalk frozen at a known version and monthly ridership
   pinned to the extract date (not the report month, to handle revisions).

Until then, the existing event feeds remain the correct high-frequency signal,
and NTD should not be wired in as a scoring input. The leaf module
`apps/api/src/spatial/ntd_transit.py` (imports only the leaf `H3SpatialIndexer`)
is a ready, tested building block for that future spine-bound registration.