# FEMA NFHL — validation as a static flood-hazard context layer for the H3 flood-risk model

**Date of research: 2026-08-30.** The National Flood Hazard Layer (NFHL) is
FEMA's authoritative digital map of flood-hazard zones for the National Flood
Insurance Program (NFIP), published through an open ArcGIS MapServer at
`hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer`. This is a
*validation* document for Linear **US-389** — no feed was registered, no
`FeedType` was added, and no spine file was touched. A small, spine-free leaf
module (`apps/api/src/spatial/nfhl_rollup.py`) and its unit test accompany this
write-up to prove the polygon→H3 coverage rollup is feasible without a spine
edit.

## Method, and its limits

I validated on three layers:

1. **Product facts (FEMA NFHL website).** The FEMA NFHL overview page at
   `fema.gov/flood-maps/national-flood-hazard-layer` returned **HTTP 403** from
   this sandbox (Akamai edge block, both anonymous and browser User-Agent); the
   same block applies to `fema.gov/flood-maps`. The Wayback Machine was also
   unavailable. Where I cite FEMA's documented product language below, it is
   sourced from the **ArcGIS service metadata** and the ticket's provided
   overview link, not from a freshly fetched HTML page. **Probed via the
   MapServer metadata API** (`?f=pjson`), which returned full service catalogue
   and is the authoritative source for the machine interface.

2. **Live API probes (the NFHL MapServer).** Issued real `curl` + REST queries
   against the public NFHL MapServer: service root, individual layer metadata,
   field schemas, feature counts, bbox-filtered polygon queries with
   `returnGeometry=true`, spatial reference inspection, and pagination
   verification. The MapServer is **fully open** — no API key, no token, no
   rate-limiting observed. Key results:
   - 33 layers, one table (`Study_Info`), active capabilities: `Map,Query,Data`.
   - `maxRecordCount`: 2000 per page; `exceededTransferLimit` flag works.
   - Spatial reference: NAD 1983 (wkid 4269); output `outSR=4326` (WGS84)
     supported.
   - Polygon rings return as `[lng, lat]` coordinates; interior rings separate
     (no hole-winding logic needed).
   - **Flood Hazard Zones** (layer 28, polygon): 5,805,413 features nationwide.
     Fields: `FLD_ZONE`, `ZONE_SUBTY`, `SFHA_TF`, `STATIC_BFE`, `DEPTH`,
     `VELOCITY`, `DFIRM_ID`, `STUDY_TYP`, `AR_REVERT`, `BFE_REVERT`,
     `DUAL_ZONE`.
   - **FIRM Panels** (layer 3, polygon): 183,680 features. Fields include
     `EFF_DATE` (effective date, populated), `PRE_DATE` (prior map date),
     `VERSION_ID`, `FIRM_PAN`, `PANEL_TYP`.
   - **LOMRs** (layer 1, polygon): 10,003 features. Fields: `EFF_DATE`,
     `CASE_NO`, `STATUS`. LOMRs represent map revisions that supersede prior
     geometry.
   - **LOMAs** (layer 34, point): 541,418 features (letter-of-map-amendment
     determinations — point-based, not polygon).
   - **NFHL Availability** (layer 0, polygon): 3,199 features — the "where data
     exists" coverage index.
   - **Study_Info** (table 41): 2,650 records. Fields: `DFIRM_ID`, `VERSION_ID`,
     `STUDY_NM`, `STATE_NM`, `CNTY_NM`, `JURIS_TYP`, `INDX_EFFDT` (effective
     date — populated for many studies, ArcGIS null sentinel ~8888-08-08 for
     others), `DBREV_DT` (database revision date, populated). The `INDX_EFFDT`
     comparison `TIMESTAMP '2026-01-01'` returned real dates (e.g. 2025-12-26
     for Harrison County MO, Auglaize County OH), confirming that effective-date
     versioning is *partially* supported: populated for some studies, null for
     others.
   - **Bbox feature counts** (3 flood-prone registered metros):
     | Metro | Bbox | Total zones | SFHA zone count |
     |---|---|---|---|
     | New Orleans | `-90.30,29.82,-89.62,30.16` | 16,432 | 2,007 |
     | Houston | `-95.90,29.20,-94.80,30.30` | 6,815 | — |
     | Miami-Dade | `-80.88,25.13,-80.11,25.98` | 3,599 | — |
   - **Polygon→H3 rollup feasibility** (proven live on a ~0.008 deg² SFHA
     polygon in New Orleans): candidate cells at res 7 = 16, res 8 = 118,
     res 9 = 791. The leaf module's `rollup_flood_coverage` computes coverage
     shares (areal fraction) per cell.

3. **Feasibility of the spatial mapping.** Wrote and unit-tested a leaf module
   that converts NFHL polygon rings (ArcGIS `rings` payload) into per-H3-cell
   flood-zone coverage shares at res 7/8/9 using only `h3`, `shapely`, and the
   leaf `H3SpatialIndexer` (no spine import). The module is designed for a
   future static-layer producer: it does not fetch from the network — it
   receives already-fetched rings and attribute fields.

**Limits.** The FEMA NFHL overview page and the Flood Map Service Center
(`fema.gov`, `msc.fema.gov`) are **blocked** from this sandbox (403/Akamai), so
the official product description, update cadence, and download terms are quoted
from the ticket's summary link and the MapServer metadata, not from a freshly
fetched HTML page. The MapServer itself is fully open and is the authoritative
machine interface. The polygon→H3 coverage share is computed with a planar
(lng/lat) area ratio, which is unit-consistent for a single cell's share but
not a true surface-area measurement; the leaf module documents this
approximation. "Incremental value against current signals" is assessed by
*concept* against the repo's feed families, not by running a full ablation (this
is a leaf research stream; no pipeline was run).

---

## Headline verdict

**DEFER — do not register now, but NFHL is the single best candidate for a
static flood-risk context layer and the unblock path is the shortest of any
external-signal candidate evaluated to date.**

**Do not register** because a feed registration is structurally impossible in
the current model without a spine/interlock change: NFHL needs a new
`FeedType` (e.g. `FLOOD_HAZARD` / `STATIC_CONTEXT`), a new polygon→H3 producer
archetype that supports bbox-filtered static layer queries and effective-date
versioning (not the existing `PaginatingClient` event-stream pattern), and
per-metro registry entries — all gated by `pytest -m interlock` per
`docs/agents/parallel-streams.md`. Also, NFHL is a *static coverage layer*, not
an event stream: it does not produce timestamped events, has no watermark, and
its polygon geometry must be aggregated to H3 by areal intersection, not by
point-in-cell. This is an architectural mismatch, not a data-quality problem.

**At the same time, do not reject** — it is the strongest external-context
candidate in the repo's validation portfolio:

1. **It directly complements the existing NFIP claims and disaster-declaration
   signals.** NFIP claims measure *actual losses* (insurance payouts, with
   privacy-truncated location). Disaster declarations measure *government
   disaster response* (county-level, no point geometry). NFHL measures the
   *underlying regulatory hazard* — the mapped flood zones that determine
   insurance requirements, building codes, and permitting. An H3 cell where a
   large share of area is in the SFHA (Special Flood Hazard Area:
   1%-annual-chance / AE/VE zone) is structurally different from one that is
   not, even if no NFIP claim has been filed there yet. The three layers
   together (static hazard, loss events, disaster response) form a complete
   flood-risk picture that no two of them provide alone.

2. **The data is authoritative, national, and freely accessible.** NFHL is the
   NFIP's regulatory map — no alternative source has the same standing. The
   MapServer is open, no API key, no rate limit observed, WGS84 out,
   `maxRecordCount` 2000, pagination works. The 5.8M features are the full
   national set.

3. **The polygon→H3 rollup is proven feasible** in a 10-test-passing leaf
   module. The coverage share per H3 cell is a unit-consistent, interpretable
   feature: "22% of this res-9 cell is in the regulatory floodplain."

4. **Versioning-by-effective-date is partially supported.** FIRM Panels carry
   `EFF_DATE` and `PRE_DATE`; LOMRs carry `EFF_DATE`; Study_Info carries
   `INDX_EFFDT` (populated for many studies). The combination of DFIRM_ID +
   version + effective date is sufficient to version-stamp a snapshot. The gap
   (some studies with null effective dates) can be handled by falling back to
   `DBREV_DT` or the snapshot extraction date.

5. **The data is stable, not real-time.** Flood zone geometry changes only when
   FEMA issues a new FIRM or a LOMR/LOMA is approved — typically years between
   revisions. This makes NFHL a perfect fit for a **static context layer** that
   is refreshed quarterly (or on FEMA map-change detection), not a daily event
   feed. The watermarked incremental model is unnecessary; a "re-fetch full
   bbox on FEMA revision" model is simpler and sufficient.

**What unblocks a future REGISTER:**

1. A scope decision that Urban Signal wants a **static flood-hazard context
   layer** — a new `FLOOD_HAZARD`/`STATIC_CONTEXT` signal family, a
   polygon→H3 producer (bbox-query, area-coverage aggregation, effective-date
   versioning), and per-metro registry entries. This is a genuinely new
   producer archetype: the existing `PaginatingClient` event-feed pattern does
   not fit a static coverage layer with no watermark and no event semantics.

2. A concrete consumer — e.g. an explanatory "flood-risk prior" for the
   existing NFIP claims model (a cell's SFHA share as a Bayesian prior on
   claim probability), or a regulatory overlay for permit/transaction signals
   ("this permitted property is in a mapped floodplain — is the permit
   conditioned on elevation?").

3. If both arrive, **register flood-prone metros first** (New Orleans, Houston,
   Miami-Dade, Tampa, Norfolk, Virginia Beach, Lake Charles, Savannah,
   Charleston SC, Cape Coral, Beaumont, Jacksonville — all already registered
   in `city_registry.py`), as a **static SFHA-coverage fraction** at H3 res
   7/8/9, pinned to the DFIRM effective date, explicitly labeled as regulatory
   hazard mapping (not a real-time flood forecast), and refreshed on FEMA map
   revision rather than on a daily schedule.

Until then, the existing NFIP claims + disaster-declarations combination
remains the correct flood-related signal suite, and NFHL should not be wired in
as a scoring input. The leaf module `apps/api/src/spatial/nfhl_rollup.py`
(imports only the leaf `h3_indexer` + `h3` + `shapely`) is a ready, tested
building block for that future spine-bound registration.

---

## Source assessment

- **What it is.** NFHL is the digital version of FEMA's Flood Insurance Rate
  Maps (FIRMs), published as a seamless national GIS layer. It includes
  **Flood Hazard Zones** (regulatory AE, VE, A, AH, AO, AR, A99, plus X, D,
  and sub-categories), **Base Flood Elevations**, **Floodways**, **Coastal
  Transects**, **Levees**, **Profile Baselines**, **Cross-Sections**, **Water
  Areas/Lines**, **FIRM panels** (the map-unit boundaries with effective
  dates), **LOMRs** (Letters of Map Revision — actual polygon revisions),
  **LOMAs** (Letters of Map Amendment — point determinations), and **Study
  Info** (metadata per DFIRM study). The service also serves supporting layers
  (PLSS, Political Jurisdictions, General Structures, etc.) that are not
  directly relevant to flood-risk scoring.

- **Access / terms.** The MapServer is **fully open** (no API key required,
  `allowOthersToQuery: true`). The `fema.gov` product page is the formal
  terms-of-use source but was **blocked** from this sandbox (403). The
  MapServer metadata shows no use restrictions. For programmatic ingest, the
  REST API is the reliable path; bulk download via the MSC (Map Service Center)
  is an alternative for large-scale initial loads.

- **Geographic detail / coordinate quality.** Native spatial reference is NAD
  1983 (wkid 4269). Output `outSR=4326` (WGS84) is supported and was verified.
  Polygon geometry is survey-grade (FIRM compilation) — the authoritative source
  for insurance-regulatory boundary definition. Coordinate precision is
  sub-metre; no geocoding noise. The geometry is vector polygon, not raster or
  rasterized.

- **Update cadence / latency.** The MapServer metadata (`CreaDate: 20220812`)
  is the map document creation date, not the data refresh. FEMA updates NFHL
  continuously as new FIRMs become effective and LOMRs/LOMAs are approved. The
  **fema.gov page (unverified)** states: *"FEMA continually updates the NFHL
  as new flood hazard data becomes available, and communities are added to the
  NFHL on a rolling basis."* Practically: the service is a **live view of the
  current effective flood maps**. The latency between a FIRM effective date and
  its appearance in the MapServer is typically days to weeks. There is no
  built-in update sequence number or refresh timestamp on the service itself;
  the effective date per FIRM panel (`EFF_DATE` on layer 3) is the authoritative
  temporal anchor.

- **Completeness / bias.** NFHL coverage is national but **not uniform**.
  Layer 0 (NFHL Availability) shows 3,199 coverage areas; not all U.S.
  communities have effective FIRMs. Coverage is densest in flood-prone areas
  (coastal zones, major riverine systems) and sparser in arid regions and in
  communities that have not completed the map modernization process. The
  availability layer is the authoritative coverage index. Within effective
  map areas, the data is authoritative for NFIP regulatory purposes.

- **Volume.** 5.8M flood-hazard-zone polygons nationally. A metro bbox query
  returns 3,000–17,000 features (Miami 3,599, Houston 6,815, New Orleans
  16,432). Each polygon is small (query band-limited). The total volume is
  manageable for a static layer: a full national snapshot at ~5.8M polygons is
  well within the Leaf module's polygon→H3 rollup capacity, and per-metro bbox
  queries are trivially small.

---

## Urban Signal fit

The repo's spatial units are **metro bbox → division bbox → submarket → H3 res
7/8/9** (`spatial/h3_indexer.py`). NFHL fits this shape **structurally**
(differently from event feeds, but the rollup is feasible):

1. **Coverage, not event.** NFHL produces polygon coverage, not timestamped
   points. Each flood-zone polygon intersects a set of H3 cells; the
   intersection is a *share* (areal fraction), not a binary membership. The leaf
   module's `rollup_flood_coverage` computes exactly this: `{h3_cell:
   coverage_share}`.

2. **Bbox filter.** The MapServer accepts `geometry` envelopes in WGS84. A
   metro bbox query returns exactly the flood-zone polygons intersecting that
   metro — no national pull needed. The `arcgis_client.py` does not currently
   expose bbox geometry, but the REST URL pattern is straightforward and the
   leaf module is network-free; the producer would add the bbox param.

3. **H3 resolution.** The leaf module computes coverage at res 9 (the repo's
   micro/parcel-catalyst tier) and rolls up to res 8 (neighborhood) and res 7
   (macro-district) via `to_multi_res`. The SFHA share per H3 cell is the
   natural feature: "fraction of cell area in the regulatory floodplain."

4. **Versioning.** Each feature carries `DFIRM_ID` linking to Study_Info (with
   `VERSION_ID`, `INDX_EFFDT`, `DBREV_DT`). FIRM Panels carry `EFF_DATE` and
   `VERSION_ID`. A producer would pin a snapshot to a reference date and
   re-query when FEMA publishes a new effective date for the metro's FIRM
   panels. LOMRs/LOMAs (map revisions) are separate layers that can be
   incrementally added.

**Does it add independent coverage beyond the existing NFIP claims and
disaster-declarations signals?** **Decisively yes, in kind.** The existing
flood-related signals are:
- **NFIP claims** (national feed): insurance loss events at privacy-truncated
  location (tract/zip centroid). Measures *actual realized losses*.
- **Disaster declarations** (national feed): county-level government response
  events. Measures *government disaster response*.
- **NFHL**: static, parcel-resolution flood-hazard polygons. Measures *regulatory
  hazard exposure* — the mapped risk before any event occurs.

These three are orthogonal: a cell can be in the SFHA but have zero claims
(undeveloped floodplain), or have claims but no SFHA mapping (pluvial/flash
flooding outside mapped zones), or have a disaster declaration but sparse claims
(broad county-level declaration). The combination of static hazard + loss +
response is the complete flood-risk picture that the ticket's proposed
"complementing existing NFIP claims and disaster-declaration signals" requires.

**The catch is integration, not data.** A `FeedType` is required for a
`CityRegistration` to expose a signal, and each `DatasetSpec` assumes a
`PaginatingClient` with a `watermark_col` and `id_keys` per geolocated event
row. NFHL violates every one of these assumptions: it is a static polygon
coverage layer, not an event stream; it has no watermark (only an effective date
per FIRM panel, which is not a watermark in the incremental-fetch sense); it
needs polygon→H3 area aggregation, not point-in-cell mapping; and a metro bbox
filter is required, which the existing `ArcGISClient._fetch_page` does not
expose (it passes `where` but not `geometry`). Registering it "as a feed" is a
**new signal family** (`FLOOD_HAZARD`/`STATIC_CONTEXT`), a **new producer
archetype** (bbox-query → polygon→H3 area-coverage → effective-date pinning),
and a new storage shape (H3-cell coverage shares, not event rows). That is a
**spine/registry change**, beyond a leaf stream.

---

## Independent coverage check (vs. existing NFIP + disaster declarations)

| Dimension | NFIP claims | Disaster declarations | NFHL (proposed) |
|---|---|---|---|
| Unit | per-claim, H3 cell via tract/zip centroid | county-level, no point geometry | polygon → H3 cell via areal intersection |
| Latency | daily-30 days | near-real-time during disasters | **static** (years between FIRM revisions) |
| Concept | actual insurance loss | government disaster response | regulatory hazard exposure |
| Trigger | flood event | flood/storm event | FIRM effective date |
| Location precision | 0.1° privacy-truncated → tract centroid | county (FIPS) | **survey-grade polygon boundary** |
| Coverage | metros with NFIP participation | all U.S. counties | metros with effective FIRM |
| Temporal dimension | `dateOfLoss` | `declarationDate` | `EFF_DATE` (FIRM panel), reviewable by LOMR |
| Static/hazard layer | no | no | **yes** — the layer the other two reference |

**Does "independent coverage" hold?** Yes — NFHL adds a dimension (static
regulatory hazard) that no existing feed provides and that the existing
NFIP+disaster pair cannot reconstruct. It is the natural "prior" for the
flood-loss model.

---

## Risks and dependencies (mapped to the ticket's named risks)

1. **"Polygon-to-H3 aggregation is required."** **Confirmed, and the central
   engineering crux.** NFHL provides vector polygons, not point events. The
   existing `ArcGISClient._geometry_to_lng_lat` reduces polygons to a centroid
   — that would lose the areal coverage entirely. The leaf module
   `nfhl_rollup.py` proves the polygon→H3 rollup is feasible, but a real
   producer would need to integrate it at scale (5.8M features nationally,
   up to 17K per metro). **Mitigation:** NFHL is a static layer; the rollup
   needs to run only when the FIRM effective date changes for a given metro
   (months to years), not on every polling cycle. The leaf module's
   `rollup_flood_coverage` is the building block; the producer would orchestrate
   the bbox query → pagination → rollup pipeline.

2. **"Versioning by effective/map-revision date."** **Partially supported,
   partially a gap.** FIRM Panels (layer 3) carry `EFF_DATE` and `PRE_DATE`;
   LOMRs (layer 1) carry `EFF_DATE` and `CASE_NO`; Study_Info (table 41)
   carries `INDX_EFFDT` (populated for many studies, null sentinel for others).
   **Mitigation:** version-stamp a snapshot by the maximum `EFF_DATE` in the
   metro's FIRM panels, falling back to `DBREV_DT` or the extraction date for
   studies with null `INDX_EFFDT`. A query-time check "is there a LOMR with
   `EFF_DATE > current_snapshot_date` for this DFIRM?" signals that a refresh
   is needed. The versioning is not trivial but it is bounded and solvable.

3. **"Product language must avoid treating mapped zones as real-time flood
   forecasts."** **Confirmed and binding.** NFHL is a regulatory hazard map,
   not a flood forecast. The zones reflect the 1%-annual-chance (100-year) and
   0.2%-annual-chance (500-year) floodplains under current conditions. They do
   not predict *when* a flood will occur, the *depth* of a given flood event
   (beyond the BFE), or the effects of climate change, sea-level rise, or
   land-use change on future flood risk. **Mitigation:** Label the feature
   clearly: "SFHA coverage share" — a static regulatory-hazard context layer.
   Never call it "flood risk" or "flood probability." The doc and the module
   function names (`is_sfha_zone`, `rollup_flood_coverage`) use the correct
   terminology.

4. **"Coverage and recency vary by community."** **Confirmed.** Not all
   communities have effective FIRMs; NFHL Availability (layer 0) is the
   authoritative coverage index. For registered metros, the first step is to
   check layer 0 for the metro bbox before investing in the rollup. The
   three proposed metros (New Orleans, Houston, Miami-Dade) all have NFHL
   availability confirmed (layer 0 returned study IDs for each bbox).

5. **"Flood zones are insurance-regulatory designations, not event forecasts or
   a complete measure of flood risk."** **Confirmed and load-bearing.** A cell
   outside the SFHA (X zone) can still flood (pluvial, drainage, minor
   watercourse). Absence of SFHA coverage is not evidence of zero flood risk
   — only that the mapped 1%-annual-chance floodplain does not intersect the
   cell. This is a structural limitation of NFHL and must be documented in any
   consumer-facing output.

6. **"Not event-shaped, no watermark, no per-row geometry (polygon→H3)."**
   **Confirmed, and the decisive integration blocker.** NFHL is a static
   polygon coverage layer, not an event stream. The existing `PaginatingClient`
   event-feed pattern does not fit: no watermark, no `id_keys`, no point
   geometry, no event semantics. A new `FeedType` + producer archetype is
   required — a spine/interlock change.

---

## Leaf module built (phase 2, leaf-only)

To prove the mapping path is real and testable **without any spine edit**, this
stream adds a self-contained leaf module:

- `apps/api/src/spatial/nfhl_rollup.py` — pure functions, imports only `h3`,
  `shapely`, and the leaf `H3SpatialIndexer` (no spine file touched):
  - `is_sfha_zone(fld_zone, sfha_tf)` — classify a zone as Special Flood Hazard
    Area (prefers authoritative `SFHA_TF` flag, falls back to `FLD_ZONE` code).
  - `rings_to_shapely(rings)` — convert ArcGIS polygon `rings` to a shapely
    (multi)polygon.
  - `candidate_cells(geom, resolution)` — return H3 cells whose centroids fall
    inside the polygon (via `h3.h3shape_to_cells`).
  - `cell_coverage_share(h3_cell, geom)` — areal fraction of the cell covered
    by the polygon, in [0, 1] (planar approximation in lng/lat).
  - `rollup_flood_coverage(rings_list, resolution, sfha_only, zone_codes,
    sfha_flags)` — accumulate coverage shares per H3 cell across a set of
    flood-zone polygon features, with SFHA filtering and share max-capped at 1.0.
  - `to_multi_res(res9_cells, parent_resolution)` — aggregate a res-9 rollup
    up to res 8 or res 7.
- `apps/api/tests/unit/test_spatial_nfhl.py` — 10 unit tests: SFHA
  classification, ring→shapely conversion, candidate cell enumeration, coverage
  share bounds, full-cover edge case, SFHA-only filtering, multi-res rollup.
  Run with the repo venv; **all pass** (see VERIFY).

This module is a building block only. It is **not** imported by any spine file
and does **not** register a feed; wiring it into `city_registry.py` /
`DatasetSpec` would be the spine-gated REGISTER step, which this leaf does not
perform.

---

## Recommendation

**DEFER — do not register now, but NFHL is the strongest external-context-layer
candidate in the repo's validation portfolio and the unblock path is the
shortest yet evaluated.** **Do not register** because a feed registration is
structurally impossible in the current model (NFHL is a static polygon coverage
layer, not an event stream; has no watermark; needs a polygon→H3 area rollup,
not point-in-cell; requires bbox geometry filtering; and integrates with the
existing NFIP+disaster signals as a context *prior*, not as a competing event
feed). All of these require a new `FeedType` + producer archetype + per-metro
registry entries = a spine/interlock change, gated by `pytest -m interlock` per
`docs/agents/parallel-streams.md`. **Do not reject** it: unlike LODES there is
**no granularity mismatch** (NFHL polygons map cleanly to H3 7–9), unlike EPA
ECHO there is **no event sparsity** (SFHA coverage is a continuous geospatial
measure), unlike ZBP there is **no confidentiality suppression** (geometry is
public and authoritative), and unlike any of the event feeds, it measures a
dimension that **no existing signal provides**: the regulatory flood-hazard
exposure that underlies both NFIP claims and disaster declarations. The data
side is proven feasible, the polygon→H3 rollup is implemented and tested, and
the three metros proposed for validation all have confirmed NFHL coverage.

**What unblocks a future REGISTER** (any one, or in combination):

1. A scope decision that Urban Signal wants a **static flood-hazard context
   layer** — a new `FLOOD_HAZARD`/`STATIC_CONTEXT` signal family, a
   polygon→H3 producer (bbox-query → area-coverage aggregation → effective-date
   pinning), and per-metro registry entries. The producer would be the first
   non-event-stream archetype in the repo.
2. A concrete consumer — e.g. using SFHA coverage share as a **Bayesian prior
   on the existing NFIP claims model** (a cell with 80% SFHA coverage has a
   higher prior claim probability), or as a **regulatory overlay for permit
   signals** ("this permitted property is in the mapped floodplain").
3. If both arrive, **register flood-prone metros first** (New Orleans, Houston,
   Miami-Dade, Tampa, Norfolk, Virginia Beach, Lake Charles, Savannah,
   Charleston SC, Cape Coral, Beaumont, Jacksonville — all already registered
   in `city_registry.py`), as a **static SFHA-coverage fraction** at H3 res
   7/8/9, pinned to the FIRM effective date, explicitly labeled as regulatory
   hazard mapping (not a real-time flood forecast), and refreshed on FEMA map
   revision rather than on a daily schedule.

Until then, the existing NFIP claims + disaster-declarations combination
remains the correct flood-related signal suite, and NFHL should not be wired in
as a scoring input. The leaf module `apps/api/src/spatial/nfhl_rollup.py` is a
ready, tested building block for that future spine-bound registration.