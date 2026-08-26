# Stream log — city-dallas — 2026-08-26

Copy this file to `.streams/<stream-id>.md` as your FIRST action (phase 1,
Claim) and update it at every step boundary. Commit it with your work.
Its absence is what makes a takeover cost twelve tool calls instead of one.

## Claim

- **Stream id:** `city-dallas`
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/dallas.py` (new city module)
  - `apps/api/src/producers/field_maps_dallas.py` (new, Dallas-specific field map)
  - `apps/api/tests/unit/test_producers_dallas.py` (new leaf test)
- **Spine files I expect to need (NOT edited in this phase):**
  - `apps/api/src/spatial/city_registry.py` (CityId.DALLAS enum, ALIASES, REGISTRY entry)
  - `apps/api/src/spatial/cities/__init__.py` (import)
  - `apps/api/src/producers/field_maps.py` (central entry — NOT edited; Dallas map lives in its own module)
  - `apps/api/src/config.py` (new endpoint setting)
  - dashboard `METRO_META` + `apps/dashboard/public/index.html` sync

## Intent

Register Dallas, TX with the live ArcGIS ROW permit layer and the audited
Building Services CRM 30-day partial 311 view. The ROW signal is explicitly a
construction proxy, not a standard building-permit feed. Both feeds use the
existing ArcGIS client and shared producers with Dallas-specific field maps.

## Decisions

- 2026-08-26 — Live probe confirmed `ROW/FeatureServer/0`, `CREATEDDATE`,
  `EXTERNALFILENUM`, point geometry, and ArcGIS `outSR=4326` coordinates.
- 2026-08-26 — Live probe confirmed
  `CRM_30Days_viewLayer_BuildingServices/FeatureServer/0`, `CreatedDate`,
  `Service_Request_Number_c`, native latitude/longitude, and a roughly 30-day
  Building Services-only view.
- 2026-08-26 — FeedType remains `FeedType.PERMITS` for ROW and
  `FeedType.COMPLAINTS_311` for CRM requests; `extra["proxy_for"]`, scope, and
  rolling-window metadata make the asymmetry explicit.

## Current step

Phase 2 (build leaf) COMPLETE. Leaf files and spine wiring are implemented and
verified: `pytest tests/unit/test_producers_dallas.py -q` -> 29 passed;
`pytest -m interlock -q` -> 22 passed; facts and product checks are green.

## Next step

Phase 3 COMPLETE. CityId.DALLAS, aliases, both ArcGIS DatasetSpecs, config,
dashboard, generated facts, and product surfaces are wired. US-149 is ready to
resolve after the Linear resolution comment is posted.
