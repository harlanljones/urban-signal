# wave5-rochester — US-351 (Rochester, NY)

- Ticket: US-351, claimed (leaf-implementation)
- Scope: `apps/api/src/spatial/cities/rochester.py`, `apps/api/src/producers/field_maps_rochester.py`, `apps/api/tests/unit/test_producers_rochester.py` (new), this file, one dispatch-log outcome row.
- Spine (NOT touched here): CityId enum + aliases, CityRegistration (+ config settings), cities/__init__.py, dashboard METRO_META + index.html, leaf-naming count pin.
- Feed: DEEDS T1 via Monroe County tax-parcel parcels (per docs/research/probe-rochester.md), deeds-led metro.
- Status: **COMPLETED 2026-08-28.**

## Live re-probe (2026-08-28, implementation re-stamp)

Endpoint `https://maps.cityofrochester.gov/server/rest/services/Open_Data/Tax_Parcels_Open_Data/FeatureServer/0`
(polygon layer, maxRecordCount 100,000, capabilities Query; native SR 102100,
queries at outSR=4326). All counts probe-exact:

- Total parcels 64,746 · 2026 YTD 2,279 (through Jul 22) · 2025 4,086
- Monthly windows: Jul 141 · Jun 350 · May 485 · **Aug 0** (monthly-roll lag holds)
- `CITY <> 'ROCHESTER'` count = 0 (city parcels only → Pittsford NOT evidenced, excluded)
- Watermark `SALE_DATE` TEXT MM/DD/YYYY (len 50) — lexical DESC lies; typed
  `%m/%d/%Y` (ADR 0005) mandatory. Newest sale **07/22/2026**.

## Byte-verbatim fixtures (≥2)

1. **OBJECTID 5294 — 547 Avis St** (probe headline row): `SALE_DATE`
   07/22/2026, `SALE_PRICE` 110000, `DEED_TYPE` W, `BOOK` 13214, `PAGE`
   320, `PRINTKEY` 090.40-2-19, `PARCELID` 09040000020190000000,
   `SITEADDRESS` "547 Avis St", `ZIP5` 14615, `VALID` "" — full 5-pt ring
   captured at outSR=4326; shapely centroid (-77.6480553, 43.19530791).
2. **OBJECTID 61058 — 396 Brooks Ave** ($1 quitclaim noise fixture):
   `SALE_DATE` 07/21/2026, `SALE_PRICE` 1, `DEED_TYPE` Q, `PRINTKEY`
   135.33-1-69, `PARCELID` 13533000010690000000, `ZIP5` 14619 — full 8-pt
   ring; centroid (-77.64601343, 43.13126719).

Plus a third priced-row capture (64616, 145 Cimarron Dr, Q, $1, 07/21/2026)
confirming the quitclaim prevalence. Submarket anchors were point-in-parcel
verified live (Charlotte 43.2270/-77.5630, Corn Hill 43.1430/-77.6240,
Center City 43.1510/-77.6180, Park Avenue 43.1500/-77.5960, NOTA
43.1530/-77.5880, Maplewood 43.1720/-77.6250, 19th Ward 43.1200/-77.6430,
Upper Falls 43.1770/-77.5960; Pittsford 43.0906/-77.5164 = 0 hits).

## Gates

- `pytest tests/unit/test_producers_rochester.py` → 36/36 green
- `pytest -k rochester` (incl. test_city_leaf_naming canonical constants) → 37 passed
- `pytest -m interlock` → 24/24 green
- Full suite (excluding sibling `test_producers_tucson.py` — collection
  TypeError in their fixture, their stream owns it): **1984 tests / 1 failed
  / 0 errors / 3 skipped** — the single failure is the spine-owned
  leaf-naming count pin (`test_all_expected_leaf_modules_present`).
- Ruff: net-new 0 beyond the leaf-convention `typing.Dict` style shared with
  every existing leaf (VB reference has the same 20 UP0xx hits); I001/RUF022
  fixed on my files.

## THE SPINE DELTA (for the orchestrator's serial hold)

- **CityId enum**: `ROCHESTER = "rochester"` + alias entries in
  `_HANDWRITTEN_ALIASES` ("rochester", "rochester ny", "rku"? keep to repo
  convention — at minimum the slug itself).
- **CityRegistration**: name "Rochester", state "NY", center
  `{"lat": 43.1560, "lng": -77.6120}`, metro bbox
  `{"min_lat": 43.10, "max_lat": 43.27, "min_lng": -77.71, "max_lng": -77.53}`
  (live layer extent in WGS84), division bboxes `ROCHESTER_DIVISION_BBOXES`
  (6), submarkets `ROCHESTER_SUBMARKETS` (8), divisions `ROCHESTER_DIVISIONS`
  (6) — all copyable from `cities/rochester.py` verbatim.
- **DEEDS DatasetSpec** (single feed; partial metro — apply the wave-4/5
  zero-SLA-less invariant if the orchestrator's snap_sla_spec helper applies):
  - endpoint: `https://maps.cityofrochester.gov/server/rest/services/Open_Data/Tax_Parcels_Open_Data/FeatureServer/0`
  - config settings name (repo convention): `arcgis_rochester_deeds_url`,
    default = the URL above
  - platform "arcgis"; watermark_col `SALE_DATE`; watermark_type "text";
    watermark_format "%m/%d/%Y" (ADR 0005); id_keys
    `["PRINTKEY", "PARCELID", "SALE_DATE"]`; oid_field `OBJECTID`;
    max_record_count 100000 (live service maxRecordCount); topic
    `settings.topic_deeds`; interval_seconds 600.0; producer_key "deeds";
    field_map `DEEDS_FIELD_MAP`; needs_geocode **False**; geocode_context
    **None**; non_spatial **False**; **no** parcel_join (native parcel
    polygons are the geometry primary — the only parcel_join-capable layer
    IS the registered layer); **no** rollover / endpoint_by_year (static
    layer, no annual rotation); **no** where clause (see noise note).
  - expected_cadence_days: **30** (honest: monthly RPS roll with lag — Jul
    rows stop 07/22, Aug=0 at re-probe; alarm at 60d; treat as stalled if
    September still shows 0 new rows).
- **Noise policy**: $1 `DEED_TYPE='Q'` quitclaims are KEPT at ingest (no
  per-city `where`; VB zero-price precedent). `VALID` arm's-length flag is
  empty on 64,632/64,746 rows — market-sale filtering is analysis-side.
- **cities/__init__.py**: export the canonical ROCHESTER_* constants.
- **serving/dashboard.py METRO_META**: add `"Rochester, NY"` (metro chip +
  `?city=rochester` deep link), then regenerate
  `apps/dashboard/public/index.html` byte-sync + snapshot manifest (res-5
  grid tiles) per the city registration rule — in the SAME spine hold.
- **test_city_leaf_naming.py**: count pin 62 → 63+ (up to orchestrator
  depending on how many wave-5 leaves land in the hold).
- Post-spine reconciliation notes: `resolve_field_map("rochester", DEEDS)`
  will start returning `DEEDS_FIELD_MAP` from the registered spec (leaf
  tests already patch it, so they are stable); `get_division_for_coordinate`
  will start resolving fixture coords to divisions (tests deliberately do
  not assert borough); the geocode hook stays silent (needs_geocode=False).
