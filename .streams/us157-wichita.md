# Stream log — us157-wichita — 2026-08-25

## Claim

- **Stream id:** `us157-wichita` (Linear US-157 — Register Wichita, KS — PERMITS)
- **Leaf files I will create/edit:** `apps/api/src/spatial/cities/wichita.py`,
  `apps/api/tests/unit/test_producers_wichita.py`, `.streams/us157-wichita.md`
- **Spine files I expect to need (orchestrator-held):** `config.py`,
  `city_registry.py`, `cities/__init__.py`, `serving/dashboard.py`,
  synced `apps/dashboard/public/index.html`, `tests/unit/test_interlock_gate.py`,
  `README.md`

## Intent

Register Wichita, KS as the PERMITS-only feed from the City of Wichita
`gismaps.wichita.gov` MISC/MABCD FeatureServer. Confirm the documented trap
that layer index 1 is the real permits layer (layer 0 is Code Enforcement
Violations), verify the live schema/freshness/geometry, land the geometry
module + registry spec + dashboard wiring, and gate it behind `pytest -m
interlock`.

## Decision — live probe (2026-08-25)

- **Layer trap CONFIRMED.** `.../MISC/MABCD/FeatureServer/0` name = **"Code
  Enforcement Violations"** (the documented trap). `.../FeatureServer/1`
  name = **"MABCD Permits SDE"** — the real permits layer. Registered layer
  index **1**, as the ticket specified.
- **Schema (layer 1):** point FeatureServer, `objectIdField=OBJECTID`,
  `maxRecordCount=2000`. Key fields: `PermitNumber` (string, e.g.
  `RFS2026-11032`, `PLR2026-00504`, `MEC2026-02583`), `ApplicationDate`
  (esriFieldTypeDate, **epoch-ms**), `LastModifiedDate` (epoch-ms),
  `PermitStatus`, `WorkType`, `DeclaredValuation`, `OccupancyType`,
  `Jurisdiction`, `InwardAddress`, `City`, `PostalCode`, `ParcelID`. No native
  lat/lng attribute columns — geometry is the point, sampled WGS84 via
  `outSR=4326`.
- **Geometry/extent (outSR=4326):** `xmin -97.8078, ymin 37.4748, xmax -97.1528,
  ymax 37.9121`. Metro bbox wraps Sedgwick County.
- **Freshness:** newest `ApplicationDate` epoch-ms `1787617743000` =
  **2026-08-25T00:29:03Z** (day of probe). 30-day volume = **3,298** rows;
  total = **271,991** rows — both match the ticket.
- **Feed-family scope:** only this one permits feed. No 311/licenses/deeds
  endpoint exists open — PERMITS-only registration, `get_dataset` raises
  readable errors for the rest.

## Files created / edited

- **created** `apps/api/src/spatial/cities/wichita.py` — `WICHITA_METRO_BBOX`
  (37.40–37.95, -97.85 to -97.05), `WICHITA_DIVISION_BBOXES` +
  `WICHITA_CORE` (37.52–37.80, -97.47 to -97.11), `is_in_wichita_metro`,
  `WICHITA_SUBMARKETS` (5 real neighborhoods: Downtown & Old Town, Delano,
  College Hill, Riverside, Crown Heights & Midtown — all inside the core),
  `WICHITA_DIVISIONS`. Mirrors the single-division `columbus.py` template.
- **created** `apps/api/tests/unit/test_producers_wichita.py` — registration,
  geometry/containment, field-map + live-row parse pins against the shared
  `DOBPermitsProducer` (mirrors columbus/nashville arcgis permits tests).
- **edited** `apps/api/src/config.py` — `arcgis_wichita_permits_url`
  (FeatureServer/1), with the layer-0-violations trap in the description.
- **edited** `apps/api/src/spatial/city_registry.py` — `CityId.WICHITA`,
  aliases (`wichita`, `wichita_ks`, `wichita ks`, `ict`), wichita import, and a
  PERMITS-only `CityRegistration` (state KS, center 37.6872,-97.3301,
  job_suffix `wichita`). `DatasetSpec`: arcgis, `watermark_col=ApplicationDate`,
  `id_keys=["PermitNumber","OBJECTID"]`, `oid_field=OBJECTID`,
  `max_record_count=2000` (server cap), `expected_cadence_days=7`, field_map
  (job_id→PermitNumber, issuance_date→ApplicationDate, cost→DeclaredValuation,
  job_type→WorkType/OccupancyType, status→PermitStatus, address_street→
  InwardAddress, zipcode→PostalCode, borough→Jurisdiction/City). OBJECTID kept
  out of the `job_id` chain (edit counter, Columbus precedent).
- **edited** `apps/api/src/spatial/cities/__init__.py` — import + `__all__`
  export of Wichita consts.
- **edited** `apps/api/src/serving/dashboard.py` — selector option, `CITY_CONFIGS`
  entry (WICHITA_CORE division + presets), `CITY_COORDINATES` entry. Generated
  static copy NOT hand-edited.
- **regenerated** `apps/dashboard/public/index.html` via
  `python scripts/export_dashboard.py` (repos mechanism) so the synced Worker
  copy carries Wichita for the `TestDashboardWiring` gate.
- **edited** `apps/api/tests/unit/test_interlock_gate.py` — added
  `CityId.WICHITA` to `CITY_EXPORT_NAMES` (gate coverage for Wichita's
  package exports; additive, matches the Houston precedent).
- **edited** `README.md` — Wichita row + metro counts 29→30 (and the 27→30
  enumerations) across the six count mentions.

## Current step

Leaf work complete; verification in progress.

## Next step

Run `pytest -m interlock` + focused `test_producers_wichita.py`; reconcile any
gate failures that are Wichita's (containment/dashboard wiring) without
weakening the gate.

## Gates / verification

- Focused `test_producers_wichita.py`: **10 passed**.
- Interlock gate run — see report. NOTE: the shared working tree is being
  edited CONCURRENTLY by sibling subagents (Indianapolis US-144, Houston
  US-140) and showed transient torn `city_registry.py` states (CityId.HOUSTON
  referenced before its enum entry landed). Any HOUSTON-only interlock failure
  is another agent's in-progress state, not Wichita's.

## Discrepancies / risks

- Concurrent write races on the shared spine files (esp. `city_registry.py`)
  mean the gate can be observed red for a sibling's torn state at the moment it
  is captured; Wichita's own blocks are internally consistent and additive. The
  orchestrator rollup should re-run the gate once all sibling streams settle.
- `ApplicationDate` is the application/watermark date — there is no true
  issuance/issued column in the schema, so `issuance_date` maps to
  `ApplicationDate` (the only dated permit event), consistent with the
  Columbus/watermark-col pattern.
