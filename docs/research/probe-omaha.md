# Wave 3 Phase-0 probe — Omaha, NE

**Date of probe: 2026-08-28 (UTC).** Row-level ArcGIS reads: newest-row
`orderByFields` watermark checks, `returnCountOnly` window counts, and
`outSR=4326` geometry verification on every public survivor.

Linear: **US-358**. Ticket hint: `data.dogis.org` (Douglas–Omaha GIS);
historical `data-cityofomaha-ne.gov`.

**Verdict: REGISTER (partial).** One strong Tier-1 family: the city's
**Mayor's Hotline (Omaha 311)** is published as an anonymous Cityworks
extract on the DCGIS ArcGIS Server — **same-day live** with native point
geocoding. Permits are Accela (UI-only), liquor licenses are a registry
with no date column (unwatermarkable), and there is no deeds stream.
The historical Socrata domain (`data-cityofomaha-ne.gov`) does not
resolve.

---

## Method, and its limits

1. Host fingerprints: `data.dogis.org` → "DCGIS Open Data Portal"
   (ArcGIS Hub, `numberMatched: 43` — all reference/cadastral layers);
   `data-cityofomaha-ne.gov` → **no Socrata domain**;
   `cityofomaha.opendata.arcgis.com` → Hub placeholder (org private,
   API 401).
2. AGOL org sweep: city org `tIBLyYZX96jUntYm` (`omaha.maps.arcgis.com`,
   1,653 items); keyword-swept for permit / 311 / service request /
   license / sales / deed. Survivors row-probed.
3. Key discovery: **`CW_service_requests - PRODUCTION`** AGOL item
   pointing at `dcgis.org/server/rest/services/Cityworks/Mayors_Hotline_Dashboard_Interactive/MapServer/0`
   plus a "Mayors_Hotline_HubPage" service family (12-month views and
   count rollups).
4. Permits: Accela fingerprint `aca-prod.accela.com/OMAHA` → 200
   (Permit & Licensing Center). "Construction Permits - DEV" items in
   the org are 2019–2020 dev artifacts.
5. SLA: `City_Liquor_Licenses` FeatureServer (1,157 rows) read
   row-level — no date column at all.

Limits: the org keyword sweep surfaced only owners `Nataliya1` and
`citizen_reporter_test` for service requests; other owners were not
row-probed. The liquor-license web map (modified 2025-10) references
the same registry. City site (`cityofomaha.org`) blocks scrapers (403)
so the 311 = Mayor's Hotline linkage rests on the service naming
("Mayors_Hotline") and the Cityworks platform.

---

## Headline table

| Family | Endpoint | Newest row (watermark) | Geocoding | Recent window | Tier |
|---|---|---|---|---|---|
| **311** | `dcgis.org/server/rest/services/Cityworks/Mayors_Hotline_Dashboard_Interactive/MapServer/0` | `DATETIMEINIT` = **2026-08-27 (probe day)** | native point geom, `outSR=4326` confirmed (−96.152, 41.262) + `PROBADDRESS` | 7d **1,152**; 60d **9,745**; Aug **4,638**; total **648,604** | **1** |
| **PERMITS** | none public. Accela `aca-prod.accela.com/OMAHA` (Permit & Licensing Center) | n/a | n/a | n/a | **3** |
| **SLA** | `City_Liquor_Licenses/FeatureServer/0` — 1,157 rows, point geom | **no date column** (`LICENSE_NUMBER`, `LICENSE_CLASS`, `LICENSE_HOLDER`, `REMOVED`) — unwatermarkable registry | native points + address | n/a | **3** |
| **DEEDS** | none. DCGIS Hub is cadastral reference; `DC_Tax_Liens_view` is tax liens, not transfers | n/a | n/a | n/a | **3** |

**Keep or reject: REGISTER partial** — 311 only. Existing
`ArcGISClient` (anonymous MapServer layer `query` — same contract as
Greenville permits; MapServer, not FeatureServer).

---

## 311 — Tier 1 (same-day live; Mayor's Hotline)

- `https://dcgis.org/server/rest/services/Cityworks/Mayors_Hotline_Dashboard_Interactive/MapServer/0`
- 648,604 rows, point geometry, `maxRecordCount` 2000, anonymous query OK.
- Columns: `OBJECTID`/`REQUESTID` (identical — one id field),
  `PROBLEMCODE` (e.g. Tree/Shrub Issue, Illegal Dumping),
  `DESCRIPTION`, `DETAILS`, `PROBADDRESS` ("15308 Wycliffe Dr, Omaha,
  NE, 68154"), `INITIATEDBY`, `SUBMITTO`, `CLOSEDBY`,
  `DATETIMEINIT`, `DATETIMEINITFULL`, `DATETIMECLOSED`,
  `WORKORDERID`, `SRX`/`SRY` (State Plane), `STATUS` (`IP` = in
  progress), `REQCATEGORY`, dept/organization fields.
- Watermark **`DATETIMEINIT`**. Newest row REQUESTID 663325 opened
  **2026-08-27** (Illegal Dumping, 6510 S 30th St). Production-grade
  window: 1,152 rows/7d, 9,745/60d.
- Geocoding: **native** — `outSR=4326` geometry returns in-city WGS84
  points on the newest rows. `SRX`/`SRY` are State Plane; do not use
  raw. `PROBADDRESS` is the fallback.
- **PII — drop at ingest:** `INITIATEDBY`, `CLOSEDBY` (Memphis
  contact-field precedent).
- Companion layers (do not register; derived views):
  `Mayors_Hotline_HubPage/MapServer/1` "Service Requests - 12 months"
  (57,897 rows), `.../4` problem-type counts, `.../5` status counts.
- Platform note: Cityworks is the CRM; the MapServer extract is the
  feed. `DATETIMECLOSED` is nullable on open rows — watermark on
  `DATETIMEINIT` only.

**Register layer 0.** Re-probe `DATETIMEINIT` ≤72 h before build.

---

## Permits — Tier 3 (Accela UI)

Omaha runs the Accela Permit & Licensing Center
(`aca-prod.accela.com/OMAHA`). The only permit items in the AGOL org
are 2019–2020 "- DEV" construction-activity artifacts. No public
permit-records feed.

## SLA — Tier 3 (registry, no watermark)

`City_Liquor_Licenses` (1,157 rows): classes (I, C, …), holder, DBA,
address, `REMOVED` flag. **No issuance/expiration date column** — the
registry cannot be watermarked, so row-level freshness is unverifiable
and the SLA flow signal is unusable. `CWS_SDLL_NEW` (special designated
liquor licenses) resolves to an app, not a layer. Do not register.

## Deeds — Tier 3

DCGIS Hub (43 items) is parcels/lots/zoning/LiDAR reference layers;
no sales/transfer dataset; no county deed feed found. Do not register.

---

## Decision

**Register Omaha as a partial Wave-3 metro: 311 only.**

- 311: Tier 1, same-day, native geocode via `outSR=4326`, MapServer
  extract of Cityworks (Mayor's Hotline).
- Permits / SLA / deeds: Tier 3.

Re-probe the layer ≤72 h before the implementation wave. Stamp:
2026-08-28.
