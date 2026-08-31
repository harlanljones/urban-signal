# Stream log — city-brownsville — 2026-08-30

## Claim

- **Stream id:** city-brownsville
- **Linear:** US-269 (Brownsville, TX — South Central, pop ~420K Cameron Co, `data.brownsvilletx.gov` / Cameron GIS, Fit Medium)
- **Leaf files I created/edited (leaf-only, no spine):**
  - `docs/research/probe-brownsville.md` (rejection probe doc)
  - (no leaf code — verdict is Tier 3)
- **Spine files I expect to need:** NONE — REJECT, no registration.

## Intent

Onboard Brownsville, TX as a South Central metro if a live family feed
satisfied ADR 0004. Live phase-0 probe (2026-08-30) finds **all four
families Tier 3**: permits, 311, SLA, deeds. Verdict is **REJECT for
municipal leaf** — a state-feed-only (TDLR/TREC/TABC, Cameron 48061)
companion is the only viable SLA path, matching the prior RGV/Cameron
Tier-3 DEFER, the McAllen reject, and the Corpus Christi municipal-Tier-3
stance. No leaf code, no spine delta.

## Live probe summary (2026-08-30 UTC)

- **Socrata/CKAN discovery:** `data.brownsvilletx.gov`,
  `data.brownsville-tx.gov`, `data.cameroncountytx.gov`,
  `data.cameroncounty-tx.gov` → all **DNS-unresolvable (000)**; no civic
  Socrata/CKAN domain.
  `api.us.socrata.com/api/catalog/v1?domains=cameroncountytx.gov,brownsvilletx.gov`
  and `domains=brownsville.gov` → **Domain not found** (not Socrata).
- **Hub:** `brownsville.opendata.arcgis.com`, `cameroncountytx.opendata.arcgis.com`,
  `co-cameron.opendata.arcgis.com` — root 200 but v3 catalog
  `api/search/v1/collections/dataset/items` → **401 private org id not
  accessible**; DCAT `api/feed/dcat-us/1.1.json` → **404 Domain record not
  found**. No enumerable dataset catalog.
- **AGOL org sweep:** `q=owner:COBGISManager` (City of Brownsville, 603
  items, `services2.arcgis.com/6oaLMZEZlktbQpyi`) and
  `q=owner:CAMERONCOUNTY_GIS3` (Cameron County, 207 items,
  `services5.arcgis.com/p65BQlkv8na0Y5l9`). City org = GIS reference
  (parcels/address/streets/parks/bus stops/resacas) + Survey123 intake
  forms. County org = boundary/reference layers (parcels, roads, drainage,
  JP/constables, schools). Per-family keyword filters:
  permit(9 county / 21 city), 311(0 county / 1 city, unrelated),
  license(0 county / 3 city), deed(1 county = PARCELS_2024 / 0 city),
  complaint(0 county / 4 city), service-request(5 county / 9 city).
- **City ArcGIS Server:** `cobgis.brownsvilletx.gov/arcgis/rest/services` →
  folders `Accela, Annexations, FEMA, Hosted, Utilities`.
  `Accela/Accela_Map_Service_V1`, `Accela/Accela_Map_Service_Test1`, root
  `Accela_Map_Service` → **esriCarto GraphicFeatureServer 500 sync error**
  (non-queryable). `Hosted` → dated parcel/address/ACS/parks snapshots.
- **Cameron County GIS Experience**
  `9153381449d7407ab67e4d0d7285dd3b` → SPA shell, no service URLs in HTML.
- **Row-level family verification (AGOL FeatureServer):**
  - PERMITS `Accela_Permits_Report_03312026` (FeatureServer 0, serviceDesc
    `AccelaAdhocreport`): **4,753 rows**; fields
    `Permit_Type/Permit__No/Address/Work_Description/X_COORD/Y_COORD/Rec_Open_Date/Permit_Issue_Date/Permit_Category`;
    **native coords 4,753/4,753 (100% x/y)**; watermark `Permit_Issue_Date`
    (ms) max **1774933200000 = 2026-03-31**, min **1688360400000 =
    2023-07-03** (2.7y window); item created ~2026-01-01, modified ~2026-05-01
    (**frozen report**); newest live reads `2025-03604` 7234 OLD HIGHWAY 77,
    `2026-00339` 6672 PADRE ISLAND HWY, `2026-00682` 2050 JOHNSON ST (all
    issue 2026-03-31). This layer backs the public "Accela Permits Map"
    webmap + "Development Activity Report" dashboard. **0 rows last
    30/60/90d** → **152 days stale** → **Tier 3**.
  - PERMITS `Residential_Permits` ("New Residential Permits w/ time
    enabled"): **2,451 rows**, `CreatedDat` max **1464652800000 =
    2016-05-31** (~10y stale), fields `PermitNumb/FullAddres/Descriptio/
    PermitType/PrintedDat/CreatedDat/Match_addr` — geocode log, wrong grain
    → **Tier 3**.
  - 311: no civic service-request layer in either org. City 311-adjacent =
    Survey123 intake (`Requests_submit` mod 2025-07-24, `MosquitoReports`,
    `Illegal Dumping Reports`, `Parks and Grounds Request`). Freshest item,
    `ServiceNow Interface Map` (mod **2026-07-29**), is a **reference base
    map** — parcels/streets/parks/bus stops/resacas/city buildings — no SR
    layer → **Tier 3**.
  - SLA: `Business Licenses Inspections 2015` (webmap/app, **stale 2015**),
    `TABC_Geocoded` (state). County `q=license` 0 → **Tier 3**.
  - Deeds: Cameron CAD `gissvr.cameroncad.org/arcgiswa/rest/services/
    Features/parcels/FeatureServer/0` — **187,816 parcel polygons**, fields
    only `OBJECTID*/GEO_ID/PROP_ID` + `created_*/last_edite` (parcel maint
    dates, not sale dates) → **Tier 3** (annual/static, not transactional).

## Verdict

**REJECT — all four families Tier 3.** No live family feed satisfies ADR
0004 (row-level watermark + native-or-address geocode). The one true permit
stream (Accela) is published only as a **frozen dated snapshot**
(`Accela_Permits_Report_03312026`, newest 2026-03-31, 152d stale, 0 rows in
last 30/60/90d); the local ArcGIS Server Accela services are **sync 500**;
county permitting is a Survey123 intake form; civic 311 has no layer in
either org; deeds are CAD parcel polygons with no transaction fields;
municipal SLA is a 2015 snapshot + state TABC. State super-feeds (TDLR
`7358-krk7`, TREC `s7ft-44qi`, TABC `7hf9-qc9f`, all live 200,
`business_county`/`county` filterable to Cameron 48061) are a **companion
only**, not a municipal leaf.

## Leaf artifacts (this hold)

- `docs/research/probe-brownsville.md` — South Central phase-0 rejection
  probe (portals, headline tier table, per-family findings, hosts
  probed/rejected, recommendation), structure mirrors `probe-mcallen.md` /
  `probe-laredo.md`.
- No leaf code (`spatial/cities/brownsville.py`, `field_maps_brownsville.py`,
  `test_producers_brownsville.py`) — NOT created (Tier-3 rejection per
  onboarding protocol step 5).

## Spine delta

**NONE.** No CityId.brownsville, no ALIASES, no REGISTRY, no config, no
METRO_META, no facts. If the metro is later pursued, it must be via a
state-feed-only (SNAP/TDLR/TREC/TABC Cameron 48061) path like the RGV
Tier-3 cluster — not a municipal leaf.

## Verification

- No leaf tests to run (no leaf code created; 0 tests).
- No spine edits in this hold (`git status` clean on spine manifest paths).
- No Linear state change, no git commit per leaf-only instruction.

## Risk / re-probe trigger

Re-probe if: (1) Accela ACA exposes a public live bulk/data-extract export;
(2) the Cameron/Brownsville Hub catalog becomes public (401 → 200) with
permit/311 layers; (3) the city AGOL org republishes the Accela permit
report as a **regenerating** (undated) service with a live watermark; or
(4) a current-year permit or 311 service-request layer appears with live
data. Until then Brownsville/Cameron stays state-feed-only.

## Current step

Probe + rejection doc complete. Leaf closed without code (Tier 3).

## Next step

None — ticket stays in Backlog. Orchestrator may note the RGV/Cameron
state-only SLA path; do NOT open a spine hold for city-brownsville.
