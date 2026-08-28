# Stream log — us-286-lakeland — 2026-08-28

## Claim

- Stream id: city-lakeland
- Leaf files I will create/edit:
  - apps/api/src/spatial/cities/lakeland.py
  - apps/api/tests/unit/test_producers_lakeland.py
- Spine files I expect to need:
  - apps/api/src/config.py
  - apps/api/src/spatial/city_registry.py
  - apps/api/src/spatial/cities/__init__.py
  - apps/api/src/serving/dashboard.py
  - apps/dashboard/public/index.html
  - apps/product/public/facts.json
  - apps/product/public/cities/lakeland.json

## Intent

Onboard Lakeland, FL as a new Urban Signal metro with a verified ArcGIS permits feed, statewide SNAP SLA fallback, complete spatial registration (metro/divisions/submarkets), and dashboard/map wiring per the city-registration rule. Keep changes additive and isolated.

## Decisions

- 2026-08-28 — Use iMS Public CED MapServer as the permits feed endpoint. SLA via SNAP (FL).

## Current step

Spine integration and dashboard byte-sync complete locally; preparing to run interlock tests.

## Next step

Run `pytest -m interlock` under apps/api, remediate any invariants, and open PR linked to US-286.

