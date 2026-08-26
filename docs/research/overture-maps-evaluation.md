# Overture Maps — evaluation as a place-change spatial signal

**Date of research: 2026-08-26.** Sources were probed **live** from the Overture Maps
Foundation documentation (`docs.overturemaps.org`): the release calendar, the
Quickstart / data-access pages, the GERS (Global Entity Reference System) overview
and Data Changelog pages, and the Buildings and Places guides. Where a claim could
not be confirmed live it is marked **unverified**. This is a *validation* document —
no feed was registered and no `.py` in the spatial pipeline was touched. The verdict
follows the same shape as the other Tier-A validation leaves (`us101` LODES,
`us102` BFS, `us122` QCEW): a single adopt / reject / defer call backed by evidence.

## Method, and its limits

I validated on three layers, in order:

1. **Product facts (live).** Read the Overture release calendar, Quickstart, GERS
   overview, Data Changelog, and the Buildings / Places guides. I used Overture's own
   words for cadence, retention, changelog semantics, theme coverage, schema licensing,
   and attribute definitions — not memory.
2. **Access paths (live).** Confirmed the AWS S3 release + changelog bucket layouts,
   the Azure mirrors, the Overture Python CLI `--bbox` download, the DuckDB `spatial` +
   `httpfs` GeoParquet query pattern, and the STAC catalog that always points at the
   latest release.
3. **Repo-fit reasoning.** Mapped the confirmed geometry/attributes/changelog onto the
   repo's metro-bbox → division/submarket → H3 7–9 model (`spatial/h3_indexer.py`,
   `spatial/submarkets.py`) by *concept*, not by running a pipeline.

**Limits.** I did not download any Parquet or run a metro extraction — this is a leaf
research stream and no pipeline was executed. The exact per-metro building/place
counts and the real-world (`added`/`removed`) delta volume for a US metro are
**unverified** (asserted from the guides' global counts and the changelog schema).
The US-specific coverage figures (e.g. how complete US building footprints are versus
OSM/authoritative sources) are **not** individually measured; only the global
coverage statements from the guides are cited. The precise legal interpretation of
ODbL share-alike obligations on a derived/redistributed product is **unverified** —
flagged for legal review, not assessed.

## Headline verdict

**DEFER.** Overture is a genuinely independent, global, free, monthly, and — uniquely
among the validation wave — **ships a native change layer** (the per-release
`added` / `removed` / `data_changed` changelog keyed on stable GERS IDs). Its
building-footprint delta and place/POI churn measure a *physical-stock* and
*commercial-presence* surface that **no existing Urban Signal feed measures**: permits
tell you what was *authorized*, Overture tells you what was *detected built / opened /
closed*. That is independent coverage in kind, and it could cross-validate
permit-derived construction velocity and enrich commercial submarket fundamentals.

But it does **not fit the feed model in this repo** (`FeedType` / `DatasetSpec` /
`PaginatingClient` are built around geolocated, watermark-paginated municipal *event*
streams; Overture is a monthly snapshot + changelog with no per-row event, no
watermark, and GeoParquet delivery), so a feed registration is structurally impossible
without a **new signal family and a new producer archetype** — a spine/interlock
change, out of scope for a leaf stream. And three non-integration facts cap it to a
trailing **context/anchor**, never a leading signal or a LIMS term:

- **Imagery-derived lag.** Overture building footprints are largely ML-extracted from
  satellite/aerial imagery (Microsoft, Google Open Buildings) conflated with OSM and
  authoritative national datasets. A building appears in Overture when imagery *detects*
  it, not when it is permitted — months to years behind the permits feed. So it cannot
  beat permits on lead time.
- **60-day public retention.** Overture keeps only the last two monthly releases in its
  public S3/Azure buckets (GDPR "right to be forgotten" lifecycle policy). Long-term
  change trends require *self-hosting* historical snapshots; the published changelog is
  only a previous→current one-month delta.
- **Matching-pipeline churn.** GERS IDs are stable by design, but a re-match (e.g. the
  July-2026 matcher upgrade) causes one-time ID churn, so naive `added`/`removed` counts
  include pipeline artifacts, not only real-world change. Change counts need filtering
  (stable-`confidence` thresholds, bridge-file reconciliation) before they are a signal.

Shelf it; the unblock path is specific and small (below). This is the same shape as the
LODES defer, but Overture is the *stronger* candidate of the two because the change
layer is native rather than reconstructed.

---

## Source assessment

- **What it is / governance.** Overture Maps Foundation, a Linux Foundation project.
  Open map dataset released as Apache Parquet on cloud object storage; no membership or
  paywall to consume the public releases.
- **Themes (relevant).** `buildings` (footprints), `places` (POI points), `addresses`,
  `transportation`, `base`, `divisions`, `land`, `water`, `networks`. For this signal
  the load-bearing themes are **buildings** and **places**.
- **Access / terms of access.** **No API key, no registration, no authentication** —
  confirmed live: the Quickstart downloads directly from
  `s3://overturemaps-us-west-2/release/...` via the `overturemaps` PyPI CLI or DuckDB,
  and the STAC catalog `https://stac.overturemaps.org/catalog.json` always resolves the
  latest release. Three consumption paths, all keyless:
  1. **Overture Python CLI** — `overturemaps download --bbox=<w,s,e,n> -f geojson
     --type=building -o out.geojson` (transfers only the bbox of interest).
  2. **DuckDB + `spatial` + `httpfs`** — `SELECT ... FROM
     read_parquet('s3://overturemaps-us-west-2/release/<REL>/theme=buildings/type=building/*')
     WHERE bbox.xmin BETWEEN ... AND bbox.xmax < ...` (server-side bbox filter before
     transfer).
  3. **Azure Blob** mirror at the equivalent paths.
- **Geographic coverage.** **Global** for both buildings and places (per the guides).
  Buildings: OSM (highest conflation priority) + Esri Community Maps + authoritative
  national/municipal datasets + ML roofprints (Microsoft, Google Open Buildings, East
  Asia zenodo set). Places: ~74M global features as of the Aug-2026 release (Meta ~58M,
  Microsoft ~6.3M, Foursquare ~4.6M, plus smaller providers). The US is a
  high-quality region (strong OSM + authoritative US sources), unlike the Global South
  where ML-derived footprints dominate and precision is lower.
- **Update cadence / latency / retention.** **Monthly** since Oct 2023. Latest release
  at research time: **`2026-08-19.0`** (schema **v1.18.0**). Proposed schedule is
  ~monthly, with **major schema changes quarantined to Mar/Jun/Sep/Dec** (quarterly).
  **Retention:** only the last **two** monthly releases stay in the public buckets
  (~60 days); older releases are deleted by lifecycle policy. So "freshness" of the
  *current* release is ~monthly, but *history* is not publicly available — you must
  archive your own.
- **Change over time — the decisive feature.** Unlike LODES (which had no native change
  layer), Overture publishes a **Data Changelog** alongside every release:
  `s3://overturemaps-us-west-2/changelog/<RELEASE>/theme=.../type=.../change_type=.../*`,
  Parquet, sorted spatially, indexed on `id`. `change_type` ∈
  **`added`** (new ID this release), **`removed`** (ID present last release, absent
  now), **`data_changed`** (same ID, geometry or properties changed), **`unchanged`**.
  Stable **GERS IDs** make the join across releases trivial — change detection is a
  changelog scan filtered by metro `bbox`, not a fuzzy geometry diff. Caveat: the
  changelog contrasts only previous→current release (one-month delta); longer trends
  need self-archived release pairs. And GERS ID churn from matcher upgrades (the
  July-2026 release is explicitly flagged as a one-time elevated-churn release) means
  `added`/`removed` must be reconciled via bridge files and confidence-filtered.
- **Building / place attributes (the signal payload).**
  - *Buildings:* `building` (outer roofprint `(multi)polygon`) and `building_part`
    (OSM-only, parented by `building_id`); attributes include `has_parts`, `height`
    (features ≥900 m excluded), source provenance, and `bbox`. No per-building
    "construction date" — change is inferred from the changelog, not an attribute.
  - *Places:* point features with `names`, `taxonomy`/`basic_category` (new, replacing
    deprecated `categories` — removed Sep-2026), `confidence` (0–1; ≤0.2 dropped at
    build), `addresses`, `websites`, `brand`, `operating_status`, `sources`, and `bbox`.
    ~2,300-category OPC taxonomy with a ~280-label `basic_category` for roll-ups.
- **Volume.** Global buildings is hundreds of GB per release, but the **metro bbox
  subset via DuckDB is small** (tens of MB per metro per release) — the same bbox
  filter event feeds use, applied to the `bbox` column server-side. Manageable.
- **Licensing (a real risk).** **Buildings are ODbL** (because they include OpenStreetMap
  data) — share-alike + attribution obligations apply to any substantial derived/
  redistributed database. **Places are CDLA Permissive 2.0 + Apache 2.0** (no OSM) —
  permissive. **Addresses** are mixed permissive (CC0, CC BY 4.0, public domain by
  jurisdiction). A combined building+place product therefore carries a **mixed-license**
  surface; the ODbL share-alike on buildings is the constraint that needs legal review
  before any derived/redistributed output.

---

## Urban Signal fit

Urban Signal units are strictly nested: **metro bbox → division bbox(es) → submarket →
H3 cells 7–9** (res 7 ≈ 5.16 km², res 8 ≈ 0.74 km², res 9 ≈ 0.105 km²). Each event feed
is bbox-filtered at ingest, then each row → `h3_res7/8/9` via
`H3SpatialIndexer.get_multi_res_hierarchy`.

**Mapping is clean and reuses existing primitives:**

1. **Places → H3.** A place is a WGS84 point. `latlng_to_h3(lat, lng, r)` directly.
   No geometry work. (Trivial — better than event feeds only in that it is already a
   point.)
2. **Buildings → H3.** A building is a `(multi)polygon`. Use the building's
   representative point (centroid or a guaranteed-interior point) →
   `get_multi_res_hierarchy`; for higher fidelity, point-in-polygon to the H3 cell that
   actually contains it. Either way it reuses the existing indexer — no new joiner.
3. **Metro gate.** Both themes and the changelog carry a `bbox` column
   (`xmin/ymin/xmax/ymax`). Filter by the repo's metro bbox *exactly* as event feeds
   are bbox-filtered (server-side in DuckDB, or `--bbox` in the CLI) — no FIPS-join
   over-counting problem.
4. **Rollup → H3 / division / submarket.** Once features (or changelog `added`/
   `removed`/`data_changed` counts) carry an H3 res-9 cell, sum per cell and reuse the
   existing `dynamic_spatial_fallback` for sparse outer cells. Division/submarket
   resolution rides the existing coordinate path.

**Does it add coverage the current feed-derived signals do not provide?** Decisively
yes, in kind. The feed families — permits, 311, SLA licenses, deeds, crime, evictions,
STR, street-cut — are all *event streams*: geolocated transactions (a permit issued, a
complaint filed, a sale recorded). **None** measures the **physical building stock** or
the **commercial-presence surface**:

- **building-footprint delta** (net new / removed / altered structures) — a structural
  *physical* change surface; permits are the *authorization* of it, and Overture also
  captures unpermitted/informal construction permits miss;
- **place/POI churn** (businesses opening/closing, category mix) — overlaps SLA
  *licenses* (registrations) but adds a *detected physical existence* + taxonomy view
  that licenses do not (a license is not a storefront; an Overture place is).

That is genuinely independent, and it is the closest thing in the wave to a
cross-validation layer for the permit-derived construction-velocity signal and an
enrichment layer for commercial submarket fundamentals. No existing feed, and no
combination of them, reconstructs a building-stock or POI-churn surface.

**The catch is the integration model, not the data.** A `FeedType` is required for a
`CityRegistration` to expose a signal, and each `DatasetSpec` assumes a
`PaginatingClient` (Socrata/ArcGIS/CKAN `$offset` paging), a `watermark_col`, and
`id_keys` per geolocated event row. Overture violates every one of those assumptions:
it is a *stateless monthly GeoParquet snapshot + changelog*, keyed by a GERS `id` UUID
with **no per-row event semantics, no watermark, no offset paging, bulk-file delivery**,
and a ~monthly (imagery-lagged) cadence. Registering it "as a feed" is not a
mapping-table exercise — it is a **new signal family** (`FeedType.BUILDING_STOCK` /
`PLACE_CHURN` or similar), a **new producer archetype** (GeoParquet download / DuckDB
bbox query → H3 rollup; changelog diff → added/removed/data_changed counts per H3
cell), and a new stored shape (H3-cell aggregates, not event rows). That is a
spine/registry change, beyond a leaf stream.

---

## Proposed validation (if later promoted to REGISTER)

A two-metro pilot, both registered metros, both high-coverage US regions (mirrors the
LODES pilot choice): **New Orleans** and **Norfolk**.

1. **Snapshot extract.** For each metro bbox, DuckDB-pull `theme=buildings/type=building`
   and `theme=places/type=place` for two consecutive releases (e.g. current + prior),
   filtering on the `bbox` column server-side. Measure per-metro row counts and MB.
2. **Change extract.** Pull `changelog/<REL>/theme=buildings/...` and
   `changelog/<REL>/theme=places/...` for the same pair, filter by metro bbox, and tally
   `added` / `removed` / `data_changed` per `change_type`. Cross-check `added`/
   `removed` against the bridge files to strip GERS-ID-churn artifacts.
3. **H3 rollup.** Map each surviving feature / change count to H3 res 7–9 via
   `H3SpatialIndexer`, apply `dynamic_spatial_fallback`, and roll to division/submarket.
4. **Cross-validation gate.** Correlate metro building-`added` rate against the
   permit-derived construction velocity already in the pipeline (does Overture lead,
   lag, or disagree — expect lag), and compare place-churn against SLA license flow.
   This is the *evidence* step that would justify a context-layer registration.
5. **Legal gate.** Obtain sign-off on ODbL share-alike exposure for any derived/
   redistributed building output before storing/serving it.

**Expected ingest path.** One-time: pin a release + schema version and archive the
pair. Per month: download metro bbox subset of buildings + places + changelog (tens of
MB), filter `added`/`removed` by stable `confidence` and reconcile bridge files, roll
to H3 7–9, fold into division/submarket resolution. Volume is small; the only real cost
is the GeoParquet + changelog + rollup synthesis code, which is new but mechanical, plus
the self-hosting of historical releases (public retention is only 60 days).

---

## Independent coverage check (vs. the existing feed families)

| Dimension | Existing feed-derived signals | Overture Maps (buildings + places) |
|---|---|---|
| Unit | geolocated **event**, H3 cell | building **polygon** → H3 cell; place **point** → H3 cell |
| Latency | near real-time (daily/weekly) | **monthly** release; imagery-derived lag behind permits |
| Concept | *events* (permit, complaint, sale, crime) | *physical stock delta* + *commercial-presence churn* |
| Coverage | only metros with that feed | **global**, incl. all US metros (high quality) |
| Change layer | per-event stream (inherent) | **native changelog** (`added`/`removed`/`data_changed`) on stable GERS IDs |
| Noise | none (record-level) | ML footprint imprecision; place duplicates/junk (`confidence` filter); ID churn |
| Licensing | municipal open data | buildings **ODbL** (share-alike); places CDLA-Permissive-2.0 / Apache-2.0 |

**Does it add independent coverage?** Yes, but only in *kind*, and only as context: it
measures a physical-building-stock and commercial-presence surface that no event feed
produces, and it can *cross-validate* permit-derived construction velocity and enrich
commercial submarket fundamentals. It does **not** add a timelier or finer *event-count*
measure — it is strictly slower and (for buildings) trailing by imagery lag. Under the
repo's rule (a signal is retained only if it adds independent coverage *and* clears its
family gate), Overture clears the "independent coverage" test but not the "usable as a
leading/timely signal" test for *scoring*; it clears both only for a **context** role.

---

## Risks and dependencies (mapped to the issue's risks)

1. **"Monthly cadence too slow for short-term change detection."** **Confirmed, and
   binding for any leading-signal role.** Monthly release + the building footprints are
   ML-imagery-derived (appear when detected, not when permitted) → trailing, not leading.
   It can only ever be a trailing **context/anchor**, never a LIMS term. (Places churn is
   also monthly, though less imagery-lagged.)
2. **"Coverage gaps / freshness in sparse areas."** **Partially confirmed.** Global
   coverage is claimed, but ML-derived footprints have lower precision outside the US,
   and US rural areas and `building_part` (OSM-only) are thinner. Places carry known
   duplicates, a high junk rate, and low property completeness — `confidence` filtering
   (e.g. >0.5, or >0.95 for "definitely exists") is mandatory. Mitigation is repo-native:
   H3 res 7–9 rollup + `dynamic_spatial_fallback` smooth sparse cells; treat place counts
   as an *index*, never a precise census.
3. **"60-day public retention breaks long-term change tracking."** **Confirmed (new risk
   vs. the issue's assumptions).** Public buckets keep only the last two releases; the
   changelog is a one-month delta. A pipeline must **self-archive** historical release
   pairs (and the changelog) to compute multi-month/year trends. This is a storage +
   version-pinning dependency not present in municipal feeds.
4. **Integration-model dependency (the decisive one).** No `FeedType` exists for a
   non-event, snapshot+changelog layer. `FeedType` is `PERMITS`, `COMPLAINTS_311`,
   `SLA`, `DEEDS`, plus `CRIME`, `STREET_CUT`, `EVICTIONS`, `STR`. An Overture
   registration needs a **new signal family** and a **new producer archetype**
   (GeoParquet/DuckDB download + bbox filter + H3 rollup; changelog diff → per-cell
   added/removed/data_changed), which is exactly the kind of spine change that must gate
   on `pytest -m interlock` per `docs/agents/parallel-streams.md` and is out of scope for
   a leaf stream. New stored shape (H3-cell aggregates, not `h3_res7/8/9`-on-event rows)
   also touches the pipeline/Postgres sync assumptions.
5. **Licensing dependency (buildings ODbL).** The OSM-derived buildings theme is ODbL —
   share-alike + attribution. Any derived/redistributed building output may inherit
   those obligations. Places (CDLA-Permissive-2.0 / Apache-2.0) and addresses (mixed
   permissive) are fine. A combined product is **mixed-license**; legal sign-off is a
   hard gate before registration, not an afterthought.
6. **GERS-ID-churn dependency.** Stable IDs are the whole change mechanism, but matcher
   upgrades (e.g. July-2026) cause one-time ID churn that inflates `added`/`removed`.
   Mitigation: reconcile via bridge files and confidence-filter; treat a single release's
   `added`/`removed` as noisy unless corroborated across two consecutive deltas.

---

## Recommendation

**DEFER** — do not register now, but this is the *strongest* candidate in the validation
wave (its change layer is native, not reconstructed like LODES's). **Do not register**
because a feed registration is structurally impossible in the current model (Overture is
not an event stream, has no watermark, no per-row coordinates on the changelog, and
needs a new `FeedType` + producer archetype + aggregate storage = a spine/interlock
change), and because its monthly, imagery-lagged cadence plus 60-day public retention
mean it can only ever be a trailing **context/anchor / cross-validation** layer, not a
signal any current scoring path depends on. At the same time, **do not reject** it:
unlike BFS/QCEW it measures a genuinely independent physical-building-stock and
commercial-presence surface, the native GERS-keyed changelog makes the change signal
cheap to compute, US coverage is high quality, metro extraction is small and reuses the
existing H3 indexer and bbox gate, and it could cross-validate the permit-derived
construction-velocity signal.

**What unblocks a future REGISTER** (any one, or in combination):

1. A positive **scope decision** that Urban Signal wants a structural
   **physical-stock / place-churn context layer** at all — a new `BUILDING_STOCK` /
   `PLACE_CHURN` signal family, its own `DatasetSpec`-adjacent spec, its own H3-aggregate
   table, and a GeoParquet/changelog producer — treated as context/LIMS-exempt (precedent:
   street-cut "disruption context only — never a LIMS term").
2. A concrete consumer that needs it — e.g. a **cross-validation gate** for
   permit-derived construction velocity, or a **commercial-fundamentals enrichment**
   (POI category mix / business-open-close churn) under the hardcoded
   `base_lims`/`capex`/`sla` submarket baselines.
3. **Legal sign-off** on ODbL share-alike exposure for any derived/redistributed
   building output.
4. If all three arrive, **pilot New Orleans and Norfolk first** (both registered metros,
   both high-coverage US regions), as a **month-over-month level/change index at
   division/submarket and H3 res 7–9**, pinned to a release + schema version with
   self-archived history (public retention is only 60 days), `confidence`-filtered, and
   bridge-file-reconciled to strip GERS-ID-churn artifacts.

Until then, the existing event feeds remain the correct timely signal, and Overture
should not be wired in as a scoring input. No code or config was touched in this leaf.

---

## Leaf deliverable note

Per the Tier-A validation convention (us101/us102/us122 are doc-only) and because the
only viable registration path is a spine-level signal family, **no leaf module was
added** under `apps/api/src/spatial/`. A premature `overture_*` module would be
unconsumed dead code (every consumer is a spine feed) and untestable against real data
with no Overture access plumbing in the repo. The mapping logic that *would* live there
— feature/bbox → H3 res 7–9 and changelog `added`/`removed`/`data_changed` rollup — is
fully specified above and reuses `H3SpatialIndexer` and `dynamic_spatial_fallback`
verbatim, so the build cost when unblocked is mechanical, not design.
