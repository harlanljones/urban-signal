# wave4-henderson — US-325 Henderson, NV (leaf implementation)

**Status: COMPLETED (uncommitted)** — 2026-08-28, LEAF-IMPLEMENTATION agent.

## Scope (leaf contract)

- `apps/api/src/spatial/cities/henderson.py` (new)
- `apps/api/src/producers/field_maps_henderson.py` (new, if needed)
- `apps/api/tests/unit/test_producers_henderson.py` (new)
- `.streams/wave4-henderson.md` + one dispatch-log outcome row

**Forbidden (spine-held):** `city_registry.py`, `config.py`, `serving/dashboard.py`,
`cities/__init__.py`, existing tests, `apps/product/**`. No git commit.

## Evidence

- `docs/research/probe-henderson.md` (stamped 2026-08-27) — Wave-3-ready:
  PERMITS Tier 1 (`DSC_Permits/FeatureServer/0`, watermark `IssueDate` 2026-08-25,
  7d/60d = 106/4,179, native `GISX`/`GISY` 11.8% nulls + address parts) and
  SLA Tier 2 (Active Business Licenses CSV item `2b3fac57…`, watermark
  `Original Issue Date` 2026-08-21, 7d/60d = 19/391, address-only →
  `needs_geocode`/context "Henderson, NV"; MJBL companion item `6c470a95…`).
- 311 / DEEDS Tier 3 — unregistered.
- **Live re-probe 2026-08-28 (this session, ~03:16 UTC):**
  - PERMITS `DSC_Permits/FeatureServer/0`: newest `IssueDate` =
    **2026-08-28T18:08 Z** (`FACT2026397633`, ObjectId 11127) — single
    probe-day sentinel (Albuquerque exclude discipline, confirmed); the
    2026-08-20 batch rows still carry the HMAC of the fixture set.
    Newest coordinate-bearing layer rows re-verified WGS84 degrees, exactly
    the fixture triad: `BSGR2026393601` (ObjectId 15810, -114.9619305 /
    36.04215361), `BOTH2026399545` (ObjectId 8457, -115.0289885 /
    36.02159836); two more in the same batch (ObjectId 8460/8468, all
    lng ≈ -115.09…-114.91 / lat ≈ 35.93…36.09). Layer type = **Table**
    (no geometry — native `GISX`/`GISY` attribute columns are the only
    coords; correct, no transform).
  - SLA Active Licenses CSV (item `2b3fac57…`): 12,851 rows downloaded
    live, max `Original Issue Date` = **2026-08-21** (3 rows co-newest,
    2 of them = the test fixtures `2026336192` / `2026336258`, field-for-field
    verbatim; `Primary Jurisdiction = City of Henderson` on 100%).
  - Both fixture sets therefore re-verified verbatim against live hosts.

## Plan

1. Re-probe both feeds live NOW (newest row per watermark), capture ≥2 fixture
   rows per feed; pin GISX/GISY spatial reference (State Plane vs Web Mercator).
2. Author `cities/henderson.py` mirroring `2a14fde` Memphis: METRO_BBOX,
   DIVISION_BBOXES, DIVISIONS, SUBMARKETS (Water Street District, Green Valley,
   Green Valley Ranch, Anthem, Seven Hills, MacDonald Ranch, Lake Las Vegas,
   Innovation District), `is_in_henderson_metro`, canonical `__all__`
   (HENDERSON_ prefix), leaf feed specs + `get_henderson_dataset` + REGISTRATION.
3. `field_maps_henderson.py`: permits ArcGIS map (GISX/GISY + address parts)
   and SLA CSV map (address-only).
4. Tests with `city_id="henderson"` strings (no CityId import, no REGISTRY
   assertions): permits via ArcGIS parse path, SLA via CSV parse path with
   mocked `geocode_row_if_declared` (norfolk/ADR-0004 precedent); H3 + bbox
   containment assertions.
5. Gates: test_producers_henderson.py + test_city_leaf_naming.py, interlock
   22/22, full suite; report spine delta.

## Decisions

- 2026-08-28 — Claimed per template. Note: `test_city_leaf_naming.py`
  `test_all_expected_leaf_modules_present` hard-pins 57 leaf modules;
  the working tree now holds all five uncommitted wave-4 leaves
  (aurora/henderson/omaha/toledo/virginia_beach) → 62 modules ≠ 57.
  The count bump belongs to the orchestrator's spine (single writer after
  all five wave-4 leaves land) — flagged, not touched. All per-leaf
  parametrized naming checks (`test_leaf_has_canonical_constants[...]`)
  including henderson are green; interlock 22/22.

## Current step

Complete. Changeset uncommitted per leaf contract:
`henderson.py`, `field_maps_henderson.py`, `test_producers_henderson.py`
(40 passed), `.streams/wave4-henderson.md`, one dispatch-log outcome row.

## Next step

Orchestrator applies the spine delta (see agent summary): `CityId.HENDERSON`
enum + aliases, `CityRegistration` with PERMITS + SLA `DatasetSpec`s,
config `topic_permits`/`topic_sla` wiring, `cities/__init__.py` export,
dashboard `METRO_META` "Henderson, NV" + snapshot/res-5 coverage, and the
leaf-naming count bump to 62.
