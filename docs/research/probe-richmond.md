# Wave 3 Phase-0 probe — Richmond, VA (US-348)

**Date of probe: 2026-08-27/28.** Row-level reads (Socrata SoQL and
ArcGIS `query` ordered by watermark DESC / windowed counts).

**Verdict: REJECT (all four families Tier 3).** Richmond has a real
Socrata portal (`data.richmondgov.com`, **FedRAMP region** — invisible to
public Socrata discovery) and a real city AGOL org, but the portal is
small (~57 views) and holds **no** permit, 311, license-with-dates, or
current sales dataset. The ticket hint "Data source: Socrata" is
directionally right and the parcel is wrong-shaped: the closest deeds
table is frozen at 2024-10-16 and the closest license table has no date
column.

Platform: **Socrata** at `data.richmondgov.com` (small catalog) +
**ArcGIS** org `k3vhq11XkBNeeOfM` (city assessor/GIS staff on
services1.arcgis.com) + **Accela** citizen portal at
`aca-prod.accela.com/RICHMOND` (200). Not CKAN.

---

## Method, and its limits

1. Hostname fingerprint: `data.richmondgov.com` (Socrata frontend,
   `X-Socrata-Region: aws-us-east-1-fedramp-prod` — hence
   `api.us.socrata.com` discovery returns 0; the local
   `/api/catalog/v1` + `/api/search/v1` were read directly),
   `maps./gis.richmondgov.com` (DNS fail), three `.opendata.arcgis.com`
   candidates (private placeholders / 0 items).
2. Catalog sweeps with `q=permit / 311 / business license / property
   sales / real estate / deed`, filtered by host membership
   (`/api/views/metadata/v1/<id>` 200 = federated on this host). Most
   hits (Chicago, Edmonton, NYC…) are global-catalog noise; only
   `hy5d-7dcv` (Business Licenses) and `83t5-hbac` (Delinquent RE
   Taxes) actually live on `data.richmondgov.com`.
3. AGOL org `k3vhq11XkBNeeOfM` (owner-domain `@rva.gov` staff):
   family keyword sweeps → Special Use Permits (planning cases),
   "8-4-1-Permits-Residential-*" (view items whose backing
   `ResidentialConstructionSince2020_WFL1` services are
   **token-required**, HTTP 499), "Dashboard Sales Public *" web maps
   backed by `AssessorProValGPINRecTransPublish`.
4. Row-level on `hy5d-7dcv` (Socrata SoQL) and
   `AssessorProValGPINRecTransPublish/FeatureServer/0` (ArcGIS).

Limits: the "8-4-1" permit series and assessor dashboards are
token-gated; if the assessor ever opens them anonymously, permits and
sales both become candidates. RVA311 (city 311) publishes no bulk
extract; the only 311-ish Socrata view is a 2014–2015 SeeClickFix
sample.

---

## Headline table

| Family | Endpoint | Newest row (watermark) | Geocoding | Recent window | Tier |
|---|---|---|---|---|---|
| **PERMITS** | none anonymous. Accela ACA `aca-prod.accela.com/RICHMOND` (200); assessor `ResidentialConstructionSince2020_WFL1` + siblings → **499 token** | n/a | n/a | n/a | **3** |
| **311** | `vgg4-…` SeeClickFix Sample **Aug 2014–Aug 2015** (stale sample); RVA311 app | n/a | n/a | n/a | **3** |
| **SLA** | `data.richmondgov.com/api/id/hy5d-7dcv.json` (Business Licenses, **7,983** rows) | **no date column**; view `rowsUpdatedAt` = **2025-03-18** | `customer_s_address` + hidden geo point | n/a — not watermarked | **3** |
| **DEEDS** | `services1.arcgis.com/k3vhq11XkBNeeOfM/.../AssessorProValGPINRecTransPublish/FeatureServer/0` (**13,938** rows) | `sale_date` = **2024-10-16** | points + `prop_street` | 0 in 2025–2026 | **3** (frozen) |

---

## Permits — Tier 3 (portal + token-gated mirror)

- Accela ACA tenant `RICHMOND` confirmed live — transactional UI,
  not a feed.
- Assessor permit views ("8-4-1-Permits-Residential-Single/Multi"
  + Heat variants) resolve to
  `ResidentialConstructionSince2020_WFL1` and
  `CommercialConstructionSince2020_WFL1`; both answer
  **499 Token Required** at `/FeatureServer/0`.
- No permit dataset on the Socrata host (`metadata/v1` 404 for the
  noise-catalog candidates).

## 311 — Tier 3

`SeeClickFix Sample Data Aug 2014 to Aug 2015` (view `vgg4-…`) is an
11-year-old sample. Inbound 911 calls datasets are CAD telephony, not
311. RVA311 app publishes no extract. Do not register.

## SLA — Tier 3 (register-shaped, but no watermark)

- `hy5d-7dcv` Business Licenses: 7,983 rows; API columns are only
  `customer_s_name`, `customer_s_address` (display schema adds DBA,
  geo point, zip, neighborhood, sector, district).
- **No issue/renewal date column exists** — incremental watermarking
  is impossible; full-snapshot diffing is the only mode.
- `rowsUpdatedAt` = **2025-03-18** (17 months before probe). Treat as
  a stale snapshot, not a register. Do not register.

## Deeds — Tier 3 (real table, frozen)

`AssessorProValGPINRecTransPublish/FeatureServer/0` — 13,938 rows,
point geometry, joined parcel/sales fields: `sale_date`, `sale_price`,
`DocNum`, `lrsn`, `GPIN`, `prop_street`, `owner1`, `asmt_year`,
`neighborhood`, `sale_prclass`.

- Newest `sale_date` **2024-10-16** ($290,000, 1305 Mt Erin Dr);
  **0 sales dated in 2025 or 2026** — the assessor's recorded-
  transaction publish is a biennial-style snapshot.
- If refreshed, this is an instant T2 deeds candidate (points +
  street + DocNum). Watch item; re-check `sale_date >= date
  '2026-01-01'` at the next wave.

---

## Hostnames tried (negatives)

| Surface | Result |
|---|---|
| `data.richmondgov.com` | Socrata (FedRAMP); ~57 views; no family feeds |
| `api.us.socrata.com` discovery | 0 (FedRAMP isolation) |
| `maps./gis.richmondgov.com` | DNS fail |
| `richmondva./richmond./data-rva.opendata.arcgis.com` | placeholders / private / 0 items |
| `services1.arcgis.com/k3vhq11XkBNeeOfM` permit services | 499 token |
| CKAN | absent |

## Decision

**Reject Richmond for Wave 3.** All families T3. Watch items: assessor
permit/sales services (token → anonymous), Business Licenses (if a
date column and refresh appear). Stamp: 2026-08-28.

## Addendum 2026-09-30: deeds from the assessor's workbook

The assessor also publishes every recorded transfer as a monthly Excel
workbook, linked from `rva.gov/media/53946` (`Assessor_Transfers_2026-09-23.xlsx`,
439,398 rows, newest transfer 2026-09-22). It has no geometry, but its `PIN`
joins the city's `Parcels/FeatureServer/0` layer, so each sale takes its
parcel's centroid. Richmond `deeds` now reads it
(`feed-health-2026-09-30.md`, "Richmond's transfers workbook"); the frozen
`AssessorProValGPINRecTransPublish` table above is not used.

## Addendum 2026-09-30: crime from Chesterfield County police

The City of Richmond publishes no usable crime data: its CrimeInfo search
returns no rows, the police department's ArcGIS samples stop in 2021, and the
Socrata portal holds no crime dataset. Henrico County's police incident
service is live, but its terms forbid commercial use, so it is held.
Chesterfield County's police publish every offense on ArcGIS Online
(`PSDWIncidents_ProdA/FeatureServer/1`, layer `Offenses`; 25,653 rows from
2024-10-01, refreshed nightly, anonymous). Richmond `crime` now reads it.

- **Coverage.** The metro box holds 1,249 offenses over the 120 days to
  2026-09-30, all in the county's part south and west of the city
  (magisterial districts Midlothian 732, Cloverhill 329, Dale 150, Bermuda
  34). The city's and Henrico's parts of the box have no crime rows.
- **Rows.** One row per incident: `RMSIncidentID` (agency prefix, report
  date, sequence) is unique. `RecordDate` is the day the offense happened,
  date only, and reports arrive late (p50 0 days, p90 9, p95 30, p99 69, max
  118), so a watermark on it would miss them. The feed is a snapshot of the
  box's last 120 days, read whole each poll (cap 2,500), and the dedup
  publishes each incident once.
- **Location.** The county masks each address to its hundred block but not
  the point. Over a year, blocks with five or more offenses show 3.8
  distinct points on average, and 12 of 20 sampled points sit within 30 m of
  an address point. The spec's `select` leaves the address and the county's
  own coordinate columns behind, and the crime producer rounds each point to
  three decimal places (`CRIME_POINT_DECIMALS`), a grid of about 100 m,
  before it is indexed or published.
- **Offense types.** `IncidentorOffenseGenCategory`, 28 categories in the
  box: Larceny 348, Traffic 196, Assault-Simple 190, Fraud / Forgery 148,
  All Other Incidents 106, Motor Vehicle Theft 56, Vandalism 54, and 21
  smaller ones. The Part-1/Part-2 rule looked for "SIMPLE ASSAULT" and read
  `Assault-Simple` as Part 1; it now reads simple assault in either order,
  which also moves Boston's `ASSAULT - SIMPLE` and Chicago's `ASSAULT` /
  `SIMPLE` (FBI code 08A) to Part 2.

Live poll 2026-09-30 (Kafka mocked): 1,249 fetched and published, none
dead-lettered, every point on the grid and inside the box (median shift
39 m, largest 70 m); the second poll published nothing.
