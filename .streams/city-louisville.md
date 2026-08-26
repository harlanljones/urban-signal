# Stream log — city-louisville — 2026-08-26

Copy this file to `.streams/<stream-id>.md` as your FIRST action (phase 1,
Claim) and update it at every step boundary. Commit it with your work.

## Claim

- **Stream id:** city-louisville
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/louisville.py` (new)
  - `apps/api/src/producers/field_maps_louisville.py` (new)
  - `apps/api/tests/unit/test_producers_louisville.py` (new)
- **Spine files I expect to need:** (all applied by orchestrator at interlock,
  NOT by this leaf stream)
  - `apps/api/src/spatial/city_registry.py` (REGISTRY entry + FeedType members +
    ALIASES + `__init__`-style import of the city module)
  - `apps/api/src/config.py` (Socrata endpoint settings for Louisville 311 + KY ABC)
  - `apps/api/src/producers/field_maps.py` (central aggregation entry)
  - `apps/dashboard/.../METRO_META` + `apps/dashboard/public/index.html` sync

## Intent

Louisville, KY is a TWO-FEED partial city (US-148): COMPLAINTS_311 from the
Louisville Metro 2026 ArcGIS layer and SLA from the Kentucky ABC active-license
ArcGIS layer, filtered to Jefferson County. Both feeds ride the existing
shared producers via registry entries and field maps. PERMITS and DEEDS remain
unregistered.

## Decisions

- 2026-08-26 — Live probe confirmed `metro_311_2026/FeatureServer/0` with
  `requested_datetime`, native point coordinates, and annual layer rotation.
- 2026-08-26 — Live probe confirmed `ABC_State_ActiveLicenses/FeatureServer/0`
  with `IssueDate`, native point coordinates, and Jefferson County filtering;
  the source is alcohol-only and not a full business-license universe.
- 2026-08-26 — No new producer archetype is required; ArcGISClient flattening
  and the shared 311/SLA parsers carry both feeds.

## Current step

Leaf and spine complete and verified: `pytest tests/unit/test_producers_louisville.py -q`
(19 passed), `pytest -m interlock -q` (22 passed), facts and product checks green.

## Next step

Phase 3 COMPLETE. CityId.LOUISVILLE, aliases, both ArcGIS DatasetSpecs,
config, dashboard/static copy, generated facts, and product surfaces are wired.
US-148 is ready to resolve after the Linear completion comment is posted.
