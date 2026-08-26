# Stream log — city-el-paso — 2026-08-26

## Claim

- **Stream id:** city-el-paso
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/el_paso.py` (geometry: metro bbox, division bboxes, submarkets, divisions, `is_in_el_paso_metro`) — already present from prior run; leaf shape verified.
  - `apps/api/src/producers/field_maps_el_paso.py` (NEW — exports `FIELD_MAP`, imports from `el_paso.py`; does NOT edit shared `field_maps.py`).
  - `apps/api/tests/unit/test_producers_el_paso.py` (NEW — spine-independent: geometry + `FIELD_MAP` via `first_mapped` + producer parse with field map injected).
- **Spine files I expect to need (NOT edited by this leaf; reported as deltas):**
  - `apps/api/src/config.py` (`arcgis_el_paso_311_url` — already present)
  - `apps/api/src/spatial/city_registry.py` (`CityId.EL_PASO`, `ALIASES`, `REGISTRY[CityId.EL_PASO]` — already present from prior run)
  - `apps/api/src/spatial/cities/__init__.py` (import block — already present)
  - Dashboard `METRO_META` + `index.html` sync (El Paso byte-present in `index.html` — already present)

## Intent

Register El Paso, TX 311 (partial) as a leaf: Austin-style geometry module plus a
per-city `FIELD_MAP` consumed by the shared `complaints_311_producer` via
`resolve_field_map`. Partial = COMPLAINTS_311 only (Accela/Cityworks
`Requests` FeatureServer/0, ArcGIS, `created_at` watermark, ~30-day rolling window).
Permits / SLA / Deeds deliberately unregistered.

## Decisions

- 2026-08-26 — Platform: El Paso 311 is an ArcGIS FeatureServer (Accela-backed);
  native TX state-plane geometry transformed by existing ArcGISClient `outSR=4326`.
  Field spellings (`id`/`request_id`/`OBJECTID`, `created_at`, `request_type`/
  `request_category`, `address`, `district`) declared as `FIELD_MAP` data, not
  grown into shared chains.
- 2026-08-26 — Leaf test written spine-independent so it passes WITHOUT
  `REGISTRY`/`ALIASES` registration (requirement of phase-2 leaf). Producer
  parse asserted with `resolve_field_map` patched to return the leaf `FIELD_MAP`.
- 2026-08-26 — PRE-EXISTING BLOCKER (out of scope, spine, forbidden to edit):
  the interlock gate is RED due to an unrelated `durham` torn write
  (`CityId.DURHAM`/ALIASES/`durham` city module exist, but no `REGISTRY`
  entry). All 5 interlock failures name `durham`, none name `el_paso`. El Paso
  itself is fully wired (in REGISTRY, `__init__`, `index.html`).

## Current step

Leaf complete: `el_paso.py` (verified self-consistent), `field_maps_el_paso.py`
created, `test_producers_el_paso.py` passes via `uv run pytest`. Awaiting spine
interlock (separate stream) to resolve the unrelated `durham` gap so the gate is green.

## Next step

- Hold interlock: confirm/apply El Paso spine deltas (reported in ticket REPORT)
  and fix the `durham` REGISTRY gap in the same interlock hold, then re-run
  `pytest -m interlock`.
- Optional leaf improvement: have the spine `REGISTRY` COMPLAINTS_311 spec import
  `FIELD_MAP` from `field_maps_el_paso` (single source of truth) instead of the
  current inline duplicate.
