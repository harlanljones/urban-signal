# SE probe — Tallahassee, FL / Leon County (US-303 leaf) — 2026-08-28

**Stream:** `city-tallahassee` (rebuild of a lost prior run) · **Linear:** US-303
· **Region:** Southeast · **Brief:** joint City/County ArcGIS Server 10.81 at
`intervector.leoncountyfl.gov`, candidate doors = ArcGIS Hub / REST.

**VERDICT: REGISTER 3 feeds.** Live, fresh, watermark-bearing, row-queryable
native-point layers exist for PERMITS, COMPLAINTS_311, and DEEDS on the
joint Leon County / City of Tallahassee ArcGIS Server. No SLA (absent — no
Local Business Tax Receipt dataset in the org). The Hub front-ends 404 on
DCAT; there is no Socrata/CKAN; `tlcpermits.org`/Accela are not needed.

## Web-adaptor correction (critical)

The ArcGIS Server is fronted (IIS + Akamai, IPv4 `23.212.62.203`) with the
REST API mounted under the **`/intervector`** web-adaptor alias, i.e. the
canonical layer base is:

```
https://intervector.leoncountyfl.gov/intervector/rest/services/MapServices/<Service>/MapServer/<LayerId>
```

The shorthand `https://intervector.leoncountyfl.gov/arcgis/rest/services/<Service>/MapServer/<LayerId>`
did NOT exist at any path I enumerated and returns the IIS 404 page; only the
`/intervector/...` form returns ArcGIS JSON. All endpoints below use the
`/intervector/rest/services/MapServices/` base.

## Probe table

| Feed | Layer | Watermark col + newest (live) | Rows | Geo | Cadence | Verdict |
|---|---|---|---|---|---|---|
| PERMITS | `MapServices/TLC_OverlayPermitsActive_D_WM/MapServer/0` ("Active Building Permits by Type") | `AppliedDate` 2026-08-18 (row OBJ 1425 `LB2601183` also carries `PubDte` 2026-08-19T18:00Z) | 1426; 60d 137, 7d 0 | native point, outSR 4326 | 7 | register, `needs_geocode=False` |
| COMPLAINTS_311 | `MapServices/LCPW_InforServiceRequest_D_WM/MapServer/1` ("All Service Requests", Infor/PublicWorks CRM) | `CALLDTTM` 2026-08-28T11:03:00Z (same-day; SERVNO 483094) | 171,552; `<= CURRENT_TIMESTAMP` = 171,546 | native point, `GPSX`/`GPSY` = FL State Plane North feet | 1 | register, `needs_geocode=False`, `where="CALLDTTM <= CURRENT_TIMESTAMP"` |
| DEEDS | `MapServices/LCPA_Last3YearsSales_D_WM/MapServer/0` ("Sales 2026", rolling 3-yr set) | `SALES_SALEDT` 2026-08-24 (extract touched 2026-08-27) | 3804; 60d 912, 7d 11 | native parcel-centroid point | 1 | register, `needs_geocode=False`, no `parcel_join` |
| SLA | — | — | — | — | — | **absent** — no Local Business Tax Receipt dataset anywhere in the org; do not register |

## Feed schemas (live, byte-verbatim highlights)

### PERMITS — `TLC_OverlayPermitsActive_D_WM/MapServer/0`
`esriGeometryPoint`, `objectIdField` **None**, `maxRecordCount` 8000. OID
field is `OBJECTID`. Date-typed: `AppliedDate`, `IssuedDate`, `CompletedDate`,
`StatusDate`, `PubDte`. Key columns: `PermitNum`, `Description`,
`OriginalAddress1/2`, `OriginalCity`, `OriginalState`, `OriginalZip`,
`Jurisdiction` ("City of Tallahassee"/"Leon County"), `PermitClass`,
`PermitClassMapped`, `WorkClassMapped`, `PermitTypeMapped`, `PermitTypeDesc`,
`StatusCurrent`, `StatusCurrentMapped`, `StatusDate`, `TotalSqFt`,
`EstProjectCost`, `PIN`, `ContractorCompanyName`, `ContractorTrade`, `ProcUse`,
`ProjectID`, `ProjectName`, `MasterPermitNum`, `PubDte`, `ExpiresDate`.
**`Latitude`/`Longitude` attributes are Web Mercator meters — never map.**

### COMPLAINTS_311 — `LCPW_InforServiceRequest_D_WM/MapServer/1`
`esriGeometryPoint`, `objectIdField` **None**, `maxRecordCount` 1000. Its OID
column is **`ESRI_OID`** — `orderByFields=OBJECTID` returns error 400 (verified
live), `orderByFields=ESRI_OID` works. Date-typed: `CALLDTTM`, `RESDTTM`. Key
columns: `SERVNO`, `COUNTY` (COT/LEON/…), `DISTRICT`, `CALL_SOURCE`,
`RESCODE`, `DESCRIPT`, `RESP` (OPS), `CATEGORY`, `CATNAME`, `PROBCODE`,
`PROBDESC`, `ADDRESS`, `LOC`, `INSPECTR`, `PRIMCALL`, `INITCALL`,
`GPSX`/`GPSY` (FL State Plane North feet), `ESRI_OID`. The geometry is
WGS84 (requested `outSR=4326`).

### DEEDS — `LCPA_Last3YearsSales_D_WM/MapServer/0`
`esriGeometryPoint`, `objectIdField` **None**, `maxRecordCount` 1000. OID
field `OBJECTID`. Date-typed: `SALES_SALEDT`, `SALES_RECORDDT`,
`SALES_TRANSDT`, etc. Key columns: `SALES_JUR`, `SALES_PARID` (space-padded
fixed-width parcel id, e.g. `110480  C0050`), `SALES_PRICE`,
`SALES_STAMPVAL`, `SALES_SEQ`, `SALES_SALEKEY` (per-sale int), `SALES_OWN1`
(grantee), `SALES_OLDOWN` (grantor), `SALES_INSTRTYP` (CT/WD), `SALES_BOOK`,
`SALES_PAGE`, `SALES_ADJPRICE`, `SALES_ASMT`, `OBJECTID`. No address column;
the layer already serves parcel-centroid points, so **no `parcel_join`** and
`needs_geocode=False`.

## Host quirks (verified live)

1. **ANSI-date-literal.** `AppliedDate >= '2026-08-21T00:00:00'` →
   `{"error":{"code":400,"message":"Failed to execute query."}}`; the ANSI
   form `AppliedDate >= date '2026-08-21'` returns a count. The scheduler's
   incremental comparison must route through `watermark_comparison` with
   `intervector.leoncountyfl.gov` added to `ANSI_DATE_LITERAL_HOSTS`.
2. **No layer publishes `objectIdField`.** Every feed requires an explicit
   `oid_field`. Permits/Deeds → `OBJECTID`; 311 → `ESRI_OID` (OBJECTID
   ordering on that layer errors).
3. **Projected coordinate columns must not be mapped.** `Latitude`/
   `Longitude` (permits) are Web Mercator meters; `GPSX`/`GPSY` (311) are FL
   State Plane North feet. Geometry (`outSR=4326`) is the only correct WGS84
   source; the ArcGIS client lifts it to `latitude`/`longitude`.
4. **`where` on 311 uses `CURRENT_TIMESTAMP`.** `CALLDTTM <= CURRENT_TIMESTAMP`
   excludes the future-dated rows (a 2029-12-11 "Pauper Burial" sentinel and
   scheduled mosquito-fogging rows, e.g. `CALLDTTM` 2026-09-18) and any
   null-dated rows: 171,552 total → 171,546 under the clause. Verified it
   works on-host.

## Spatial grounding

Metro bbox grounded in the live deeds extent (sampled sales since 2026-07-01:
lat 30.2997..30.6218, lng -84.6948..-84.0605). Registration center
{30.4383, -84.2807} (downtown/capitol). 6 divisions and 10 submarkets, each
submarket pinned to a real Sales-2026 row's geometry + `SALES_PARID`:

| Division | Submarket | Sales-2026 PARID | lat | lng |
|---|---|---|---|---|
| DOWNTOWN_CAPITAL | Downtown / Capitol | 2136340006080 | 30.43916 | -84.28413 |
| DOWNTOWN_CAPITAL | Myers Park / South Monroe | 310775  E0130 | 30.41057 | -84.27399 |
| MIDTOWN_NORTH | Midtown | 212360  E0040 | 30.46439 | -84.29130 |
| MIDTOWN_NORTH | Lafayette / North Monroe | 212423  10060 | 30.47220 | -84.27865 |
| NORTHEAST_KILLEARN | Killearn Lakes | 142560 AS0050 | 30.53835 | -84.21013 |
| NORTHEAST_KILLEARN | Betton Hills / Buckhead | 111790  A0180 | 30.48527 | -84.25132 |
| NORTHWEST_LAKE_JACKSON | Lake Jackson | 253622  B0040 | 30.52554 | -84.38255 |
| NORTHWEST_LAKE_JACKSON | West Tallahassee / Jackson Bluff | 211941  B0070 | 30.46353 | -84.36692 |
| SOUTHSIDE_BOND | Southside / Bond | 311930  C0010 | 30.38206 | -84.27208 |
| SOUTHEAST_SOUTHWOOD | Southwood | 310270  A0270 | 30.42630 | -84.19719 |

## Files

- `.streams/city-tallahassee.md` (stream log + spine delta)
- `docs/research/se-probe-tallahassee.md` (this file)
- `apps/api/src/spatial/cities/tallahassee.py`
- `apps/api/src/producers/field_maps_tallahassee.py`
- `apps/api/tests/unit/test_producers_tallahassee.py`
