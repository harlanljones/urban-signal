# Annual NLCD land-cover change — validation as a physical-change contextual signal

**Date of validation: 2026-08-26.** This is the US-123 leaf deliverable. Source facts
are inherited from the live-probed research in `docs/research/annual-nlcd-layers.md`
(probed 2026-08-25, one day before this write) and are treated here as the verified
evidence base; that document carries the inline primary-source attributions, the
ESTIMATE/UNVERIFIED labels, and the two still-open verification items (COG status of
the CONUS mosaics; the live S3 path for release 1.2). This document re-validates
specifically against the US-123 framing — **annual land-cover *change* signals** — and
states the registration decision. No `.py` was touched; this is a validation, not a
registration.

## Method, and its limits

I validated on three layers, in order, reusing the prior pass:

1. **Product facts (probed 2026-08-25).** USGS Annual NLCD product-suite, MRLC `data`
   and Data-Access pages, and the ScienceBase data release. Used the program's own words
   for resolution, coverage, temporal extent, version history, classification scheme,
   license, and distribution channels — not memory.
2. **Spatial fit.** Mapped the 30 m raster grid onto the repo's H3 res-7/8/9 hierarchy
   (`spatial/h3_indexer.py`: res 7 ≈ 5.16 km², res 8 ≈ 0.74 km², res 9 ≈ 0.105 km²) to
   derive pixels-per-cell and a recommended aggregation level.
3. **Incremental-value assessment.** Compared NLCD change against the repo's existing
   *event* feed families by concept (not by running an ablation — this is a leaf
   research stream; no pipeline was run).

**Limits (carried from the prior pass).** No raster was downloaded; storage figures are
derived from the 30 m pixel plus registered metro bounding boxes (labelled ESTIMATE
where compressed). The CONUS mosaics' Cloud-Optimized-GeoTIFF status and the live S3
path for release 1.2 remain UNVERIFIED. Collection-version drift is treated as the
dominant long-term risk. "Incremental value" is a conceptual comparison, not a measured
ablation.

## Headline verdict

**DEFER — do not register now.** Annual NLCD is a *genuinely independent* physical-change
signal the municipal event feeds cannot produce: impervious-surface growth, developed-
land expansion, vegetation/disturbance transitions, and water/marsh loss at 30 m across
CONUS, **annually back to 1985**. The source is U.S. federal **public domain**, free to
redistribute, and the two-metro pilot is **trivially cheap** (free via the MRLC AOI
download; order of a few hundred MB to ~1 GB for Austin + New Orleans, 1985–2025, key
products). But it is **not registerable today** and a registration is **not** recommended
now, for two structural reasons:

- **The repo cannot ingest a raster.** There is no `platform="raster"` value on
  `DatasetSpec.platform` (contract reads `"socrata" | "arcgis" | "ckan" | "csv"`),
  no land-cover `FeedType`, no rasterio/GDAL producer, and no H3 zonal-aggregation
  engine. A registration would require all four — a spine/interlock change, out of
  scope for a leaf.
- **Cadence and rewrite semantics cap it to context.** NLCD is annual, and each new
  collection **rewrites the entire 1985–current series** (1.0 → 1.1 → 1.2 already
  happened). It can only ever be a *trailing* physical-context/validation layer, never
  an event-level or LIMS input. It cannot drive short-term change detection, which is
  the whole point of the event feeds.

DEFER the registration; run the validation pilot as a follow-up leaf; plan the raster +
H3-zonal capability as a separate spine stream. The verdict flips to **REGISTER** only
after (a) the two-metro pilot confirms an H3-level change signal composes with
permits/311, and (b) the raster platform exists to hold a collection-versioned snapshot.

---

## Source assessment

| Attribute | Finding | Basis |
|---|---|---|
| Products (six) | Land Cover, Land Cover Change, Land Cover Confidence Index, Fractional Impervious Surface, Impervious Descriptor, Spectral Change Day of Year | USGS product-suite + MRLC `data` pages |
| Spatial resolution | **30 m** | USGS "30-m spatial resolution" |
| Coverage extent | **CONUS only**; AK/HI "planned" | USGS Data Access + product-suite pages |
| Temporal coverage | **1985 → 2025** (Collection 1.2, June 2026) | MRLC `data` page (published 2026-06-10) |
| Version history | C1.0 (1985–2023); C1.1 (+2024); **C1.2 (+2025)** — each rewrites the whole series | MRLC news; USGS banner |
| Land-cover scheme | modified Anderson Level II (~16–20 classes) | USGS product-suite page |
| Validation sample | Reference dataset of **8,360** 30 m samples (C1.0) | USGS C1.0 Validation Tables |
| Data license / reuse | **Public Domain** (USGS); DOI 10.5066/P94UXNTS | USGS landing + product-suite ("Sources/Usage: Public Domain") |
| Format | Raster (GeoTIFF family); COG status **UNVERIFIED** | USGS Data Access page |
| Download channels | EarthExplorer; MRLC Web Viewer (free AOI clip); MRLC mosaic; ScienceBase; **AWS S3 (us-west-2, requester-pays)**; WMS | USGS Data Access page |

**Distribution detail that matters for cost.** The documented S3 path
`s3://usgs-landcover/annual-nlcd/c1/v0/[region[cu-ak-hi]]/...` is **requester-pays** and
hosted in us-west-2; the `c1/v0` component looks frozen at the Sept-2024 page date while
the release is now **v1.2** — the live bucket layout for 1.2 is **UNVERIFIED**. The
MRLC Web Viewer AOI download, by contrast, is **free** and returns exactly the bbox you
draw, sidestepping egress for the pilot.

---

## Urban Signal fit

### Why NLCD is outside the current registration model

`get_dataset(city_id, feed)` (`city_registry.py`) returns a `DatasetSpec` keyed by
`FeedType`. Feeds are municipal **event** streams — PERMITS, COMPLAINTS_311, SLA, DEEDS,
CRIME, STREET_CUT, EVICTIONS, STR. `DatasetSpec.platform` drives the paginator
(`PaginatingClient`); current values are `socrata`/`arcgis`/`ckan`/`csv`. NLCD is a
**raster layer**, not an event stream: it needs `platform="raster"`, a land-cover
`FeedType`, a rasterio/GDAL producer able to window-read a metro bbox, and an H3 zonal
mean/mode aggregation. All four are absent. This is the structural blocker behind DEFER
— and the reason this US-123 leaf is validation-only.

### Clipping to city bounds

A windowed read of the CONUS mosaic over a metro bbox (or, for the pilot, the MRLC Viewer
AOI clip of the same rectangle) yields per-pixel values for exactly the cells the city
pipeline reasons over. Registered boxes such as New Orleans (`min_lat 29.82, max_lat
30.16, min_lng −90.30, max_lng −89.62`) and Austin (`min_lat 30.10, max_lat 30.62,
min_lng −98.05, max_lng −97.52`) already deliberately exclude leakage-prone areas — a
nice property for a raster clip, which has no geographic pruning of its own. Division/
submarket resolution then reuses the existing coordinate → division → submarket path.

### Composing with the H3 aggregation model

| H3 res | Cell area | 30 m pixels / cell | Fit for NLCD change |
|---|---|---|---|
| 7 | ~5.16 km² | ~5,700 | Macro-district rollup — very stable; ratios smooth single-pixel noise |
| 8 | ~0.74 km² | ~820 | Neighborhood submarket — **recommended aggregation level**; stable % impervious/cell |
| 9 | ~0.105 km² | ~117 | Micro block — **borderline**; ~117 px/cell means classification noise dominates a cell's change; flag low-confidence cells (use the Confidence product or a pixel-count floor) |

**Implication:** aggregate change metrics at **res 8**, roll up to res 7 for division/
submarket, and treat res 9 as noisy for *derived change features*. Composition rule:
NLCD-derived features are **slow-cadence context on the same H3 cells the event streams
populate** — per-cell attributes (year-over-year Δimpervious, Δdeveloped-land, class-
transition flags), never another event stream. That keeps them out of the event-level
LIMS input path and makes them a legitimate contextual/validation signal (same family
that keeps NYC-only evictions out of LIMS).

---

## Proposed validation approach (the funded pilot)

Run as a follow-up **leaf** (no code; AOI clips + local raster math):

1. **Pilot metros:** **Austin** (fast-growth sunbelt — developed-land expansion; rich
   permits feed) and **New Orleans** (infill/land-loss/coastal-disturbance; four feeds
   incl. deeds). Both already verified live-registered.
2. **Products:** Fractional Impervious Surface (Δimpervious), Land Cover (developed-land
   extent), Land Cover Change (class-transition flags); optionally Land Cover Confidence
   as a per-cell gate. Free via MRLC Viewer AOI clip of each metro bbox.
3. **Aggregate:** zonal stats to res 8 (and res 7), 1985–2025.
4. **Lead/lag test:** align yearly res-8 Δimpervious/Δdeveloped against the metro's
   *permit issuance dates* for the same H3 cells; test whether permit density leads
   year-over-year impervious gain (expected 0–2 yr lead in Austin; longer/negative lag in
   NOLA rebuild). NLCD is annual, so compare *yearly sums* — it cannot support sub-annual
   lead/lag.
5. **Stability gate:** incidence of same-class year-to-year flip-flop using the annual
   Land Cover series + Confidence product; reject flip-flop cells as classification noise.
6. **Spot-check:** 10–20 highest-Δ res-8 cells against current high-res imagery + permit
   locations to confirm real, on-time change.
7. **Success criterion:** per-cell Δimpervious/Δdeveloped correlates positively with
   permit density at the appropriate lead/lag, and the stability gate rejects < a few %
   of "change" cells. If both pass in both metros, the REGISTER case is strong.

**Storage/cost (derived/ESTIMATE from prior pass).** Pilot raw ≈ 6 MB/product-year ×
3 products × 41 yr ≈ **~0.74 GB raw** (compressed ESTIMATE ~100–250 MB) — trivial and
free via AOI. National key-subset backfill ≈ 1.1 TB raw (0.12–0.37 TB compressed),
one-time, egress only via requester-pays S3; store snapshots locally afterward.

---

## Independent coverage check (vs. existing feed families)

| Dimension | Existing feed-derived signals | Annual NLCD land-cover change |
|---|---|---|
| Unit | geolocated **event**, H3 cell | **30 m raster** → H3 cell aggregate |
| Latency | near real-time (daily/weekly) | **annual**, with collection-rewrite |
| Concept | *events* (permit, complaint, sale, crime, eviction) | *physical stock/transition* (impervious, developed, vegetation/water) |
| Coverage | only metros with that feed | CONUS, every year 1985–2025 |
| Noise | none (record-level) | classification error (8,360-sample reference; Confidence product gates it) |
| Dimensions | event + type/date | impervious %, land-cover class + transitions, disturbance |

**Does it add independent coverage?** Yes, and uniquely: it measures the *physical* city
— impervious growth, sprawl, green-loss, coastal/disturbance change — that no municipal
event feed captures. It does **not** add a timelier or finer *event-count*; it is strictly
slower and aggregate. For the repo's scoring goal (event velocity + value at H3, then
ablation into LIMS) NLCD can contribute a **context/validation anchor** (e.g. "this
division is a sprawl node"), but cannot drive short-term change detection. Under the
repo's rule (a signal is retained only if it adds independent coverage and clears its
family gate), NLCD clears "independent coverage" but not "usable at target
resolution/timeliness for *scoring*"; it clears both only for a **context** role.

---

## Risks and dependencies (mapped to the issue)

1. **"Annual cadence limits responsiveness."** **Confirmed, and binding for any LIMS
   role.** Event feeds resolve sub-annually; NLCD is yearly and collection-rewritten.
   Use as slow-cadence context/validation only; aggregate yearly for lead/lag. Never an
   event-level input.
2. **"30 m resolution limits parcel-level interpretation."** **Confirmed.** One pixel ≈
   a small parcel; res-9 H3 ≈ ~117 px. Mitigation is repo-native: aggregate at **res 8**
   (~820 px/cell), roll up to res 7, keep res 9 behind a Confidence/pixel-count floor.
3. **"Classification error."** **Real.** C1.0 reference = 8,360 samples, per-year classes.
   Use Land Cover Confidence as a per-cell gate; report a classification-stability
   (flip-flop) metric as a quality gate.
4. **Product-version changes — the dominant risk.** **Confirmed and the most dangerous.**
   1.0 → 1.1 → 1.2 each rewrites the *entire* 1985–series, not just the newest year. Any
   ingestion must record **collection version + effective date** and re-snapshot the whole
   series on a bump — never treat a bump as a delta.
5. **Raster volume / distribution.** Derived ≈ 6 MB/product-year pilot (free via AOI);
   ≈ 1.1 TB raw national (key products), one-time, egress only via requester-pays S3.
   Prefer MRLC AOI/WMS for pilot; store production snapshots locally. Re-check the live
   S3 path for 1.2 (`c1/v0` looks stale) and COG status before any automation.
6. **Coverage outside CONUS.** **Confirmed — CONUS-only; AK/HI planned.** Hard boundary;
   all current metros are CONUS. Flag if the portfolio ever leaves the lower 48.
7. **Integration-model dependency (the deciding one).** No `FeedType` exists for a raster,
   non-event layer. `FeedType` is PERMITS/COMPLAINTS_311/SLA/DEEDS + CRIME/STREET_CUT/
   EVICTIONS/STR. A NLCD registration needs a **new platform + new FeedType + raster
   producer + H3 zonal engine** — exactly the spine/interlock change that must gate on
   `pytest -m interlock` and is out of scope for this leaf. Also new: the stored shape is
   H3-cell aggregate rows, not the `h3_res7/8/9`-on-event rows the pipeline/Postgres sync
   assume.

---

## Recommendation

**DEFER — do not register now; run the two-metro pilot as a leaf; plan the raster + H3
capability as a spine stream.**

The source clears the bar (public domain, annual 1985–2025, CONUS-wide, 30 m, and it
supplies physical-change context no municipal feed can). The blocker is not the data — it
is that **this repo cannot ingest a raster** and that NLCD's cadence + collection-rewrite
semantics make it a trailing context/validation layer, never a leading or LIMS signal.
A registration would require a new `platform="raster"`, a land-cover `FeedType`, a
rasterio/GDAL producer with windowed reads, an H3 zonal-aggregation step, and a
collection-versioning scheme — all spine-touching and absent today.

**What unblocks a future REGISTER** (any one, or in combination):
1. A positive scope decision that Urban Signal wants a physical-change **context layer**
   at all — a new land-cover signal family, its own spec, its own H3-aggregate table, and
   a raster producer — treated as context/LIMS-exempt (precedent: street-cut "disruption
   context only — never a LIMS term").
2. A concrete consumer — e.g. an explanatory "sprawl/disturbance anchor" for a
   submarket, or a coastal/land-loss exposure view no event feed supplies.
3. If both arrive, **register Austin + New Orleans first** (both CONUS, fast-growth vs
   infill contrast, fully feed-registered), as a **year-over-year level context index at
   res 7–8**, pinned to the NLCD collection version with effective-date recording, and
   explicitly calibrated to treat each year as a noisy but order-preserving level.

**Code decision for this leaf:** **none added.** A land-cover metrics kernel would operate
on cell-level aggregates that do not yet exist (no raster platform, no zonal engine), and
the recommendation is DEFER — so writing one now would be speculative and untestable. Per
the leaf rule, code is added only when clearly warranted; it is not.

Until then, the existing event feeds remain the correct timely signal, and NLCD should
not be wired in as a scoring input. **No spine delta is required by this stream.**
