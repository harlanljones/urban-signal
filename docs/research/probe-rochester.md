# Wave 3 Phase-0 probe — Rochester, NY

**Date of probe: 2026-08-27.** Ticket US-351. Public ArcGIS Hub at
`data.cityofrochester.gov` (~47 city items, AGOL org
`services2.arcgis.com/yoz1ZtATTCokO9nU` + on-prem
`maps.cityofrochester.gov/server`). Every row below read live that day.

## Headline verdict

**Register partial — DEEDS/sales Tier 1 (monthly cadence); permits / 311 /
SLA Tier 3.** The Hub's hidden gem is **Tax Parcel Records: Open Data**:
64,746 parcels with per-parcel `SALE_DATE`/`SALE_PRICE`/`BOOK`/`PAGE`/
`DEED_TYPE`, newest sale **2026-07-22** and ~350 sales in the last 60 days
— the closest thing to ACRIS-shape this project has seen outside a county
clerk. Meanwhile 311 is a **2022 archive** on both Hub items, and there is
no permits or licenses dataset at all.

| Family | Endpoint | Newest row (watermark) | Geocoding | Recent window | Tier |
|---|---|---|---|---|---|
| **DEEDS/sales** | `maps.cityofrochester.gov/server/rest/services/Open_Data/Tax_Parcels_Open_Data/FeatureServer/0` | `SALE_DATE` = **2026-07-22** (547 Avis St, $110,000, W) | native parcel **polygons** + `SITEADDRESS`/`ZIP5` 485/485 newest sale rows | Jul 2026 **141**; Jun **350**; May **485**; 60d ≈ **350**; 2026 YTD 2,279; 2025: 4,086 | **1** (monthly cadence exception) |
| PERMITS | none (`q=permit/construction/building` → zoning districts, community gardens, footprints) | n/a | n/a | n/a | **3** |
| 311 | `311_Case_Data` FeatureServer/0 + `311_Case_Data_-_2021_DRAFT.csv` | `Request_Date` max **2022-02-07** (51,721 rows; 0 since) | native points on archived rows | 0 since 2022-02-07 | **3** (frozen archive) |
| SLA/licenses | none (`q=license` → community gardens) | n/a | n/a | n/a | **3** |

## Deeds/sales — Tier 1 with cadence caveat (register candidate)

- **Rows:** 64,746 parcels. **Sales by year:** 2023: 3,854 · 2024: 4,041 ·
  2025: 4,086 · 2026: 2,279 (through Jul 22). Monroe County RPS-derived.
- **Watermark:** `SALE_DATE` is **text `MM/DD/YYYY`** (len 50). Text
  `orderByFields=DESC` **lies** (`12/31/2025` > `08/15/2026` string-wise) —
  first pass "max 12/31/2025" was wrong; month-prefix `LIKE` counts found
  July 2026 rows. ADR 0005 text-watermark with `%m/%d/%Y`, or filter by
  month-prefix windows. No nulls in sale-bearing rows observed.
- **Geocoding:** polygon geometry (parcel) + `SITEADDRESS`/`ZIP5` complete
  on sampled sale rows; `PRINTKEY` is the parcel key, `PARCELID` alt.
- **Noise:** `$1` quitclaim transfers (`DEED_TYPE` `Q`) are present; `VALID`
  (deed-validity flag) is empty on 64,632/64,746 rows — the county's
  arm's-length filter did not survive the extract. Filter `DEED_TYPE='W'`
  and/or `SALE_PRICE > threshold` at ingest; do not ingest $1 transfers as
  market sales.
- **Cadence:** monthly roll refresh with lag (Jul rows stop at 07/22; Aug 0
  as of the Aug 27 probe). Same class as the Memphis permits monthly
  exception — document it, and re-probe ≤72 h before build; if September
  still shows 0 after a full month, treat as stalled.
- Client: existing ArcGIS client. `MultiSale` / `PARCEL_SOURCE` columns
  available for dedupe.

## Permits — Tier 3 (absent)

Full catalog keyword sweep (`permit`, `construction`, `building`,
`violation`) surfaces zoning districts, Building Footprints: Live, Code
Enforcement **Inspector Areas** (staffing geography, not cases), community
gardens. No permit-case dataset anywhere on the Hub.

## 311 — Tier 3 (frozen archive)

- FeatureService `311_Case_Data/0`: 51,721 rows, points, fields
  `Subject/Reason/Type/Department/Bureau/Request_Date/Street_Name/ZIP`;
  newest `Request_Date` **2022-02-07**.
- The CSV item is literally `311_Case_Data_-_2021_DRAFT.csv` (7.4 MB,
  created 2022-07-22) ending 2/7/22. Both surfaces are one archive.

## Platform / method / limits

Hub OGC collections search (`data.cityofrochester.gov`), AGOL item→URL
resolution, layer metadata, `outStatistics` max/count, `returnCountOnly`
window counts via text-`LIKE` (necessary because `SALE_DATE` is a string),
newest-row reads, 500-row completeness. Socrata discovery: `Domain not
found` for `data.cityofrochester.gov`. Not CKAN. Limits: the Hub OGC
unscoped query returns global (non-Rochester) results; city items were
isolated via `source`/`q=Rochester` + keyword passes, so an item with
neither the word "Rochester" nor a family keyword could in principle hide —
all 47 `q=Rochester` titles were read; none is a permit/311/license feed.

## Decision

**Register Rochester partial on DEEDS/sales** (Tax Parcel Records: Open
Data) with the text-watermark + quitclaim-noise handling above. Re-probe
311 only if the city resumes the extract. Stamp: 2026-08-27.
