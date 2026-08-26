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

Louisville, KY is a TWO-FEED partial city (US-148): COMPLAINTS_311 (Louisville
Metro open-data 311 service requests) and SLA (Kentucky Alcoholic Beverage
Control liquor-license feed). Build the leaf module following `austin.py`
(bbox, divisions, submarkets, `is_in_*_metro`) plus a per-city field-map module
and a leaf-only test that passes WITHOUT spine registration. No new producer
archetype is required — both feeds ride the existing Socrata-backed 311 and SLA
producers via a registry entry + field_map.

## Decisions

- 2026-08-26 — DISCOVERY: Louisville Metro open data = Socrata portal
  (data.louisvilleky.gov); Kentucky ABC licenses = Kentucky open data Socrata
  portal (data.kentucky.gov). Both 311 + SLA shapes are already carried by the
  shared `complaints_311_producer` / `sla_licenses_producer` Socrata clients.
  CONFIRMED: no new archetype needed; leaf is registry entry + field_map only.
- 2026-08-26 — Field spellings for the two feeds are declared as
  `LOUISVILLE_FIELD_MAPS` (mirrors the Wave-B mechanism). The exact Socrata
  resource IDs / watermark columns are flagged "confirm at interlock" because
  live catalog discovery was unavailable from the build sandbox; the SHAPE is
  correct and the leaf test pins the field-map structure.

## Current step

Leaf complete and verified: `uv run pytest tests/unit/test_producers_louisville.py -q`
(19 passed) and `uv run pytest -m interlock -q` (22 passed). Awaiting interlock.

## Next step

Orchestrator applies the spine deltas recorded in the report: REGISTRY entry +
CityId member + ALIASES, the city-module import (cities/__init__.py __all__ and
city_registry.py import block), the field_maps central aggregation entry, the
config.py Socrata endpoint settings, and the dashboard METRO_META + index.html
sync — all in one spine hold so the interlock gate stays green.
