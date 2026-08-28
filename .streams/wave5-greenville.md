# wave5-greenville — US-340 Greenville, SC (leaf implementation)

**Status: DONE** — 2026-08-28, LEAF-IMPLEMENTATION agent (resume of a prior
attempt whose leaf modules survived in 89d4307; tests authored this session).

## Claim

- **Stream id:** wave5-greenville (US-340)
- **Leaf files I created/edit:**
  - `apps/api/src/spatial/cities/greenville.py` (verify/fix, inherited)
  - `apps/api/src/producers/field_maps_greenville.py` (verify/fix, inherited)
  - `apps/api/tests/unit/test_producers_greenville.py` (new)
  - this file + one dispatch-log outcome row
- **Spine files I expect to need (NOT touched by this leaf):**
  `city_registry.py`, `config.py`, `serving/dashboard.py`, `cities/__init__.py`,
  existing tests, `apps/product/**`. No git commit.

## Intent

Register Greenville, SC as a ONE-FEED PARTIAL metro (PERMITS only, Tier 1 —
`citygis.greenvillesc.gov` ArcGIS Server 10.81 MapServer
`InfoHUB/BuildingPermits_PriorTwoYears/MapServer/0`, watermark `NewIssueDate`,
daily; 311/SLA/deeds Tier 3 unregistered per probe). Verify the inherited
leaf module, author parse tests through the real `DOBPermitsProducer` path
with live-captured fixtures (`city_id="greenville"` strings, no CityId
import), and run all gates. Tests must NOT assert division/borough
resolution or geocode-hook call counts (spine-volatile); assert parse
fields, source-neighborhood passthrough, H3 from fixture coords, bbox
containment, field-map mappings instead.

## Evidence

- `docs/research/probe-greenville.md` (stamped 2026-08-28): PERMITS T1 daily,
  native outSR=4326 geometry (do NOT use State Plane `X_COORD`/`Y_COORD`
  attributes), `STREETADDRESS` fallback, id_keys `["PERMIT_NUM"]`,
  maxRecordCount 7000, rolling 2-year window, MapServer (not FeatureServer).
- **Resume re-probe 2026-08-28 UTC (this session):** newest
  `NewIssueDate` = `1787803200000` = **2026-08-27T04:00:00+00:00** —
  unchanged from the prior attempt's re-probe (four co-newest rows; today's
  roll had not landed new rows yet). Windows: 3d=29, 7d=38, 60d=280,
  total 3,886. 0 blank `STREETADDRESS`; all 3,886 rows carry geometry;
  `X_COORD`/`Y_COORD` ≈ 1.58e6/1.08e6 feet (some rows 0.0). NEW vs probe:
  the `time=` parameter is silently ignored (no time definition on the
  layer — returns unfiltered counts), and `NewIssueDate` is not
  where-clause queryable (ArcGIS 400) → window counts are client-side only.

## Verification verdict on inherited artifacts

- `cities/greenville.py` — SOUND. Imports clean; canonical constants
  present; all 6 division bboxes nest inside the metro bbox; all 8
  submarket anchors sit inside their own division (and the metro); all
  anchors are real Greenville places (Falls Park/Fluor Field cross-checked
  contained); FEED_SPECS consistent with the probe (endpoint, watermark,
  id_keys, maxRecordCount 7000, daily cadence); `get_greenville_dataset`
  and `REGISTRATION` well-formed. FIXES: docstring re-stamped with the
  resume re-probe (windows, `time=` caveat, oldest-row 2024-01-02, 0
  address nulls, 0.0 State Plane rows); the odd "04:0x" stamp replaced.
- `field_maps_greenville.py` — SOUND against the live layer (all mapped
  columns exist with the exact spellings; PII owner/contractor blocks never
  candidates). FIX: `job_id` gains the `OBJECTID` OID fallback (Henderson
  precedent) — `["PERMIT_NUM", "OBJECTID"]`.

## Outcome (2026-08-28)

- `apps/api/tests/unit/test_producers_greenville.py` — **36 tests**,
  spine-stable. 3 live fixtures byte-verbatim (OBJECTID 490 townhouse /
  595 single family / 636 garage — the co-newest watermark rows, captured
  at `outSR=4326`), verified dict-identical to the raw capture. Tests run
  the REAL `ArcGISClient._flatten_feature` lift (geometry → lat/lng,
  epoch-ms → ISO) before `parse_socrata_row(city_id="greenville")`:
  event fields (job_id/status/cost/address/dates), pinned APPLICDATE-None
  quirk, H3 res7/8/9 from fixture coords, metro-bbox containment via the
  leaf helper, State-Plane-guard pin, geocode-fallback outcome (no
  call-count asserts), field-map mappings, spec-vs-live-layer checks.

## Gates

- `pytest tests/unit/test_producers_greenville.py`: **36 passed**.
- `pytest tests/unit/test_city_leaf_naming.py -k greenville`: green.
- `pytest -m interlock`: **24 passed / 0 failed**.
- Full suite: **2150 tests — 1 failed / 0 errors / 3 skipped**; the one
  failure is the spine-owned leaf-count pin
  (`test_city_leaf_naming.py::test_all_expected_leaf_modules_present`,
  asserts `len(_LEAF_MODULES) == 62`; concurrent wave-5 leaves push past
  62 — orchestrator bumps with the spine hold). Note: a transient
  `test_producers_anchorage.py` failure seen mid-session was the sibling's
  in-flight uncommitted work (passes standalone); final run is clean.

## THE SPINE DELTA (for the orchestrator hold)

- **CityId enum:** add `GREENVILLE = "greenville"` (leaf passes city_id
  strings; no CityId import in the leaf).
- **Aliases:** `_HANDWRITTEN_ALIASES` += "greenville".
- **CityRegistration:** new `CityRegistration(city_id=CityId.GREENVILLE,
  name="Greenville", state="SC", center={"lat": 34.8497, "lng": -82.3992},
  metro_bbox=GREENVILLE_METRO_BBOX, division_bboxes=GREENVILLE_DIVISION_BBOXES,
  submarkets=GREENVILLE_SUBMARKETS, divisions=GREENVILLE_DIVISIONS,
  feeds={"permits": ...})` importing from `src.spatial.cities.greenville`.
- **DatasetSpec (PERMITS):** endpoint
  `https://citygis.greenvillesc.gov/arcgis/rest/services/InfoHUB/BuildingPermits_PriorTwoYears/MapServer/0`;
  config settings name: `arcgis_greenville_permits_url` (default = that
  URL) — no other settings needed (single feed, no companions);
  platform="arcgis" (MapServer, NOT FeatureServer — same `query` contract);
  watermark_col="NewIssueDate"; id_keys=["PERMIT_NUM"]; topic=
  settings.topic_permits; interval_seconds=300.0; producer_key="permits";
  ingestion_mode="incremental"; expected_cadence_days=1 (**honest cadence:
  daily** — prior-day issuance observed on both probes); needs_geocode=True
  (ADR 0004 supplement for any geometry-less rows; 0 of 3,886 live rows
  lacked geometry at re-probe); geocode_context="Greenville, SC";
  oid_field="OBJECTID"; max_record_count=7000; order_by="NewIssueDate DESC";
  field_map=PERMITS_FIELD_MAP (copy verbatim from
  field_maps_greenville.py so `resolve_field_map` post-spine matches the
  tests' patched map).
- **Acquisition caveats the spine must respect:** `NewIssueDate` is NOT
  where-clause queryable (ArcGIS 400) — watermark checks must page with
  `orderByFields=NewIssueDate DESC` and filter client-side; the `time=`
  parameter is silently ignored; rolling 2-year window (min(date) is not
  staleness); coordinates come from `outSR=4326` geometry only — never map
  State Plane `X_COORD`/`Y_COORD`.
- **cities/__init__.py:** export GREENVILLE_* block (mirrors HENDERSON_*).
- **serving/dashboard.py METRO_META:** add "Greenville, SC" metro chip +
  `?city=greenville` deep link; then dashboard wiring gate
  (TestDashboardWiring/TestSnapshotWiring) + byte-synced
  apps/dashboard/public/index.html regen + snapshot/res-5 coverage —
  registration is not done until the city shows on the map (AGENTS.md
  city-registration rule).
- **test_city_leaf_naming.py:** bump leaf-count pin 62 → 63+ (orchestrator
  counts concurrent wave-5 leaves).
- **snap_sla_spec:** Greenville has NO SLA feed — partial-metro SLA-less
  handling per the wave-5 orchestrator gate.
- **Do NOT register:** 311 ("Service Requests For Dashboard" backs internal
  `gistestpublic.greenvillesc.ads` — DNS-fails publicly), SLA
  (`InfoHUB/BusinessLicensesForHUB_2025` — static 2021-2024 renewal
  snapshot, no watermark column), deeds (parcel CAMA attributes, no
  transaction stream), and the private-org ArcGIS Hub placeholders.
