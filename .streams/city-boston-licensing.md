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

Register Boston's Licensing Board feed as a CKAN SLA feed using Path A. The
source CKAN resource's `gpsx/gpsy` values are Massachusetts Mainland State
Plane US survey feet (EPSG:2249); `pyproj` transforms them to WGS84 at parse
time.

## Decisions

- 2026-08-26 — **Platform:** CKAN (`data.boston.gov`), dataset id
  `04dc653b-1789-4374-9669-b07df7233344` (matches `config.ckan_boston_licenses_endpoint`).
- 2026-08-26 — **State-plane fork:** user chose Path A. Live CKAN rows and the
  acceptance sample match EPSG:2249 (US survey feet), despite earlier evidence
  text naming EPSG:26986 meters; `gpsx`/`gpsy` are transformed with pyproj.
- 2026-08-26 — Live CKAN schema pinned: `license_num`, `license_type`, `expires`,
  `business_name`, `dba_name`, `address`, `city`, `status`, `gpsx`, `gpsy`.
- 2026-08-26 — **No new FeedType enum member:** Licensing Board maps to the
  existing `FeedType.SLA`. No new archetype needed in the shared producers.

## Current step

Implementation complete: registry, producer transform, dependency lock, tests,
README, and config description are updated.

## Next step

Run the focused Boston tests, interlock gate, product checks, and then close
US-137 in Linear.
