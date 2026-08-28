# wave5-tucson — US-328 Tucson, AZ (leaf implementation)

**Status: COMPLETED (uncommitted)** — 2026-08-28, LEAF-IMPLEMENTATION agent.

## Scope (leaf contract)

- `apps/api/src/spatial/cities/tucson.py` (new)
- `apps/api/src/producers/field_maps_tucson.py` (new)
- `apps/api/tests/unit/test_producers_tucson.py` (new, 41 tests)
- `.streams/wave5-tucson.md` + one dispatch-log outcome row

**Forbidden (spine-held):** `city_registry.py`, `config.py`,
`serving/dashboard.py`, `cities/__init__.py`, `watermarks.py`, existing
tests, `apps/product/**`. No CityId import for tucson; `city_id="tucson"`
strings only. No git commit.

## Evidence

- `docs/research/probe-tucson.md` (stamped 2026-08-27) — SLA Tier 2
  (`OpenData_EconomicDevelopment/MapServer/3` `BUSLIC`, watermark
  `DT_START`, future-dated sentinels, slow cadence); PERMITS/311/DEEDS
  Tier 3.
- **Live re-probe 2026-08-28 (this session):**
  - Row count **93,483** (probe-exact). `maxRecordCount=2000`;
    `objectIdField` absent from metadata (OBJECTID still the id);
    `DT_START` is the only `esriFieldTypeDate` column.
  - **Future-dated sentinels confirmed live:** newest `DT_START` =
    **2026-09-12** (`NICHOLS BARBARA JANE`, OBJECTID 16 — **null
    geometry**), then 2026-09-03 (`FORUM AT TUCSON`, OBJECTID 5). Newest
    non-future = **2026-05-29** (Trader Joe's #288, OBJECTID 6) —
    probe-exact. 4 fixtures captured **byte-verbatim** (OBJECTID
    16/6/7/9), including the CHAR-padded columns (`ACC_NUM`
    `"T3092422            "`, `LIC_STATUS` `"Application         "`,
    `ZIP_CODE` `"85714     "`).
  - **ANSI-date host (NEW finding, not in probe):**
    `gis.tucsonaz.gov` rejects ISO date literals in `where` (400
    "Unable to complete operation") and only accepts ANSI
    `date 'YYYY-MM-DD'` — same family as `ANSI_DATE_LITERAL_HOSTS`
    (DC/Milwaukee/Charlotte). Bare-literal `DT_START NOT IN ('…')` also
    400s; `date '…'` NOT IN works (93,473).
  - Guard verified live: `DT_START <= CURRENT_TIMESTAMP` + `orderByFields
    =DT_START DESC` → newest = OBJECTID 6 (2026-05-29).
  - CITY value evidence: TUCSON 79,012; PIMA COUNTY 12,424; **ORO VALLEY
    1,021** (evidences the Oro Valley edge submarket); MARANA 672;
    SOUTH TUCSON 249.

## Sentinel / watermark handling (encoded in the leaf spec)

- Primary guard: spec `where = "DT_START <= CURRENT_TIMESTAMP"` — excludes
  the rolling set of future-dated application rows at the source. A
  static `watermark_exclude` list cannot pin rolling sentinels, and the
  bare-literal NOT IN it emits is server-broken on this ANSI-date host,
  so `watermark_exclude` stays **empty** (pinned by test).
- Scheduler's US-111 `is_future_watermark` guard covers any residual
  future row from pinning the high watermark (tested against the live
  sentinel fixture).
- Slow cadence: `expected_cadence_days=30` (probe: 7–30; live ≈2
  non-future rows/60d) + `alarm_exempt=True` +
  `alarm_exempt_reason` citing the pace, the sentinel guard, and the
  maintained layer.
- Spine MUST add `gis.tucsonaz.gov` to `ANSI_DATE_LITERAL_HOSTS`
  (watermarks.py) so incremental `watermark_comparison` renders ANSI on
  incremental passes (snapshot mode never composes the comparison).

## Decisions

- 2026-08-28 — Claimed per leaf contract. Wave-4/5 lesson applied: tests
  assert parse fields, source passthrough, H3 from fixture coords, bbox
  containment, field-map mappings, flatten contract, sentinel semantics —
  NOT division/borough resolution results and NOT geocode-hook call
  counts.
- 2026-08-28 — `address_street` maps to `FULLADDRESS` (single clean
  field), NOT the STREETNUM/DIR/NAM/SUF parts-join the probe sketched:
  `first_mapped` returns one value and the padded `STREETNUM` part alone
  is not geocodeable. Padded source columns pinned verbatim; SLA parser
  strips `license_id` itself.
- 2026-08-28 — 5 divisions / 8 submarkets (exactly the ticket list; Oro
  Valley edge evidenced by 1,021 CITY='ORO VALLEY' rows). The SWEET TOOTH
  fixture (34 W Columbia St, South-Tucson area) lands in ZERO divisions
  by design (independent city, not a leaf division) — pinned
  geometrically, inside metro bbox.
- 2026-08-28 — `ArcGISClient._flatten_feature` is an instance method in
  the current tree (not staticmethod as in 2a70e39) — tests instantiate
  the client; no network.

## Gates

- `pytest tests/unit/test_producers_tucson.py` → **41 passed**.
- Leaf naming `-k tucson` → green (parametrized canonical-constants check);
  `test_all_expected_leaf_modules_present` RED: 68 modules ≠ pinned 62 —
  **spine-owned** (tucson + 6 concurrent wave-5 leaves).
- `pytest -m interlock` → **24 passed / 0 failed** (gate grew from 22 via
  in-flight spine edits).
- Full suite → **2021 passed / 3 skipped / 1 failed** — the single failure
  is the spine-owned leaf-naming count pin. Nothing else red.

## Current step

Complete. Changeset uncommitted per leaf contract.

## Next step

Orchestrator applies the spine delta (see agent summary /
`.streams/wave5-tucson.md` spine-delta section): `CityId.TUCSON` enum +
aliases, `CityRegistration` with the SLA `DatasetSpec` (config setting
`arcgis_tucson_sla_endpoint` default = TUCSON_SLA_ENDPOINT), snapshot mode,
`ANSI_DATE_LITERAL_HOSTS` += `gis.tucsonaz.gov`, cities/__init__ export,
dashboard `METRO_META` "Tucson, AZ" + snapshot/res-5 coverage + byte-synced
index.html, leaf-naming count bump.
