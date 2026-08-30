# MapLibre rendering performance at scale — research spike (US-416)

**Date of research: 2026-08-30 (stub — full run pending).** Blocks `US-413` dashboard blended LOD renderer. Primary sources to be probed live; claims below are scaffold, not verified.

## Method, and its limits

Planned primary-source layers, in order:

1. **MapLibre spec.** Read MapLibre GL JS `3.6.2` docs (`apps/dashboard/public/index.html:17`) for `geojson` source + `fill` / `fill-extrusion` / `line` layer performance notes and `maxzoom`/`minzoom` semantics. Use official docs, not secondary blogs.
2. **Current renderer.** Read `apps/dashboard/public/index.html:2569` `setupGridLayers`, `2433` `res5ParentsCoveringBounds`, `1537` `ZOOM_FLOOR=6`/`NATIONAL_HIDE_ZOOM=12`, `2539` eviction `120k`, `2643` `updateMetricVisuals`, `1806` `nationalColorExpression`. Treat code as source.
3. **Synthetic load spike.** Generate synthetic `gridtiles_res7/8/9` payloads via throwaway `scripts/measure_coverage.py` (uses `coverage.metro_cells(max_ring=3)` shape before `coverage.py` lands) at 30k / 120k / 250k features. Load in Chrome (desktop + mobile 390×844), record `frame ms` (Performance panel), `GPU memory`, `tile bytes` (Network), `KV fetch ms` (separate). Run with `prefers-reduced-motion` both states.
4. **Heatmap comparison.** Add `heatmap` layer on same synthetic data at `z 6-9`, measure frame time vs hex `fill` and visual gap perception.

**Limits.** Synthetic payloads approximate real `k_ring=3` density; not exact `lims_score` distribution. No vector tile path tested here (covered by `US-417`). Results bounded to Esri dark raster basemap (`index.html:1893` `MAP_STYLE`) and `geojson` source type.

## Source assessment (to be verified)

- **Access / terms.** MapLibre GL JS is BSD-3-Clause, CDN `unpkg.com` (no auth). Verify `maplibre-gl@3.6.2` CDN availability and `h3-js@4.1.0` (`index.html:24`).
- **File families.** `gridtiles/{parent}.json` today, planned `gridtiles_res7/8/9/{parent}`. Each `register()` enforces `20MiB/value` (`snapshot_builder.py:68`). Verify per-chunk `~5MiB` target holds under `k_ring=3` dense.
- **Revision / reproducibility.** Pin `maplibre-gl` version + `h3-js` version + synthetic seed. Record `manifest.generated_at` for each run.

## Headline verdict (stub — to be filled after spike)

**Pending.** Hypothesis: `120k` geojson `fill` at `z 7` holds `~16ms` frame budget on desktop, exceeds on mobile; `250k` requires per-res eviction (`tileFeatures` keyed by `res`, `fetchedTiles` per `res`). Heatmap at `z<9` is cheaper but blurs metro boundaries and breaks `*_national_pct` comparability. Spike to confirm and set eviction policy.

## Recommendation (stub)

- **If 120k holds:** keep single `h3-grid-source` with per-res eviction, no heatmap. Retire `zoom-hint` `index.html:1351` after dead-zone removal.
- **If 120k exceeds mobile budget:** add per-res `maxCount` (e.g., 60k at `res7`, 120k at `res9`) and center-out fetch (`parentDistance` already exists) as LRU guard.
- **Heatmap:** do not ship unless `z 6-9` hex at `120k` fails mobile `16ms` budget by >30%.

## What unblocks

- `US-413` `lodForZoom(z)` thresholds (`z>=11 res9`, `9-11 res8`, `6-9 res7`), `res`-aware `stepLat` sampling, eviction policy
- `zoom-hint` retirement decision

## Risks and dependencies

- `GeoJSON` at `250k` may hit `KV 20MiB` per value before render — verify `register()` budget first (`US-411` spike).
- `fill-extrusion` height expression (`* max(...,40) * factor`) dominates GPU at low zoom; test `2D` vs `3D` toggle.

## Sources to cite (primary)

- `apps/dashboard/public/index.html:17`, `1537`, `2433`, `2569`, `2539`, `2643`, `1806`, `1893`
- `apps/api/src/export/snapshot_builder.py:68`
- MapLibre GL JS `3.6.2` docs (geojson source, fill/fill-extrusion)
- Chrome Performance traces + Network waterfall (to be captured)
