# Wave 3 Phase-0 probe — Toledo, OH

**Date of probe: 2026-08-28 (UTC).** Row-level ArcGIS reads (newest-row
watermark, window counts, `outSR=4326` geometry) on the city ArcGIS
Server and Hub catalog enumeration.

Linear: **US-359**. Ticket hint: ArcGIS Hub (municipal GIS).

**Verdict: REGISTER (partial).** One Tier-1 family hiding behind a
misleading name: the city's **Engage Toledo / Cityworks service-request
extract** — `Public/CityWorks_ServiceRequest_2022/MapServer/0` — is
**same-day live** (newest row probe day), natively geocoded, and holds
the full current year (43,252 rows). Permits are a UI-only portal,
there is no license feed (only a static rental-registry shapefile), and
no deeds stream.

---

## Method, and its limits

1. Host fingerprints: `toledo.opendata.arcgis.com` (ArcGIS Hub, public,
   `numberMatched: 91`); `cityoftoledo.opendata.arcgis.com` (private,
   401); no Socrata; `data.toledo.oh.gov` DNS fail.
2. Hub catalog: full 91-item listing (ops layers, surveys, static
   shapefile/CSV exports — including `Rental_Registry_SEPT_2025.zip`
   and `All_Demos.geojson`).
3. City ArcGIS Server: `gis.toledo.oh.gov/arcgis/rest/services`
   (folders Basemaps, Contractors, Fire, GPS, Hosted, Internal, Public,
   Public_Application_Services, Survey, Utilities). `Public` folder
   walked — found `CityWorks_ServiceRequest_2022` and
   `For_Sale_Data`; row-level on both.
4. AGOL org: owner `EngUser` (City of Toledo Data Hub owner; ~330 items
   in the org, sampled) — `CityworksSRDash` item resolved to the same
   Cityworks service. Keyword sweeps for permits/licenses hit only
   other cities' items.
5. Permits portal: `permits.toledo.oh.gov` exists (403 to anonymous
   probe — the city's Toledo Build/permit portal), `aca-prod.accela.com/TOLEDO`
   404. No permit-records feed.

Limits: the org owner sweep was partial (AGOL pagination quirk);
`Internal` and `Contractors` folders returned empty service listings
from outside. The 311 layer name says "2022" — verified via row-level
counts that it currently holds **only 2026 rows** (total 43,252 = count
since 2026-01-01), i.e. a current-year rolling extract, not an archive.

---

## Headline table

| Family | Endpoint | Newest row (watermark) | Geocoding | Recent window | Tier |
|---|---|---|---|---|---|
| **311** | `gis.toledo.oh.gov/arcgis/rest/services/Public/CityWorks_ServiceRequest_2022/MapServer/0` | `INIT_DATE` = **2026-08-27 (probe day)** | native point geom, `outSR=4326` confirmed (−83.56, 41.70) + `LOCATION` address | 7d **1,080**; 60d **9,839**; 2026 YTD **43,252** (= layer total → current-year rolling window) | **1** |
| **PERMITS** | none public. `permits.toledo.oh.gov` portal (403 to anonymous probes); no permit records on server/Hub | n/a | n/a | n/a | **3** |
| **SLA** | none live. `Rental_Registry_SEPT_2025.zip` is a static rental-registry shapefile export (Sept 2025), no feed | n/a | n/a | n/a | **3** |
| **DEEDS** | none. `For_Sale_Data/FeatureServer/0` is city-surplus parcels; no transfer stream | n/a | n/a | n/a | **3** |

**Keep or reject: REGISTER partial** — 311 only. Existing
`ArcGISClient` (anonymous MapServer layer `query`; MapServer, not
FeatureServer — same contract as Greenville permits / Omaha 311).

---

## 311 — Tier 1 (same-day live; Engage Toledo / Cityworks)

- `https://gis.toledo.oh.gov/arcgis/rest/services/Public/CityWorks_ServiceRequest_2022/MapServer/0`
  (source view `Cityworks.AZTECA.COT_Dashboard_SR_VW Events`)
- 43,252 rows (all `INIT_DATE >= 2026-01-01` — current-year rolling
  window; year rollover will truncate history, register with
  `expected_cadence_days: 1` and treat the layer as today-forward),
  point geometry, `maxRecordCount` 20000, anonymous query OK.
- Columns: `REQUEST_ID`, `TYPE` ("REQUEST"), `DESCRIPTION`
  (e.g. "Parked Vehicle Concern", "Water Backup Inside Concern"),
  `INIT_DATE`, `INVT_DATE`, `CLOSED_DATE`, `STATUS` (`IP`/`CLOSED`),
  `RESOLUTION`, `LOCATION` ("811 ANNABELLE DR, TOLEDO, OH, 43612"),
  `PROBZIP`, `SUBMITTO`, `DISPATCHTO`, `INIT_BY`, `X_COORD`/`Y_COORD`
  (projected), `DISTRICT`.
- Watermark **`INIT_DATE`**. Newest row REQUEST_ID 796117 opened
  **2026-08-27** (Parked Vehicle Concern, 811 Annabelle Dr). Window
  counts: 1,080/7d, 9,839/60d — production-grade volume.
- Geocoding: **native** — `outSR=4326` geometry returns in-city WGS84
  points on the newest rows. `X_COORD`/`Y_COORD` are projected; do not
  use raw. `LOCATION` is the fallback.
- **PII — drop at ingest:** `INIT_BY`.
- `CLOSED_DATE` nullable on open rows — watermark on `INIT_DATE` only.
- Do not register the sibling `CityworksSRDash` dashboard item or the
  Hub's static exports.

**Register layer 0.** Re-probe `INIT_DATE` ≤72 h before build.

---

## Permits — Tier 3 (portal UI)

`permits.toledo.oh.gov` is the city's permit portal (blocks anonymous
probes); no Accela tenant (404); no permit-records layer on the public
REST server or Hub. `All_Demos.geojson` in the Hub is a one-shot
demolitions export (modified 2024-10), not a live permit stream.

## SLA — Tier 3 (static export)

`Rental_Registry_SEPT_2025.zip` — rental registry as a static
shapefile upload (Sept 2025). No live service, no watermark. Do not
register.

## Deeds — Tier 3

`For_Sale_Data` = city-owned surplus parcels for sale. Lucas County
auditor surfaces are UI/index only. No transaction stream.

---

## Decision

**Register Toledo as a partial Wave-3 metro: 311 only.**

- 311: Tier 1, same-day, native geocode via `outSR=4326`; note the
  current-year rolling window (misleading "2022" layer name).
- Permits / SLA / deeds: Tier 3.

Re-probe `INIT_DATE` and layer row count ≤72 h before the
implementation wave (confirm the layer does not rotate away on Jan 1).
Stamp: 2026-08-28.
