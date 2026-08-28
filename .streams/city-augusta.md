## Stream id: city-augusta

- Leaf files created:
  - `apps/api/src/spatial/cities/augusta.py` (metro bbox, 4 divisions, 8 submarkets, contains() helper, SpatialRegistration)
- Spine files edited (interlock phase):
  - `apps/api/src/spatial/city_registry.py` (CityId.AUGUSTA + ALIASES + CityRegistration with PERMITS + SNAP SLA)
  - `apps/api/src/spatial/cities/__init__.py` (export AUGUSTA_* + is_in_augusta_metro)
  - `apps/api/src/config.py` (`arcgis_augusta_permits_url` setting)
  - `apps/api/src/serving/dashboard.py` (METRO_META entry "Augusta, GA"; static copy re-synced)

## Intent

Register Augusta, GA as a new Urban Signal metro. Verify a public permits feed; fall back to SNAP SLA (GA) if 311 requires keys and no native permits points exist.

Findings:
- ArcGIS Hub: `geohub-augustagis.opendata.arcgis.com` (Open Augusta).
- Verified public permits table: `https://gismap.augustaga.gov/arcgis/rest/services/EnterpriseApps/iasWorld_Permit/MapServer/1` (CityView_Permit, non-spatial ArcGIS table). Address-only with `JOBADDRESS`, `DATE_ISSUE`, `PERMITNUMBER`, `PERMIT_STATUS`, `WORKCOST`. Registered as PERMITS with ADR-0004 geocoding and a minimal field_map; `oid_field="OBJECTID"`; cadence 7d.
- 311: Open311 exists (`augusta2-production.spotmobile.net/open311`) but requires an API key — not registered.
- SLA: Registered SNAP GA slice via `snap_sla_spec("GA")`.

## Dashboard wiring (city-registration rule)

Added METRO_META `"augusta": { name: "Augusta, GA" }` and re-synced `apps/dashboard/public/index.html` via `python scripts/export_dashboard.py`. Snapshot export derives support from `CityId` automatically; containment holds for divisions/submarkets inside the metro bbox.

## Next step

Run `pytest -m interlock` in `apps/api` where dependencies allow; export site facts (`scripts/export_site_facts.py`) to refresh `apps/product/public/facts.json` and `apps/product/public/cities/augusta.json`.

