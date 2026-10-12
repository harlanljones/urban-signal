# Spec: Adaptive Hex Coverage Tiers and Regional Backfill

Implements [ADR-0010](../adr/0010-adaptive-hex-coverage-tiers-and-regional-backfill.md).
Vocabulary is the root [`CONTEXT.md`](../../CONTEXT.md). Executable plan,
owners, and gates live in [`ROADMAP.md`](../../ROADMAP.md); this document is
the contract those work items implement. Measured baselines are labeled
*(measured)*; proposed values that need calibration are labeled *(proposed,
calibrate)* and carry the roadmap task that pins them.

## 0. Invariants that never change

| ID | Invariant | Enforced by |
|---|---|---|
| INV-1 | Outside an Urban Anchor, detail-tier cells do not exist; nothing is ever synthesized there (US-408 honesty rule). | `CoveragePlan` never emits them; `TestCoveragePlan` |
| INV-2 | A promoted region's cell count equals its plan's golden count exactly. | `promote_region` |
| INV-3 | A failed or shrunken region build never replaces a valid region pointer. | `promote_region` (atomic swap, previous retained) |
| INV-4 | Percentile ranks are computed from raw values at each resolution, never by averaging child percentiles (US-415). | `coverage.aggregate*`, unchanged |
| INV-5 | Coverage planning is transport-free: it returns H3 sets and plain data; it never runs inference or touches HTTP/KV. | module boundary (`coverage_plan.py` imports no engine/serving) |
| INV-6 | Under `authority="k_ring"` the plan reproduces today's metro sets exactly: 157 metros, 53,799 unique res-9 cells *(measured; pinned in `scripts/autoresearch_coverage.json`)*. | `TestCoveragePlan.test_k_ring_authority_matches_pin` |
| INV-7 | National golden counts stay 5,251 / 36,757 / 257,299 *(measured)*. | `national_grid` tests, unchanged |
| INV-8 | Every detail-tier feature carries an honesty label; a label is never inferred client-side. | builder stamps `coverage_source`; worker/client only read it |
| INV-9 | A cell belongs to exactly one region. Seed fixture: the 373 res-9 cells two metros publish today across 8 pairs (Oakland/SF 123, SF/San Jose 62, Chandler/Tempe 37, Henderson/Las Vegas 37, Long Beach/LA 37, Pierce/Tacoma 37, SF/Santa Rosa 32, Scottsdale/Tempe 8) *(measured from the pinned fixture; today resolved by first-city-wins in `_bucket_grid_tiles`)*. | `TestCoveragePlan.test_no_cell_has_two_regions` |
| INV-10 | Every published rank is attributable to a named rank epoch; a region generation never mixes epochs. | `RegionManifest.rank_epoch`; §4.6 |

## 1. Urban Anchor asset

**Module:** `apps/api/src/spatial/urban_anchors.py` (new leaf).
**Asset:** `apps/api/src/spatial/assets/us_urban_areas_2020.geojson` (vendored,
same pattern as `national_grid.OUTLINE_ASSET`).

- Source: Census Bureau 2020 Urban Areas cartographic boundary file
  (`cb_2020_us_ua20_500k`; public domain). Fields retained per feature:
  `UACE20` (5-digit anchor id), `NAME20`, `ALAND20` (m²), `POP20` *(if the
  chosen file carries it; otherwise joined from `2020_Census_ua_list_all.xlsx`
  — the vendoring task records which)*.
- Simplification tolerance and coordinate rounding: *(proposed, calibrate;
  HX-A1)* start at the outline's 0.004° / 5 decimals; the acceptance test is
  that **aggregate** res-7 polyfill cell count differs from the unsimplified
  geometry by ≤ 0.5 %. *(Measured at HX-A1: a per-anchor ≤ 0.5 % bound is
  unachievable at any practical size — a ±1-cell flip on a 20-cell anchor is
  5 % — so the criterion is aggregate. At 0.004° the asset is 4.29 MB and net
  drift is +0.024 %, with boundary cells flipping both ways.)*
- The feature count of the vendored asset becomes `ANCHOR_GOLDEN_COUNT`
  *(TBD; pinned by HX-A1)*. Puerto Rico and Island Area anchors are retained in
  the asset but are not eligible for the detail tier until a feed exists
  (LODES has no territory coverage — nulls stay nulls).

```python
# urban_anchors.py
ANCHOR_ASSET: Path
ANCHOR_GOLDEN_COUNT: int                      # pinned by HX-A1

@dataclass(frozen=True)
class UrbanAnchor:
    anchor_id: str                            # UACE20
    name: str
    land_km2: float
    population: int | None
    geometry: dict                            # GeoJSON (Multi)Polygon, [lng, lat]

def load_anchors() -> dict[str, UrbanAnchor]  # lru_cache(1); raises on count != golden
def anchor_cells(anchor_id: str, res: int) -> tuple[str, ...]
    # polyfill of the anchor geometry at res; per-part, sorted, deduped;
    # hierarchically closed: res r+1 = children of res r (national_grid pattern)
def anchors_intersecting(bbox: dict[str, float]) -> tuple[str, ...]
def detail_resolution(anchor: UrbanAnchor) -> int   # §3
```

## 2. Registry spine change (interlock hold)

`SpatialRegistration` gains one slot; `CityRegistration` exposes it.

```python
urban_anchors: tuple[str, ...]   # UACE20 ids; () = no anchor → k-ring authority
```

The ADR wrote `ua_id` (singular); the contract is a tuple because one metro can
span several Census urban areas, and one urban area can span several ADR-0007
jurisdictions (DC / Montgomery / Prince George's all sit inside the Washington
urban area). Empty tuple is legal in Stage A and means "k-ring stays
authoritative for this metro".

How the tuple is populated is decision gate **DG-2** (`ROADMAP.md`): derived
by an accessor from `anchors_intersecting(reg.metro_bbox)` (roadmap default;
no per-metro curation, leaf city modules untouched) or curated per metro. The
gate assertions below hold under either choice.

Gate extension `TestUrbanAnchorWiring` (added to `test_interlock_gate.py` in
the same hold, per `docs/agents/parallel-streams.md`):

1. every id in `reg.urban_anchors` exists in the vendored asset;
2. every anchor geometry intersects `reg.metro_bbox`;
3. when `urban_anchors` is non-empty, at least one submarket center lies inside
   the union of the anchors (otherwise the wrong anchor was attached);
4. a metro with zero anchors is logged, not failed (Stage A state for all 157).

`TestSpineCoverage` continues to require that the new field is gated.

## 3. CoveragePlan

**Module:** `apps/api/src/spatial/coverage_plan.py` (new leaf; deep module).
`coverage.py` keeps `metro_cells`, `assign_cell`, `aggregate*` as the
implementation `CoveragePlan` composes; in Stage B `_dense_metro_grid` stops
calling `metro_cells` directly and consumes plans.

```python
Authority = Literal["anchor", "k_ring"]
Label = Literal["measured", "interpolated"]      # LIMS provenance; null LIMS = owner None

INTERPOLATION_BOUND_KM = 1.5   # today's dense-grid bound (measured); calibration is DG-9
                               # (assign_cell's 25 km default is NOT the authority here)
DETAIL_RESOLUTIONS = (7, 8, 9)

@dataclass(frozen=True)
class PlannedCell:
    cell: str
    owner: str | None            # "city_id/submarket"; None only for LODES-only detail (Stage D)
    distance_km: float | None    # to owner center; 0.0 when cell is the owner's center cell
    label: Label

@dataclass(frozen=True)
class CoveragePlan:
    region_id: str               # "metro/{city_id}" | "anchor/{UACE20}" (§4.1)
    city_ids: tuple[str, ...]    # metros registering this region; () for Stage D anchors
    authority: Authority
    anchor_ids: tuple[str, ...]
    detail_res: int              # 7 | 8 | 9
    cells: tuple[PlannedCell, ...]   # at detail_res, sorted by cell
    golden_count: int            # == len(cells)
    plan_hash: str               # §3.3

def plan_region(region_id: str) -> CoveragePlan
def plan_all() -> dict[str, CoveragePlan]   # every detail region the registry + asset imply
def roll_up(plan: CoveragePlan, to_res: int) -> tuple[str, ...]   # parents of plan.cells; to_res < detail_res
```

The region is the plan's unit, not the metro: a shared anchor is **one**
`anchor/{UACE20}` region whose owners are resolved across every metro that
registers it, which is what keeps DC / Montgomery / Prince George's from
producing three overlapping detail sets.

### 3.1 Cell selection

- `authority="k_ring"`: `cells = coverage.metro_cells(city_id, res=9, k=3, 1.5 km)`;
  labels via `assign_cell` (`center` → `measured`, else `interpolated`).
  INV-6 pins this path.
- `authority="anchor"`:
  `candidates = ∪ anchor_cells(a, detail_res) for a in anchor_ids` ∩ cells
  whose centroid lies inside the union of `metro_bbox` over `city_ids` (the
  registry extent still bounds jurisdiction; the anchor bounds geography).
  Each candidate is kept iff `assign_cell(cell, city, max_dist_km=
  INTERPOLATION_BOUND_KM)` resolves for the nearest submarket among `city_ids`;
  label `measured` when the cell is a submarket's center cell at `detail_res`,
  else `interpolated` with `distance_km`. Candidates with no owner within the
  bound are absent (INV-1 extended inside the anchor: never invent an owner).
- Within an anchor, LIMS provenance is bounded exactly as today: `interpolated`
  only within `INTERPOLATION_BOUND_KM` of a submarket center. Anchor cells
  beyond the bound are still in the plan (geography is covered) with
  `owner=None` — LIMS null, LODES measured at the anchor's detail resolution
  (§4.7). This is the honesty rule, not a loophole: nothing synthesizes LIMS
  across tens of km of plateau from a handful of points.
- Default authority: `"anchor"` iff `reg.urban_anchors` is non-empty, else
  `"k_ring"`. Stage A ships the module with `"anchor"` implemented but every
  registry entry still `()`, so production coverage is byte-identical.
- Stage B ships anchors with LIMS-bearing cells only (anchor ∩ bound); the
  `owner=None` remainder of each anchor arrives with LODES-at-detail in
  Stage D (§4.7). Stage B therefore clips k-rings to urban geometry and
  pins per-region golden counts; it does not yet fill whole urban areas.

### 3.2 Detail resolution per anchor *(proposed, calibrate; DG-3 / HX-B2)*

| Anchor class | Rule | detail_res |
|---|---|---|
| large | `population ≥ 1,000,000` or `land_km2 ≥ 1,000` | 9 |
| mid | `population ≥ 100,000` or `land_km2 ≥ 100` | 8 |
| small | otherwise | 7 |

A metro's `max_detail_res` (published in `metro_index`) is the max over its
anchors. Calibration target: total detail-tier cells nationwide within the ADR
envelope (~0.5–1.5 M cells at Stage D); the thresholds are constants in
`urban_anchors.py` and changing them changes every affected `plan_hash`
(explicit rebaseline, §4.4).

### 3.3 Determinism

`plan_hash = sha256(authority, detail_res, sorted anchor_ids, ANCHOR_ASSET sha256,
submarket centers of every city in city_ids, sorted (cell, owner, label))`.
Same registry + same asset ⇒ same hash; the hash is the region's input
fingerprint for coverage (feeds and model add theirs in §4.3).

### 3.4 Terminal-cell propagation (mixed-resolution viewports)

The loader has one active resolution per viewport, and a viewport can span a
res-9 anchor and a res-7 anchor. Rule: an anchor's **terminal cells** (its
cells at its own `detail_res`) are published into every finer LOD tile set
under their parents — a res-7 anchor's cells appear in `gridtiles_res8/*` and
`gridtiles_res9/*` as res-7 hexes. The client requests one resolution and
receives each anchor at its terminal resolution; paint follows the feature's
`resolution` property, not the requested LOD. Cost is bounded by the res-7/8
cell counts (tens of thousands), not by res 9. Regression: a mixed-viewport
case in `grid-zoom.test.js` (two anchors, `detail_res` 9 and 7, one z ≥ 11.1
fetch, both render).

## 4. Regions and backfill

**Module:** `apps/api/src/export/regions.py` (new leaf). Two adapters satisfy
`RegionBuilder` — the existing dense-metro path (wrapped) and the anchor path —
which is what makes the seam real.

### 4.1 Region identity

| Region kind | `region_id` | Chunks it owns |
|---|---|---|
| metro detail (k-ring authority) | `metro/{city_id}` | `gridtiles_res{7,8,9}/{parent}` for that metro's parents; `cells/{h3}`; `grid/{city_id}`; `catalysts/{city_id}`; `submarkets/{city_id}` |
| anchor detail | `anchor/{UACE20}` | same key families, parents of the anchor's plan |
| national base | `national/{res}/{res3_parent}` | `national/{res}/{res3_parent}` (one chunk) |

A detail-tile parent shared by two regions (adjacent metros under one res-4
parent) is owned by the region that contributes more cells to it; the other
region lists it under `shared_parents` and the builder merges at assembly
(today's `_bucket_grid_tiles` already merges across cities — the ownership
rule only decides which region's generation the chunk is addressed under).

### 4.2 Generation and pointer layout (KV)

```
regions/{region_id}/current            -> RegionPointer (JSON)
regions/{region_id}/gen/{generation}   -> RegionManifest (JSON)
objects/{sha256}                       -> chunk bytes (existing content-addressed objects)
```

```python
@dataclass(frozen=True)
class RegionManifest:
    region_id: str
    generation: str            # sha256 over sorted (chunk_key, chunk_sha256)
    input_hash: str            # §4.3
    plan_hash: str
    golden_count: int
    measured_count: int        # cells labeled "measured" (LIMS) or with ≥1 non-null LODES field
    chunks: dict[str, dict]    # chunk_key -> {"sha256": str, "bytes": int}
    built_at: str              # ISO-8601 UTC
    builder_revision: str

@dataclass(frozen=True)
class RegionPointer:
    current: str               # generation
    previous: str | None
    promoted_at: str
    golden_count: int
```

Generations are immutable. Retention: `current` + `previous` always
(matches today's prune policy); longer retention for historical backfill is
decision gate **DG-5** in `ROADMAP.md` (cost vs value is not yet measured).

### 4.3 Input hash and incremental refresh

```
input_hash = sha256(plan_hash,
                    model bundle id (engine.model_id),
                    builder_revision,
                    sorted feed watermarks for every city in city_ids,
                    context artifact sha (if applied),
                    national artifact sha (national regions only))
```

`build_snapshot` computes `input_hash` per region before building. If it equals
`RegionPointer.current`'s `input_hash`, the region is **skipped**: no build, no
upload; the snapshot manifest references the existing generation. Metric:
`regions_skipped / regions_total` per refresh (baseline 0 %, measured once
Stage C lands).

### 4.4 Promotion gate

This is **new verification**, not pattern reuse: `promote_national` today
checks a `checksum_verified` flag the builder hard-codes to `True`, requires
≥ 1 measured hex, and never compares against a golden count *(measured:
`national_builder.py` `_build_manifest` / `promote_national`)*. `promote_region`
hashes chunk bytes at promote time.

```python
class PromotionRefused(ValueError): ...

def promote_region(out_dir: Path, region_id: str, *, rebaseline: str | None = None) -> RegionPointer
```

Refuses (raises, pointer untouched) when any of:

1. any chunk's bytes do not match its recorded sha256;
2. `len(plan.cells) != manifest.golden_count` (INV-2);
3. `measured_count < 1`;
4. `measured_count < MEASURED_FLOOR_RATIO * previous.measured_count`
   *(proposed 0.8, calibrate; HX-C1)* — a sudden drop in measured cells is a
   feed outage, not a coverage change;
5. `manifest.golden_count != previous.golden_count` **and** `plan_hash` is
   unchanged — coverage drift without a coverage edit;
6. `golden_count` changed **with** a changed `plan_hash` but no `rebaseline`
   reason string was supplied — a registry/asset edit must say so.

On success: write `gen/{generation}` manifest, then atomically swap
`current` (`previous ← old current`). Order is fixed: objects → manifest →
pointer, so a crash never leaves a pointer at a partial generation (INV-3).

### 4.5 Snapshot assembly

- Manifest gains `regions: {region_id: generation}`, `rank_epoch` (§4.6), and
  `coverage.tiers = {"national": {...existing...}, "detail": {"authority_counts":
  {"anchor": n, "k_ring": m}, "cells": total, "resolutions": {...}}}`.
  `coverage.schema_version` becomes 2 when `regions` lands (HX-C2); the
  client's `coverageSchemaSupported` must accept 2 one release earlier
  (HX-C7) — reader before writer.
- `snapshot_id` canonicalization (`_manifest_snapshot_id`) is unchanged; the
  `regions` map participates like any other field. Client caches are keyed
  by region generation, not by `snapshot_id` (HX-C7), so promoting one region
  no longer flushes every visitor's cache for the other regions.
- Legacy keys (`gridtiles_res{res}/{parent}`, `cells/{h3}`, `national/*`)
  continue to be published during the compatibility window; the worker switches
  to region pointers (HX-C4) and only then does the builder stop emitting the
  legacy twins (HX-C5). Reader before writer, as with `cells/index`.
- Boot budget: `MAX_MANIFEST_BYTES` is 10 MiB *(measured)*; today's manifest
  is 2,479,735 bytes *(measured)*. Two maps grow with cell count: the per-KV-key
  `keys` integrity index and `tile_indexes`. Neither is needed to boot the
  client; both move to their own objects (`manifest/keys`,
  `manifest/tile_indexes`) when the projected boot manifest exceeds 8 MiB,
  and `keys` moves first because it is one entry per key. Rule owned by
  HX-C2 / HX-D3; the one-anchor pilot in HX-B2 measures `manifest_bytes`,
  `bulk_bytes`, and `snapshot_ms` before any anchor takes authority
  (today: 12,606 ms median for 53,799 cells with per-cell inference
  *(measured)*; LODES-only cells need no inference, and repeated synthetic
  vectors hit the prediction cache).

### 4.6 Rank epochs (incremental refresh vs publish-wide percentiles)

`<metric>_national_pct` is ranked over the complete publish today and is the
only field the client paints from *(measured: `_apply_percentile_normalization`;
paint expressions in `dashboard.py`)*. Rebuilding one region would change
every other cell's correct rank, so incremental refresh needs ranks that are
not recomputed per publish:

- A **full build** computes, per metric and per LOD resolution, a breakpoint
  table (proposed 101 quantiles *(calibrate; DG-10)*) and publishes it as
  `ranks/{rank_epoch}` with `rank_epoch = sha256(table)`.
- An **incremental** region build ranks its raw values against the current
  epoch's breakpoints and records `rank_epoch` in its `RegionManifest`
  (INV-10). It never re-ranks other regions.
- The manifest names `rank_epoch` and `rank_epoch_at`; the legend shows the
  epoch date when it is older than the snapshot. A full re-rank runs on a
  cadence *(proposed weekly; DG-10)* or when any metric's observed drift
  (fraction of cells whose epoch rank differs from a fresh rank by > 5
  points) exceeds a threshold *(proposed 2 %; DG-10)*.
- LIMS percentiles and LODES percentiles remain separate rank spaces; the
  legend never shows them on one ramp (resolves the Pending item in
  `docs/research/map-blended-lod-honesty.md` before Stage D).

### 4.7 LODES at detail resolution (Stage D, and the `owner=None` remainder)

`national_builder.aggregate_state` takes a resolution parameter; whether it
scales to res 7–9 restricted to anchor cell sets is HX-D1's feasibility
report *(inference; untested)*. Output rides the monthly national artifact
cadence; detail regions whose only input is that artifact have
`input_hash` = its sha and are skipped on every daily refresh. Fields:
`jobs`, `workers`, `jobs_pct`, `workers_pct` (national rank space), LIMS
fields null, `coverage_source = "measured"` for the LODES group.

## 5. Client display ladder

**Module:** inline client in `apps/api/src/serving/dashboard.py`, byte-synced
to `apps/dashboard/public/index.html` via `scripts/export_dashboard.py`.
Regression surface: `apps/dashboard/tests/grid-zoom.test.js` (Node) and
`bun run --cwd apps/dashboard test`.

### 5.1 One ladder *(proposed, calibrate; HX-A3 prototype, HX-B8 ships)*

```js
// replaces lodForZoom + nationalResForZoom + the ZOOM_FLOOR hard cut
const DISPLAY_LADDER = [        // [minZoom, res]
  [0,    4],
  [5.0,  5],
  [6.0,  6],                    // bridge band: national res 6, never requested today
  [7.4,  7],                    // DG-4 knob, see below
  [8.9,  8],                    // existing metro thresholds retained
  [11.1, 9],
];
const LADDER_HYSTERESIS = 0.2;  // existing ±0.1/0.2 behavior generalized
function displayResForZoom(z, activeRes, maxDetailRes) { ... }  // result ≤ maxDetailRes
```

Tier by resolution: `res ≤ 6 → national`, `res ≥ 7 → detail`. Parent
bucketing: `{4:3, 5:3, 6:3, 7:4, 8:4, 9:5}` (national routes keep res-3
parents; detail keeps today's `LOD_TO_PARENT_RES`).

`maxDetailRes` comes from the viewport's regions (`metro_index[].max_detail_res`,
§3.2) and is 6 where no detail region covers the viewport. Today `lodForZoom`
returns 9 unconditionally at z ≥ 11.1; the clamp is the one new client
mechanism per-anchor resolution needs.

**Bridge-band policy is decision gate DG-4** (`ROADMAP.md`), with two shapes:

| Shape | Display at z ∈ [6, ~7.4) inside a metro | Outside metros | Risk the HX-A3 prototype must measure |
|---|---|---|---|
| (a) ladder band | national res 6 (change from today's res 7) | national res 6 | metros lose detail for ~1.4 zoom levels |
| (b) underlay | res-6 national drawn beneath detail res 7 (no change) | national res 6 | 3D extrusion stacking (the US-422 double-draw class); request/CPU delta in `bash autoresearch.sh` |

Acceptance either way: no empty grid inside the nation outline at any zoom,
hysteresis tests green, benchmark within DG-8.

### 5.2 Tier seam

- The existing handoff (`renderGridHandoff`: morph when combined features
  ≤ 2,500, else 260 ms cross-fade; reduced-motion skips) ghosts only the
  `h3-grid-source` layers, while national features live in
  `national-hex-source` today *(measured)*. The unified loader below moves
  res-6 features into `h3-grid-source`, so the handoff is reused without a
  cross-source mechanism; paint becomes tier-aware (LODES fields at res ≤ 6,
  LIMS fields at res ≥ 7) and resolution-aware per feature (§3.4).
- When the detail tier has no coverage for a viewport (outside anchors), the
  national grid stays rendered at every zoom — by the res-6 underlay under
  DG-4 shape (b), or by the `maxDetailRes = 6` clamp under shape (a) — and
  the legend reads the detail state as `none` (new coverage state next to
  the existing `loading / ready / empty / failed / stale`).
- Loader state is unified: one `tileFeatures` map keyed by cell, one
  generation counter, one `lodTileCache` across all six resolutions; the two
  fetch routes (`/api/v1/national/{res}`, `/api/v1/gridtiles`) stay as they
  are until HX-C4.

### 5.3 Honesty in the legend

Three producer vocabularies exist today and no client code reads any of them
*(measured)*: `assigned_features` emits `measured | k_ring_interpolated`,
`_dense_metro_grid` publishes `coverage_source ∈ {center, bounded}`, and LOD
aggregates publish `source = lod_aggregate` without propagating provenance.
Contract: one enum at the `CoveragePlan` boundary —
`coverage_source ∈ {measured, interpolated, aggregate}` plus
`coverage_distance_km` and, on aggregates, `interpolated_fraction` — stamped by
the builder on every detail feature (INV-8). Both producers migrate in HX-B3;
the client reads the old strings for one release. `interpolated` cells get a
**distinct render style** (hatch or desaturation) and a legend row; this is a
Stage B acceptance criterion, not polish, because on the shared `_national_pct`
ramp an interpolated cell is otherwise indistinguishable from a measured one.
Stage D LODES-only cells carry `coverage_source = "measured"` for the LODES
group with LIMS null; the legend states "workforce detail — no catalyst
forecast".

## 6. Stage acceptance

| Stage | Ships | Production-visible change | Exit gate |
|---|---|---|---|
| A | asset + loader; `urban_anchors` slot (all `()`); gate extension; `displayResForZoom` with res-6 bridge band wired | res-6 national band renders at z 6–7.4 (was blank between tiers) | pre-flight green; INV-6 pin unchanged; `bash autoresearch.sh` not regressed; browser check: no empty grid at z 4–12 over NYC and over a non-metro point (e.g. rural Kansas) |
| B | `CoveragePlan`; anchors registered for a pilot set of metros; `interpolated` label; per-region golden counts in manifest | pilot metros' detail set follows urban geography | pilot metros' cells ⊆ anchor polyfill; golden counts pinned; pre-flight green; benchmark fixture rebaselined explicitly (`scripts/autoresearch_coverage.json` + semantic sha) |
| C | `regions.py`; `promote_region`; per-region pointers; worker reads pointers; incremental skip; legacy twins retired after worker cutover | daily refresh uploads only changed regions | `regions_skipped` observed > 0 on an unchanged day; forced region failure keeps previous generation (chaos test); pre-flight green |
| D | `plan_region("anchor/…")` for unregistered anchors with LODES-measured detail; manifest split rule (§4.5) and DG-7 (slimming vs MVT) resolved | detail grid appears in urban areas with no registered metro, honestly labeled | total detail cells within envelope; manifest < 8 MiB; benchmark within DG-8; browser check over an unregistered urban area |

## 7. Out of scope

- Vector tiles (MVT): decision gate DG-7, after property slimming is measured.
- LIMS for unregistered anchors: requires feeds and submarket baselines; not
  backfilled (INV-1).
- Changing `DatasetSpec` / multi-source metros: ADR-0007 stands.
- Territories in the detail tier: no LODES coverage; stays null.
