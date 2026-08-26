# Stream log — city-las-vegas — 2026-08-26

Copy of `.streams/_TEMPLATE.md` (phase 1, Claim). This stream builds the
PHASE-2 leaf for Linear US-145: register Las Vegas, NV (Clark County) for
PERMITS + sales/deeds, geocoder-ready per ADR-0004.

## Claim

- **Stream id:** `city-las-vegas`
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/las_vegas.py` (NEW — bbox, submarkets, divisions, FeedType specs for PERMITS + DEEDS)
  - `apps/api/src/producers/field_maps_las_vegas.py` (NEW — exports `FIELD_MAP`, imported by `las_vegas.py`)
  - `apps/api/tests/unit/test_producers_las_vegas.py` (NEW — fixtures + assertions; passes WITHOUT spine)
- **Spine files I expect to need (do NOT edit here — reported as deltas):**
  - `apps/api/src/spatial/city_registry.py` (CityId.LAS_VEGAS + REGISTRY entry + ALIASES + imports from `las_vegas.py`)
  - `apps/api/src/spatial/cities/__init__.py` (import line)
  - `apps/api/src/producers/field_maps.py` — NOT edited (per HARD RULE); map rides on `las_vegas.py` specs instead
  - `apps/api/src/serving/dashboard.py` METRO_META + `apps/dashboard/public/index.html` sync (city registration rule)
  - `apps/api/src/config.py` — optional endpoint settings if the orchestrator hoists the URL constants

## Intent

Register Las Vegas / Clark County as a TWO-FEED partial city: PERMITS
(Clark County building permits) carries native geometry; DEEDS (Clark County
parcel sales / recorded deeds) is address-only and therefore geocoder-ready
under ADR-0004 (`needs_geocode: True`). The leaf is fully self-contained and
testable without any spine edit, following the Austin two-feed pattern.

## Decisions

- 2026-08-26 — Scope is **Clark County** (countywide), consistent with the
  Reno/Washoe and Austin/Travis pattern: the county feeds cover the metro and
  the registration is named "Las Vegas".
- 2026-08-26 — DISCOVERY (no network in this environment; flagged for live
  confirmation during interlock): Clark County open data is published on a
  Socrata/ArcGIS portal (`data.clarkcountynv.gov` / `opendata.clarkcountynv.gov`).
  Building permits and real-property parcel sales are expected Socrata datasets.
  Exact resource IDs are placeholders in `las_vegas.py` constants and MUST be
  confirmed against the live catalog before the spine interlock wires them.
- 2026-08-26 — DEEDS is **address-only** (street address, no lat/lng on the
  wire): declared `needs_geocode: True` with `geocode_context="Las Vegas, NV"`
  so ADR-0004 geocodes at enrichment. PERMITS exposes `location_1` lat/long
  (Socrata geo column), so it parses natively today.
- 2026-08-26 — Field maps live on `las_vegas.py`'s `DatasetSpec.extra["field_map"]`
  (built from `field_maps_las_vegas.FIELD_MAP`), NOT in shared
  `field_maps.py`, per the HARD RULE.

## Current step

Leaf files written and unit tests verified green without spine registration.
Awaiting orchestrator interlock to apply the reported spine deltas.

## Next step

If resumed: confirm the two Clark County dataset resource IDs against the live
portal, then apply the spine deltas in `city_registry.py` + `__init__.py` +
dashboard METRO_META + `index.html` sync, run `pytest -m interlock`.
