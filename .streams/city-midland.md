# Stream log — city-midland — 2026-08-28

## Claim

- **Stream id:** city-midland
- **Leaf files I will create/edit:** 
  - apps/api/src/spatial/cities/midland.py
  - apps/api/tests/unit/test_producers_midland.py (if pattern requires)
  - apps/api/tests/unit/test_spatial_midland.py (containment: submarket⊂division⊂metro)
  - apps/api/src/spatial/cities/__init__.py (__all__ export)
- **Spine files I expect to need:** 
  - apps/api/src/serving/dashboard.py (METRO_META)
  - apps/product/public/facts.json
  - apps/product/public/cities/midland.json
  - apps/dashboard/public/index.html (byte-sync)
  - docs/agents/spine-manifest.txt (ensure Midland listed)

## Intent

Onboard Midland, TX as a new Urban Signal metro (South Central). Verify municipal permits dataset via get_dataset() (fallback: snap_sla_spec(\"TX\") only if permits unavailable), add spatial definition and containment tests, register CityId.midland with REGISTRY and ALIASES, wire METRO_META and dashboard byte-sync, update snapshot/grid coverage and product facts so Midland appears on the public dashboard and passes the interlock gate.

## Decisions

- 2026-08-28 — Claimed stream for US-279 (Midland, TX). Will follow leaf-first then spine.

## Current step

Exploring existing Texas city patterns and adding apps/api/src/spatial/cities/midland.py plus tests.

## Next step

Export city in cities/__init__.py, verify dataset sources, then wire spine (METRO_META, manifests, product facts, dashboard byte-sync) and run pytest -m interlock.

