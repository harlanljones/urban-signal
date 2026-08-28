# Stream log — city-alexandria — 2026-08-28

## Claim

- **Stream id:** city-alexandria
- **Leaf files I will create/edit:**
  - apps/api/src/spatial/cities/alexandria.py
  - apps/api/tests/unit/test_producers_alexandria.py
- **Spine files I expect to need:**
  - apps/api/src/spatial/city_registry.py
  - apps/api/src/spatial/cities/__init__.py
  - apps/api/src/serving/dashboard.py
  - apps/dashboard/public/index.html
  - apps/api/src/export/snapshot_builder.py

## Intent

Register CityId.alexandria (Alexandria, LA) as a new Urban Signal metro. Deliver a verified leaf geometry module plus containment tests; verify Rapides Parish/city permits and, if no verifiable public API exists, register SNAP-only using the Louisiana slice via `snap_sla_spec("LA")`. Then wire the spine (REGISTRY + ALIASES + METRO_META + snapshot/grid + dashboard byte-sync) so Alexandria appears on the public map per the city-registration rule. Keep edits strictly additive to avoid conflicts with in-flight spine PRs.

## Decisions

- 2026-08-28 — Alexandria permits run through My Permit Now (no open data endpoint found); Rapides Parish permits cover unincorporated areas via RAPC. Proceed with SNAP SLA (LA slice) only.

## Current step

Scaffolding leaf module `alexandria.py` and containment/unit tests following the Waco/Amarillo pattern.

## Next step

Add Alexandria to `CityId`, `_HANDWRITTEN_ALIASES`, and `_HANDWRITTEN_REGISTRY` (SNAP LA slice), export from `cities/__init__.py`, and wire `METRO_META` + dashboard byte-sync. Then run `pytest -m interlock` and address any gates.

