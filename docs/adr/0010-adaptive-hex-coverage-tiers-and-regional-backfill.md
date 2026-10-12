# ADR 0010: Adaptive Hex Coverage Tiers and Regional Backfill

**Status:** Proposed
**Date:** 2026-10-12
**Scope:** spatial coverage, snapshot publication, dashboard grid
**Companion:** US-408 (bounded expansion), US-415 (raw-then-rank), US-422
(disjoint zoom bands), US-438/US-440/US-443 (Bay-Area geography pilots),
ADR-0007 (the registry models jurisdictions)
**Supersedes:** none (extends, does not reverse, US-408's honesty rule)

## Context

Measured facts about today's system:

- A metro's render set is a union of bounded k-rings (k=3, ≤1.5 km) around
  hand-registered submarket points (`src/spatial/coverage.py:metro_cells`,
  US-408). No administrative or urban boundary clips the render set; the
  registry's metro bbox is used only for ingestion filtering. Real-polygon
  joins exist only as Bay-Area pilots — ZCTA area-weighting (US-440), TIGER
  block groups (US-438), Overture buildings (US-443) — while national
  attribution is centroid/bbox sampling (`geography_crosswalk.py`).
- Two disjoint pyramids: the national display tier at res 4/5/6 (golden
  closure 5,251 / 36,757 / 257,299 cells; LODES-only signal; published
  monthly) and the metro LOD tier at res 7/8/9 (157 metros, 53,799 unique
  res-9 cells; LIMS signal; published daily). The client hard-cuts between
  them at `ZOOM_FLOOR=6`: national res-6 chunks are built, published, and
  servable, but the client's national loader returns before requesting them
  at z ≥ 6, so they are never displayed — a dead band — and any hex outside
  a registered metro carries only LODES at every zoom.
- Every refresh rebuilds all 157 metros from scratch: 111,843 KV keys,
  ~571 MB bulk per run, in ~12–15 s. Publication is content-addressed and
  atomic (release twins, pointer promoted last, prune keeps two
  generations), but the build is all-or-nothing: a failed region of the
  snapshot has no per-region previous generation to keep. The national
  builder's `promote_national` is the closest pattern, but it is weaker
  than it looks: it checks a `checksum_verified` flag the builder hard-codes
  to `True`, requires ≥ 1 measured hex, and compares nothing against the
  golden counts (those are asserted only in unit tests).
- Percentile ranks (`<metric>_national_pct`, the only field the client
  paints from) are computed over the complete publish before any key is
  written; rebuilding one metro changes the correct rank of every other
  cell.
- 31 of 157 registered metro bboxes overlap another's, and the pinned
  coverage fixture already holds 373 res-9 cells with two owners across 8
  metro pairs (Oakland/SF 123, SF/San Jose 62, …), resolved today by
  first-city-wins in `_bucket_grid_tiles`.
- The client already morphs between metro LODs (≤2,500 features: polygon
  interpolation from parent centroid, 260 ms cross-fade; completed LODs are
  cached and restored without refetching).

Nationwide math that forces a decision rather than incremental growth:

- The golden ladder multiplies ×7 per level, so full-nation uniform detail
  would be ≈1.80 M cells at res 7, ≈12.6 M at res 8, ≈88.3 M at res 9 —
  a ~1 TB-class key space at today's ~5 KB-per-key density. Uniform detail
  at fine resolutions is infeasible; detail must be bounded by geography.
- The 2020 Census urban-area criteria (minimum 5,000 people / 2,000 housing
  units; no more urbanized-area/urban-cluster split) put 80.0 % of the U.S.
  population inside urban areas at an average density of 2,553 people per
  square mile. Derived envelope: ~269,000 km² of urban land → ~52 k cells at
  res 7, ~364 k at res 8, ~2.7 M at res 9. Urban-bounded detail at an
  adaptive resolution is buildable; uniform detail is not.

## Decision

**One display ladder over two coverage tiers, with geography-anchored coverage
and region-granular content-addressed backfill.**

1. **One display ladder, two coverage tiers.** H3 res 4–9 stays one ladder;
   coverage splits by promise, not by pyramid. The national base tier (res
   4/5/6, everywhere, LODES signal) is joined by an urban detail tier (res
   7/8/9, only inside Urban Anchors, LIMS signal). The client's zoom mapping
   becomes one `displayResForZoom` function over the whole ladder with
   hysteresis. The `ZOOM_FLOOR` hard cut becomes a tier seam that cross-fades
   — national res 6 morphs into urban res 7 as the detail tiles arrive — and
   the dead res-6 band becomes the bridge band that carries geography between
   metros. No zoom shows an empty grid inside the nation outline.

2. **The Urban Anchor is the coverage authority.** The detail-tier coverage
   set stops being hand-placed k-rings and becomes the polyfill of Census
   2020 Urban Area geometry intersected with the metro's registered extent,
   vendored as a national asset (the same pattern as the US outline in
   `national_grid.py`). Submarket points stop being coverage bounds and
   become LIMS interpolation anchors inside the anchor. The honesty rule
   gains its third label: `measured` / `interpolated` (inside the anchor,
   synthesized from the nearest submarket baseline, carrying its distance) /
   null (outside the anchor — never invented). This generalizes the
   Bay-Area polygon pilots into the standard coverage pipeline instead of
   leaving real-geography joins as a one-metro pilot.

3. **Adaptive detail resolution per anchor.** Each Urban Anchor's detail
   resolution is assigned by size/density class (large → 9, mid → 8, small
   → 7) and revisited only when the Census republishes urban areas. The
   tier keeps a total cell budget from the envelope above (~0.5–1.5 M cells
   nationwide) instead of a uniform res-9 nation. A viewport can span
   anchors of different detail resolution, and the loader has one active
   resolution; so each anchor's terminal cells are also published into
   every finer LOD tile set (a res-7 anchor's cells appear in the res-8 and
   res-9 tiles under their parents). The client keeps one active resolution
   and the existing morph; the only client change is paint that follows the
   feature's own resolution, not the requested one.

4. **Backfill is regional and content-addressed, never a full rebuild.** The
   build and promotion unit becomes the **region** — one Urban Anchor's
   detail set (several registered metros may contribute to it), or a
   national res-3 parent group. Each region build carries real per-chunk
   checksums, a golden-count invariant, and a minimum-measured-hex
   invariant — a `promote_region` gate that verifies what `promote_national`
   only asserts today — and swaps a per-region generation pointer
   atomically. A failed or partially-failed region keeps its previous
   generation, shrinking the failure domain from the whole snapshot to one
   region. A refresh rebuilds only regions whose inputs changed (per-region
   input hash), so daily cost scales with change, not with nation size.
   Ranks survive this because they stop being recomputed per publish: a
   full build publishes a **rank epoch** (per-metric breakpoints per LOD)
   that incremental region builds rank against, and the manifest names the
   epoch so staleness is bounded and visible. Historical backfill becomes
   structurally possible — generations are immutable and content-addressed —
   but retaining more than `current` + `previous` is a separate storage and
   cost decision, not a free consequence.

5. **The coverage seam stays transport-free; MVT is the escape hatch.** The
   coverage planning interface (`metro_cells`/`aggregate_values` today, a
   `CoveragePlan` behind them) remains the module boundary and keeps
   producing plain H3 sets and values. JSON chunk keys stay
   `gridtiles_res{res}/{parent}` and `national/{res}/{parent}`; if the
   detail tier's payload math demands it, the same plan maps to
   `tiles/{z}/{x}/{y}.pbf` without touching the interface (the seam is
   already documented in `coverage.py`). Property slimming (coarse cells
   carry fewer fields) comes first; MVT only when slimming is not enough.

**Module shape.** `CoveragePlan` is the deep module — geography and registry
in; per-tier cell sets with ownership and honesty labels out; transport,
engine, and HTTP stay outside it. `RegionBuild` gets two adapters, which is
what makes its seam real: today's dense-metro builder and the anchor
backfill builder. The client keeps two small interfaces:
`displayResForZoom(zoom)` and the tier-seam morph.

## Alternatives Considered

- **Uniform nationwide res-9 detail.** Rejected: ~88 M cells, ~1 TB-class
  key space; the ladder math above. Detail must be bounded by geography, or
  nationwide coverage never ships.
- **Keep k-ring coverage and merely add boundary clipping.** Rejected: the
  coverage authority would stay hand-placed, so "matching geography" would
  be cosmetic and every nationwide expansion would multiply hand curation of
  submarket points. The registry keeps modelling jurisdictions (ADR-0007);
  coverage authority moves to the anchor, which is data, not curation.
- **Full rebuild with bigger, faster uploads.** Rejected: a ~10 GB-class
  daily bulk, one failure domain for the whole nation, and no history —
  the opposite of backfill.
- **Backfill unmeasured geography with synthesized values.** Rejected:
  violates US-408's honesty rule, which this ADR extends rather than
  reverses — outside an anchor, cells are null; inside an anchor, LIMS
  fields are `interpolated` only within the existing bounded distance of a
  submarket (the bound is a calibration gate, not a license), and what
  fills the rest of the anchor is measured LODES at the anchor's detail
  resolution, with LIMS null.
- **Adopt vector tiles now.** Rejected as premature: at adaptive resolution
  the JSON chunk math holds, and the transport-free seam means MVT can be
  adopted later without a coverage change.

## Consequences

- The registry gains `urban_anchors: tuple[str, ...]` per metro (plural:
  a metro can span several urban areas and one urban area can span several
  ADR-0007 jurisdictions) — a spine change across `registration.py`
  (`__slots__`), `city_registry.py`, and `city_data.py` (its definition
  validator rejects unknown fields), so it must extend the interlock gate
  in the same spine hold per the parallel-streams rules; a metro with an
  empty tuple keeps its k-ring set as the fallback authority, so the
  rollout never parks a torn write.
- Cell ownership becomes a stated invariant: a cell belongs to exactly one
  region. The 373 cells that two metros publish today are the seed fixture
  for the gate that enforces it.
- Golden counts generalize: the national tier keeps its closure counts, and
  each region gains its own golden-count invariant, so registry edits can no
  longer silently shrink a metro's coverage (the k-ring era had no such
  invariant).
- The res-6 national band becomes load-bearing (the bridge band). Its
  request path is dead client-side today, and its features live in a
  different map source than the metro grid, so wiring it is a loader change
  (one feature map across all six resolutions), not just a fetch.
- Rollout is staged and each stage leaves production green: (A) vendor UA
  geometry + registry `urban_anchors` + gate extension, k-rings still authoritative;
  (B) `CoveragePlan` takes over coverage with anchors, per-region golden
  counts; (C) region-granular builds, promotion, and incremental refresh;
  (D) detail backfill beyond registered metros, then property slimming or
  MVT as payload math demands.
- The dashboard's coverage legend grows the tier distinction (national-only
  view vs urban detail view vs interpolated cells), extending the existing
  coverage-states honesty labels rather than replacing them.
- LODES nulls (territories, AK WAC 2017+) remain null and visible as gaps;
  backfill fills measured geography, never invents it.
