# MapLibre rendering performance at scale for the hex map (US-416)

**Researched: 2026-08-31.** Research-only assessment feeding the US-408 "Plan MVT next" seam decision. Companion to the planned live-spike method in `docs/research/map-rendering-performance.md` (stub) and the MVT feasibility spike (`docs/research/map-mvt-feasibility.md`, US-417).

## Summary

The dashboard renders hexes through MapLibre `geojson` sources with a single `fill` layer + `fill-extrusion`, fed by per-viewport tiles (`/api/v1/gridtiles`, res-5 parents) selected by `lodForZoom(z)` → res 7/8/9, and a national overlay at res 4/5/6 below z12. A 120k-feature eviction cap already exists.

The web evidence does **not** show a hard polygon-count wall between 50k and 250k. Documented degradation drivers are, in order of impact:

1. **feature-state** — re-evaluated on the main thread when cached tiles reload; 20k features with fat property objects caused up to 10 dropped frames per zoom change (maplibre#6633, unfixed as of 2025, dup of #7590).
2. **`setData()` churn** — each call re-serializes and re-slices the entire dataset in the geojson-vt worker; rapid calls previously caused a worker-queue memory leak (maplibre#6154, fixed).
3. **Per-tile rendered complexity + property-object size** — not raw feature count alone.

MapLibre's own large-data guide recommends exactly the ladder we are on: URL-served data → per-tile/viewport chunking → vector tiles for "very large" data (their Martin demo handles a 13 GB PostGIS DB via server-side MVT).

**Verdict: the GeoJSON LOD approach can ship at ~120k hexes.** Our architecture (viewport-scoped tile fetches, 32-parent batches, concurrency 2, per-res eviction, static styling expressions, no feature-state) sidesteps every documented cliff. The MVT swap (US-417) is a byte-size/deploy win, not a rendering necessity at this scale.

## Current renderer (code evidence)

- `apps/dashboard/public/index.html:1576` — `lodForZoom(z)`: z≥11 → res 9, z≥9 → res 8, else res 7; `ZOOM_FLOOR=6`.
- `parentsCoveringBounds()` (`index.html:~2487`): samples res-5 parents (0.14° step, 4000-sample cap; res-4 parents 0.45°/800 for coarse LODs) → per-viewport polygon budget, not whole-metro.
- Fetch path: 32 parents per request, concurrency 2, 220ms viewport debounce, per-res eviction cap **120k** features (`index.html:~2539`).
- Layers: `h3-hex-fill` (`fill`, opacity 0.78) + `h3-hex-extrusion`; `national-h3-fill` overlay. Styling uses data-expressions on `*_national_pct`; no `setFeatureState` loops on the hex path (popup/hover via queryRenderedFeatures).
- Byte guard: res-6 shard measured ~254 KB against the 20 MiB `register()` ceiling (`snapshot_builder.py:68`).

Polygon budget per LOD level ≈ hexes in the current viewport at that res; a full ~120k-hex metro is only resident when the whole metro is in view at res 9.

## Evidence table

| Hex/feature count | Expected behavior | Evidence |
|---|---|---|
| ≤ 20k | Smooth *unless* feature-state or fat property objects are used; then up to 10 dropped frames per zoom change | maplibre-gl-js#6633 (20k features, ~40 props, setFeatureState) |
| 50k–120k | Fine with static fill styling + per-viewport data; main risk is `setData()` re-slicing cost on updates, not render fps | MapLibre large-data guide; geojson-vt README (5.4M-point demo) |
| >120k | No published fps tables; community guidance converges on tiling (client geojson-vt or server MVT/PMTiles) | maplibre.org large-data guide (Martin 13 GB demo); geojson-vt README |
| Any count | `setData()` on large sources = full worker re-slice; use `updateData()` diffs with `promoteId` ids | GeoJSONSource docs; #7336 (5.20.x diff-update regression ~7.5×) |

Caveat: no third-party GeoJSON-vs-MVT choropleth fps benchmark was found; this quantitative gap is why the synthetic-load spike in `map-rendering-performance.md` is still worth running before US-408 commits.

## Mitigations, ranked by effort

1. **(done / near-free) Zoom-based res scaling + viewport tile fetch + eviction** — already implemented (`lodForZoom`, 120k cap).
2. **Trivial: keep features off feature-state; keep property objects lean** — the dashboard already avoids setFeatureState loops on the hex path; don't add them. Cite #6633 when reviewing PRs.
3. **Low: source `maxzoom` tuning + `tolerance` on the geojson sources** — set `maxzoom: 12` and a modest `tolerance` on `h3-grid-source`/national sources per the official guide; one-line changes.
4. **Low-medium: feed sources by URL, diff with `updateData()`** — if tile payloads grow, serve tile JSON via URL and use `promoteId` + `updateData()` instead of full `setData()` rebuilds.
5. **Medium: avoid whole-national `setData` churn** — national overlay is already chunked per res-3 parent; keep updates per-chunk, not whole-collection.
6. **High (defer, US-417): vector tiles / PMTiles** — convert the `gridtiles_res*/{parent}` seam to `tiles/{z}/{x}/{y}.pbf` or single `tiles.pmtiles`. Worth it for bytes and deploy simplicity, not required for the 120k-hex rendering target.

## Recommendation

The GeoJSON LOD approach **hits no 120k wall** in the documented evidence; ship it. Guardrails: (a) never add feature-state to the hex path; (b) prefer `updateData()` over `setData()` when payloads grow; (c) run the synthetic 30k/120k/250k load spike from `map-rendering-performance.md` to convert this literature review into measured frame times (mobile especially) before declaring US-416 closed. MVT/PMTiles migration stays a US-417 byte/deploy decision, not a performance necessity.

## Sources

- https://maplibre.org/maplibre-gl-js/docs/guides/large-data/ — official large-GeoJSON optimization guide
- https://maplibre.org/maplibre-style-spec/sources/#geojson — geojson source options (`maxzoom`, `tolerance`, `promoteId`)
- https://github.com/maplibre/maplibre-gl-js/issues/6633 — 20k features + feature-state → 10-frame zoom stalls (dup of #7590)
- https://github.com/maplibre/maplibre-gl-js/issues/6154 — setData worker-queue memory leak (fixed #1102)
- https://github.com/maplibre/maplibre-gl-js/issues/7336 — updateData perf regression in 5.20.x
- https://github.com/mapbox/geojson-vt — worker tiling defaults (`indexMaxZoom: 5`, `indexMaxPoints: 100k`), 5.4M-point demo
- https://maplibre.org/maplibre-gl-js/docs/API/classes/GeoJSONSource/ — URL preference, updateData/promoteId
- Local: `apps/dashboard/public/index.html:1576, 2487, 2539, 2637`; `apps/api/src/export/snapshot_builder.py:68`
