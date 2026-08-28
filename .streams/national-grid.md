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

Surveying existing signal-research leaves (`us101-lodes`, `signal-overture`,
`signal-nlcd`, `signal-acs`, `us122-qcew`) + spatial module layout before writing
`national_grid.py`, to reuse rather than duplicate.

## Next step

Read existing signal leaf logs + spatial module; then implement polyfill + golden
count gate; then national_builder skeleton with one signal end-to-end.
