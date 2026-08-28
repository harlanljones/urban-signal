# wave4-omaha — US-358 Omaha, NE (leaf implementation)

**Status: CLAIMED** — 2026-08-28, LEAF-IMPLEMENTATION agent.

## Scope (leaf contract)

- `apps/api/src/spatial/cities/omaha.py` (new)
- `apps/api/src/producers/field_maps_omaha.py` (new, if needed)
- `apps/api/tests/unit/test_producers_omaha.py` (new)
- `.streams/wave4-omaha.md` + one dispatch-log outcome row

**Forbidden (spine-held):** `city_registry.py`, `config.py`, `serving/dashboard.py`,
`cities/__init__.py`, existing tests, `apps/product/**`. No git commit.

## Evidence

- `docs/research/probe-omaha.md` — REGISTER partial, 311 only (Tier 1).
- DCGIS ArcGIS: `Cityworks/Mayors_Hotline_Dashboard_Interactive/MapServer/0`.
- Watermark `DATETIMEINIT`; native point geom `outSR=4326`; PII drop
  `INITIATEDBY`/`CLOSEDBY`. Probe stamp 2026-08-28.

## Plan

1. Re-probe live watermark (newest `DATETIMEINIT` by `orderByFields`), capture ≥2 fixture rows.
2. Author `cities/omaha.py` mirroring Memphis (311-led partial): bbox NE side only,
   divisions + submarkets, `is_in_omaha_metro`, canonical `__all__` (OMAHA_ prefix).
3. `field_maps_omaha.py` if the ArcGIS row → Complaint311Event mapping needs one.
4. Tests: fixture rows through `complaints_311_producer` with `city_id="omaha"`
   (string, no CityId import), classify/H3/bbox assertions.
5. Gates: test_producers_omaha.py + test_city_leaf_naming.py + interlock 22/22 + full suite.

## Outcome

**COMPLETED** (leaf, uncommitted) — 2026-08-28.

- Leaf artifacts: `cities/omaha.py` (1-feed partial, COMPLAINTS_311), `field_maps_omaha.py`, `test_producers_omaha.py` (37 tests green).
- Live re-probe: `Mayors_Hotline_Dashboard_Interactive/MapServer/0` = 648,608 rows;
  newest `DATETIMEINIT` 2026-08-27 (DateOnly, same-day). Fixtures OBJECTID 663169
  (Tree/Shrub, 15308 Wycliffe Dr) and 663325 (Illegal Dumping, 6510 S 30th St)
  re-verified **verbatim** on top of the watermark window; geoms match outSR=4326.
- Gates: `test_producers_omaha.py` green; leaf-naming per-module constants green;
  interlock `-m interlock` 22/22. Full suite: single failure is the spine-owned
  `test_city_leaf_naming.py::test_all_expected_leaf_modules_present` (57→62 count;
  wave4 leaves added aurora/henderson/omaha/toledo/virginia_beach). No spine files
  touched, no commit.
- Spine delta for orchestrator: see US-358 final summary message.
