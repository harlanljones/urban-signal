# USGS Annual National Land Cover Database (NLCD) — validation as a physical-change context layer

**Date of validation: 2026-08-25.** Every source fact below was probed from the live
USGS/EROS and MRLC pages on that date. Facts that come from a primary source are
attributed inline; anything I could not verify is explicitly labelled
**UNVERIFIED** or, where it is arithmetic derived from a verified spec, shown as
**derived**. Where USGS does not publish an exact figure (e.g. compressed tile
sizes) I give a clearly-labelled **ESTIMATE** rather than a fabricated number.

---

## 1. Method, and its limits

**Method.** I read the repo's spatial model (registration, urban-unit geometry, H3
hierarchy) and then probed the official Annual NLCD source pages for the six
science products, the temporal/version history, the CONUS-only coverage, and the
distribution channels. Storage figures are derived from two verifiable inputs —
the 30 m pixel and the registered metro bounding boxes — plus a labelled
compression assumption.

**Limits.**

- **Product-version drift is real and is the dominant long-term risk.** The
  collection has already gone 1.0 → 1.1 → 1.2 (Oct 2024 → ~2025 → June 2026), and
  each release **rewrites the entire 1985–current time series**, not just the
  newest year. A feed that snapshots "the latest layer" is silently invalidated
  when the next collection lands. Any registered ingestion must record a source
  **collection version** (e.g. `c1/v1.2`) and an **effective date** and treat a
  collection bump as a re-snapshot, not a delta.
- **Raster tooling does not exist in this repo.** I grepped `apps/api` for
  `geotiff/raster/tif/gdal/rasterio` — the only raster hits are the CARTO basemap
  declared as a MapLibre `raster` **source** in `serving/dashboard.py` (a basemap
  tile url, not local pixel data). There is no raster ingest, no `platform`
  value for it, no `FeedType` for land cover, and no H3 zonal-stats engine. The
  `DatasetSpec.platform` contract reads `"socrata" | "arcgis" | "ckan" | "csv"`
  (`city_registry.py`). Registering NLCD is therefore **not a leaf edit** — it
  needs a new platform, a new FeedType, a raster producer, and a
  pixel-to-H3 aggregation step.
- **Volume figures are order-of-magnitude.** USGS does not publish a per-tile or
  per-mosaic byte size on the pages I probed. I give derived uncompressed math and
  a labelled compressed estimate; nobody should sign off on infrastructure off
  these numbers without a ~5 GB real download.
- **Coverage outside CONUS is explicitly unsupported today.** The product suite is
  CONUS-only; "products for Alaska and Hawaii are planned" and an existing FAQ
  address "are Annual NLCD data available outside CONUS". Registered Urban Signal
  metros are all CONUS, but anyone scaling beyond the lower 48 must treat this as
  a hard coverage boundary.
- I did **not** download a single raster to verify a tile is a Cloud-Optimized
  GeoTIFF or to measure real bytes. The AWS layout is documented as a template,
  and the exact live bucket path for release 1.2 is **UNVERIFIED** (see §3).

---

## 2. Headline verdict

**DEFER** (with a funded two-metro pilot).

Annual NLCD passes **source assessment outright**: it is U.S. federal **public
domain**, free to redistribute, CONUS-wide, 30 m, **annual back to 1985**, and it
provides exactly the physical-change signal municipal feeds cannot — impervious
delivery/walkability, developed-land expansion, vegetation and disturbance
transitions. The two-metro pilot is also **trivially cheap** (on the order of a
few hundred MB to a couple of GB, free via the MRLC AOI download path). It is NOT,
however, registerable **today**: the repo has no raster/Geo-TIFF platform, no land
-cover FeedType, no H3 zonal-aggregation engine, and every registered feed changes
on a sub-annual cadence while NLCD changes annually with a post-collection
rewrite. That is a spine-shaped capability, not a leaf, and the issue's own
"Proposed validation" is the correct first step. **DEFER the registration; run the
validation now as a leaf** to lock the ingestion path and storage/cost profile, and
in parallel plan the raster+H3 capability as a spine stream. The verdict would flip
to REGISTER only after (a) the two-metro pilot confirms an H3-level change signal
composes with permits/311, and (b) the raster platform exists to hold a
collection-versioned snapshot.

---

## 3. Source assessment

| Attribute | Finding | Basis |
|---|---|---|
| Products (six) | Land Cover, Land Cover Change, Land Cover Confidence Index, Fractional Impervious Surface, Impervious Descriptor, Spectral Change Day of Year | USGS Annual NLCD Product Suite page; MRLC `data` page |
| Spatial resolution | 30 m | USGS "30-m spatial resolution"; MRLC TCC note (same 30 m grid family) |
| Coverage extent | **CONUS only**; Alaska & Hawaii "planned" | USGS Data Access + product suite pages |
| Temporal coverage | **1985 → 2025** (Collection 1.2, June 2026) | MRLC `data` page (published 2026-06-10) |
| Version history | C1.0 (1985–2023); C1.1 (+2024); **C1.2 (+2025)** | MRLC news; USGS banner "Collection 1.2 … adding 2025 data"; ScienceBase data-release title |
| Land-cover scheme | modified Anderson Level II (~16–20 classes) | USGS product suite page |
| Classification/validation | Reference dataset of **8,360** 30 m samples (C1.0), interpreters assign class per year 1984–2023 | USGS C1.0 Validation Tables + Reference Data Product pages |
| Data license / reuse | **Public Domain** (USGS); citation: "U.S. Geological Survey (USGS), 2024, Annual NLCD Collection 1 Science Products", DOI 10.5066/P94UXNTS | USGS landing + product-suite pages ("Sources/Usage: Public Domain") |
| Format | Raster (GeoTIFF family). Whether the CONUS mosaics are Cloud-Optimized GeoTIFFs is **UNVERIFIED** on the pages I probed; the S3 path is described as `/mosaic/` | USGS Data Access page |
| Download channels | EarthExplorer (Landsat ARD tile scheme); MRLC Web Viewer (AOI rectangle/polygon/GeoJSON/shapefile → email); MRLC Mosaic download (`mrlc.gov/data`); ScienceBase (full archive, item `655ceb8ad34ee4b6e05cc51a`); AWS S3 (us-west-2); WMS endpoint | USGS Data Access page |

**Key distribution detail — AWS S3 is a requester-pays bucket.** The documented path
is `s3://usgs-landcover/annual-nlcd/c1/v0/[region[cu-ak-hi]]/tile/h{xx}v{yy}/` and
`.../mosaic/`, hosted in **us-west-2 (Oregon)**, and "requester pays". Three
consequences: (1) reading it for a backfill accrues egress to your AWS account;
(2) the `[region[cu-ak-hi]]` component confirms a **cu** (CONUS) / **ak** / **hi**
split, reinforcing the CONUS-now boundary; (3) the **`c1/v0`** component looks
frozen at the September-2024 page date while the release is now **v1.2** — the
live bucket layout for release 1.2 is **UNVERIFIED** and must be re-checked before
any automation depends on it. The MRLC Viewer AOI download, by contrast, is **free**
and returns exactly the bbox you draw, which sidesteps requester-pays egress for
the pilot.

---

## 4. Urban Signal fit

### How a feed gets registered today (and why NLCD is outside it)

`get_dataset(city_id, feed)` (`city_registry.py:2482`) returns a `DatasetSpec`
(`city_registry.py:245`) keyed by `FeedType` (`city_registry.py:213`). Feeds are
municipal **event** streams — PERMITS, COMPLAINTS_311, SLA, DEEDS, CRIME,
STREET_CUT, EVICTIONS, STR. `DatasetSpec.platform` drives the paginator
(`PaginatingClient`, `city_registry.py:230`); current values are
`socrata`/`arcgis`/`ckan`/`csv`. `resolve_endpoint` (`city_registry.py:2458`) only
handles a `calendar-year → endpoint` map for jurisdictions that publish one file per
year — an interesting precedent, but it points at a Socrata/CSV record endpoint,
not a raster.

NLCD is a **raster layer**, not an event stream: it needs a
`platform="raster"`, a land-cover `FeedType`, a rasterio/GDAL producer able to
window-read the metro bbox, and an H3 zonal mean/mode aggregation. All four are
absent. This is the structural blocker behind the DEFER verdict.

### Clipping to city bounds

Raster clipping follows the existing metro-bbox contract, exactly like the
municipal feeds do. The relevant registered boxes:

- **New Orleans** (`new_orleans.py:23`): min_lat 29.82, max_lat 30.16,
  min_lng −90.30, max_lng −89.62. Already deliberately tuned to exclude the
  north-shore St. Tammany license leaks — a nice property for a raster clip, which
  has no geographic pruning of its own.
- **Austin** (`austin.py:26`): min_lat 30.10, max_lat 30.62, min_lng −98.05,
  max_lng −97.52.

A windowed read of the CONUS mosaic over that bbox (or, for the pilot, the MRLC
Viewer AOI clip of the same rectangle) yields the per-pixel values for exactly the
cells the city pipeline already reasons over. Division/submarket resolution then
reuses the existing coordinate → division → submarket path.

### Composing with the H3 aggregation model

The repo's model (`h3_indexer.py`) operates on a res-7/8/9 hierarchy with nominal
cell areas res 7 ≈ 5.16 km², res 8 ≈ 0.74 km², res 9 ≈ 0.105 km². The spatial
model default `graph_builder.resolution = 8` and events resolve to res-7/8/9 via
`get_multi_res_hierarchy`.

Combining that with a 30 m pixel (0.0009 km²) gives a **pixel-per-cell
downsampling** that is the single most important fit fact:

| H3 res | Cell area | 30 m pixels per cell | Fit for NLCD change |
|---|---|---|---|
| 7 | ~5.16 km² | ~5,700 | Macro-district rollup — very stable; ratios smooth out single-pixel noise |
| 8 | ~0.74 km² | ~820 | Neighborhood submarket — **recommended aggregation level**; stable % impervious per cell |
| 9 | ~0.105 km² | ~117 | Micro block — **borderline**; ~117 px/cell means classification noise dominates a cell's change, so per-cell derived features need a confidence/no-pixel floor |

Implication: **aggregate change metrics at res 8**, roll up to res 7 for
division/submarket, and treat res 9 as noisy for *derived change features* — still
usable for a raw impervious % but flag low-confidence cells (use the Land Cover
Confidence product as the per-cell gate, or drop cells under a pixel-count floor).
Composition rule: the NLCD-derived features are **slow-cadence context on the same
H3 cells the event streams already populate** — they are a per-cell attribute
(year-over-year Δimpervious, Δdeveloped-land, class-transition flags), not another
event stream. That keeps them out of the event-level LIMS input path and makes them
a legitimate contextual/validation signal.

---

## 5. Two-metro feasibility

### Chosen metros

**Austin** (fast-growth sunbelt, permits + 311 registered, ArcGIS) and **New
Orleans** (four feeds registered — permits/311/SLA/deeds, Socrata). Rationale: the
two metros maximise analytic contrast and each is already a verified, live-
registered city in the repo (see `docs/research/new-orleans-austin-verification.md`):

- **Austin** supplies the cleanest *developed-land expansion* signal — exurban
  subdivision and impervious-growth that NLCD fraction-impervious and land-cover
  change measure directly, and that the rich Austin permits feed can be compared
  against.
- **New Orleans** supplies the *infill / land-loss / coastal-disturbance* signal —
  a different change regime (developed-land drift, marsh/water transitions, post-
  disaster rebuild) with the most complete municipal comparison set (four feeds,
  including deeds).

Alternatives: **Denver** is a near-perfect stand-in for Austin (two-feed ArcGIS
partial city, high growth); **Norfolk** or **Detroit** would test a slower, older
infrastructure-change regime. Austin + New Orleans is the preferred pairing because
both are already the subject of a full verification pass.

### Expected raster-ingest path

1. **Pilot (avoid requester-pays, free):** draw each metro bbox as an AOI in the
   **MRLC Web Viewer** and request a clip of the two/three products we care about
   for the years we care about → get an emailed zipped clip. No S3 egress, no COG
   dependency, exact bbox.
2. **Products for the pilot:** Fractional Impervious Surface (Δimpervious),
   Land Cover (developed-land extent), Land Cover Change (class-transition flags).
   Optionally Land Cover Confidence (per-cell quality gate). Skip Impervious
   Descriptor and Spectral Change DOY for the pilot (added value is low relative to
   the extra bytes).
3. **Production (post-capability):** choose one of (a) full-mosaic snapshot into a
   collection-versioned partition `annual_nlcd/c1/v1.2/<year>/<product>.tif` via
   the requester-pays S3 bucket, or (b) a windowed COG read at ingest if the mosaics
   prove to be COGs (**UNVERIFIED**). Either way record **collection version +
   effective date**, and re-snapshot the whole series (not a delta) on a collection
   bump.

### Measurement against permits / satellite evidence

- **Lead/lag:** align NLCD Δimpervious/Δdeveloped at **res 8** by year against the
  metro's **permit issuance dates** (Austin `issue_date`, New Orleans `issuedate`)
  for the corresponding H3 cell. Test whether development-permit density leads
  year-over-year impervious gain and by how many years (expected 0–2 lead in
  Austin; potentially a longer / negative lag in NOLA rebuild). Because NLCD is
  annual and permits are event-level, compare *yearly sums* — NLCD cannot support
  sub-annual lead/lag.
- **Classification stability:** for each cell, compute the incidence of year-to-year
  class flip-flop of the *same* class (e.g. developed→undeveloped→developed) using
  the annual Land Cover series and the Confidence product; high flip-flop in a low
  -confidence cell is classification noise, not real change. Report a stability
  metric (share of cells whose primary class is unchanged across a sliding window)
  as a quality gate.
- **Recent satellite/local inspection:** reconcile a handful (e.g. 10–20) of the
  highest-Δimpervious res-8 cells at the newest available year against current
  high-res imagery (satellite/aerial) and, where available, the municipal permit
  location, to sanity-check that a detected change is real and on-time. Keep this a
  spot-check, not a full validation — the USGS reference dataset is the rigorous
  accuracy surrogate.
- **Success criterion:** per-res-8-cell Δimpervious and Δdeveloped-land should
  correlate positively with permit density at the appropriate lead/lag, and the
  classification-stability gate should reject < a few % of "change" cells as
  flip-flop noise. If those two pass in both metros, the registration case is
  strong.

---

## 6. Storage / cost profile

All sizes are **derived** from the 30 m pixel plus registered bounding boxes, or
labelled **ESTIMATE**. Uncompressed raw = pixels × 1 byte (uint8). Compressed
figures assume LZW/Deflate-style GeoTIFF compression on highly autocorrelated land
cover and are **ESTIMATES only** — USGS publishes no per-mosaic byte size on the
pages I probed, and no file was downloaded to verify.

Derived constants: CONUS conterminous area ≈ 8.08×10⁶ km² (standard ~3.1×10⁶ mi²),
30 m pixel = 9×10⁻⁴ km² → **≈ 9.0×10⁹ pixels**; single-band uint8 CONUS mosaic ≈
**9 GB raw** (uint16 ≈ 18 GB).

### Two-metro pilot

| Metro | bbox area (derived) | pixels @30 m (derived) | raw per product-year |
|---|---|---|---|
| New Orleans | ~2,470 km² | ~2.75×10⁶ | **~2.7 MB** |
| Austin | ~2,940 km² | ~3.26×10⁶ | **~3.3 MB** |

Combined pilot raw, 3 products (LndCov + LndChg + FctImp) × 41 years (1985–2025):
~6 MB × 3 × 41 ≈ **~0.74 GB raw**; compressed **ESTIMATE ~100–250 MB**. Trivial —
an order of magnitude smaller than a single NYC 311 backfill (~1.0M rows) and it is
**free** via the MRLC Viewer AOI path.

### National backfill

| Scope | Layer-years | Raw (uint8, derived) | Compressed (ESTIMATE) |
|---|---|---|---|
| Key context subset (LndCov + LndChg + FctImp) × 41 yr | 123 | ~1.1 TB | ~0.12–0.37 TB |
| Full six products × 41 yr | 246 | ~2.2 TB | ~0.25–0.75 TB |

Cost notes: the dominant cost is the **one-time backfill read**, and only via the
**requester-pays S3 bucket** does it hit your egress (us-west-2 egress pricing
applies; exact rate unverified, but at current rates the figure is modest —
low-hundreds of gigabytes of compressed reads once, then per-year deltas). The MRLC
AOI download avoids egress entirely but is not a bulk-backfill mechanism (email
clips). **Operational steady-state is cheap**: one new layer-year × key products
per year after the collection publishes. Recommend local/regional object storage for
the snapshot (not the requester-pays bucket) so re-reads are free.

---

## 7. Risks and dependencies, mapped to the issue

| Issue risk | Assessment | Handling |
|---|---|---|
| Annual cadence limits responsiveness | Confirmed — event streams resolve to sub-annual; NLCD is yearly | Use as slow-cadence context/validation only; never as an event-level input; aggregate yearly for lead/lag |
| 30 m resolution limits parcel-level interpretation | Confirmed — one pixel ≈ a small parcel; res-9 H3 ≈ ~117 px | Aggregate at res 8 (≈820 px/cell) as the recommended level; roll up to res 7; keep res 9 behind a confidence/pixel-count floor |
| Classification error | Real — C1.0 reference = 8,360 samples, per-year classes | Use Land Cover Confidence as a per-cell gate; report a classification-stability (flip-flop) metric |
| Product-version changes | **Dominant risk** — 1.0 → 1.1 → 1.2 rewrites the *entire* 1985–series | Record collection version + effective date; re-snapshot whole series on bump; do not treat a bump as a delta |
| Raster volume | Derived ≈ 6 MB/product-year pilot; ≈ 1.1 TB raw national (key products) | Pilot trivial (free AOI); national backfill is a one-time cost; store snapshots locally, egress only for S3 reads |
| Coverage outside CONUS | Confirmed — CONUS-only; AK/HI planned | Hard boundary; all current metros are CONUS; flag if the portfolio ever leaves the lower 48 |
| Distribution / reuse terms | Public Domain; requester-pays S3; WMS available | Free reuse; prefer MRLC AOI/WMS for pilot; use requester-pays only for national backfill and re-check the live bucket layout (UNVERIFIED `c1/v0` vs `v1.2`) |

---

## 8. Recommendation

**DEFER registration; run the two-metro pilot now (Austin + New Orleans) as a leaf
stream; plan the raster + H3 capability as a spine stream.**

The source clears the bar (public domain, annual 1985–2025, CONUS-wide, 30 m, and
it provides physical-change context municipal event feeds cannot). The blocker is
not the data — it is that **this repo cannot ingest a raster**. Registering it would
require a new `platform="raster"`, a land-cover `FeedType`, a rasterio/GDAL producer
with windowed reads, an H3 zonal-aggregation step, and a collection-versioning
scheme, all of which are spine-touching and absent today.

Concrete next steps, in order:

1. **Run the pilot (leaf, no code).** AOI-clip Austin + NOLA bboxes from the MRLC
   Viewer for Fractional Impervious + Land Cover + Land Cover Change (optionally
   Confidence), 1985–2025. Compute per-res-8 Δimpervious and Δdeveloped-land;
   compare with permit-dated feed signals for lead/lag; spot-check 10–20
   high-change cells against current imagery. Record the real compressed byte counts
   to replace the ESTIMATEs above.
2. **Verify the two unverified items** before any production work: (a) whether the
   CONUS mosaics are Cloud-Optimized GeoTIFFs (windowed-read friendly), and (b) the
   live S3 bucket path for release 1.2 (the documented `c1/v0` looks stale).
3. **Spin a spine stream** to add raster + H3-zonal capability (reusing the
   existing `DatasetSpec.extra["endpoint_by_year"]` idea — but versioned by NLCD
   *collection*, not calendar year — as a partial precedent). Gate it with
   `pytest -m interlock` per `docs/agents/parallel-streams.md`.
4. **Re-issue the REGISTER decision** only after 1 and 3 land and the H3-level change
   signal demonstrably composes with permits/311 in both metros.

One product/registration note for whoever picks it up: NLCD is a **per-cell
attribute**, not an event stream, so even once registered it should sit in the
signal-survey "context/validation" family (US-72 style), never as a LIMS input —
same asymmet rule that keeps NYC-only evictions out of LIMS.
