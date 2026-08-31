# HPMS roadway and traffic context — validation as a baseline infrastructure layer

**Date of research: 2026-08-30.** Linear **US-171** ("Validate HPMS roadway and
traffic context"). This is a *validation* document — no feed was registered, no
`FeedType` was added, and no spine file was touched. A small, spine-free leaf
module (`apps/api/src/spatial/hpms_context.py`) and its unit test accompany
this write-up to prove the HPMS-segment→H3 and attribute-completeness rollup is
feasible without a spine edit. The evidence memo for source, distribution, and
three-metro proposal was already recorded on US-171 (2026-08-26 comment).

---

## Method, and its limits

I validated on three layers:

1. **Authoritative source facts.** FHWA HPMS field manual
   (`fhwa.dot.gov/policyinformation/hpms/fieldmanual`), the state shapefile
   catalogue (`shapefiles_2017.cfm`, years 2011–2017, one zip per state plus a
   national arterial set), and the 2018 HPMS Public Release hosted feature
   layers (`geo.dot.gov/server/rest/services/Hosted/<State>_2018_PR/FeatureServer`).
   These are FHWA's own descriptions of annual state submissions, due dates,
   reuse terms, and schema — quoted, not reconstructed from memory. Contact on
   record: Thomas Roff, Office of Highway Policy Information.

2. **Repo fit by concept.** Mapping HPMS's geography (linework segments with
   `URBAN_CODE` / `COUNTY_CODE` / `STATE_CODE` + linear referencing), cadence
   (annual, lagged), and attributes (AADT, lanes, functional system, IRI, speed)
   against the repo's H3 res 5 metro tiles, res 7–9 event cells, and the
   `PaginatingClient` / `DatasetSpec` / `watermark_col` feed contract, using the
   same reasoning pattern applied to the LODES, QCEW, HMDA, and NTD validations.

3. **Feasibility of the spatial mapping.** Wrote and unit-tested a leaf module
   that, given HPMS segment midpoints and per-segment attributes, computes
   attribute completeness, release lag, H3-5/H3-7 coverage, and the four metrics
   proposed on US-171 (spatial-match coverage, attribute completeness, release
   lag, incremental model value) via `H3SpatialIndexer` — without downloading
   the ~758 MB national arterial set or invoking geopandas.

**Limits.** I did **not** download the per-state zipped shapefiles or hit the
2018 Hosted Feature Layers in this environment (the geoprocessing — `geopandas`/
`h3-py` line→H3 polygon covering and the local-DOT centerline overlay for
NYC/Chicago/SF — is the non-trivial compute the 2026-08-26 comment flagged as
needing an explicit scope decision). No numeric three-metro rollup is presented
as a measured file characteristic — unlike the NTD validation, which downloaded
and parsed a live MBTA GTFS zip. "Incremental value against current signals" is
assessed by *concept* against the repo's feed families, not by running an
ablation. The exact byte sizes and FeatureServer response shapes are sourced
from FHWA documentation and the US-171 evidence memo, not from a live download
in this run. The 2018 public-release year is staled against 2026-08-30 (the
page was last modified Sep 2022 per the memo).

---

## Headline verdict

**DEFER (do not register as a `FeedType`; retain as a documented baseline-context
candidate).** HPMS is an authoritative, free, federal, nationally-uniform
roadway inventory whose **functional-system class, through-lanes, speed limit,
and AADT** are dimensions **no existing Urban Signal feed measures** — the
current feeds (311, permits, crime, SLA, deeds, street-cut, etc.) are
**event** streams with point coordinates, while HPMS is a **roadway-section
baseline** (linework, not events). It fits the repo's H3 grid **structurally for
context** (line segments can be discretised to H3-5 tiles the dashboard already
uses for context layers, then to res 7–9 for micro-unit rollups), and the
spatial covering is trivially feasible via midpoint→H3 or line→H3 polygon
covering — the memo proposes H3-5 as the primary tile, exactly the dashboard's
context resolution.

But four facts keep it at DEFER rather than ADOPT:

1. **Not an event stream — annual baseline, not a signal.** States submit
   annually (Interstate Apr 15, remaining Jun 15 per the Field Manual); the
   **public geospatial release lags the reporting year by ~7–8 years** (latest
   public shapefile year 2017, latest public Feature Layer year 2018, per the
   memo; a newer extract may exist on `data.transportation.gov` but was not
   confirmed reachable as a geospatial Hosted Feature Layer). This is a
   **baseline / annual-context layer**, never a near-real-time LIMS term — the
   ticket's own risk note. It cannot drive a short-term change detector.

2. **Linework, not points — new geometry producer.** Urban Signal's producers
   assume per-row point lat/lng → `H3SpatialIndexer.get_multi_res_hierarchy`.
   HPMS rows are **line segments** (`ROUTE_ID` + `BEGIN_POINT`/`END_POINT`
   linear referencing + shapefile linework) with no per-row event ID or
   watermark. Registering it requires a **line→H3 covering** step (segment
   polyline intersected with H3-5 or res 7–9 cells), which the current
   `PaginatingClient` / `DatasetSpec` / `watermark_col` contract does not
   provide. This is the same spine-gated gap seen in the HMDA (tract polygon)
   and NTD-ridership (aggregate) validations.

3. **State-varying completeness and QA.** FHWA explicitly attaches caveats:
   geodetic accuracy/topology **not evaluated** (not for navigation); spatial
   format **may not fully cover** all Federal-aid highways; GIS summaries can
   **diverge** from the official Highway Statistics tables; underlying records
   originate from **State DOTs**, so state-specific QA/versioning is required.
   Coverage and attribute quality vary by state — a metro that straddles a
   state line (e.g. NYC: NY/NJ) inherits two QA regimes.

4. **Integration is a spine change.** No `FeedType` exists for a roadway-baseline
   context. A real registration would need a new signal family (e.g.
   `ROADWAY_BASELINE` / `TRAFFIC_CONTEXT`), a **bulk shapefile/FeatureServer
   producer** (not Socrata/ArcGIS/CKAN pagination), and per-metro clipping by
   `URBAN_CODE`/county/bbox plus line→H3 covering — all spine edits gated by
   `pytest -m interlock`. That is explicitly out of scope for this leaf stream.

**What changes with a future REGISTER:** HPMS could be a **slow-moving
infrastructure context layer** (functional-class / lane / speed / AADT / IRI as
roadway-capacity and traffic-exposure priors), analogous to the street-cut
"disruption context only — never a LIMS term" precedent and the NTD "transit-
demand context" recommendation. It is **never a scoring signal** — no HPMS
attribute should drive a LIMS weight directly; it would sit under the hardcoded
`base_lims`/`capex` baselines as a **period_type="year" context observation**,
if it sits anywhere.

---

## Source assessment

### What it is

The Highway Performance Monitoring System is FHWA's annual, state-reported
national roadway inventory. States report section-level extent, condition,
performance, and traffic; FHWA publishes a public geospatial extract and the
official Highway Statistics series from the same submissions.

### Access / terms / cadence

| Surface | Years | Form | Auth | Route notes |
|---|---|---|---|---|
| State zipped shapefiles | 2011–2017 | one zip per state + national arterial ~758 MB | none (public download) | `fhwa.dot.gov/policyinformation/hpms/shapefiles_2017.cfm` |
| 2018 HPMS Public Release (Hosted Feature Layers) | 2018 | ArcGIS Hosted Feature Layer per state (`geo.dot.gov/server/rest/services/Hosted/<State>_2018_PR/FeatureServer`) | none (public FeatureServer) | Most recent geospatial public release; page last modified Sep 2022 |
| `data.transportation.gov` extract | unknown / check | Socrata/API | none | Memo flags: confirm before any nationwide backfill; may be newer but not confirmed as geospatial Hosted layer |

**Distribution / reuse terms.** U.S. DOT/FHWA works are U.S. federal government
productions and carry **no copyright — public domain**; free to download and
reuse. FHWA caveats (field manual / download pages): geodetic accuracy and
topology **not evaluated**; spatial format may not fully cover all Federal-aid
highways; aggregated GIS summaries can diverge from official Highway Statistics;
records originate from State DOTs → state-specific QA/versioning required.

**Update cadence.** States submit **annually**: Interstate by **Apr 15**,
remaining by **Jun 15** (Field Manual due dates). **Public geospatial release
lags reporting year by several years** — latest public shapefile 2017, latest
Feature Layer 2018 (memo). So even a 2025 HPMS submission year is unlikely to
have a 2025 public shapefile/Feature Layer by 2026-08-30. Treat as **annual
baseline with multi-year publication lag**.

### Schema of interest (2018 release, from the memo)

`YEAR_RECORD`, `STATE_CODE`, `ROUTE_ID`, `BEGIN_POINT`, `END_POINT`, `AADT`,
`AADT_COMBINATION`, `AADT_SINGLE_UNIT`, `COUNTY_CODE`, `F_SYSTEM`,
`FACILITY_TYPE`, `IRI`, `IRI_YEAR`, `NHS`, `OWNERSHIP`, `PSR`, `ROUTE_NUMBER`,
`SPEED_LIMIT`, `STRAHNET_TYPE`, `THROUGH_LANES`, `TOLL_*`, `TRUCK`,
`URBAN_CODE`.

* `URBAN_CODE` is the **Census urban-area code** — the natural join key to
  metro extents (analogous to NTD's `UACE`).
* `F_SYSTEM` (functional system: Interstate / other freeway / principal arterial
  / minor arterial / collector / local) is the **roadway-class** axis.
* `AADT` / `AADT_COMBINATION` / `AADT_SINGLE_UNIT` / `TRUCK` is the
  **traffic-volume** axis (the validation target).
* `THROUGH_LANES`, `SPEED_LIMIT`, `IRI`/`PSR` are **capacity / condition** axes.
* Linear referencing is `ROUTE_ID` + `BEGIN_POINT`/`END_POINT` + shapefile
  linework — **not** a point coordinate.

### Geographic detail / spatial mapping

Each HPMS record is a **road-section line** (polyline in the shapefile /
Feature Layer). There is **no point lat/lng** — geography is the line's
geometry plus `STATE_CODE`/`COUNTY_CODE`/`URBAN_CODE`. To map to the repo's
grid, the natural path is:

1. **Clip** to metro: select segments whose `URBAN_CODE` matches the metro's
   Census urban area, or whose `COUNTY_CODE`/`STATE_CODE` + shapefile geometry
   intersects the dashboard's `metro_index` bbox (the `URBAN_CODE` path is
   more precise for multi-county metros like NYC).

2. **Line→H3 covering.** Intersect each segment's polyline with the repo's
   tiles. The proposal is **H3 resolution 5** as the primary context tile
   (the dashboard's context tile, `apps/api/src/serving/dashboard.py:1417`
   context), with an optional res 7–9 rollup for micro-unit comparison. Two
   implementation options: (a) **midpoint approximation** — map the segment's
   midpoint to H3-5/7 (cheap, leaf-feasible, proven in this module); (b)
   **true covering** — `h3.polyfill` / `ogr2ogr` polyline→H3 covering (accurate
   for long segments that cross many res-7 cells; needs `geopandas`/`h3-py` and
   is the "heavy geoprocessing" the memo deferred).

3. **Attribute assignment.** Once a segment maps to one or more H3 cells,
   attach its attributes (`F_SYSTEM`, `THROUGH_LANES`, `SPEED_LIMIT`, `AADT`)
   to those cells. Long segments that cover many cells would have their
   attributes **replicated** across cells (or length-weighted, in a full
   producer).

4. **Comparison leg.** Overlay the proposed local-DOT centerlines/AADT on the
   **same H3-5 cells** and report coverage and attribute disagreement — the
   four-metric design from the memo (spatial coverage, attribute completeness,
   release lag, incremental model value).

**Why H3-5.** The dashboard context layer already tiles on H3 res-5 parents
(§ dashboard `metro_index`); the memo's H3-5 join is therefore the honest
target for a baseline roadway layer. Res 7–9 remain honest for the overlay
comparison, but a single HPMS segment (often hundreds of meters to kilometers)
will naturally span many res-9 cells — per-res-9 attribution without
line-splitting would be smearing.

### Volume (documentation-derived, not measured in this run)

The national arterial shapefile is ~758 MB; per-state zips vary. A single
metro (NY: ~10k segments, IL: similar, CA/Bay Area: similar order) is a small
slice of the state file after `URBAN_CODE` filtering — but the *download* is
still the whole state zip / FeatureLayer, not a paginated API. The full
producer cost is therefore **bulk download → clip → H3 covering**, not
incremental pagination.

---

## Urban Signal fit

Urban Signal units are strictly nested: **metro bbox → division bbox(es) →
submarket → H3 cells 7–9** (`spatial/h3_indexer.py`: res 7 ≈ 5.16 km², res 8 ≈
0.74 km², res 9 ≈ 0.105 km²). The dashboard's context layer is **H3 res 5**
(`dashboard.py:1417` metro tiles). Each event feed is bbox-filtered at ingest,
then each row → `h3_res7/8/9` via `H3SpatialIndexer.get_multi_res_hierarchy`.

**HPMS's granularity is the right *kind* for a context layer, wrong shape for
an event feed.** A segment is **larger than a res-9 cell** and often larger than
a res-7 cell; it must be *covering-assigned* to the cells it crosses. This is
the opposite of the LODES "block is finer than H3" (clean rollup) and analogous
to the HMDA "tract is larger than H3" problem — except HPMS is a **line**, not
a polygon, so the covering is line→H3 rather than centroid→H3. The honest
target is therefore **H3 res 5 (dashboard context) and res 7 (macro)**; res 8/9
are honest only after explicit line-splitting whose per-cell signal is mostly
shared across adjacent cells.

Required (future) mapping work, if ever registered:

1. **Metro clip.** `URBAN_CODE` (Census urban-area) filter or `COUNTY_CODE` +
   geometry intersect against the repo's metro bbox (exact list in
   `METRO_META`). County-only over-counts for city-scoped metros (cf. Norfolk
   finding in the LODES validation) — use `URBAN_CODE` or bbox intersect.

2. **Line→H3 covering.** Convert each segment polyline to its covering set at
   res 5 (and res 7 for the comparison leg). Midpoint→H3 is the cheap leaf
   approximation; `h3.polyfill`-style covering is the accurate version for long
   arterials. Needs `geopandas` + `h3-py` (new deps, heavy).

3. **Attribute attachment.** Replicate or length-weight `AADT`, `F_SYSTEM`,
   `THROUGH_LANES`, `SPEED_LIMIT`, `IRI` onto the covering cells.

4. **H3→division/submarket.** Reuse `get_division_for_coordinate` /
   `find_nearest_submarket` on segment midpoints (or on each covering cell's
   center) — but long segments that straddle a division boundary genuinely cover
   two divisions, so midpoint-assignment misattributes boundary arterials
   (needs covering, not centroid).

**Does it add coverage the current feed-derived signals do not provide?** Partly.
The feed families — permits, 311, SLA, deeds, crime, evictions, STR,
street-cut — are all **events**. HPMS measures the **roadway infrastructure
baseline**: functional class, lane count, speed limit, pavement roughness
(`IRI`/`PSR`), and traffic load (`AADT`). That is independent coverage on the
**roadway-capacity / traffic-exposure** axis, which no event feed produces.
Concretely: `STREET_CUT` records the *cut event* (a disruption), not the
underlying lane count or the AADT that the cut disrupts; `CRIME`/`SLA` are
unrelated. So HPMS is **not redundant** with `DEEDS` or the event feeds — it is
an orthogonal baseline.

But its *value* is **slow and coarse**: annual, 7–8-year publication lag, line-
not-point, state-QA-varying. It can only ever be a **trailing infrastructure
context/anchor**, never a leading or short-term change signal. Under the repo's
rule (a signal is retained only if it adds independent coverage *and* clears
its family gate at target resolution/timeliness), HPMS clears "independent
coverage" on roadway/traffic, but **fails "usable at event-feed cadence" for
scoring** — it clears both only for a **baseline context** role, and even there
it needs a spine change.

---

## Three-metro feasibility (concept, not measured)

Same proposal as the 2026-08-26 US-171 comment; metros chosen as registered
metros with strong local-DOT centerline + AADT sources for the comparison leg:

| city_id | Metro | State(s) | HPMS slice | Local DOT comparison source (confirm in execution) | FIPS / URBAN_CODE notes |
|---|---|---|---|---|---|
| `nyc` | New York City | NY (+NJ for the metro) | `NY_2018_PR` FeatureServer or `NY.zip` shapefile; `URBAN_CODE` for the NYC urbanized area (also NJ side) | NYC DOT Street Centerline (CSCL) + NYC traffic-volume / AADT counts (NYC Open Data) | NY is a high-QA state; NYC metro spans NY/NJ — clip by `URBAN_CODE` + bbox |
| `chicago` | Chicago | IL | `IL_2018_PR` / `IL.zip` | Chicago Data Portal street centerline + city traffic-count / AADT (CDOT) | Cook County 17031 + collar counties; single-state QA |
| `san_francisco` | San Francisco Bay Area | CA | `CA_2018_PR` / `CA.zip` (large) | SFMTA / SF Open Data street centerline + traffic counts | Alameda 06001, SF 06075, etc.; Bay Area spans 9 counties — URBAN_CODE essential |

(From `METRO_META` at `apps/api/src/serving/dashboard.py:1417`; 49 registered
metros. The memo proposed these three; any of the 49 with good local DOT data
is substitutable.)

- **Expected ingest path.** Pull the state Feature Layer (ArcGIS
  `.../FeatureServer/0/query?where=URBAN_CODE+IN+(...)` or whole-state
  download) or the state zipped shapefile; filter to the metro's `URBAN_CODE`
  set (or county + bbox if `URBAN_CODE` coverage incomplete); map each
  segment's polyline → H3-5 (and res 7) covering; attach `AADT`/`F_SYSTEM`/
  `THROUGH_LANES`/`SPEED_LIMIT` to covering cells; intersect the same H3-5
  cells with the local-DOT centerline/AADT overlay; compute the four metrics.

- **Feasibility of the *download + filter* step: moderate.** Per-metro slice is
  small after filtering, but the download is the whole-state zip / Feature Layer
  and the covering needs `geopandas` + `h3-py`. The *comparison leg* (local DOT
  centerline/AADT on the same H3-5 cells) needs a second data fetch (Socrata
  for NYC/Chicago/SF).

- **Resolution ceiling.** Only **H3-5 (dashboard context) and H3 res-7 (macro)**
  are honest without explicit polyline-splitting. Res 8/9 are reachable only
  via covering with length-weighting; per-res-9 attribution of a kilometer-long
  arterial without splitting is pure replication.

### The four metrics (memo-concrete, not yet measured here)

For the three metros, once the geoprocessing lands:

1. **Spatial-match coverage** — fraction of metro H3-5 tiles (and res-7 cells)
   with ≥1 HPMS segment covering them.
2. **Attribute completeness** — % of segments carrying `AADT` / `IRI` /
   `SPEED_LIMIT` / `THROUGH_LANES` (by state, then metro).
3. **Release lag** — reporting year vs. publication year (expect ~7–8 years on
   the public geospatial release; check `data.transportation.gov` for a fresher
   vintage).
4. **Incremental model value** — predictive lift of HPMS context over existing
   municipal event feeds (AUC/MAE delta) — the only metric that tells whether
   the baseline actually improves the downstream model.

---

## Independent coverage check (vs. the existing feed families)

| Dimension | Existing feed-derived signals | HPMS roadway/traffic context |
|---|---|---|
| Unit | geolocated **event**, H3 cell (res 7–9) | **road-section line** → H3-5 context / res-7 macro |
| Latency | near real-time (daily/weekly) | **annual, ~7–8-year publication lag** on the public geospatial extract |
| Concept | *events* (permit, complaint, sale, crime, eviction, disruption) | *infrastructure baseline* (class, lanes, speed, condition, traffic load) |
| Coverage | only metros with that feed | **every Federal-aid road section nationwide** (but spatial format may not fully cover all) |
| Unique axes | none on roadway class / traffic load | **functional system, through-lanes, speed limit, AADT, IRI/PSR** |
| Redundant with | `STREET_CUT` (disruption-shape overlap, but HPMS is the *capacity* that disruption impacts) | **Not redundant** — no event feed measures roadway class or traffic volume |

**Does it add independent coverage?** Yes, **cleanly** on the roadway-capacity /
traffic-exposure axis (functional class, lane count, speed, AADT, IRI), which no
event feed or `DEEDS` reconstructs. But it is **orthogonal-slow**: it is an
annual baseline, not a change detector, so it can only inform **context priors**
(micro-market infrastructure character), never a short-term leading signal. Under
the repo's gate, it clears "independent coverage" but fails "usable at
event-feed cadence for scoring" — it clears both only as a **baseline context**
(wiring cost: a new signal family + bulk-file/FeatureServer producer + line→H3
covering, all spine).

---

## Risks and dependencies (mapped to the issue's risks)

1. **"Annual state submissions make this baseline context, not a near-real-time
   signal."** **Confirmed, binding for any LIMS/scoring role.** Apr 15 / Jun 15
   state filing + multi-year publication lag → HPMS can **never be a feed**;
   it can only ever be a **baseline context/anchor** (period_type="year"), same
   conclusion class as LODES/QCEW/HMDA — but even slower (7–8 years vs. 12–18
   months for HMDA). The incremental-model-value ablation is the only honest
   test of whether this slow baseline is worth the producer cost.

2. **"Geometry, coverage, and attribute quality can vary by state; versioning
   and state-specific QA are required."** **Confirmed and binding.** FHWA's own
   caveats (geodetic accuracy/topology not evaluated; spatial format may not
   fully cover all Federal-aid highways; GIS summaries can diverge from Highway
   Statistics; state-originated records) mean a **per-state QA and version pin**
   is required. The 758 MB national arterial set and per-state Feature Layers
   are the versioned artifacts to pin. Boundary metros (NYC: NY/NJ) inherit
   **two QA regimes**; `URBAN_CODE` filtering must be per-state.

3. **"Confirm public-download mechanics and reuse terms before any nationwide
   backfill."** **Public domain (17 U.S.C. § 105), no auth, two mechanised
   paths.** State zipped shapefiles (2011–2017) and 2018 Hosted Feature Layers
   are free, unauthenticated public downloads / ArcGIS queries. No API key, no
   registration. Reuse is **public domain**, but FHWA attaches the accuracy and
   coverage caveats above, and the underlying state DOT QA must be versioned.
   The `data.transportation.gov` path may be fresher — **confirm it before any
   nationwide backfill**, as the memo flags.

4. **Line→H3 covering dependency (new, analogous to HMDA's tract-centroid
   dependency).** The repo has **no line→H3 producer** today. Midpoint→H3 is the
   cheap leaf approximation (implemented in `hpms_context.py`); true polyline
   covering needs `geopandas` + `h3-py` and `h3.polyfill`-style logic, which is
   the "heavy geoprocessing" the memo deferred. Boundary arterials that straddle
   two divisions genuinely cover two divisions — centroid/nearest misattributes
   them; covering is required for correctness.

5. **Integration-model dependency (decisive, same class as LODES/QCEW/HMDA/NTD).**
   No `FeedType` exists for a non-event, line-aggregate baseline. Current
   families: `PERMITS`, `COMPLAINTS_311`, `SLA`, `DEEDS`, `CRIME`, `STREET_CUT`,
   `EVICTIONS`, `STR`. HPMS needs a **new** baseline family (`ROADWAY_BASELINE`
   / `TRAFFIC_CONTEXT`), a **new producer archetype** (bulk zip / FeatureServer
   → clip → line→H3 covering + attribute fan-out), and **new aggregate storage**
   (H3-5 / division lane/AADT/class aggregates, not `h3_res7/8/9`-on-event rows) —
   exactly the spine/interlock change `docs/agents/parallel-streams.md` gates,
   and out of scope for this leaf stream. The annual vintage also suggests a
   **year-versioned table**, not a watermarked event stream.

---

## Recommendation

**DEFER — do not register now; validation is complete.** HPMS is authoritative,
free, public-domain, and nationally uniform, and its **functional-system class,
through-lanes, speed limit, and AADT/I RI** are genuine independent coverage
that no event feed provides (orthogonal, not redundant). **Do not register**
because (a) it is **annual with a ~7–8-year publication lag** on the public
geospatial extract, so context-only and very slow; (b) it is **linework, not
points** — no per-row coordinate, no `watermark_col`, bulk delivery — so it
needs a **new line→H3 producer** that the pipeline does not have; (c) it needs
a **spine/interlock change** (new `FeedType` + bulk/FeatureServer producer +
H3-5/H3-7 covering + aggregate tables) that is out of scope for a leaf stream;
and (d) **state-varying QA** and incomplete spatial coverage mean per-state
versioning and a `data.transportation.gov` freshness check are required before
any nationwide backfill. The **incremental model-value ablation** (the fourth
metric) is the honest gate for a future REGISTER — if HPMS context does not
improve the model over the event feeds, even the context case is weak.

**What unblocks a future REGISTER (any one, or in combination):**

1. A positive **scope decision** for a structural **roadway/traffic baseline
   context layer** — a new `ROADWAY_BASELINE`/`TRAFFIC_CONTEXT` family, its own
   year-versioned H3-5 / division aggregate table, and a bulk/FeatureServer
   producer (download → `URBAN_CODE`/bbox clip → line→H3 covering via
   `geopandas`+`h3-py` → attribute fan-out) — treated as context/LIMS-exempt
   (precedent: street-cut "disruption context only — never a LIMS term" and NTD
   "transit-demand context only").

2. A concrete consumer that needs it — e.g. a **roadway-capacity / traffic-
   exposure prior** (lanes + functional class + AADT as a prior under the
   hardcore `base_lims` baselines), or a **commercial-site / logistics /
   street-impact exposure** view no event feed supplies. The consumer must
   accept **period_type="year"** semantics and a multi-year lag.

3. A **freshness verification** on `data.transportation.gov` or a direct FHWA
   contact (Thomas Roff) confirming a **post-2018 public geospatial vintage**
   exists with documented reuse terms, plus a per-state QA/versioning note.

4. If both arrive, **register selectively** — only metros where the roadway-
   exposure prior is material — as a **metro-normalized annual index at H3-5
   (dashboard context) and H3 res 7 (macro)**, via line→H3 covering with
   length-weighting for long segments, and explicitly calibrated so lane/AADT
   values are **ratios/indices within a metro**, never raw national counts.

Until then, the event feeds (and street-cut for the disruption axis) remain the
correct timely signals, and HPMS should not be wired in as a scoring input. A
small, **unintegrated** leaf helper (`apps/api/src/spatial/hpms_context.py`)
demonstrates midpoint→H3 assignment, attribute completeness, release-lag, and
coverage computations so the future register path is concrete; it is not
imported by any spine or pipeline code.

---

## Leaf artifact

`apps/api/src/spatial/hpms_context.py` — pure functions:
`attribute_completeness`, `coverage_fraction`, `release_lag_years`,
`segment_midpoint_to_h3`, `rollup_segments_to_h3`, with
`apps/api/tests/unit/test_hpms_context.py`. No spine import; leaf-only. The
polygon-covering producer (geopandas + `h3.polyfill`) is left for the REGISTER
path — the leaf proves the metric plumbing without the heavy dep.

