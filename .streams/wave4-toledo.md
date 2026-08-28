# Wave 4 — Toledo, OH

- **Ticket:** US-359
- **Agent:** leaf-implementation
- **Status:** claimed → completed
- **Spine delta:** pending (enum TOLEDO + aliases, CityRegistration COMPLAINTS_311 1-feed partial, config, cities/__init__, dashboard METRO_META "Toledo, OH" + index.html + snapshot wiring, leaf-naming count 57→62)
- **Leaf files:**
  - `apps/api/src/spatial/cities/toledo.py`
  - `apps/api/src/producers/field_maps_toledo.py`
  - `apps/api/tests/unit/test_producers_toledo.py` (new, 25 tests)

## Live re-probe (2026-08-27 23:04 UTC)

- Watermark `Public/CityWorks_ServiceRequest_2022/MapServer/0`: newest REQUEST_ID
  796130, `INIT_DATE` = 2026-08-27 23:04:37+00:00. 7-day count 1,092; current-year
  43,260 (probe doc's 43,252 was one day stale).
- Fixtures re-anchored byte-verbatim: 796129 (2550 Cherry St, DIST 4, H3
  872a94d23ffffff/882a94d23dfffff/892a94d23dbffff), 796127 (721 Williamsville Ave,
  DIST 1, H3 872a94d02ffffff/882a94d027fffff/892a94d026bffff), 796130 (newest,
  "1469 Bradmore Dr" — the row that exposed the geometry/CRS traps).
- CRS probes: `X_COORD`/`Y_COORD` are **mixed projection** — Web Mercator meters
  (~-9.3M/+5.1M) on most rows, Ohio State Plane **feet** (1.67M/0.74M) on 796130.
  outSR=4326 geometry is authoritative (flattened to lat/lng); LOCATION is the
  needs_geocode fallback (geocode context "Toledo, OH"). Never read X_COORD/Y_COORD
  as degrees — pinned by tests.
- Geometry reliability: 19/20 newest rows clean WGS84; the newest row (796130)
  returns a corrupted non-geographic point (15.03, 6.67) in outSR=4326 — passes the
  producer's abs() guard (in-range) and is dropped downstream by `is_in_toledo_metro`.
- Layer metadata: date fields INIT_DATE/INVT_DATE/CLOSED_DATE; esriGeometryPoint;
  `objectIdField` is None → leaf pins `oid_field="REQUEST_ID"`, `order_by="INIT_DATE DESC"`,
  `max_record_count=2000` paging; layer `maxRecordCount: 20000`.

## Gates

- Toledo suite: 25/25 green
- `test_leaf_has_canonical_constants[toledo]` + `test_city_registration.py -k toledo`: green
- interlock `-m interlock`: 22/22 green
- Full suite: 1805 passed / 3 skipped / 1 failed — the single red is the shared
  leaf-naming count 57→62 (spine-side), present on every wave-4 working tree
- Env note: installed `pyproj>=3.6.0` (declared in pyproject, was missing from the
  working venv), unblocking the aurora/boston state-plane tests that were failing
  outside my changeset