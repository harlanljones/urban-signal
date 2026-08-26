# Stream log — city-boise — 2026-08-26

## Claim

- **Stream id:** `city-boise`
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/boise.py`  (geography + PERMITS spec data + imports FIELD_MAP)
  - `apps/api/src/producers/field_maps_boise.py`  (exports `FIELD_MAP`)
  - `apps/api/tests/unit/test_producers_boise.py`  (fixtures + assertions, incl. state-plane handling)
- **Spine files I expect to need (NOT edited by this leaf — reported as deltas):**
  - `apps/api/src/spatial/city_registry.py` (REGISTRY entry + FeedType member + ALIASES + __init__ import)
  - `apps/api/src/spatial/cities/__init__.py` (import boise)
  - `apps/api/src/producers/field_maps.py` (central entry dispatch to FIELD_MAP)
  - `apps/api/src/serving/dashboard.py` + `apps/dashboard/public/index.html` (METRO_META)
  - `apps/api/src/config.py` (permit endpoint setting)

## Intent

Register Boise, ID as a **residential-only, thin PERMITS feed** sourced from the
City of Boise Open Data (ArcGIS Hub, Idaho Transverse Mercator / EPSG:3694
state-plane geometry). The state-plane coordinates are NOT indexed as degrees —
the shared producer's `abs(lat)>90 / abs(lng)>180` guard drops them and the
ADR-0004 geocoder resolves the permit's street address instead. No other feeds
(311/SLA/DEEDS) are registered: Boise is a partial, single-feed city. Build only
the leaf; the spine edits are reported as exact deltas for the interlock phase.

## Decisions

- 2026-08-26 — Platform = `arcgis` (Boise Open Data Hub FeatureServer). Geometry
  arrives in EPSG:3694 state-plane; producer guard + address geocoding cover it.
- 2026-08-26 — Scope = `PERMITS` only, residential permit types. No 311/SLA/DEEDS.
- 2026-08-26 — No new producer archetype needed: address-geocode + state-plane
  guard already exist in `dob_permits_producer.py` / `geocoder.py`. Leaf is
  purely data + tests.
- 2026-08-26 — Field map `{latitude:["SHAPE__Y"], longitude:["SHAPE__X"]}` carries
  the state-plane values by their real feed names so the guard fires on them.

## Decisions (cont.)

- 2026-08-26 — No new `FeedType` needed: Boise reuses `FeedType.PERMITS`. The
  spine needs a new `CityId.BOISE` enum member, not a new feed type.
- 2026-08-26 — No `field_maps.py` edit needed: `resolve_field_map` already reads
  `spec.extra["field_map"]`, and the spine REGISTRY spec embeds
  `field_maps_boise.FIELD_MAP`. The per-city module is the only mapping source.

## Current step

Leaf complete. `pytest tests/unit/test_producers_boise.py -q` => 4 passed.
`pytest -m interlock -q` is red ONLY on pre-existing `durham`/`portland`/etc.
parallel leaves (no `boise` reference anywhere); Boise adds no registered city
so the gate never evaluates it.

## Next step

Hand the exact spine deltas below to the interlock phase (one stream at a time):
REGISTRY entry + CityId member + ALIASES, cities/__init__.py import,
METRO_META in dashboard.py + regenerated index.html, and the config.py endpoint.
