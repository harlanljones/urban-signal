# Vector tile (MVT/PMTiles) feasibility on Cloudflare — research spike (US-417)

**Date of research: 2026-08-30 (stub — full run pending).** Informs `US-408` horizon `Plan MVT next` and `US-411` manifest split decision. No feed registration; spine-adjacent.

## Method, and its limits

Planned primary-source layers, in order:

1. **MVT spec.** Read Mapbox Vector Tile spec `2.1` (official GitHub) and `tippecanoe` README + `planetiler` docs. Use first-party repos, not secondary write-ups.
2. **Cloudflare serving.** Read Cloudflare R2 vs KV limits (KV `25MiB` hard cap, `25MiB` is `20MiB` build budget in `snapshot_builder.py:68`; R2 no per-object cap) and `Cache API` / `wrangler kv bulk put` docs. Verify `wrangler kv bulk put` `512MiB` bulk cap (`snapshot_builder.py:70` `MAX_BULK_BYTES`).
3. **Size comparison spike.** For `nyc, chicago` pyramid `res7/8/9` (same inputs as `US-411` spike), generate GeoJSON `gridtiles_res*` via `build_snapshot` then run `tippecanoe -zg --drop-densest-as-needed` to `tiles/{z}/{x}/{y}.pbf` and `pmtiles` single-file. Record `byte_size` per `z`, `pbf` count, `pmtiles` size. Compare to GeoJSON `byte_size` per `gridtiles_res*` chunk.
4. **MapLibre fit.** Read MapLibre GL JS `vector` source spec and test `addSource({type:'vector', tiles:['/tiles/{z}/{x}/{y}.pbf']})` against `index.html:1893` `MAP_STYLE` raster baseline. Verify `maxzoom` overzoom behavior matches Esri `BASEMAP_MAX_TILE_ZOOM=16` pattern.

**Limits.** No live R2 bucket created here; size numbers are local. No `wrangler` deploy. MVT schema is property-only (`h3_index`, `*_national_pct`, `city_id`); no geometry simplification beyond `tippecanoe` defaults. Results bounded to `k_ring=3 + 1.5km` density.

## Source assessment (to be verified)

- **Access / terms.** `tippecanoe` is BSD-2-Clause, `planetiler` is Apache 2.0, MVT spec is BSD, MapLibre is BSD-3-Clause — all no-auth. Verify local binary availability (`tippecanoe --version`).
- **File families.** Today `gridtiles/{res5_parent}.json` (KV), planned `gridtiles_res7/{res4_parent}` etc. MVT alternative is `tiles/{z}/{x}/{y}.pbf` (R2) or `tiles.pmtiles` (single file, range requests). Verify `pmtiles` `Cache API` support on Workers.
- **Revision / reproducibility.** Pin `tippecanoe` version + `h3` version + `snapshot_builder` commit. Record `manifest.generated_at` per run.

## Headline verdict (stub — to be filled after spike)

**Pending.** Hypothesis: MVT `pbf` is ~35-50% of GeoJSON bytes for same hex pyramid (measured `national` GeoJSON rows-of-arrays `~254KB` vs binary `201KB` precedent in `snapshot_builder.py:247`). Single `pmtiles` simplifies deploys vs thousands of KV keys. Spike to confirm and quantify `R2` vs `KV` `25MiB` headroom.

## Recommendation (stub)

- **If MVT <60% GeoJSON and `pmtiles` <500MiB total:** keep GeoJSON `tile_indexes` seam MVT-ready (parent key naming `gridtiles_res*/{parent}` → `tiles/{z}/{x}/{y}.pbf` mapping in `coverage.py` docstring), defer migration until `US-411` ships and `R2` + `Cache API` path is proven.
- **If MVT not significantly smaller:** stay GeoJSON, split manifest into `tile_index_res7` etc. fetched lazily to respect `10MiB` cap.
- **Gate:** no MVT publish without `R2` bucket + `Cache API` verified on Workers.

## What unblocks

- `US-408` horizon decision (stay GeoJSON vs migrate)
- `US-411` manifest shape (`tile_indexes` single key vs per-res keys)

## Risks and dependencies

- `PMTiles` range requests require `Cache API` + `R2` — verify Workers `fetch` range support.
- `MVT` schema must preserve `*_national_pct` percentile rank semantics; `tippecanoe` attribute handling must not quantize floats.
- `Legacy shim` `manifest.tile_index == tile_indexes[9]` must survive either path.

## Sources to cite (primary)

- Mapbox Vector Tile spec `2.1` (GitHub)
- `tippecanoe` README, `planetiler` docs
- Cloudflare R2 docs, KV limits, `Cache API`, `wrangler` docs
- `apps/api/src/export/snapshot_builder.py:68`, `70`, `247`
- `apps/dashboard/public/index.html:1893`
- MapLibre GL JS `vector` source docs
