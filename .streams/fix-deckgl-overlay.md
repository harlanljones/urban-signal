# Stream log — fix-deckgl-overlay — 2026-08-30

## Claim

- **Stream id:** `fix-deckgl-overlay`
- **Leaf files I will create/edit:**
  - `apps/api/src/serving/dashboard.py`
  - `apps/dashboard/public/index.html` (byte-synced via `scripts/export_dashboard.py`)
  - `.streams/fix-deckgl-overlay.md`
- **Spine files I expect to need:** none

## Intent

Fix the broken national all-metros LOD overlay (US-391): the deck.gl 8.9.36 UMD
bundles clobber the global `deck` namespace (each bundle runs
`root['deck'] = factory()`, so only the last-loaded package's exports survive),
which means `H3HexagonLayer` and `@deck.gl/layers` never resolve and the overlay
never renders. Drop deck.gl entirely (preferred option 1) and render the national
LOD hexes as MapLibre `geojson` layers fed by the existing
`/api/v1/national/{res}` endpoint, colored by the selected metric's `_national_pct`
ramp (emerald → amber → orange → crimson), 3D extrusion when
`currentPerspective === '3D'` and flat in 2D. Preserve 3D/2D toggle, metric
switching, metro-chip flights, `?city=` deep links, `prefers-reduced-motion`, and
the metro res-9 tile layers. Regenerate the byte-synced `apps/dashboard/public/index.html`
via `scripts/export_dashboard.py`; run `tests/unit/test_serving.py` and `pytest -m interlock`
green. No spine files touched.

## Decisions

- <2026-08-30> Claimed ticket US-391; chose option 1 (drop deck.gl, MapLibre geojson layers).
- <2026-08-30> Confirmed via worker src + tests that `/api/v1/national/{res}` returns rows-of-arrays chunks (`{cols, rows}`), NOT GeoJSON `features` — the old JS read `payload.features` and would have received nothing even with a working deck.gl. New client converts each row to a GeoJSON Polygon via `h3.cellToBoundary`.
- <2026-08-30> National chunks carry LODES percentiles (`jobs_pct`/`workers_pct`), not per-metric `_national_pct`. Color/height expressions use `['coalesce', ['get', '<metric>_national_pct'], ['get','jobs_pct'], ['get','workers_pct']]` so a future national payload with metric percentiles colors correctly, falling back to LODES pcts today. Rows with neither percentile finite are skipped (honesty rule).
- <2026-08-30> Implementation done, export byte-synced, all tests green (see below).

## Current step

All verification complete. Changes left dirty in working tree (no commit).

## Next step

None — stream complete. Report back to dispatcher.

## Verification

- `apps/api/tests/unit/test_serving.py`: 32 passed.
- `pytest -m interlock` (apps/api): 24 passed (no spine files touched).
- `node --check` on extracted main inline `<script>`: JS syntax OK.
- `python3 scripts/export_dashboard.py` regenerated `apps/dashboard/public/index.html`; `get_dashboard_html() == static copy` byte-identical.
- `grep -i "deck\.gl\|@deck\|deckOverlay\|H3HexagonLayer\|MapboxOverlay" apps/dashboard/public/index.html`: 0 matches.

