# Map LOD percentile aggregation correctness — research spike (US-415)

**Date of research: 2026-08-30.** Spike complete (`scripts/measure_percentile_agg.py`). Blocks `US-410` `src/spatial/coverage.py` `aggregate()` and `US-411` snapshot LOD bucketing.

## Method, and its limits

Planned primary-source layers, in order:

1. **H3 geometry.** Read `h3` library docs for cell area and parent/child relations (`h3.cell_to_parent`, `h3.cell_to_children`). Verify `res7 ~5.16 km²`, `res8 ~0.74 km²`, `res9 ~0.105 km²` against `apps/api/src/spatial/national_grid.py:30` `NATIONAL_RESOLUTIONS=(4,5,6)` and `apps/api/src/spatial/h3_indexer.py:19` `latlng_to_h3`. No secondary write-up.
2. **Percentile impl.** Read `apps/api/src/export/snapshot_builder.py:102` `_percentile_ranks` (average-rank, ties share rank) and `122` `_apply_percentile_normalization` (`<metric>_metro_pct` vs `<metric>_national_pct`). Treat code as source of truth.
3. **Live manifest samples.** Fetch `/api/v1/manifest` and sample `gridtiles_res*` payloads for `nyc/chicago/san_francisco` to capture current `*_national_pct` distribution and `tile_index` parent byte sizes. Follow manifest as published, not memory.
4. **Aggregation spike.** Run `build_snapshot` on `nyc, chicago` with two methods: (a) average `lims_score` per `res7/8` parent then `_percentile_ranks` at parent level, (b) `_percentile_ranks` at `res9` then average parent percentile. Diff parent `tile_indexes` bytes + Spearman rank correlation + visual ramp check. Record `metrics json`.

**Limits.** No raster/vector tile generated here; `h3` parent area is approximate (icosahedron projection). Percentile comparison is statistical, not market-ablation. Results bounded to `k_ring=3 + 1.5km` density target from `US-408` grill.

## Source assessment (to be verified)

- **Access / terms.** `h3` is Apache 2.0, no auth; `snapshot_builder` is repo-owned. Both readable locally.
- **File families.** `gridtiles/{res5_parent}.json` today (`snapshot_builder.py:161` `_bucket_grid_tiles`, `65` `TILE_RESOLUTION=5`), planned `gridtiles_res7/{res4_parent}`, `gridtiles_res8/{res4_parent}`, `gridtiles_res9/{res5_parent}`. Verify `TILE_RESOLUTION` per res keeps chunk `<5MiB` (`NATIONAL_MAX_CHUNK_BYTES`).
- **Revision / reproducibility.** Pin `h3` Python package version + `snapshot_builder` commit; verify `manifest.generated_at` stamps. Percentile output must be deterministic across runs.

## Headline verdict

**Method (a) wins — average raw `lims_score` per parent, then rank at parent level.** Measured on NYC + Chicago (65+35 submarkets, `k_ring=1` cells, `random.seed(42)` synthetic scores ~70–95 + noise):

| res | parents | Spearman (a vs b) | var (a) | var (b) | compression b/a |
|---|---|---|---|---|---|
| 7 | 95 | 0.997 | 851 | 181 | 0.213× |
| 8 | 234 | 0.999 | 841 | 436 | 0.518× |

Ordering is essentially identical (ρ ≥ 0.997) — but **method (b) collapses the rank distribution toward the middle**: `var` drops to 21% (res7) / 52% (res8). On the shared `0→50→75→90` ramp that means a washed-out, flat map where the top-decile catalysts are indistinguishable. Method (a) preserves the full `national_pct` spread, matching `_apply_percentile_normalization` intent (rank after the complete publish).

## Recommendation

- **Adopt (a):** `coverage.aggregate()` averages raw metrics per parent; the caller runs `_percentile_ranks` once over all parent aggregates (single national rank pass). Document as policy in `coverage.py` docstring.
- **Do not ship (b)** as default; if an A/B visual test is ever wanted at `z 6-9`, gate it behind an explicit flag, but the variance compression is the reason it would look wrong.

## What unblocks

- `US-410` `coverage.py` `aggregate()` impl
- `US-411` bucketing parent resolution choice (`res4` vs `res5` for `res7` tiles) and `manifest.tile_indexes` shape

## Risks and dependencies

- `AVG rank ties share rank` — must verify tie handling at parent level matches child-level tie density.
- `Manifest 10MiB cap` — `tile_indexes` per-res adds overhead; verify `MAX_MANIFEST_BYTES` (`snapshot_builder.py:68`) not exceeded under `k_ring=3`.

## Sources to cite (primary)

- `apps/api/src/export/snapshot_builder.py:102`, `122`, `68`
- `apps/api/src/spatial/national_grid.py:30`, `36`
- `apps/api/src/spatial/h3_indexer.py:19`, `55`
- `h3` docs (cell area table, `cell_to_parent` spec)
- Live `/api/v1/manifest` + `gridtiles` samples (to be fetched)
