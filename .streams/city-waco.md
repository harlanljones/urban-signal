# Stream log — city-waco — 2026-08-28

## Claim

- **Stream id:** city-waco
- **Leaf files I will create/edit:** 
  - apps/api/src/spatial/cities/waco.py
  - apps/api/tests/unit/test_producers_waco.py
- **Spine files I expect to need:** 
  - apps/api/src/spatial/city_registry.py
  - apps/api/src/spatial/cities/__init__.py
  - apps/api/src/serving/dashboard.py
  - apps/dashboard/public/index.html
  - apps/api/src/export/snapshot_builder.py

## Intent

Register CityId.waco (Waco, TX) as a new Urban Signal metro. Deliver a verified leaf geometry module plus containment tests; verify public permits feed or fall back to SNAP SLA (TX slice) without faking endpoints; then wire the spine (REGISTRY + ALIASES + METRO_META + snapshot/grid + dashboard byte-sync) so Waco appears on the public map per the city-registration rule. Keep edits strictly additive to avoid conflicts with the in-flight Beaumont PR.

## Decisions

- 2026-08-28 — Start from latest main (Amarillo merged). Will register Waco with SNAP-only unless a verifiable permits API is confirmed.

- 2026-10-02 — `311` registered from the City's MyWaco requests layer on ArcGIS Online, public requests only (stream `texas-south-feeds`, `docs/research/one-family-depth-2026-10-02.md`). Permits live in Tyler EnerGov, whose GIS layers are empty.

## Current step

Scaffolding leaf module `waco.py` and containment/unit tests following the Amarillo pattern.

## Next step

Add Waco to `CityId`, `_HANDWRITTEN_ALIASES`, and `_HANDWRITTEN_REGISTRY` (SNAP TX slice), export from `cities/__init__.py`, and wire `METRO_META` + dashboard byte-sync. Then run `pytest -m interlock` and address any gates.

