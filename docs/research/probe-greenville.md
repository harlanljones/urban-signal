# Wave 3 Phase-0 probe — Greenville, SC

**Date of probe: 2026-08-28 (UTC).** Row-level reads: layer metadata,
`returnCountOnly` window counts, and newest-row `orderByFields` with
`outSR=4326`. Catalog dates ignored as freshness evidence.

Linear: **US-340**. Ticket hint: ArcGIS Hub (`citygis.greenvillesc.gov`).

**Verdict: REGISTER (partial).** One Tier-1 family. The ticket's Hub hint is
the wrong door — the Hub placeholders (`greenvillesc.opendata.arcgis.com`
etc.) are private/empty (401 "private org … not accessible") and no Socrata
exists — but the city's **ArcGIS Server 10.81 at
`citygis.greenvillesc.gov`** serves an anonymously queryable permits layer
updated daily. 311 exists as an AGOL item but points at an internal-only
`.ads` host. SLA is a static annual snapshot; deeds are parcel CAMA
attributes.

---

## Method, and its limits

1. Hostname fingerprint: `citygis.greenvillesc.gov` (HTTPS 200, HTTP 403;
   `/arcgis/rest/services` → ArcGIS Server **10.81** with 25 folders),
   Hub placeholders (8 KB landing pages, APIs 401), `data.greenvillesc.gov`
   / `opendata.greenvillesc.gov` (DNS fail), Socrata discovery (0).
2. Folder walk: `GeneralData` (reference layers + Parcels),
   `InfoHUB` (BuildingPermits_PriorTwoYears, BusinessLicensesForHUB_2025,
   ArchitecturalDesignReview), `DevelopmentProjects` (empty),
   `AddressSearch`, `RoadClosures`, `Utilities` (system only).
3. Row-level on survivors: permits and licenses layers got newest-row +
   window counts + geometry checks.
4. Replacement hunt: AGOL search scoped to the city org owner
   (`cdurham@greenvillesc.gov_grvlsc`) — surfaced "Service Requests For
   Dashboard with Time as Text" whose backing URL is
   `gistestpublic.greenvillesc.ads` (DNS fail — internal AD domain).

Limits: the Hub catalog is invisible from outside (private org), so a
published-but-hidden dataset cannot be ruled out; every folder on the
public REST endpoint was walked. SeeClickFix not probed (not a municipal
feed per prior probes).

---

## Headline table

| Family | Endpoint | Newest row (watermark) | Geocoding | Recent window | Tier |
|---|---|---|---|---|---|
| **PERMITS** | `citygis.greenvillesc.gov/arcgis/rest/services/InfoHUB/BuildingPermits_PriorTwoYears/MapServer/0` | `NewIssueDate` = **2026-08-26** (prior day) | point geometry, `outSR=4326` confirmed (−82.408, 34.852, in-city) + `STREETADDRESS` on newest rows | last 3 days **9**; 7d **17**; 60d **264**; total 3,874 | **1** |
| **311** | AGOL item "Service Requests For Dashboard with Time as Text" → `gistestpublic.greenvillesc.ads` (internal) | n/a — host not resolvable publicly | n/a | n/a | **3** |
| **SLA** | `InfoHUB/BusinessLicensesForHUB_2025/MapServer/0` | static snapshot; `LICENSEYEAR` max **2024** (24,324 rows); no issuance/renewal date column (only `OPENDATE`/`DATE_OPENED`) | address present | none (not watermarked) | **3** |
| **DEEDS** | `GeneralData/…/MapServer/2` Parcels (`DEEDTE`, `SLPRICE`, `CUBOOK`/`CUPAGE`) | CAMA ownership snapshot with last-deed attributes — no transaction stream | native points | n/a | **3** |

**Keep or reject: REGISTER partial** — permits only. Existing
`ArcGISClient` shape (anonymous layer `query`, but note it is a
**MapServer**, not a FeatureServer — same `query` contract).

---

## Permits — Tier 1 (daily live)

- `https://citygis.greenvillesc.gov/arcgis/rest/services/InfoHUB/BuildingPermits_PriorTwoYears/MapServer/0`
- 3,874 rows, point geometry, `maxRecordCount` 7000, anonymous query OK.
- Rolling window: layer holds the prior two years of permits (name says
  so); rows older than that are purged, so `min(date)` is not evidence of
  staleness.
- Columns: `OBJECTID`, `Status`, `PERMIT_TYPE` (BLDG/DEMC/…),
  `APPLICDATE` (numeric `YYYYMMDD`), `BP_STATUS`, `PERMIT_NUM`,
  `STREETADDRESS`, `UNITNUM`, `PERMIT_VALUATION`, `X_COORD`/`Y_COORD`
  (State Plane feet), owner/contractor blocks, `PERMIT_LOCATION`,
  `NewIssueDate` (esri date), `PERMIT_COMMENTS`.
- Watermark **`NewIssueDate`**. Newest row `PERMIT_NUM` 2600003454 issued
  **2026-08-26** (DEM at 101 S Hudson St); application 2026-08-13.
- Geocoding: **native** — query with `outSR=4326` returns in-city WGS84
  points on the newest rows (`x=-82.408277, y=34.852703`).
  `X_COORD`/`Y_COORD` attributes are State Plane feet; do not use raw.
  `STREETADDRESS` is the address fallback.
- id_keys: `["PERMIT_NUM"]`. Cadence: daily. 7d count 17 is healthy for a
  70k-population city.

**Register this layer.** Note in registration: rolling 2-year window
(no full history) and MapServer/FeatureServer distinction.

---

## 311 — Tier 3 (internal only)

AGOL item `620fc2d1ee8d4ec0882f74ec2b81ec77` "Service Requests For
Dashboard with Time as Text" exists in the city org, but its service URL
is `gistestpublic.greenvillesc.ads/.../ServiceRequestsForDashboard/MapServer/0`
— `.ads` is the city's internal Active Directory namespace and does not
resolve publicly. No public 311/service-request layer on `citygis`
folders, Hub (private), or Socrata (no domain). Do not register; re-probe
if the city publishes the service on a public host.

---

## SLA — Tier 3 (annual snapshot)

`InfoHUB/BusinessLicensesForHUB_2025/MapServer/0`: 24,324 rows,
`LICENSE_NUM`, `BUSINESS_NAME`, `BUSINESSADDRESS`, `OPENDATE`,
`DATE_OPENED`, `CLASS_DESC` (NAICS), `LICENSEYEAR` (distinct values
21–24 → 2021–2024). Layer name says 2025 but no license row carries a
2025+ issuance or renewal date; there is no watermark column at all. A
renewal snapshot, not a live registry. Do not register.

---

## Deeds — Tier 3 (parcel snapshot)

`GeneralData/GeneralData_WebMercator/MapServer/2` Parcels: `OWNAM1`,
`DEEDTE` (last deed date), `SLPRICE`, `CUBOOK`/`CUPAGE` (deed book/page),
valuation fields. Ownership/CAMA snapshot with last-deed attributes —
same shape as Memphis `CERT_TAX_PARCELS`, not a transaction stream.
No register-of-deeds feed found. Do not register.

---

## Non-family live data (do not register as families)

Road closures (WAZE feed), parking, zoning, addresses, garbage routes —
reference/ops layers.

---

## Decision

**Register Greenville as a partial Wave-3 metro: PERMITS only.**

- Permits: Tier 1, daily, native geocode via `outSR=4326`; rolling
  2-year window documented; MapServer (not FeatureServer).
- 311 / SLA / deeds: Tier 3.

Re-probe the permits layer ≤72 h before the implementation wave. Stamp:
2026-08-28.
