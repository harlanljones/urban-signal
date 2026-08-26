# Stream log — dc-deeds-parcel-join — 2026-08-26

## Claim

- **Stream id:** `dc-deeds-parcel-join`
- **Leaf claim:** DC deeds producer/client enrichment for CAMA SSL rows using Parcel Lots polygons
- **Spine expected:** config.py, city_registry.py, deeds_acris_producer.py, arcgis_client.py, README, tests, interlock

## Intent

Join DC CAMA sales table rows to Parcel Lots polygons on `SSL`, then emit deed coordinates from polygon centroids while preserving the existing deeds contract.

## Decisions

- 2026-08-26 — Claimed Linear US-139 after verifying it was open, unassigned, and had no blocking relations.
- 2026-08-26 — Keep the existing CAMA sales endpoint as the primary feed and use the same-service Parcel Lots layer as a bounded centroid lookup.

## Current step

Implementation complete; the DC deeds registration now declares and executes the bounded SSL parcel join.

## Verification

- DC parcel-join, DC producer, and ArcGIS client tests: 74 passed
- `pytest -q -m interlock`: 22 passed
- `scripts/export_site_facts.py`: completed with 35 metro artifacts
- `git diff --check`: clean

## Next step

No remaining implementation step; Linear US-139 is resolved and marked Done.
