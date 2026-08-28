# SE Probe — Gulfport, MS (Harrison County) — 2026-08-28

Leaf probe for Linear US-305. **VERDICT: NOT-VIABLE.** No live, queryable,
municipal row-level feed exists for the four probe families against the City
of Gulfport, MS or Harrison County. Documented negative evidence below. No
registration is fabricated.

## Probe summary

| Door | Platform | Reached | Outcome |
|---|---|---|---|
| City of Gulfport ArcGIS Server (`maps.gulfport-ms.gov`) | ArcGIS REST (v10.51) | yes | Only business-license layer exists; **FROZEN** Dec 2024. No permits, no 311, no deeds/sales. |
| City of Gulfport AGOL org (`gulfport-ms.maps.arcgis.com`, "City of Gulfport, MS", GulfportGIS) | ArcGIS Online | yes | All authored content is under the private GulfportGIS org (GPT_* MapServices mirroring the server). Public content = no qualifying MS Gulfport row feeds. |
| AGOL "Gulfport Permits" Feature Service (`services1.arcgis.com/UCf4GN8d89BVnHt2`) | ArcGIS Online | yes | **WRONG GULFPORT** — rows are Gulfport, FLORIDA (State "Florida ", Zip 33707, `pwgulfportfl.maps.arcgis.com`). No date column either. |
| Harrison County (`harrisoncountyms.gov`) | Web portal + AGOL | yes | No open ArcGIS Server (gis/webgis/arcgis hosts all fail). County data = application/search web forms, no row-level feed. |
| Harrison county AGOL (`harcogis.maps.arcgis.com`) | ArcGIS Online | yes | Org content public surface is the global gallery (unrelated hits). No county-hosted row feed surfaced. |
| Gulfport FL AGOL (`pwgulfportfl.maps.arcgis.com`, "mygulfport") | ArcGIS Online | yes | The FL city's public-works org — same "Gulfport" items above. Wrong state. |
| MS state Socrata (`data.ms.gov`) | Socrata | no | Host unreachable (000). |
| MS Dept of Marine Resources (`dmr.ms.gov`) | Web | yes | Informational permitting/seafood pages only; no open row feed. Seafood-marine licenses are a state-coastal (MDMR) category, not a municipal feed. |
| Gulf Regional Planning Commission (`grpc.com`) | Web | redirect | 301; regional planning, no municipal row feed. |

## Per-family negative evidence

### PERMITS — no feed
City ArcGIS Server enumerated fully (Basemaps / CityServices / PublicServices /
Utilities / Hosted). The only permit-ish service is `GPT_BuildingFootprints`
(geometric footprints, not permits) and `CapitalImprovmentProjects*` (capital
projects). **No building-permit layer exists.** The AGOL "Gulfport Permits"
is Gulfport, FLORIDA (see cross-city note). Harrison County permits are web
application/download forms (`code_administration/permit_application_portal.php`,
`engineering/permits.php`) — interactive portals, no row-level REST feed with a
watermark.

### COMPLAINTS_311 — no feed
No 311 / CRM / citizen-request layer anywhere on the city ArcGIS Server or
either AGOL org. Harrison County publishes no open 311 dataset. Not registered.

### SLA — feed exists but FROZEN
`CityServices/GPT_BusinessLicense/MapServer/0` ("Business License"):
- 510 total rows (a current/active snapshot, not full history).
- **Max `ISSUE_DATE` = 1733961600000 → 2024-12-12** (~8.5 months stale as of
  2026-08-28). Same max on `GPT_SocialDistMainStBusLic/BusinessLicense/0`.
- `ISSUE_DATE` is esriFieldTypeDate (date-typed).
- Geometry is **MS State Plane East, feet** (layer extent wkid 102694 /
  latestWkid 2254 = EPSG:2254; sample pt x=900752.44 y=315315.84) — **not
  WGS84**. Any live use would need `outSR=4326` or state_plane handling.
- PII columns: `OWNER_NAME`, `CONTACT`. Address-only/mixed.
- **Not viable: source is frozen.** Does not clear the freshness gate.

Seafood-marine licenses: issued by MDMR (state agency), coastal-wide, no open
row feed. Not a Gulfport municipal leaf feed.

### DEEDS — no transaction feed
City server has only `GPT_StCadastral` Parcels:
- 108,080 parcels, a **county-wide assessor ownership cadaster** (rows show
  `Perkinston MS`, `Crossett AR`, year `RANGE/TOWNSHIP/SECTION`).
- Fields `NAME`, `ADDRESS_1` (PII). **No sale date, no sale amount, no
  transfer type** — it is an ownership roll, not a sales/transactions feed.
  Not a DEEDS signal. Not cleanly Gulfport-only (county-wide).
- Harrison County land records are web-form systems: `DuProcessWebInquiry`
  (an e-recording portal — the landing page text is a reused Seminole County,
  FL template) and `harrisonms.geopowered.com/propertysearch/` (a GeoPowered
  CAMA web app). Neither exposes a row-level REST feed with a watermark.

## Cross-city collision (critical)
The most promising-looking AGOL hit — `Gulfport_Permits`
(FeatureServer `/0` "Issued Permit", 492 rows) — is the **wrong Gulfport**:
sample rows carry `City="Gulfport"`, `State="Florida "`, `Zip_Code=33707`
(Gulfport / St. Petersburg, Pinellas County, FL), and its web apps live under
`pwgulfportfl.maps.arcgis.com` (the FL city's public-works org). Permit
numbers (`MECR2024-…`, `ELER2024-…`) follow Pinellas County numbering. It
also lacks any date column (fields: Permit_Number, Permit_Type, Address,
Street, Zip_Code, City, State, FID), so even as a snapshot it has no
watermark to track freshness. Rejected as the wrong city.

## Freshness caveat
All "Gulfport Issued Permits" web-map titles are date-range snapshots (e.g.
"9/27/2024 to 2/4/2025"), consistent with a frozen/near-frozen publish. No MS
Gulfport feed shows a fresh watermark.

## What would make this viable (re-probe triggers)
- A City of Gulfport MS permits/311/CRM layer appearing on
  `maps.gulfport-ms.gov` or the `gulfport-ms.maps.arcgis.com` org.
- `GPT_BusinessLicense` gaining 2026 `ISSUE_DATE` rows (register no longer
  frozen).
- A Harrison County open ArcGIS Server surfacing a sales/transfers layer
  (parcel_join-ready `parcel_layer` + a dated DEEDS signal).
- Any Gulfport-MS item on the AGOL org published publicly with a date column.

Until then: do NOT register. NOT-VIABLE.
