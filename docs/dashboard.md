# Dashboard current state

This document is the implementation-facing guide to the Urban Signal dashboard. The
FastAPI HTML response is the source of truth at
`apps/api/src/serving/dashboard.py`; `scripts/export_dashboard.py` copies that
response to `apps/dashboard/public/index.html` for the Cloudflare Worker static asset.

## Current interaction model

The dashboard has two related modes:

- **Single region:** the city selector changes the map, division tabs, grid, catalyst
  feed, and inspector context to one registered region.
- **Comparison:** choose a primary region, open **+ Compare**, select one or more
  additional regions, and choose **Show selected regions**. Grid snapshots are fetched
  per city and merged into one GeoJSON source. The viewport fits the combined geometry.
  Catalyst alerts are merged and labeled with their source region.

The primary region remains the context for submarket search and parcel inspection.
This keeps the right-hand inspector unambiguous while allowing nearby regions such as
Washington DC and Montgomery County to be viewed together.

## Data and serving surfaces

| Surface | Implementation |
| --- | --- |
| City and division configuration | `CITY_CONFIGS` in `apps/api/src/serving/dashboard.py` |
| Primary region selection | `changeCity()` |
| Comparison state | `activeCities`, `toggleCompareMenu()`, `applyComparison()` |
| Grid snapshots | `GET /api/v1/grid?city_id=<id>` |
| Catalyst snapshots | `GET /api/v1/catalysts?city_id=<id>&min_lims=85.0` |
| Edge static asset | `apps/dashboard/public/index.html` |
| Static export | `python scripts/export_dashboard.py` |
| Interlock verification | `pytest -m interlock apps/api/tests/unit/test_interlock_gate.py` |

## Screenshot evidence

These captures were taken from the live dashboard on 2026-08-24 after selecting
Washington DC as the primary region and adding Montgomery County through the
comparison control:

- [DC + Montgomery County map](screenshots/dashboard-dc-montgomery.png)
- [Comparison menu state](screenshots/dashboard-comparison-menu.png)

The live API may have uneven snapshot coverage by city. A comparison remains valid
when a selected region has no current snapshot: the UI preserves the selected region
state and renders available grid/catalyst data without presenting another city's data
as a fallback.

## Refresh procedure

After changing dashboard markup or behavior:

1. Edit `apps/api/src/serving/dashboard.py`.
2. Run `python scripts/export_dashboard.py` so the Worker copy is synchronized.
3. Run the interlock gate.
4. Capture a representative single-region view and a comparison view in
   `docs/screenshots/`.
5. Update the README screenshot table and this document when the interaction model
   changes.
