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
- 2026-10-02 — Deeds held: the Polk County Property Appraiser's nightly sales file (`ftp_sales.zip`) is registrable with the City's `LandBase/Parcels` layer for placement, but its member unpacks to 518 MB, which the CSV client reads whole. See `.streams/florida-deeds.md`.
- 2026-10-02 — Deeds registered: the CSV client now streams a zip member, so the Polk County Property Appraiser's nightly sales file reads in 6 MB instead of a gigabyte; sales on parcels numbered 23 to 25 are placed through the City's `LandBase/Parcels` layer and clipped to the metro box (1,885 published on the first live poll). See `.streams/lakeland-deeds.md`.

## Current step

Spine integration and dashboard byte-sync complete locally; preparing to run interlock tests.

## Next step

Run `pytest -m interlock` under apps/api, remediate any invariants, and open PR linked to US-286.

