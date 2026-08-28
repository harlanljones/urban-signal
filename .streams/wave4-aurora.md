# Stream log — wave4-aurora — US-326 Aurora, CO (leaf implementation)

Copy of `.streams/_TEMPLATE.md`. Status: **COMPLETE** 2026-08-27, LEAF-IMPLEMENTATION agent.

## Claim

- **Stream id:** `wave4-aurora` (US-326)
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/aurora.py` (new)
  - `apps/api/src/producers/field_maps_aurora.py` (new, if needed)
  - `apps/api/tests/unit/test_producers_aurora.py` (new)
  - `.streams/wave4-aurora.md` + one dispatch-log outcome row
- **Spine files I expect to need (orchestrator only):** `city_registry.py`,
  `config.py`, `serving/dashboard.py`, `cities/__init__.py`,
  `tests/unit/test_city_leaf_naming.py` (module-count bump, see Decisions).

Forbidden: spine-manifest files, existing tests, `apps/product/**`. No git commit.
Tests pass WITHOUT the spine: `city_id="aurora"` strings only; no REGISTRY/CityId
assertions for aurora.

## Intent

Aurora, CO leaf: PERMITS (MapServer/44, WKID 2232 native → outSR=4326 geometry)
+ SLA (L34 liquor + L77 non-home businesses, native X/Y), Tier 1 both. City
module with metro/division/submarket nesting interlock-correct BEFORE
registration, field maps, producer parse tests from live-captured fixtures,
and the full spine delta (CityId member, CityRegistration text, config keys,
METRO_META) reported back as paste-able code.

## Decisions

- 2026-08-27 — Stream claimed; evidence = `docs/research/probe-aurora_co.md`
  (probe stamp 2026-08-27). L156/L157 rolling windows stay unregistered.
- 2026-08-27 — KNOWN SPINE DELTA (shared gate): `test_city_leaf_naming.py`
  pins `len(_LEAF_MODULES) == 57`; adding `cities/aurora.py` makes 58.
  Measured at dispatch close: **62** leaf modules present because ALL 5 wave-4
  siblings are in the working tree. The count bump is spine-held (existing test
  file, forbidden to leaf) and must land with registration — the interlock
  wiring gate (TestDashboardWiring/TestSnapshotWiring) is NOT affected until a
  registered city is missing. Flagged in the dispatch-log outcome row.
- 2026-08-27 — **LIVE RE-PROBE (my own, 2026-08-27):** `MapServer/44` newest
  `IssueDate` = **2026-08-26T18:30:01Z** (row `26-2649763-000-00`,
  OBJECTID 552631118 — geometry -104.873226, 39.752099). `MapServer/34`
  (liquor) newest `Issue_Date` = **2026-08-18** (OBJECTID 9439714 PAYLESS
  LIQUOR). `MapServer/77` newest `Issue_Date` = **2026-08-22** (OBJECTID
  9439724 BEE LINE MEDICAL SUPPLY). All four fixture rows verified by
  OBJECTID query against the live layers; columns, geometry, and X/Y all match
  the fixtures. Probe's L77 "2026-08-21" was stale by +1d; the re-probe
  advanced both L34/L77 to the live values.
- 2026-08-27 — **State-plane transform verified live:** `_transform_state_plane`
  (EPSG:2232 NAD83 Colorado South ftUS → EPSG:4326) reproduces each fixture's
  outSR=4326 geometry to ~1e-5° (~1 m) on ALL FOUR current rows. One OLD
  (2023) permit row's PropX/PropY disagrees with its geometry by ~0.12° —
  geometry stays the primary coordinate path; the state-plane branch is the
  declared fallback (Boston-style) that the spine wires. Tested at abs=2e-5.
- 2026-08-27 — Ruff: zero net-new violations. Removed a genuinely-unused
  `FIELD_MAP` import from `cities/aurora.py` (F401) and sorted the test import
  block (I001). The remaining 17 UP006/UP035 `Dict`/`List` flags are the
  repo-wide pre-existing typing style (memphis.py / denver.py flag identically)
  and are left untouched per the "ruff net-new 0" policy.

## Current step

DONE — all leaf files authored and verified:
- `apps/api/src/spatial/cities/aurora.py` — AURORA_METRO_BBOX (39.54..39.83,
  -104.98..-104.60), 6 division bboxes, 10 submarkets in 6 divisions
  (Downtown=Original Aurora & Colfax / NW Aurora MLK; Fitzsimons-Anschutz;
  Aurora Highlands / Painted Prairie; Central Havana / Mission Viejo-Aurora
  Hills; Southlands / Seven Hills-Saddle Rock; Piney Creek & Smoky Hill),
  `is_in_aurora_metro`, AURORA_FEED_SPECS, `get_aurora_dataset`,
  `REGISTRATION`, `__all__` with all four canonical `AURORA_` constants.
- `apps/api/src/producers/field_maps_aurora.py` — PERMITS_FIELD_MAP (no
  latitude/longitude/PropX/PropY candidates), SLA_FIELD_MAP (no X/Y as
  coordinates; TaxText-first license_type), FIELD_MAP, GEOCODE_CONTEXT.
- `apps/api/tests/unit/test_producers_aurora.py` — 42 tests: spatial nesting /
  division-claim / submarket-meta; feed-spec contract; field-map column pinning
  (state-plane never degrees); state-plane transform; real producer parse of 4
  live fixtures (L44 ×2, L34 ×1, L77 ×1) through `dob_permits_producer` /
  `sla_licenses_producer` with `city_id="aurora"`; H3 tags; metro-bbox checks.

## Gates (final)

- `pytest tests/unit/test_producers_aurora.py -q` → **42 passed**.
- `pytest -m interlock -q` → **22 passed** (unregistered leaf does not break closure).
- Full `pytest tests/unit` → **1797 passed, 3 skipped, 1 failed** — the single
  failure is `test_city_leaf_naming.py` `62 == 57` (5 wave-4 sibling modules,
  spine-held count bump; not leaf-caused).
- Ruff: net-new 0; format matches reference convention.

## Next step

Orchestrator applies the spine delta (paste-able in the stream final message):
CityId.AURORA + aliases, `config.py` `arcgis_aurora_*_url` settings, REGISTRY
`CityRegistration` with the two DatasetSpecs (state-plane keys + snapshot SLA
+ companion_endpoints), `cities/__init__.py` import, `dashboard.py` METRO_META
`aurora: { name: 'Aurora, CO' }`, and the `test_city_leaf_naming.py` count pin
57 → 62 at close-out — then re-run interlock + the 5-suite registration gate.

## Spine delta (paste-able)

See the stream final message: full `CityId` member + `_HANDWRITTEN_ALIASES` lines,
`CityRegistration(...)` with both `DatasetSpec`s, `config.py` settings fields,
`METRO_META` entry, and producer-fallback notes.