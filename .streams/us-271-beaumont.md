# Stream log — city-beaumont — 2026-08-28

## Claim

- **Stream id:** city-beaumont
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/beaumont.py`
  - `apps/api/tests/unit/test_producers_beaumont.py`
- **Spine files I expect to need:**
  - `apps/api/src/spatial/city_registry.py`
  - `apps/api/src/spatial/cities/__init__.py`
  - `apps/api/src/serving/dashboard.py` (METRO_META)
  - `apps/dashboard/public/index.html` (byte-sync via `python scripts/export_dashboard.py`)

## Intent

Onboard Beaumont, TX as a new Urban Signal metro. Implement the leaf geometry and submarkets first, then register `CityId.beaumont` in the spine with aliases, dashboard METRO_META, and byte-synced dashboard static copy. Register only feeds that exist and are verifiable; use `snap_sla_spec("TX")` if no public permits feed is available.

## Decisions

- 2026-08-28 — Initial claim created. Will verify public feeds (permits, county GIS) and proceed leaf-first.

## Current step

Create leaf module `apps/api/src/spatial/cities/beaumont.py` with metro bbox, one division bbox, and 4–5 submarkets. Add unit tests to assert containment and naming.

## Next step

Verify live permits endpoints. If unavailable, register only SNAP SLA (TX slice) in the spine, add aliases, add Beaumont to METRO_META, byte-sync `apps/dashboard/public/index.html`, and run `pytest -m interlock` from `apps/api`.*** End Patch***} >>>
