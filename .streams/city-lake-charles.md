# Stream log — city-lake-charles — 2026-08-28

## Claim

- **Stream id:** city-lake-charles
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/lake_charles.py`
  - `apps/api/tests/unit/test_cities_lake_charles.py`
- **Spine files I expect to need:**
  - `apps/api/src/spatial/city_registry.py`
  - `apps/api/src/spatial/cities/__init__.py`
  - `apps/api/src/serving/dashboard.py`
  - `apps/dashboard/public/index.html` (generated via `scripts/export_dashboard.py`)
  - `apps/product/public/facts.json` and `apps/product/public/cities/lake_charles.json` (generated via `scripts/export_site_facts.py`)

## Intent

Add Lake Charles, LA as a new Urban Signal metro. Leaf first: implement `lake_charles.py` with metro/division/submarket geometry and containment guarantees, plus a leaf test enforcing containment. Spine last: register `CityId.LAKE_CHARLES` with a minimal dataset set (SLA via `snap_sla_spec("LA")` pending verified Calcasieu GIS municipal feeds), wire aliases, export in `cities/__init__.py`, add `METRO_META`, regenerate the dashboard static copy, and export product facts. Keep edits additive and isolated; do not touch Amarillo/Beaumont/Waco/Tyler.

## Decisions

- 2026-08-28 — Calcasieu Parish/Lake Charles public ArcGIS permit endpoints not verifiably discoverable in a quick probe; proceed with SLA fallback (`snap_sla_spec("LA")`). Register permits later when a public API is confirmed. Louisiana, not Texas — SNAP uses `"LA"`.

## Current step

Implementing `apps/api/src/spatial/cities/lake_charles.py` and the containment test.

## Next step

Wire spine: add `CityId.LAKE_CHARLES` + `_HANDWRITTEN_REGISTRY` entry (SLA only), aliases, cities exports; then METRO_META + byte-sync; export site facts; run `pytest -m interlock` if deps allow; open PR. 

