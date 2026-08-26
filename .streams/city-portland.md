# Stream log — city-portland — 2026-08-26

Copy of `.streams/_TEMPLATE.md` — first action of PHASE-2 leaf for Linear US-143.

## Claim

- **Stream id:** `city-portland`
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/portland.py` (new city module)
  - `apps/api/src/producers/field_maps_portland.py` (per-feed field maps)
  - `apps/api/tests/unit/test_producers_portland.py` (leaf tests, green w/o spine)
- **Spine files I expect to need (NOT edited here — reported as deltas):**
  - `apps/api/src/spatial/city_registry.py` — CityId.PORTLAND enum, REGISTRY entry (PERMITS + SLA), ALIASES
  - `apps/api/src/spatial/cities/__init__.py` — import PORTLAND_* + merge into `__all__`
  - `apps/api/src/producers/field_maps.py` — central entry wiring FIELD_MAP_PORTLAND
  - `apps/api/src/config.py` — `socrata_portland_permits_endpoint` / OLCC endpoint settings
  - `apps/dashboard/public/index.html` + serving METRO_META — City registration rule (TestDashboardWiring)

## Intent

Register **Portland, OR** as a two-feed partial city: **PERMITS** (Portland Maps /
data.portlandoregon.gov Socrata permits) and **SLA** (Oregon Liquor Control
Commission — OLCC — liquor licenses). Build only the leaf (city geometry,
submarkets/divisions, per-feed field maps). No spine file is touched; the
datasets' spec data is exposed on `portland.py` (`PORTLAND_FEED_SPECS`) so the
orchestrator can fold it into REGISTRY via `get_dataset()`. Tests are green
without any spine registration.

## Decisions

- **2026-08-26 — Discovery constraint.** No live network access from the sandbox;
  Portland/OLCC dataset IDs are **UNVERIFIED**. Designed from platform
  conventions: Portland Open Data is Socrata (`data.portlandoregon.gov`); OLCC
  publishes licensed-premises data (Socrata on `data.oregon.gov`, or a CSV
  export). Endpoints are placeholder constants in `portland.py` and MUST be
  confirmed by the spine owner before the REGISTRY entry is written. The real
  resource 4x4 IDs are the only unknowns — the field-map shape and geometry are
  correct regardless of the exact ID.
- **2026-08-26 — No new shared-producer archetype needed.** SLA already has the
  `sla_licenses_producer` (handles socrata/arcgis/carto/ckan/csv + geocode
  fallback). OLCC is a standard SLA registry entry (platform `socrata`, or
  `csv` if OLCC ships only a CSV). No new producer code required.
- **2026-08-26 — Two-feed partial.** PERMITS + SLA only. No DEEDS/COMPLAINTS_311
  planned for this leaf (Portland 311 is a separate consideration; left for a
  later ticket). `get_dataset(PORTLAND, FeedType.DEEDS/311)` will raise like LA's
  absent feeds.
- **2026-08-26 — Geometry.** 5 divisions, 14 submarkets, all nested in
  `PORTLAND_METRO_BBOX`; center ~45.5152, -122.6784.

## Current step

Writing `portland.py`, `field_maps_portland.py`, and
`test_producers_portland.py`; then running the leaf suite + interlock gate.

## Next step

Run `uv run pytest tests/unit/test_producers_portland.py -q` (expect green) then
`uv run pytest -m interlock -q` (expect spine untouched / green). Report spine
deltas to the orchestrator for the interlock phase.
