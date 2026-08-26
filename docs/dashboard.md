# Dashboard current state

This document is the implementation-facing guide to the Urban Signal dashboard. The
FastAPI HTML response is the source of truth at
`apps/api/src/serving/dashboard.py`; `scripts/export_dashboard.py` copies that
response to `apps/dashboard/public/index.html` for the Cloudflare Worker static asset.

## Current interaction model

The dashboard is a **single national map**: every registered metro renders at the
same time. There is no city selector and no comparison mode to operate.

- **National boot:** on load the client fetches `/api/v1/manifest`, fits the
  camera to the union of all metro bounding boxes, and renders metro chips plus
  the combined catalyst feed (`/api/v1/catalysts/all`). Cell hexagons stay
  hidden until the camera crosses the zoom floor.
- **Metro chips (navigation only):** one chip per metro plus an "All Metros"
  reset. A chip flies the camera to that metro's bbox and scopes only the
  catalyst feed list; it never unloads or hides other metros' data.
- **Lazy loading:** cell data lives in res-5 parent-H3 tiles in Workers KV.
  On camera settle (`moveend`, debounced) the client samples the visible bounds,
  intersects with the manifest's `tile_index`, and batch-fetches missing tiles
  from `/api/v1/gridtiles?parents=<csv>` (max 32 parents/request, 2 concurrent,
  center-out ordering). Loaded cells accumulate in one GeoJSON source, deduped
  by H3 index. Below zoom 6 nothing is fetched and a hint is shown instead.
- **Deep links:** `?city=<id>` deep links land preselected as a camera preset
  (validated against `METRO_META`). Product-site city pages and `sitemap.xml`
  generate these links; they no longer scope data.
- **Search:** submarket search runs over the merged catalog of all metros; each
  result carries its city attribution.

## Cross-metro normalization

Raw LIMS scores are sigmoid-projected z-scores against fixed NYC-calibrated
baselines (`apps/api/src/features/lims_calculator.py`), so equal raw scores in
different metros are not distribution-comparable. To make one national color
scale meaningful, the snapshot builder stamps two average-rank percentile ranks
onto every grid feature for each map metric
(`lims_score`, `delta_6m_p50`, `delta_12m_spillover`,
`prob_18m_macro_outperformance`):

| Property | Meaning |
| --- | --- |
| `<metric>_metro_pct` | percentile rank within the feature's own metro |
| `<metric>_national_pct` | percentile rank across every exported metro |

Percentiles are computed once per publish over the complete dataset before any
KV key is written, so lazily-loaded viewport tiles always agree with each other.
Ties share an averaged rank; the scale is 0–100. Map paints read
`*_national_pct`; tooltips and the inspector show the raw score alongside both
percentiles. Catalyst thresholds keep raw-LIMS semantics (85) unchanged.

## Data and serving surfaces

| Surface | Implementation |
| --- | --- |
| Metro metadata (chips, deep-link validation) | `METRO_META` in `apps/api/src/serving/dashboard.py` |
| Snapshot metadata / tile index / camera bboxes | `GET /api/v1/manifest` (`tile_index`, `metro_index`) |
| Viewport tiles | `GET /api/v1/gridtiles?parents=<res5 csv>` |
| Combined catalyst feed | `GET /api/v1/catalysts/all` |
| Per-city snapshots (agents/back-compat) | `GET /api/v1/grid\|catalysts\|submarkets?city_id=<id>` |
| Snapshot builder (normalization + tiles) | `apps/api/src/export/snapshot_builder.py` |
| Edge static asset | `apps/dashboard/public/index.html` |
| Static export | `python scripts/export_dashboard.py` |
| Interlock verification | `uv run pytest -m interlock apps/api/tests/unit/test_interlock_gate.py` |

## Registration rule

A registration is done when the city appears on the map: `METRO_META` entry in
the dashboard source (chip + deep link), snapshot export coverage, grid-tile
coverage, and a byte-equal workers static copy — all enforced by
`pytest -m interlock` in `test_interlock_gate.py`.

## Refresh procedure

After changing dashboard markup or behavior:

1. Edit `apps/api/src/serving/dashboard.py`.
2. Run `python scripts/export_dashboard.py` so the Worker copy is synchronized.
3. Run the interlock gate.
4. Capture a representative national view and a metro-focused view in
   `docs/screenshots/`.
5. Update the README screenshot table and this document when the interaction model
   changes.

The live API may have uneven snapshot coverage by metro: the manifest's
`metro_index` drives chips and the camera, while `tile_index` gates which
viewport tiles exist. A metro with registered submarkets but no published cells
fails the tile-coverage interlock test rather than rendering as an empty map.
