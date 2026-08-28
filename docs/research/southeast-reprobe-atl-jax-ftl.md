# Southeast re-probe — Atlanta, Jacksonville, Fort Lauderdale

**Date of re-probe: 2026-08-28.** A dispatcher-driven re-assessment of the
three Southeast cities whose 2026-08-27 wave-3 phase-0 probes judged **all four
signal families Tier 3 / not wave-ready**: Atlanta (US-336), Jacksonville
(US-338), Fort Lauderdale (US-342). Every row below was read live this day
(2026-08-28); **only newest-row-by-watermark counts as evidence** — catalog
`modified` and portal `lastEditDate` are labels, never freshness. "Fresh" for
this pass means newest row ≥ **2026-07-29** (~30 days).

Scope discipline (per the Myrtle Beach sibling-probe warning "North Myrtle
Beach AGOL STR data must never be swept into a Myrtle Beach bbox"): a county /
Broward-wide / neighboring-jurisdiction table is **never** attributed to these
cities. Where a live signal is county-shaped (FTL deeds), it is called that,
not a city leaf.

Prior context:
- `docs/research/wave-3-probe-atlanta.md`, `wave-3-probe-jacksonville.md`,
  `wave-3-probe-fort-lauderdale.md`, `wave-3-probe-broward.md`. (The referenced
  `docs/research/se-probe-*.md` sibling files were **not present** in this
  checkout; the Myrtle Beach discipline is applied from the brief instead.)

---

## ATLANTA (US-336)

**RECOMMEND = KEEP-DEFERRED.** No family graduated. No new door found.

| Family | Platform / endpoint | Watermark col + newest | ≥30d | ≥60d | Total | Geo | Verdict |
|---|---|---|---|---|---|---|---|
| PERMITS | arcgis — `services5.arcgis.com/5RxyIIJ9boPdptdo/.../Building_Permit_latest/FeatureServer/0` (DCP org, `gpickren2`) | `OrigOpened` **2026-01-29** | **0** | **0** | 36,115 | native point | Tier 3 — **frozen** |
| PERMITS (official Hub CSV) | arcgis Hub `All Building Permits 2019-2024` (item `655f98...`) | `DATE OPENED` **2024-04-26** | 0 | 0 | 38,107 | lat/lng on CSV | Tier 3 — archive |
| 311 | — | no public feed (ATL311 is Dynamics 365 self-service) | — | — | — | — | Tier 3 — absent |
| SLA | arcgis — DCP org extracts (GBL_WFL1 / BusinessLicenses_2024_Revenue / Business_Licenses_2026) | citywide `USER_Business_License_Issued_Da` **2022-06-01**; AMS-district clip `license_issued` **2026-07-30** (508 rows, 0 in Aug) | 0 | 0 | 26,643 / 19,297 / 508 | point / mixed; clip not citywide | Tier 3 — stale snapshot + clipped extract |
| DEEDS | arcgis — Fulton `Tyler_YearlySales` | last published year **2022** | 0 | 0 | ~12,875/yr | polygon, no sale stream | Tier 3 — annual archive |

### Evidence (live, this day)

- **TLS retry `opendata.atlantaga.gov` — still dead.** Strict HTTPS `curl` exit
  `000`; `-k` gives HTTP 404 "Microsoft Azure Web App — Error 404". The custom
  domain still points at an empty Azure Government web app. Do not re-treat a
  future TLS fix as a portal until the 404 clears.
- **`Building_Permit_latest` FeatureServer (unofficial AGOL "latest" extract) —
  STILL FROZEN.** `dataLastEditDate` = `2026-01-29 09:00:29Z` (unchanged from the
  wave-3 value). Newest row `RecordID=BB-202600801`, `OrigOpened` 2026-01-29,
  "797 VEDADO NE, ATLANTA, GA 30308". Row counts ≥2026-07-29 (30d) **0**, ≥2026-06-29
  (60d) **0**. Total 36,115. Native point; `Address` populated. Seven-month-stale
  extract — still a thaw-watch, not a feed.
- **New-door search, pushed one level past the wave-3 Hub/Server discovery** by
  enumerating the DCP org `5RxyIIJ9boPdptdo` Feature Services and a broad AGOL
  keyword sweep:
  - `Code_Enforcement_Data_2021_2023` (org `5RxyIIJ9boPdptdo`) — 20,781 rows,
    `Open_Date` max **2023-12-29**, 0 in 30d/60d. Frozen; and is code-enforcement
    cases (2021–23), not citizen 311. **Not** a new door.
  - `Service Request` (org `8gr8DRX2cvuioG1p`, item `b2d1288e...` — a **different**
    org than the DCP one) — it is a Survey123 `Form`/`FeatureService` with fields
    `request_number, city, district, weather_temperature, walkout_plan` — a
    survey/worksheet form, not the ATL311 municipal table. **Not** a new door.
  - `AMS_BuildingPermits`, `Atlanta Main Street Business Licenses 2026`
    (`Business_Licenses_2026`, layer 50 "Revenue2026BusinessLicenses_AMS") — the
    small Main Street district clip the wave-3 probe already called too-clipped
    (508 rows). Not citywide.
  - No org or AGOL result surfaced a live Atlanta permit, 311, or license
    FeatureServer. Deeds remain Fulton-county-only and year-archive shaped.

### Re-probe triggers (if deferred)
1. `Building_Permit_latest` layer 0: newest `OrigOpened` within ~30 days of a
   re-probe **and** an interlock decision that an unofficial DCP-org extract is
   an acceptable system of record versus Accela. Until both, thaw-watch only.
2. `gis.atlantaga.gov/dpcd` ArcGIS Server 11.3: any future `BuildingPermits` /
   `ServiceRequest` / `BusinessLicense` table that is not in the current folder
   set (AdministrativeArea, DocumentArchive, LandUsePlanning, OPALMapServices,
   ReferenceData, Tolemi, Utilities).
3. Any Atlanta city domain publishing an Open311 `/open311/v2/services.json` or a
   Socrata/CKAN catalog (none seen).

---

## JACKSONVILLE (US-338)

**RECOMMEND = KEEP-DEFERRED.** No family graduated. One door *thawed* (deeds
parcel snapshot) but it is the wrong-shape class the deeds ADR rejects.

| Family | Platform / endpoint | Watermark col + newest | ≥30d | ≥60d | Total | Geo | Verdict |
|---|---|---|---|---|---|---|---|
| PERMITS | custom — JAXEPICS SPA (`jaxepics.coj.net`), API `jaxepicsapi.coj.net` | none (MSAL/Akamai-403) | — | — | — | — | Tier 3 — no public bulk REST |
| 311 | custom — MyJax (`myjax.custhelp.com`, Oracle RightNow) | none | — | — | — | — | Tier 3 — submit/track UI only |
| SLA | arcgis — `services1.arcgis.com/NXfNVaFp7QMxnE3j/.../Business_Data_WFL1/FeatureServer/0` | **no date column** (2020 JSO snapshot) | 0 | 0 | 59,765 | native LAT/LONG | Tier 3 — 2020 snapshot |
| DEEDS (parcel snapshot) | arcgis — `maps.coj.net/coj/rest/services/CityBiz/Parcels/MapServer/0` | `SALESLYY/LMM/LDD` composite **2026-08-20** | **62** | — | 408,202 | native `LAT`/`LONG` | Tier 3 for DEEDS — live but last-sale-on-parcel, no price/doc |
| DEEDS (transaction file) | file dump — Duval PA `...-SALES-FIXED-FORMAT-TEXT-FILE-08-10-2026.zip` | rec03 sale **2026-07-22** (file as-of 08-10) | — | — | 3,479,623 rec03 | site address / RE join | Tier 3 — ~5-week lag, no sale price |

### Evidence (live, this day)

- **`opendata.coj.net`** still DNS-unresolved (not re-listed here; the wave-3 DNS
  sweep was exhaustive). The working successor is GIS + file dumps, not a catalog.
- **JaxGIS ArcGIS Server 11.1** `maps.coj.net/coj/rest/services` live (36 folders).
  Sibling `maps1.coj.net/ags115` still token-gated for folder contents (error 499
  Token Required on folder queries), so its `DuvalProperty` / `CityBiz` / `CRM`
  folders were **not** row-verifiable anonymously this pass; the org remains the
  reliable anonymous surface.
- **DEEDS — the parcel last-sale snapshot IS moving.** CityBiz/Parcels MapServer
  0: composite `SALESLYY,SALESLMM,SALESLDD` newest sale **2026-08-20**
  (`RE 171223 0000`, `645 SAILFISH DR`; `RE 000035 0000`, `18835 BEAVER ST W`).
  `SALESLYY=2026` total **22,505**; June/July 2,114 / August 31; 30d
  (≥2026-07-29) **62**. Native `LAT` / `LONG` on all. **But** this is the exact
  one-row-per-parcel last-sale overlay `docs/research/seattle-deeds-replacement.md`
  rejects ("no new row per sale; watermark would not move with sales", no
  `SALEPRICE` / deed book / instrument). It is **wrong-shape for a DEEDS feed**,
  not wrong-jurisdiction — so **REGISTER-PARTIAL is not warranted**. It is a
  probe trigger, not a registration.
- **Duval PA monthly sales file — unchanged cadence.** Newest file on the
  data-offerings page is as-of **08-10-2026** (same as wave-3); the prior reads
  put newest rec03 sale at **2026-07-22** with no observed sale-price field and
  ~5-week lag. Not a Wave-3 feed (Cincinnati-deeds is a **daily** county CSV).
  Only becomes viable if (1) sale price is confirmed in the layout, and (2)
  monthly lag is accepted as `expected_cadence_days: 45` — a later-wave build,
  not the "easiest verified win".
- **Permits** — JAXEPICS SPA still serves client-side HTML; `jaxepicsapi.coj.net`
  returns Akamai **403** on `/api`. AGOL org `NXfNVaFp7QMxnE3j` scoped search:
  `permit` 0, `complaint` 0, `license` 0, `workorder` 0; "service request" 8 hits
  are **JEA utility** work orders / a `Requests_submit` Survey123 form — not city
  311. No new door.
- **311** — MyJax is Oracle Service Cloud / RightNow (submit/track). No Open311,
  no FeatureServer. No new door.
- **SLA** — `Business_Data_WFL1` layer "BusinessData_2020_JSO" (59,765 points,
  `LATITUDE`/`LONGITUDE` + `PRIMARY_ADDRESS`) — **zero date columns**, static 2020
  JSO snapshot. Local Business Tax Receipts live at `county-taxes.net/fl-duval/btexpress`
  (search/pay UI only). No new door.

### Re-probe triggers (if deferred)
1. Newest composite sale date on `CityBiz/Parcels` continues to move **and** an
   interlock decision to accept last-sale-on-parcel as a deeds signal — but note
   the watermark does **not** append per sale, so this never becomes a true
   transaction log without a price/doc-number column. Likely reject.
2. JAXEPICS: any public `swagger` / `openapi` / bulk REST surfacing
   (`jaxepicsapi.coj.net` stops 403ing).
3. Duval PA: a sales file with a documented sale-price field and a shorter lag
   (currently ~5 weeks).
4. Any city 311 Open311 endpoint (`myjax.custhelp.com` exposing GeoReport).

---

## FORT LAUDERDALE (US-342)

**RECOMMEND = KEEP-DEFERRED.** No family graduated as a city leaf. The only live
tabular signal is Broward-county-shaped and belongs to a `broward` county leaf,
not FTL.

| Family | Platform / endpoint | Watermark col + newest | ≥30d | ≥60d | Total | Geo | Verdict |
|---|---|---|---|---|---|---|---|
| PERMITS | arcgis — `gis.fortlauderdale.gov/server/rest/services/BuildingPermits/FeatureServer/0` | `SUBMITDT` **2026-03-16** | **0** | **0** | 204,760 | native point (2236) | Tier 3 — frozen |
| 311 | arcgis — `ServiceRequest/FeatureServer/0` | `REQUESTDATE` **2022-02-05 17:49** | 0 | 0 | 2,267 | native point | Tier 3 — frozen |
| 311 (SeeClickFix) | report — `seeclickfix.com/api/v2/issues?place_url=fort-lauderdale` | `created_at` **2026-08-28** | ~105 | — | 1,299 | native lat/lng | NOT city feed — thin public place |
| SLA | arcgis — `BusinessLicense/FeatureServer/0` | `ISSUEDATE` null 0/21,849; `EXPIREDATE` **2021-09-30** (wave-3) | 0 | 0 | 21,849 | native point | Tier 3 — frozen 2019–20 BTR |
| DEEDS | arcgis — `TaxParcel/FeatureServer/0` (BCPA last-5) | `SALEDATE1` **2026-08-13** | **405** countywide / **185** FTL in 30d | 1,612 / 60d | 195,107 (85,241 FTL-ish) | native polygon + lat/lng | live, but **Broward-wide** last-5 mutation — not an FTL leaf |

### Evidence (live, this day)

- **PERMITS — STILL FROZEN.** `BuildingPermits/0`: newest `SUBMITDT` = **2026-03-16**,
  0 rows ≥2026-07-29 (30d) and ≥2026-06-29 (60d). Native point + `FULLADDR`.
  `APPROVEDT` is null on every row. Same March 2026 cliff as wave-3.
- **311 — STILL FROZEN.** `ServiceRequest/0`: newest `REQUESTDATE` **2022-02-05 17:49**,
  0 rows ≥30d/≥60d. This is a Jan 5–Feb 5 2022 window only. SeeClickFix place is
  live (`newest` 2026-08-28) but ~3.6 public issues/day — an unofficial public
  place, not the municipal system of record, and it would need a new client.
  Not a city 311 feed.
- **SLA — STILL FROZEN.** `BusinessLicense/0`: `ISSUEDATE` non-null **0 / 21,849**;
  newest `EXPIREDATE` 2021-09-30 (re-read via count windows; the on-prem SQL
  backend 400s on `orderByFields` for these date columns, so only the wave-3
  ordered read stands). 0 rows ≥30d/≥60d.
- **DEEDS — live but Broward-shaped.** `TaxParcel/0`: `SALEDATE1` newest
  **2026-08-13** (FTL `WD` $525,000 sample; `QCD` $100). 30d (≥2026-07-29):
  **405** countywide / **185** `PARCELCITY='FORT LAUDERDALE'`. Native
  `LATITUDE`/`LONGITUDE`. **Same disposition as wave-3**: it is a Broward County
  Property Appraiser last-**five**-sales snapshot the city happens to host,
  covering 19 municipalities; `SALEDATE1` mutates on re-sale rather than
  appending a deed log, so a parcels watermark is unverifiable; and a city
  registration would leak Pompano/Tamarac/… or require a `PARCELCITY` filter.
  **Broward-county-only** is the right home. Do not stretch to FTL DEEDS.
- **Only live city feed:** `FranchisePermit` (utility/right-of-way, 11 edits
  ≥30d) — wrong family for the four-family contract.

### Re-probe triggers (if deferred)
1. `BuildingPermits/0`: `SUBMITDT` moves off the 2026-03-16 cliff (schema is
   already Tier-1-shaped — native point + address + Accela IDs).
2. `ServiceRequest/0`: `REQUESTDATE` resumes (currently frozen Feb 2022).
3. `BusinessLicense/0`: any `ISSUEDATE` becoming non-null / `EXPIREDATE` moving
   past 2021.
4. Broward county probe on the `TaxParcel` BCPA snapshot (own it at `broward`
   CityId, not FTL).
5. Any FTL Open311 / Socrata / CKAN catalog (none seen).

---

## CROSS-CITY pattern

All three cities share the same obstacle, in two flavors. **Obstacle 1 — the
dead civic open-data portal was never replaced.** Atlanta's
`opendata.atlantaga.gov` is a TLS-broken Azure Government 404, Jacksonville's
`opendata.coj.net` is DNS-unresolved, and Fort Lauderdale never had a Socrata/CKAN
catalog; each rebuilt on ArcGIS (Hub + Server + AGOL org), but the ArcGIS layer is
**planning/GIS reference surfaces** (parcels, zoning, NPUs, boundaries) and
**unofficial hand-exported extracts** that are frozen months to years behind the
system of record. **Obstacle 2 — the transactional system of record is a
vendor SPA without a public bulk REST** (Accela for Atlanta/FTL permits, JAXEPICS
for Jacksonville permits, Dynamics 365 / Oracle RightNow for 311, tax-collector
UIs for SLA), so even though residents submit just-in-time, no row-level open
table exists to watermark. The one signal that *does* publish is **county-shaped
and either laggy or last-sale-shaped**: Fort Lauderdale's live deeds live on a
Broward Property Appraiser 19-municipality snapshot, and Jacksonville's moving
deeds signal is a one-row-per-parcel last-sale overlay with no price/doc-number.
What would change all three: (1) a vendor (Accela / Accela-to-ESRI) bulk REST or
`FeatureServer`-grade export of the permitting and 311 tables — one integration
per vendor would unlock Atlanta and Fort Lauderdale permits simultaneously; (2) a
city-owned Open311 (GeoReport) endpoint or hosted 311 FeatureServer; and (3) for
deeds, a genuine recorder/assessor transaction stream with price + document
number per sale, with the correct home at the **county** `CityId`
(`fulton`, `duval`, `broward`) rather than the city — a county leaf is where the
Southeast deeds wins (e.g. Broward SLA already registers as a Tier 1 county leaf)
belong, not a stretch on a city with frozen municipal registers.
