# Stream log — city-texarkana — 2026-08-28

## Claim

- **Stream id:** city-texarkana
- **Leaf files I will create/edit:**
  - apps/api/src/spatial/cities/texarkana.py
  - apps/api/tests/unit/test_producers_texarkana.py
- **Spine files I expect to need:**
  - apps/api/src/spatial/city_registry.py
  - apps/api/src/spatial/cities/__init__.py
  - apps/api/src/serving/dashboard.py
  - apps/dashboard/public/index.html
  - apps/api/src/export/snapshot_builder.py
  - apps/product/public/facts.json
  - apps/product/public/cities/texarkana.json

## Intent

Onboard CityId.texarkana (Texarkana, TX-AR) as a new Urban Signal metro per US-282. Deliver a verified leaf geometry module plus containment tests; verify public permits endpoints on both sides (TX/AR) and, if not verifiable, register SNAP SLA using the primary TX slice without inventing a dual-state registration. Then wire the spine (REGISTRY + ALIASES + METRO_META + snapshot/grid + dashboard byte-sync + product facts) so Texarkana appears on the public map per the city-registration rule. Keep edits strictly additive to avoid conflicts with in-flight spine work (Beaumont #8 through Alexandria #19).

## Decisions

- 2026-08-28 — Register Texarkana SNAP-only (TX slice). Municipal permits endpoints not verified on both sides; registry supports a single state slice for SNAP today. Documented in REGISTRY comment for later expansion.

## Current step

Scaffolded leaf module `texarkana.py` and containment/unit tests following the Waco pattern.

## Next step

Add Texarkana to `CityId`, `_HANDWRITTEN_ALIASES`, and the `_HANDWRITTEN_REGISTRY` (SNAP TX slice); export from `cities/__init__.py`; wire `METRO_META` + dashboard static copy; export product site facts. Then run `pytest -m interlock` and address any gates.

