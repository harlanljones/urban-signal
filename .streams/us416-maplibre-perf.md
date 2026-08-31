# Stream log — us416-maplibre-perf — 2026-08-31

## Claim

- **Stream id:** `us416-maplibre-perf`
- **Leaf files I will create/edit:** `docs/research/us-416-maplibre-perf.md`, `.streams/us416-maplibre-perf.md`
- **Spine files I expect to need:** none (research-only, leaf-shaped; child of US-408)

## Intent

Research MapLibre rendering performance at scale (120k hex limit): polygon-count limits, GeoJSON source decode costs, fill-layer perf, worker/tile strategies, and when a GeoJSON LOD pyramid stops being viable vs an MVT/PMTiles swap. Deliverable is a written recommendation with cited evidence and a threshold table (hex count → fps / decode time), feeding the US-408 "Plan MVT next" seam decision.

## Findings

### Dashboard current state (code read, 2026-08-31)
- `lodForZoom(z)` (`apps/dashboard/public/index.html:1576`): z>=11 → res 9, z>=9 → res 8, else res 7. `ZOOM_FLOOR=6` (below: national layer only).
- Metro tiles fetched per res-5 parent cell (res-4 parents for LOD 7/8): `parentsCoveringBounds()` samples candidates (0.14° step, 4000-sample cap at res 5; 0.45°/800 coarser), 32 parents per `/api/v1/gridtiles` request, concurrency 2, viewport debounce 220ms.
- Render: single `fill` layer `h3-hex-fill` (opacity 0.78) + `fill-extrusion` (3D); national overlay `national-h3-fill` res 4/5/6. Deck.gl removed (US-391). Eviction cap 120k features exists (index.html ~2539).
- Note: prior stub `docs/research/map-rendering-performance.md` targets the same issue with a planned live-spike method; my deliverable `us-416-maplibre-perf.md` is a web-evidence-based threshold/migration assessment and should cross-link it.

### Web research (2026-08-31)
- Official guide "Optimising MapLibre Performance: Tips for Large GeoJSON Datasets" (maplibre.org/maplibre-gl-js/docs/guides/large-data/): store GeoJSON at a URL not inline; convert to vector tiles for large data; server-side tiling (Martin demo handles 13 GB PostGIS); set source `maxzoom: 12`; prefer `updateData()` diffs over `setData()` with unique ids via `promoteId`.
- Issue #6633: 20k features with ~40 properties + `setFeatureState` loops cause up to 10 dropped frames per zoom change — cached tiles re-evaluate feature-state expressions on the **main thread**. Closed as dup of #7590, unfixed. Avoids feature-state at scale.
- geojson-vt (runs in worker for `geojson` sources): handles 5.4M-point/100MB US zips demo; defaults `indexMaxZoom: 5`, `indexMaxPoints: 100k`; `setData()` re-slices the WHOLE dataset each call; rapid setData caused a worker-queue memory leak (fixed #1102). Diff-update perf is version-sensitive (#7336 reports ~7.5x regression in 5.20.x).
- No hard published fps tables at 50k/100k/250k polygons; degradation is driven by per-tile rendered complexity, property-object size, feature-state usage, and setData frequency rather than raw count alone.
- Key implication for us: our per-viewport tile fetch + single `fill` layer with static data-add pattern avoids the worst documented cliffs; our 120k cap is consistent with community practice. Main risks: national overlay `setData` churn, feature-state, fill-extrusion at low zoom.

## Outcome

- **Deliverable written:** `docs/research/us-416-maplibre-perf.md` — summary, evidence table, ranked mitigations, recommendation: GeoJSON LOD ships at ~120k hexes; no documented wall. Cross-links the live-spike stub (`map-rendering-performance.md`) and US-417 MVT doc.
- **Linear comment posted on US-416:** https://linear.app/harlanljones/issue/US-416/research-maplibre-rendering-performance-at-scale-120k-hex-limit#comment-65d63a89
- **Open follow-up (out of scope here):** synthetic 30k/120k/250k frame-time spike (needs a browser harness) to convert literature findings into measured mobile fps.
- No code edited; research-only, leaf-shaped. No spine files touched.
