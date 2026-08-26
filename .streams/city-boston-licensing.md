# Stream log — city-boston-licensing — 2026-08-26

Copy of `.streams/_TEMPLATE.md`. Leaf worker for US-137: register Boston
Licensing Board feed. This stream handles PHASE-2 (leaf) only; the spine
interlock (registry entry, central field_maps entry, dashboard) is the
orchestrator's job and is reported, not applied here.

## Claim

- **Stream id:** `city-boston-licensing`
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/boston.py` (extend with `BOSTON_LICENSING_BOARD_FEED` spec — leaf)
  - `apps/api/src/producers/field_maps_boston_licensing.py` (new — exports `FIELD_MAP`, imports from `boston.py`)
  - `apps/api/tests/unit/test_producers_boston_licensing.py` (new — fixtures + assertions)
  - `.streams/city-boston-licensing.md` (this file)
- **Spine files I expect to need (applied by orchestrator, NOT touched here):**
  - `apps/api/src/spatial/city_registry.py` — `FeedType.SLA` already exists; add `REGISTRY[CityId.BOSTON].datasets[FeedType.SLA]` DatasetSpec + flip the "SLA excluded" comment
  - `apps/api/src/producers/field_maps.py` — central `FIELD_MAPS` entry (leaf file is the source, orchestrator references it)
  - `apps/dashboard/public/index.html` — `METRO_META` / `?city=boston` deep link already present (line ~1402); no change unless SLA adds a tile (it does not)
  - `apps/api/src/config.py` — `ckan_boston_licenses_endpoint` ALREADY exists; only its description ("not ingested…") needs updating

## Intent

Register Boston's Licensing Board feed as an address-only SLA feed (ADR 0004).
The source CKAN resource's only coordinates are `gpsx/gpsy` in Massachusetts
State Plane meters (EPSG:26986); we do NOT map them to latitude/longitude and
instead geocode the business address string at parse time, satisfying the
"State-Plane transform or ADR 0004" fork via ADR 0004.

## Decisions

- 2026-08-26 — **Platform:** CKAN (`data.boston.gov`), dataset id
  `04dc653b-1789-4374-9669-b07df7233344` (matches `config.ckan_boston_licenses_endpoint`).
- 2026-08-26 — **State-plane fork:** choose ADR 0004 (geocode address string).
  `gpsx`/`gpsy` are intentionally absent from the field map's latitude/longitude
  lists, so the producer never ingests State Plane meters as WGS84 degrees.
- 2026-08-26 — **Column spellings are PROPOSED** pending a live probe of the
  CKAN resource (mirrors the Philadelphia precedent). They are pinned by the
  unit test's equality assertion so the orchestrator inherits an exact contract.
- 2026-08-26 — **No new FeedType enum member:** Licensing Board maps to the
  existing `FeedType.SLA`. No new archetype needed in the shared producers.

## Current step

Writing the leaf files (boston.py extension, field_maps_boston_licensing.py,
test) and running the leaf test + interlock gate.

## Next step

Report exact spine deltas to the orchestrator for the interlock phase:
registry SLA DatasetSpec, central field_maps reference, dashboard note, and the
config.py description update.
