# Stream log — city-fort-smith — 2026-08-28

Claimed per parallel-streams protocol. Updating at each step boundary.

## Claim

- **Stream id:** `city-fort-smith`
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/fort_smith.py` (metro bbox, division bbox, submarkets, contains)
  - `.streams/city-fort-smith.md` (this log)
- **Spine files I expect to need (serial hold):**
  - `apps/api/src/spatial/city_registry.py` (CityId.FORT_SMITH + ALIASES + REGISTRATION with SNAP AR SLA)
  - `apps/api/src/spatial/cities/__init__.py` (export Fort Smith symbols + __all__)
  - `apps/api/src/serving/dashboard.py` (METRO_META entry "Fort Smith, AR")
  - `apps/dashboard/public/index.html` (byte-synced static copy)
  - `apps/product/public/facts.json` + `apps/product/public/cities/fort_smith.json` (via `scripts/export_site_facts.py`)

## Intent

Onboard Fort Smith, AR as a new Urban Signal metro (South Central region). Verify availability of a municipal building-permits feed; if none is publicly verifiable, register SNAP Retailer Locator as the SLA slice (`snap_sla_spec("AR")`) per ticket guidance. Deliver a complete registration per city-registration rule: REGISTRY + ALIASES + METRO_META + snapshot/grid coverage + byte-synced dashboard static. Keep the edit additive and isolated from Amarillo/Beaumont/Waco/Tyler/Lake Charles.

## Decisions

- 2026-08-28 06:55Z — Probe result: no public municipal permits API found for Fort Smith (CityView portal present; GIS public items limited to utilities). Proceeding with SNAP SLA fallback using `snap_sla_spec("AR")` (ticket allows; use AR, not TX/LA).

## Current step

Authoring `apps/api/src/spatial/cities/fort_smith.py` with metro/division bboxes and 5–6 submarkets; ensure containment invariant holds.

## Current step

Leaf geometry authoring.

## Next step

1) Register CityId + ALIASES + REGISTRY (SLA only, AR) + exports. 2) Add METRO_META and export dashboard static. 3) Export product facts. 4) Run `pytest -m interlock`. 5) Open ready PR linked to US-275.
