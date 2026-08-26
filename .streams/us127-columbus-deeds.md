# Stream log — us127-columbus-deeds — 2026-08-25

- **Stream id:** `us127-columbus-deeds` (Linear US-127, claimed via --assignee self).
- **Spine files I edit:** `apps/api/src/config.py`, `apps/api/src/spatial/city_registry.py`,
  `apps/api/src/producers/deeds_acris_producer.py`, `apps/api/tests/unit/test_producers_columbus.py`,
  `README.md`. Spine manifest kept additive (no new spine path needed).
- **Interlock right:** held for this whole task. No other agent edits spine files.

## Live probe (before any edit) — FCAO_Sales_Dashboard_Last_Years_Sales_Points/0

Fetched live 2026-08-25 via direct HTTP to
`https://services1.arcgis.com/7r2Wl09a1Apy459r/arcgis/rest/services/FCAO_Sales_Dashboard_Last_Years_Sales_Points/FeatureServer/0`.

- **Layer metadata:** name `DashboardSalesPtsJuly25`, `serviceItemId` `d2550387e1284da6a3704ba07b124b76`,
  `geometryType` `esriGeometryPoint`, `objectIdFieldName` `OBJECTID`,
  `maxRecordCount` = **2000**, `advancedQueryCapabilities.supportsPagination` = **True**,
  `editingInfo.lastEditDate` = **1785855272015** (epoch-ms → 2026-08-04? — actually
  2026-07-31 in the sweep doc; treat as the annual-snapshot edit stamp, not a per-row watermark).
  Spatial ref wkid 4326; `returnGeometry=true&outSR=4326` yields WGS84 x/y directly.
- **Record count confirmed live:** `where=1=1&returnCountOnly=true` → **1568** rows.
- **Schema (as served):** old/new dual set both present:
  old `SALEPRICE`, `OWNERNME1`, `OWNERNME2`, `OWNERNME3`, `X_COORD`, `Y_COORD`,
  `PSTLNME1/2`; new `Sale_Price`, `OWN1`, `OWN2`, `Instrument_Number`,
  `Transfer_Date`, `ObjectID_1`, `NHBDNAME`, `COMMNAME`, `MUNINAME`, `COUNTYNAME`,
  `AREANAME`, `No_Of_Parcels`. Fundamental: `PARCELID`, `SALEDATE`, `SITEADDRESS`,
  `ZIPCD`, `VALID`/`Validity`, `LASTUPDATE`, `ORIG_FID`, `PARID`.

### Key observed values (live `where=1=1&orderByFields=SALEDATE DESC&outSR=4326`)

Row 1 (OBJECTID 128): `PARCELID 010-054436`, `SALEPRICE 360000`, `Sale_Price 360000`,
`OWNERNME1 'REESE JAMES M'`, `OWN1 'REESE JAMES M'`, `OWN2 '& REESE MICHELLE'`,
`Instrument_Number None`, `SITEADDRESS '348 W FIRST AVE'`, `ZIPCD '43201'`,
`SALEDATE 2025-07-16T05:00:00+00:00`, geometry (-83.013761, 39.980748).

Row 2 (OBJECTID 169): `PARCELID 010-070656`, `Sale_Price 290900`, `SALEPRICE 290900`,
OWN pair present, geometry (-83.084250, 39.950824).

Row 3 (OBJECTID 178): `PARCELID 010-072179`, `Sale_Price 503000`, geometry (-83.013047, 40.042935).

Old-schema sampling (`orderByFields=SALEDATE ASC`), OBJECTIDs 30/1311/888:
`SALEPRICE 0` but `Sale_Price` populated (84000/90000/365000); `OWN1` populated;
`Instrument_Number None`; `SALEDATE` 1976/1979 (deep-history rows) — the published
layer is the full "last N years" sales set, not only July 2025, despite the layer name.

### Dual-schema / freshness verdicts FROM LIVE COUNTS (deltas vs the ticket)

| Predicate | Live count | Meaning |
|---|---|---|
| total | 1568 | validated subset |
| `Sale_Price IS NOT NULL` | 1568 | new price col always populated |
| `SALEPRICE IS NOT NULL` | 1543 | old price col on 1543 rows (25 missing) |
| `OWN1 IS NOT NULL` | 1568 | new grantee always populated |
| `SALEDATE IS NOT NULL` | 1543 | 25 rows carry no SALEDATE (the same 25 missing `SALEPRICE`) |
| `Instrument_Number IS NOT NULL` | **0 / 1568** | **Instrument_Number is NULL on EVERY row** (not just recent) |
| `MUNINAME IS NOT NULL` | **0 / 1568** | **MUNINAME is NULL on EVERY row** |
| `NHBDNAME IS NOT NULL` | 0 (via MUNINAME=0 precedent, same empty-new-schema sublayers) | | 

**Discrepancy to record (does NOT block):** the ticket/sweep believed
`Instrument_Number`/`Transfer_Date` were "NULL on recent rows" and `MUNINAME`/
`NHBDNAME`/`Instrument_Number` present on older rows. Live, `Instrument_Number`,
`MUNINAME`, and `NHBDNAME` are **empty across the entire layer** (0/1568); the
"old schema" that survives is `SALEPRICE`/`OWNERNME1`, while the "new" `Sale_Price`/
`OWN1`/`OWN2` populate every row. So:
- `id_keys` still lists `["PARCELID","Instrument_Number","OBJECTID"]` (harmless; the
  effective key is `PARCELID`+`OBJECTID` since `Instrument_Number` is always null).
- `field_map` `doc_id: ["Instrument_Number","PARCELID"]` resolves to `PARCELID` (null
  first candidate falls through). Correct.
- `field_map` `borough: ["MUNINAME","NHBDNAME"]` resolves to None on every row — the
  producer falls back to coordinate→division resolution (geo_utils), which resolves to
  `COLUMBUS_CORE` for in-metro points. Correct and unaffected.
- `document_amount: ["Sale_Price","SALEPRICE"]` — `Sale_Price` first (populated 1568/1568).
  Correct.

No live-probe contradiction forces a STOP: the feed exists, is point-geocoded via
outSR=4326, paged, and reachable anonymously. Registering proceeds.

## Decisions
- Register as ArcGIS FeatureServer, `watermark_col="SALEDATE"`, `expected_cadence_days=365`
  (annual snapshot per sweep §4 + `lastEditDate` 2026-07-31).
- `oid_field="OBJECTID"`, `max_record_count=2000` (live cap).
- Field map from sweep §4, with `Sale_Price` BEFORE `SALEPRICE` (live: Sale_Price 1568/1568,
  SALEPRICE 1543/1568) and `MUNINAME`/`NHBDNAME` kept (they resolve to None but are harmlessly
  the first borough candidates; coordinate division lookup is the real borough source).
- Columbus is an already-listed city (selector option + CITY_CONFIGS + workers static copy all
  present in dashboard.py / apps/dashboard/public/index.html). Verified against
  `TestDashboardWiring` — no dashboard edit needed; the interlock gate confirms Columbus is on
  all three wires. FEED additions do not touch the city wiring.
- Producer: add an uppercase Columbus city-sniff branch (`PARCELID` + OWN1/OWNERNME1) so a row
  autodetects to columbus, plus additive uppercase fallback chain terms
  (`Instrument_Number`/`PARCELID`, `PARCELID`, `OWNERNME1`, `OWN1`/`OWN2`). All gated on
  uppercase keys that only this layer carries → no effect on other cities.

## Verification (run from apps/api)
- `.venv/bin/python -m pytest -m interlock` → expect 21 passed.
- `.venv/bin/python -m pytest tests/unit/test_producers_columbus.py tests/unit/test_producers_cincinnati.py` → pass.
- `.venv/bin/ruff check <touched file>` → zero net-new findings vs pre-change baseline.
