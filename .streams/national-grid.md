# Stream log — national-grid — 2026-08-27

## Claim

- **Stream id:** `national-grid`
- **Linear ticket:** US-382 (National grid foundation: CONUS polyfill + national
  signal pipeline), child of US-381 (umbrella). Related: US-383 (publish, blocked
  by this), US-384 (deck.gl, blocked by US-383), US-385/US-386 (parallel streams).
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/national_grid.py` (new — CONUS outline + polyfill)
  - `apps/api/src/spatial/data/conus_outline.geojson` (new vendored asset, if needed)
  - `apps/api/src/export/national_builder.py` (new — per-hex national signals CLI)
  - `apps/api/tests/unit/test_national_grid.py` (new)
  - `.streams/national-grid.md` (this file)
- **Spine files I expect to need:** none.

## Intent

Data foundation for the national hex layer: deterministic CONUS polyfill at H3
res 4/5/6 (golden count gate), a national-builder CLI producing per-hex signal
Parquet (v1: at least one real signal end-to-end, e.g. LODES employment; others
stubbed nullable + documented), standalone from the 15-min CI validate job.
`pytest -m interlock` stays green; no edits to any spine file or to the other
in-flight stream's dirty files (batch-push.yml, city_registry.py, producer tests,
product city JSONs).

## Decisions

- 2026-08-27 — Two-layer architecture ratified by user: national LOD display layer
  (deck.gl) + existing res-9 metro deep data. Real national signals, never
  synthesized values outside metros.
- 2026-08-27 — Rendering = deck.gl H3HexagonLayer over MapLibre via MapboxOverlay
  (user choice). Consequence for this stream: publish format is H3-index+value
  chunks (no polygon tiling); Parquet per res, partitioned by parent.

## Current step

US-382 deliverables complete (uncommitted — repo policy: human/CI commits):
- `src/spatial/assets/us_outline_census_20m.geojson` — vendored Census
  cb_2023_us_nation_20m (public domain), simplified 0.004°/5dp, 82 parts, 102 KB.
- `src/spatial/national_grid.py` — hierarchically-closed pyramid res 4/5/6;
  golden counts 5,251 / 36,757 / 257,299 (closure cost vs raw polyfill: +0.04% at
  res 5; raw fill is NOT parent-closed along coastlines).
- `src/export/national_builder.py` — LODES v1 signal (WAC jobs / RAC workers,
  sha-verified downloads, block internal-point → hex aggregation, null-honest
  group sums, percentile ranks reused from snapshot_builder), Parquet chunks
  partitioned by res-3 parent + build_report.json; CLI mirrors snapshot_builder.
- Tests: 20 unit tests green (test_national_grid.py, test_national_builder.py —
  synthetic fixtures, no network); real-network proof run: Delaware 2023
  (6,373 WAC / 12,698 RAC blocks → 144/257,299 cells with jobs; 409,883 jobs,
  407,158 workers; null cells keep null ranks). `pytest -m interlock` green.
  ruff clean. No spine edits; no overlap with wave-4 dirty files.

## Next step

Close US-382 on Linear; claim US-385 (KV sharding + CI gates, lowest open).
Remaining signals (buildings/OSM/VIIRS/ACS) are documented TODOs in
national_builder.py for follow-up tickets.
