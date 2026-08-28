# Stream log — city-macon_bibb — 2026-08-28

## Claim

- **Stream id:** `city-macon_bibb`
- **Leaf files I will create/edit:** `apps/api/src/spatial/cities/macon_bibb.py`, `apps/api/tests/unit/test_producers_macon_bibb.py`, `.streams/city-macon_bibb.md`
- **Spine files I expect to need:** `apps/api/src/spatial/city_registry.py` (CityId.MACON_BIBB + ALIASES + REGISTRY entry), `apps/api/src/spatial/cities/__init__.py` (export), `apps/api/src/config.py` (ArcGIS permits endpoint setting), `apps/api/src/serving/dashboard.py` (METRO_META + byte-sync via `scripts/export_dashboard.py`)

## Intent

Register Macon-Bibb, GA as a new Urban Signal metro (`CityId.macon_bibb`). Deliver a verified leaf geometry module (metro bbox, divisions, submarkets) with containment tests. Prefer a verified public permits feed from the ArcGIS Hub over SNAP-only; fall back to SNAP SLA GA slice if no suitable municipal feed is available. Wire the spine (CityId + ALIASES + REGISTRY entry + config endpoint + cities/__init__.py export + dashboard METRO_META + static index sync) and export product facts so Macon-Bibb appears on the public map per the city-registration rule.

## Decisions

- 2026-08-28 — Verified a public Building Permits ArcGIS FeatureServer layer:
  `https://services6.arcgis.com/Yx1h0qHJ9wIpQWuU/arcgis/rest/services/Building_Permits_Public/FeatureServer/0`
  Fields include `INDATE` (filing), `ISSUEDATE` (issuance), address parts, and polygon geometry; max record count 1000; updated 2026-08-28.
- 2026-08-28 — 311 uses SeeClickFix; no county-managed ArcGIS REST 311 feed found. Do not register COMPLAINTS_311.
- 2026-08-28 — Register PERMITS (ArcGIS) + SLA (SNAP GA slice) in REGISTRY. Add `settings.arcgis_macon_bibb_permits_url`.

## Current step

Author the leaf geometry module (`macon_bibb.py`) with metro bbox, 4–6 divisions, and 6–10 submarkets; then add containment tests.

## Next step

Wire spine edits: CityId/ALIASES/REGISTRY in `city_registry.py`, add endpoint in `config.py`, export from `cities/__init__.py`, add METRO_META + byte-sync `apps/dashboard/public/index.html`, export product facts, and run `pytest -m interlock`.

