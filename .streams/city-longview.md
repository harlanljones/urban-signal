# Stream log — city-longview — 2026-08-28

## Claim

- **Stream id:** city-longview
- **Linear issue:** US-276 — Onboard Longview, TX as new metro (South Central)
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/longview.py`
  - `apps/api/tests/unit/test_producers_longview.py`
- **Spine files I expect to need:**
  - `apps/api/src/spatial/city_registry.py`
  - `apps/api/src/spatial/cities/__init__.py`
  - `apps/api/src/serving/dashboard.py`
  - `apps/dashboard/public/index.html`
  - `apps/product/public/facts.json`
  - `apps/product/public/cities/longview.json`

## Intent

Register CityId.longview (Longview, TX) as a new Urban Signal metro. Deliver a verified leaf geometry module plus containment tests; verify public permits feed or fall back to SNAP SLA (TX slice) without faking endpoints; then wire the spine (REGISTRY + ALIASES + METRO_META + snapshot/grid + dashboard byte-sync) so Longview appears on the public map per the city-registration rule. Keep edits strictly additive to avoid conflicts with in-flight metros.

## Decisions

- 2026-08-28 07:10 UTC — No verifiable municipal permits API identified pre-commit; register SLA (SNAP Retailers, TX slice) only via `snap_sla_spec("TX")`. Expand with permits in a follow-up once a public endpoint is proven.

## Current step

Leaf complete: `longview.py` geometry and containment tests authored.

## Next step

Wire spine: CityId + aliases + REGISTRY entry, `cities/__init__.py` exports, dashboard `METRO_META` + byte-sync, product facts. Then run `pytest -m interlock` and open PR linked to US-276.

