# Stream log — city-tallahassee — 2026-08-28

Phase-2 leaf stream (REBUILD) for Linear US-303: Tallahassee, FL / Leon County
registration (PERMITS + 311 + DEEDS). A PRIOR run of this stream completed
successfully (53 tests) but its leaf files were LOST to a branch switch
(main -> `chore/restore-metros-and-columbus`). Spine is serial after this
stream; do NOT edit spine files here. Do NOT touch Linear, git commit/push, or
PRs (permission-denied). Do NOT touch the sibling streams (west-coast wave +
other southeast rebuilds) editing this same tree.

## Claim

- **Stream id:** `city-tallahassee`
- **Leaf files I will create/edit:**
  - `.streams/city-tallahassee.md` (this file)
  - `docs/research/se-probe-tallahassee.md` (NEW — probe findings)
  - `apps/api/src/spatial/cities/tallahassee.py` (NEW)
  - `apps/api/src/producers/field_maps_tallahassee.py` (NEW)
  - `apps/api/tests/unit/test_producers_tallahassee.py` (NEW)
- **Spine files I expect to need (do NOT edit in this stream):**
  - `apps/api/src/spatial/city_registry.py` (CityId.TALLAHASSEE, ALIASES, REGISTRY)
  - `apps/api/src/spatial/cities/__init__.py`
  - `apps/api/src/config.py` (arcgis_tallahassee_*_endpoint)
  - `apps/api/src/serving/dashboard.py` METRO_META
  - `apps/api/src/producers/watermarks.py` (ANSI_DATE_LITERAL_HOSTS)
  - `apps/dashboard/public/index.html` (city registration rule)

## Intent

Leaf-complete the Tallahassee metro (CityId value `tallahassee`, aliases
tallahassee/tallahassee_fl/tallahassee fl/leon_county_fl/leon county fl/tlh) on
the joint City/County ArcGIS Server 10.81 at `intervector.leoncountyfl.gov`
(web-adaptor path `/intervector/rest/services/MapServices/...`). Three feeds:
PERMITS (active-building-permits overlay, watermark `AppliedDate`, cadence 7),
COMPLAINTS_311 (Infor/PublicWorks CRM, watermark `CALLDTTM`,
`where="CALLDTTM <= CURRENT_TIMESTAMP"`, producer_key "311", esri OID),
DEEDS (rolling 3-yr sales, watermark `SALES_SALEDT`, cadence ~1, native
parcel-centroid point, no parcel_join). No SLA (absent). All three native
points, `needs_geocode=False`; geometry supplies WGS84 lat/lng. Tests pass
WITHOUT a registry entry (patch resolve_field_map + mock geocoder).

## Decisions

- 2026-08-28 — Orchestrator (southeast-wave) claimed US-303 and dispatched this
  leaf stream. Re-probe LIVE FIRST (trust live rows over the sweep).
- 2026-08-28 (probe, live) — **web-adaptor correction:** the confirmed URLs
  land under `/intervector/rest/services/MapServices/`, **not**
  `/arcgis/rest/services/` (the latter 404s at the IIS/Akamai edge).
  `/intervector` is the ArcGIS Server web-adaptor alias. Corrected endpoint
  paths captured below.
- 2026-08-28 — All three layers are native `esriGeometryPoint`, publish
  **no** `objectIdField`, and `needs_geocode=False`: geometry (requested
  `outSR=4326`) flattens to WGS84 `latitude`/`longitude`; the attribute
  columns `Latitude`/`Longitude` (permits, Web Mercer meters) and
  `GPSX`/`GPSY` (311, FL State Plane North feet) must NEVER be mapped. No
  parcel_join — the deeds layer already serves parcel-centroid points.
- 2026-08-28 — Host is **ANSI-date-literal**: `AppliedDate >= '2026-08-21T...'`
  400s returnCountOnly with `{"error":{"code":400,...}}` while
  `AppliedDate >= date '2026-08-21'` returns a count. Note for the spine hold:
  add **intervector.leoncountyfl.gov** to `ANSI_DATE_LITERAL_HOSTS` (do NOT
  edit watermarks.py in this leaf stream).
- 2026-08-28 — 311 ordering: `orderByFields=OBJECTID` returns error 400 (the
  311 layer has no OBJECTID field; its OID column is `ESRI_OID`), while
  `orderByFields=ESRI_OID` works. 311 spec must declare `order_by="ESRI_OID"`
  and `oid_field="ESRI_OID"`. Permits/Deeds order by `OBJECTID` (both OK
  live).
- 2026-08-28 — Permits `max_record_count` set to the layer's reported
  `maxRecordCount` (8000). Layer supports up to 8000 rows/page.
- 2026-08-28 — Deeds id key is `SALES_SALEKEY` (per-sale integer; unique per
  transfer). `SALES_INSTRUNO`/`SALES_TRANSNO` are NULL across the newest
  batch. `doc_type` left unmapped => producer defaults to "DEED" (no padded /
  shorthand literal). `SALES_PARID` (space-padded fixed-width) is the bbl,
  kept verbatim.

## Live probe (2026-08-28, all positive; re-probed live before capturing)

Trust live rows, not the sweep. All watermarks re-verified against live
queries (returnCountOnly + newest-by-watermark) at build time.

| Feed | Endpoint (web-adaptor path) | Watermark col + newest | Rows | Geo | Cadence | Verdict |
|---|---|---|---|---|---|---|
| PERMITS | `.../TLC_OverlayPermitsActive_D_WM/MapServer/0` | `AppliedDate` 2026-08-18 (PubDte 2026-08-19T18:00Z) | 1426 total (60d 137, 7d 0) | native point, outSR 4326 | 7 | register, needs_geocode False |
| COMPLAINTS_311 | `.../LCPW_InforServiceRequest_D_WM/MapServer/1` | `CALLDTTM` 2026-08-28T11:03:00Z (same-day) | 171,552 total; `<= CURRENT_TIMESTAMP` = 171,546 (excludes future/null) | native point, GPSX/GPSY state-plane | 1 | register, needs_geocode False, `where` clause |
| DEEDS | `.../LCPA_Last3YearsSales_D_WM/MapServer/0` | `SALES_SALEDT` 2026-08-24 | 3804 total (60d 912, 7d 11) | native parcel-centroid point | 1 | register, needs_geocode False, no parcel_join |

Full probe write-up in `docs/research/se-probe-tallahassee.md`.

## Spatial

- Metro bbox grounded in live deeds extent (sampled sales since 2026-07-01:
  lat 30.2997..30.6218, lng -84.6948..-84.0605): {min_lat 30.29, max_lat
  30.63, min_lng -84.70, max_lng -84.05}.
- Registration center {30.4383, -84.2807} (downtown/capitol; verified inside
  the metro bbox).
- 6 divisions, 10 submarkets, each submarket pinned to a **real Sales-2026
  row** (geometry + `SALES_PARID`), all coordinates inside their division
  bbox and every division bbox inside the metro bbox. Full PARID ledger in
  the module docstring + research doc.
- Self-verified containment (division-in-metro, submarket-in-division).
  Resolves at the leaf via `REGISTRATION` (spatial/registration.py).

## Files written

- `docs/research/se-probe-tallahassee.md`
- `apps/api/src/spatial/cities/tallahassee.py`
- `apps/api/src/producers/field_maps_tallahassee.py`
- `apps/api/tests/unit/test_producers_tallahassee.py`

## Tests

```
cd apps/api && .venv/bin/python -m pytest tests/unit/test_producers_tallahassee.py -q
51 passed in 2.06s
```

No `CityId.TALLAHASSEE`. No spine edits.

## Spine delta (do NOT apply in this stream)

Copy-paste for the serial interlock hold:

1. `CityId.TALLAHASSEE = "tallahassee"` (after `TUCSON`).
2. Aliases in `_HANDWRITTEN_ALIASES`:
   - `tallahassee`, `tallahassee_fl`, `tallahassee fl`, `leon_county_fl`,
     `leon county fl`, `tlh`
3. `city_registry.py` imports:
   - `from src.spatial.cities.tallahassee import TALLAHASSEE_CENTER,
     TALLAHASSEE_DIVISION_BBOXES, TALLAHASSEE_DIVISIONS,
     TALLAHASSEE_METRO_BBOX, TALLAHASSEE_SUBMARKETS`
   - `from src.producers.field_maps_tallahassee import FIELD_MAP as
     TALLAHASSEE_FIELD_MAP`
4. `cities/__init__.py` export block.
5. `config.py`:
   - `arcgis_tallahassee_permits_endpoint =
     "https://intervector.leoncountyfl.gov/intervector/rest/services/MapServices/TLC_OverlayPermitsActive_D_WM/MapServer/0"`
   - `arcgis_tallahassee_311_endpoint =
     "https://intervector.leoncountyfl.gov/intervector/rest/services/MapServices/LCPW_InforServiceRequest_D_WM/MapServer/1"`
   - `arcgis_tallahassee_deeds_endpoint =
     "https://intervector.leoncountyfl.gov/intervector/rest/services/MapServices/LCPA_Last3YearsSales_D_WM/MapServer/0"`
   - **NOTE the `/intervector/rest/services/MapServices/` web-adaptor path**
     (corrects the earlier `…/TLC_OverlayPermitsActive_D_WM/MapServer/0`
     shorthand in the wave payload).
6. `watermarks.py` `ANSI_DATE_LITERAL_HOSTS` +=
   `"intervector.leoncountyfl.gov"` (400 on bare ISO date literals; ANSI
   `date 'YYYY-MM-DD'` verified on-host).
7. `REGISTRY[CityId.TALLAHASSEE]`:
   - name `"Tallahassee / Leon County"`, state `"FL"`
   - center `{"lat": 30.4383, "lng": -84.2807}`
   - job_suffix `"tallahassee"`
   - datasets (3; needs_geocode False all three; every feed declares explicit
     `oid_field`):
     - PERMITS: endpoint, arcgis, watermark `AppliedDate`, id_keys
       `["PermitNum","OBJECTID"]`, producer_key "permits",
       expected_cadence_days 7, order_by `OBJECTID`, oid_field `OBJECTID`,
       max_record_count 8000, field_map `TALLAHASSEE_FIELD_MAP["permits"]`
     - COMPLAINTS_311: endpoint, arcgis, watermark `CALLDTTM`, id_keys
       `["SERVNO","ESRI_OID"]`, producer_key "311",
       expected_cadence_days 1, `where="CALLDTTM <= CURRENT_TIMESTAMP"`,
       order_by `ESRI_OID`, oid_field `ESRI_OID`, max_record_count 1000,
       field_map `TALLAHASSEE_FIELD_MAP["311"]`
     - DEEDS: endpoint, arcgis, watermark `SALES_SALEDT`, id_keys
       `["SALES_SALEKEY","OBJECTID"]`, producer_key "deeds",
       expected_cadence_days 1, order_by `OBJECTID`, oid_field `OBJECTID`,
       max_record_count 1000, field_map `TALLAHASSEE_FIELD_MAP["deeds"]`
8. `METRO_META` in `apps/api/src/serving/dashboard.py` **and** byte-synced
   `apps/dashboard/public/index.html`:
   - `tallahassee: { name: 'Tallahassee / Leon County' }`

## New quirks / corrections vs the wave payload

- Web-adaptor base is `/intervector/rest/services/MapServices/` — the earlier
  wave payload and dispatch-log wrote the shorthand
  `…/TLC_OverlayPermitsActive_D_WM/MapServer/0` which 404s unless prefixed.
  Confirm the spine config keys carry the full `/intervector/...` path above.
- `LCPW_InforServiceRequest_D_WM/MapServer/1` (not 0) is the "All Service
  Requests" layer; `objectIdField` is None, its OID field is `ESRI_OID`
  (OBJECTID ordering 400s).
- The 311 dataset's `where` uses the SQL-standard `CURRENT_TIMESTAMP`; the
  host is ANSI-date-literal so the scheduler's incremental comparison must
  route through `watermark_comparison` with `intervector.leoncountyfl.gov` in
  `ANSI_DATE_LITERAL_HOSTS`. Total 171,552; `<= CURRENT_TIMESTAMP` = 171,546
  (the future-dated 2029 sentinel + scheduled fogging rows excluded).

## Current step

Leaf complete. Tests green. No spine edits. Report back to orchestrator.

## Next step

Orchestrator applies the spine delta serially (after the west-coast hold
lands), then `pytest -m interlock` + full suite + `export_dashboard`
byte-sync.
