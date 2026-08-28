# Stream log — city-abilene — 2026-08-28

## Claim

- **Stream id:** city-abilene
- **Leaf files I will create/edit:**
  - apps/api/src/spatial/cities/abilene.py
  - apps/api/tests/unit/test_producers_abilene.py
- **Spine files I expect to need:**
  - apps/api/src/spatial/city_registry.py
  - apps/api/src/spatial/cities/__init__.py
  - apps/api/src/serving/dashboard.py
  - apps/dashboard/public/index.html
  - apps/api/src/export/snapshot_builder.py
  - apps/product/public/facts.json
  - apps/product/public/cities/abilene.json

## Intent

Register CityId.abilene (Abilene, TX) as a new Urban Signal metro. Deliver a verified leaf geometry module plus containment tests; verify public permits feed or fall back to SNAP SLA (TX slice) without faking endpoints; then wire the spine (REGISTRY + ALIASES + METRO_META + snapshot/grid + dashboard byte-sync + product facts) so Abilene appears on the public map per the city-registration rule. Keep edits strictly additive to avoid conflicts with in-flight Texas spine holds.

## Decisions

- 2026-08-28 — Will register Abilene with SNAP-only (TX slice) pending a verifiable municipal permits API.

## Current step

Scaffolding leaf module `abilene.py` and containment/unit tests following the Amarillo/Waco pattern; wiring enum, aliases, and registry.

## Next step

Wire METRO_META + dashboard byte-sync and export product facts; run `pytest -m interlock` and address any failing gates.

