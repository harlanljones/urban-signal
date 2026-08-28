# Stream log — city-odessa — 2026-08-28

## Claim

- **Stream id:** city-odessa
- **Leaf files I will create/edit:**
  - apps/api/src/spatial/cities/odessa.py
  - apps/api/tests/unit/test_producers_odessa.py
- **Spine files I expect to need:**
  - apps/api/src/spatial/city_registry.py
  - apps/api/src/spatial/cities/__init__.py
  - apps/api/src/serving/dashboard.py
  - apps/dashboard/public/index.html
  - apps/product/public/facts.json
  - apps/product/public/cities/odessa.json
  - apps/api/src/export/snapshot_builder.py

## Intent

Register CityId.odessa (Odessa, TX) as a new Urban Signal metro in the South Central region. Deliver a verified leaf geometry module plus containment tests; verify municipal permits and fall back to SNAP SLA (TX slice) if no verifiable public permits endpoint is available. Then wire the spine (REGISTRY + ALIASES + METRO_META + snapshot/grid + dashboard byte-sync + product facts) so Odessa appears on the public map per the city-registration rule. Keep edits strictly additive and isolated from in-flight neighboring Texas streams.

## Decisions

- 2026-08-28 — Initial registration will use SNAP SLA (TX) only unless a verifiable Odessa municipal permits API is found during leaf work (no faked endpoints).

## Current step

Scaffolding leaf module `odessa.py` and Odessa containment/unit tests based on the Waco pattern.

## Next step

Add Odessa to `CityId`, `_HANDWRITTEN_ALIASES`, and `_HANDWRITTEN_REGISTRY` (SNAP TX slice), export from `cities/__init__.py`, wire `METRO_META`, regenerate the static dashboard HTML, and export product facts/city brief. Then run `pytest -m interlock` and address any gates.

