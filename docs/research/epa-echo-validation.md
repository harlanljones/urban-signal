# EPA ECHO — validation as a compliance-event signal for neighborhood environmental risk

**Date of research: 2026-08-26.** ECHO (Enforcement and Compliance History Online)
is EPA's public window onto facility-level environmental compliance and
enforcement across the major media programs (CAA, CWA/NPDES, RCRA, SDWA) plus
CERCLA/EPCRA and formal EPA enforcement cases. This is a *validation* document
for Linear US-170 — no feed was registered, no `FeedType` was added, and no
spine file was touched. A small, spine-free leaf module
(`apps/api/src/spatial/epa_echo.py`) and its unit test accompany this write-up
to prove the geometry/severity mapping is feasible without a spine edit.

## Method, and its limits

I validated on three layers, in order:

1. **Product facts.** Read ECHO's live "About the Data" page (data sources,
   refresh dates, completeness notes) and the "Web Services" catalog page. These
   are EPA's own descriptions of program coverage, extraction cadence, and the
   explicit robotic-query prohibition — quoted, not reconstructed from memory.
2. **Live API probes.** Issued real `curl` requests against the documented
   machine interfaces: the `echo-rest` REST search services, the ArcGIS
   `ECHO_FAC` MapServer, and the bulk-download (ECHO Exporter / National
   Datasets) URLs exposed on the Data Downloads page.
3. **Feasibility of the spatial mapping.** Wrote and unit-tested a leaf module
   that maps one geocoded ECHO facility compliance event to the repo's H3 res
   7/8/9 hierarchy using the existing `H3SpatialIndexer` (no new joiner, no
   spine import).

**Limits.** The `echo-rest` REST search services returned **HTTP 403
(Forbidden)** to a scripted client in this session (even with a browser
User-Agent); the documented `echo.epa.gov/echo-rest/.../cwa_rest_services`
path 404s and the services appear to have moved to `echogeo.epa.gov`, where
they block programmatic access (consistent with ECHO's published warning). I
could **not** pull a live JSON event sample through the REST API, so per-event
field shapes are asserted from documentation, not from a downloaded record. The
ArcGIS `ECHO_FAC` service name resolved but returned no usable facility layer
metadata in this session. The ECHO Exporter / National Datasets bulk ZIP URLs
**were** confirmed live and are the realistic ingestion path. "Incremental value
against current signals" is assessed by *concept* against the repo's feed
families, not by running an ablation (this is a leaf research stream; no
pipeline was run).

---

## Headline verdict

**DEFER.** EPA ECHO is a genuinely event-shaped, geocoded, reasonably fresh
compliance/enforcement signal measuring a dimension **no existing Urban Signal
feed covers** — environmental compliance burden at the facility level (air/water/
hazardous-waste/drinking-water violations, inspections, formal enforcement
actions, penalties). Unlike the LODES case (granularity + cadence mismatch),
ECHO fits the repo's event→H3 model *structurally*: each facility has FRS
lat/long, and events carry dates, so a producer could map rows to H3 7–9 exactly
like the existing event feeds. Its refresh (weekly snapshot, formal enforcement
available for all years) is far timelier than LODES' ~28-month lag, so it *could*
be a leading-ish contextual risk signal rather than a trailing anchor.

But two facts keep it at DEFER rather than ADOPT:

1. **Event sparsity.** Formal enforcement actions, major violations, and
   inspections are *rare* per neighborhood — orders of magnitude sparser than
   permits/311/SLA/deeds. Most H3 res-9 cells will carry zero events. The signal
   is only usable as a sparse division-scale risk prior with `dynamic_spatial
   _fallback` smoothing, never as high-frequency velocity.
2. **Integration is a spine change.** ECHO has no `FeedType`, and the only
   reliably accessible delivery is **bulk file download** (Exporter / FRS / per-
   program ZIPs) or a **bot-blocked REST API** — neither matches the existing
   `PaginatingClient` (Socrata/ArcGIS/CKAN) producer archetype. A real
   registration needs a new `FeedType` (e.g. `EPA_ECHO` / `COMPLIANCE`),
   a bulk-download producer, and per-city registry entries — all spine edits
   gated by `pytest -m interlock` (see `docs/agents/spine-manifest.txt`:
   `config.py`, `city_registry.py`, `producers/*` are spine). That is explicitly
   out of scope for this leaf stream. A leaf module demonstrating the geometry
   mapping is included; the wiring is not.

---

## Source assessment

- **What it is / programs.** ECHO consolidates EPA national data systems of
  record: **ICIS-Air** (CAA), **ICIS-NPDES** (CWA permits, limits, DMRs),
  **RCRAInfo** (hazardous waste handlers), **SDWIS/Fed** (drinking water),
  **ICIS FE&C** (formal enforcement across CAA/CWA/RCRA/SDWA/CERCLA/EPCRA/FIFRA/
  MPRSA/TSCA), plus NNCR (noncompliance report), TRI, GHGRP, and context layers.
  For a *neighborhood risk* signal the directly relevant event classes are
  facility **violations**, **inspections/compliance evaluations**,
  **enforcement actions/cases**, and **penalties** — all timestamped.
- **Access / terms.** Federal government work (17 U.S.C. § 105), public domain;
  no API key for the downloads. **But** ECHO's "About the Data" page states
  verbatim: *"ECHO is not designed for large scale data transfers or robotic
  queries. EPA reserves the right to disable users that initiate robotic,
  programmed queries."* This was corroborated live: `echogeo.epa.gov/echo-rest/
  services/echo/cwa_rest_services` returned **HTTP 403** to a scripted client.
  Practical consequence: **ingest via the bulk-download ZIPs, not the REST
  API.** (The Exporter ZIP `echo_exporter.zip` and `frs_downloads.zip` and
  per-program ZIPs were confirmed live at `https://echo.epa.gov/files/
  echodownloads/...`.)
- **Geographic detail / geocoding.** Facility identification (including
  **latitude/longitude**) comes from EPA's **Facility Registry Service (FRS)**,
  which "is updated weekly." So each facility already carries a point coordinate
  — no separate geocoder is required to place an event in H3, *provided* the
  bulk extract carries FRS coordinates (the `frs_downloads.zip` and the Exporter
  do). **Caveats:** FRS coordinate quality is uneven for smaller/non-major
  facilities (some geocoded to ZIP/centroid), and ECHO itself warns geospatial
  data from external parties "are not independently verified by EPA." This is the
  ticket's named **geocoding risk**: a single large facility's violations can
  dominate a cell, and coordinate noise can misplace a sparse event.
- **Update cadence / latency.** Data are "typically refreshed on a weekly
  schedule from EPA source databases" (most source systems last extracted
  2026-08-22, next 2026-08-29 in the live table). Lag between source entry and
  ECHO appearance is "a week up to three months." **Timeliness is good** — this
  is a near-monthly signal, not a multi-year-lag one. Coverage window: facility
  search shows past **5 years** of inspection/enforcement, the Detailed Facility
  Report shows **10 years**, and *all years* of formal enforcement are searchable.
- **Completeness / bias.** ECHO presents data "as-reported." Larger facilities
  are far more complete; "states are not required to report violations occurring
  at Clean Water Act non-major facilities," so non-major-facility violations may
  be absent. Interpretation must account for this structural under-reporting —
  the signal is biased toward *major* sources and toward states that report
  fully.
- **Volume.** The ECHO Exporter caps at **~1.5 million regulated facilities**
  nationwide. A metro subset (bbox-filtered, exactly like event feeds) is small
  — tens of thousands of facilities, a tiny fraction of the 1.5M, and the event
  subset (violations/enforcement in-window) is far smaller still. Volume is a
  non-issue; sparsity, not size, is the constraint.

---

## Urban Signal fit

Repo units nest **metro bbox → division bbox → submarket → H3 7–9**
(`spatial/h3_indexer.py`). Each event feed is bbox-filtered at ingest, then each
row → `h3_res7/8/9` via `H3SpatialIndexer.get_multi_res_hierarchy`.

ECHO fits this shape **better than LODES did**:

1. **Event, not aggregate.** A violation/inspection/enforcement is a
   timestamped event at a point — the same primitive as permits/311/SLA/deeds.
   No block-aggregate rollup or crosswalk join is needed; the FRS point *is* the
   geocoder.
2. **Coordinate → H3.** `latlng_to_cell(lat, lng, 9)` + parent chain, identical
   to existing feeds. The accompanying leaf module does exactly this and is
   unit-tested.
3. **Metro filter.** Bbox-filter the facility extract on the repo's metro bbox,
   exactly as event feeds are filtered.
4. **Sparse-cell smoothing.** `H3SpatialIndexer.dynamic_spatial_fallback` already
   rolls res-9 → res-8 → res-7 when density is thin; this is precisely the
   mechanism a sparse compliance signal needs (most res-9 cells will be empty).

**Does it add independent coverage?** Decisively yes, in *kind*. The current
feed families (permits, 311, SLA licenses, deeds, crime, evictions, STR,
street-cut) measure **development, services, transactions, and public-safety
events** — none measure **environmental compliance burden**. A cluster of RCRA
hazardous-waste violations or CWA NPDES major violations in a division is a
neighborhood risk dimension no existing feed produces, and it is a plausible
explanatory/context prior for hard-to-explain submarket distress.

**The catch is integration, not data.** A `FeedType` is required for a
`CityRegistration` to expose a signal, and each `DatasetSpec` assumes a
`PaginatingClient` with a `watermark_col` and `id_keys` per geolocated event row.
ECHO violates those assumptions: delivery is bulk ZIP (no watermark; `createdate`
/ extract-date only) or a bot-blocked REST API. Registering it "as a feed"
requires a **new signal family** (`COMPLIANCE`/`EPA_ECHO`), a **new producer
archetype** (download → parse ZIP → FRS-coordinate → H3 rollup), and **per-city
registry entries** — all spine/interlock edits. That is exactly the work this
leaf stream must not do.

---

## Risks and dependencies (mapped to the ticket's named risks)

1. **"Event sparsity."** **Confirmed and binding for any per-cell scoring.**
   Formal enforcement and major violations are rare; most H3 res-9 cells will be
   empty. Mitigation already exists in-repo: `dynamic_spatial_fallback` to res
   8/7 and a division-scale aggregation. The signal must be treated as a sparse
   **risk prior / context layer**, never as high-frequency velocity or a LIMS
   term. (Precedent: street-cut is "disruption context only — never a LIMS
   term.")
2. **"Geocoding."** **Partially mitigated by the source, partially real.**
   FRS supplies facility lat/long, so no external geocoder is needed — but FRS
   coordinate quality varies (centroid geocoding for some facilities) and EPA
   explicitly disclaims verification of external geospatial data. Mitigation:
   trust FRS points, document coordinate-quality tiers, and rely on the
   spatial-fallback smoothing to absorb a small number of misplaced sparse
   events. A single major facility can still dominate a cell; flag
   facility-level rather than only cell-level.
3. **Robotic-query prohibition (newly surfaced).** **Confirmed live (HTTP 403).**
   The REST API is not a viable automated pipeline source. The realistic
   ingestion path is the **bulk-download ZIPs** (Exporter/FRS/per-program), which
   are live and anonymous. This reinforces that ECHO needs a *bulk-file*
   producer archetype, not a `PaginatingClient` — i.e. a spine change.
4. **Cadence vs. "freshness" expectation.** **Not a blocker — better than
   expected.** Weekly refresh with up-to-3-month source lag is timely enough for
   a trailing-context risk prior. Note the 5-year search window means very old
   events age out of the facility view; the leaf module's recency half-life
   (2.5 y) handles this by down-weighting stale events.
5. **Completeness bias.** **Real but acceptable for a prior.** Non-major-
   facility under-reporting means the signal reflects *major-source* compliance,
   not total. Document this as a known limitation; do not present an empty cell
   as "clean" — absence of ECHO events is not evidence of compliance.
6. **Integration-model dependency.** The decisive one. No `FeedType` exists for
   an environmental-compliance layer, and the only accessible delivery is bulk
   file (spine-bound). This is why the recommendation is DEFER, not ADOPT.

---

## Recommendation

**DEFER** — do not register now, but this is a *stronger* candidate than the
LODES validation and the data side is proven feasible. **Do not register**
because a feed registration is impossible in the current model without a spine/
interlock change: ECHO needs a new `FeedType` (`COMPLIANCE`/`EPA_ECHO`), a new
bulk-download producer archetype (the REST API is bot-blocked at HTTP 403, so
ingest must be the live Exporter/FRS ZIPs), and per-city registry entries — all
gated by `pytest -m interlock` per `docs/agents/parallel-streams.md`. Also, its
event sparsity and major-facility reporting bias mean it can only ever be a
**sparse division-scale risk prior / context layer**, not a cell-level velocity
signal. **Do not reject** it: unlike LODES there is *no granularity or cadence
mismatch* (FRS points map cleanly to H3 7–9; refresh is weekly), the geocoder is
built in (FRS), volume is trivial, and it measures a dimension (environmental
compliance burden) that no existing feed provides.

**What unblocks a future REGISTER** (any one, or in combination):

1. A scope decision that Urban Signal wants an **environmental-compliance
   context layer** — a new `COMPLIANCE`/`EPA_ECHO` signal family plus a
   bulk-file producer (download Exporter/FRS ZIP → parse → FRS-coordinate → H3
   rollup), treated as context/LIMS-exempt, mirroring the street-cut precedent.
2. A concrete consumer — e.g. an **explanatory "environmental-risk prior"** for
   a submarket (violation/enforcement density as a contextual factor behind
   hard-to-explain distress), or a screening overlay for industrial-adjacent
   divisions.
3. If both arrive, **register major-facility-heavy metros first** (those with
   dense CAA/CWA/RCRA majors — e.g. Houston, Chicago, Los Angeles, New Orleans'
   petrochemical corridor), as a **recency-weighted, division-scale compliance-
   risk index** at H3 res 7–9 with `dynamic_spatial_fallback`, sourced from the
   FRS-coordinate bulk extract pinned to an extract date, and explicitly labeled
   as reflecting *major-source* compliance only.

Until then, the existing event feeds remain the correct timely signal, and ECHO
should not be wired in as a scoring input. The leaf module
`apps/api/src/spatial/epa_echo.py` (imports only the leaf `h3_indexer`) is a
ready, tested building block for that future spine-bound registration.
