# Stream log — west-santa_clarita — 2026-08-28

## Claim

- **Stream id:** `west-santa_clarita`
- **Leaf files I will create/edit:** NONE (REJECT outcome)
- **Spine files I expect to need:** NONE

## Intent

Live-verify 1-4 official municipal open-data feeds for Santa Clarita, CA
(~280K pop, LA County) via ArcGIS Hub. If verifiable official feeds exist,
build a leaf registration. If no verifiable official feed exists, report REJECT
with evidence.

## Decisions

- 2026-08-28T21:00Z — PROBE COMPLETE. Outcome: **REJECT**.
- 2026-08-28T21:05Z — Final re-verify of LA County deeds fallback and city
  server sweep. Confirmed no verifiable feed. REJECT stands.

## Probe evidence (PHASE A)

### Summary
Santa Clarita, CA has NO verifiable open data feed for permits, 311/service
requests, business licenses (SLA), or recorded deeds/sales. The city's GIS
infrastructure (ArcGIS Enterprise at maps.santa-clarita.com, ArcGIS Online org
"santa-clarita" / VIT2lop0SYQZYGmw) is largely token-protected or broken. The
ArcGIS Hub at santa-clarita.hub.arcgis.com is an empty generic shell. REJECT.

### 1. Permits — Accela (ACA + ArcGIS)
- **ACA web portal:** `https://aca-prod.accela.com/SANTACLARITA/Default.aspx`
  — web UI only, not an open API/feed.
- **ArcGIS Accela services** (maps.santa-clarita.com):
  - `Accela/FeatureServer` — HTTP 200, empty body; layer query returns 500
    "No Layer or Table was initialized"
  - `Accela/MapServer` — 500 same
  - `Accela/Accela/FeatureServer` — 499 Token Required
  - `Accela` folder listing — 499 Token Required
- **Hosted Accela-related services** (Film_Days, Film_Revenue,
  Number_of_Businessess_Combined_Data): all 499 Token Required.
- **Verdict:** ❌ No verifiable permit feed.

### 2. 311 / Service Requests
- **Illegal Fireworks 2019/2020/2021** (Administrative/FeatureServer lyr 9/10/12):
  - Point geometry (esriGeometryPoint) + native lat/lng attributes
  - Fields: Request, Topic, Entered_date, Location, Latitude, Longitude
  - Counts: 597 / 499 / 75 rows (1,171 total)
  - Newest Entered_date: 1628467200000 = **2021-08-09** (5 years stale)
  - Static annual snapshots, NOT a live feed; no 2022-2026 data
  - ⚠️ 311-style with coordinates but stale — disqualified as a live feed.
- **Graffiti Cleanup All Data:** public portal item tagged "Open Data" but
  FeatureServer URL returns 404. Not accessible.
- **RSC (Resident Service Center) monthly surveys:** aggregated tables
  (Date/Type/Responses/Label), no geometry, no individual requests,
  ~22 rows/month. Static survey stats, not a transactional feed.
- **Verdict:** ❌ No verifiable live 311 feed.

### 3. Business Licenses (SLA)
- Nothing found in any portal or ArcGIS Online org.
- "Number_of_Businessess_Combined_Data" — 499 Token Required.
- **Verdict:** ❌ No SLA feed.

### 4. Deeds / Sales
- **LA County Socrata** (data.lacounty.gov): migrated to ArcGIS Hub; API
  endpoints ("Cannot GET /api/...") all dead. Not usable.
- **LA County ResidentialParcels** (ArcGIS Online): parcel reference layer
  (polygon, AIN/APN/situs address/use code) — no sale price, transaction
  date, or deed metadata. NOT a deeds feed.
- **LA County Assessor Portal** (portal.assessor.lacounty.gov): web UI only.
- **Verdict:** ❌ No verifiable deeds feed (county or city level).

### 5. ArcGIS Hub
- **santa-clarita.hub.arcgis.com:** generic ArcGIS Hub shell (8KB), no
  datasets. "Customer Service" Hub Page item says hub not deployed
  (URL has a colon typo: `santa-clarita.hub.arcgis.com:/overview/edit`).
- **data-santa-clarita.opendata.arcgis.com:** generic shell.
- **santaclarita.opendata.arcgis.com:** generic shell.
- **Verdict:** ❌ No populated ArcGIS Hub.

### 6. Portal Open Data
- maps.santa-clarita.com portal has `openData: enabled: true` but
  `/portal/opendata` returns 500 Application Error. Broken.

### 7. Other public services (non-feeds)
- RoadRehabPublic — capital projects, not a transaction feed.
- Emergency feeds (RoadClosures, Incidents, Evacuations) — transient.
- Property/Administrative/Zones/Boundary — reference layers only.
- CRM/CRM MapServer — reference data (addresses, parcels, boundaries).

## Current step

Final stream log write-out.

## Outcome

**REJECT** — Santa Clarita, CA has no verifiable official open data feed for
permits, 311, SLA, or deeds. The city's GIS is token-protected (Accela permits,
hosted services) or contains only static/reference layers. The Illegal
Fireworks data (Administrative/FeatureServer layers 9/10/12) is 311-style with
coordinates, but it is a stale static snapshot (last data 2021-08-09, ~5 years
old) — never a live feed, and a stale mirror is explicitly disallowed.

Candidate feeds verified: **0 of 4** (permits/311/SLA/deeds).
Watermarks: n/a.
Tests: n/a.

## Spine delta

NONE — REJECT outcome; no leaf build, no registration, no spine changes.

**Recommended Linear comment for US-251:** REJECT — Santa Clarita, CA has no
verifiable official open-data feed. Accela permits are token-protected/broken
on the city ArcGIS server; 311 data is a stale static snapshot (Illegal
Fireworks 2019-2021, newest 2021-08-09); no SLA or deeds feed exists (LA County
parcels are a reference layer, not a sale stream). Recommend wontfix/needs-info:
city must publish open data (ArcGIS Hub is an empty shell) before registration
is possible.