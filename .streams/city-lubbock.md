# Stream log — city-lubbock — 2026-08-30

## Claim

- **Stream id:** city-lubbock (US-268)
- **Leaf files I will create/edit:** `docs/research/probe-lubbock.md` (probe), no leaf city module / field_maps / tests (Tier 3 REJECT — leaf build not authorized)
- **Spine files I expect to need:** none (leaf-only, no spine; Tier 3 so no CityId / REGISTRY / dashboard / product facts)

## Intent

LIVE probe Lubbock, TX (US-268, South Central, pop ~360K, Lubbock County 48303,
Fit Medium) at 2026-08-30 UTC against Socrata, ArcGIS Hub, City/County ArcGIS
Server, hosted AGOL org, ArcGIS Search API, Tyler EnerGov SelfService,
Permitium, GovQA 311, and LCAD/County parcel surfaces with row-level
watermark/DESC/count/geocode tier checks for permits / 311 / SLA / deeds
(+ bonus Crime). Write `docs/research/probe-lubbock.md`. If Tier 1/2 authorize
leaf build (`cities/lubbock.py`, `field_maps_lubbock.py`, 30+ tests); if Tier 3
write REJECT doc only. No spine edits, no commit, no Linear mutation —
leaf-only interlock.

## Decisions

- 2026-08-30 — Claim filed; ticket hint read (County GIS + city permits, pop
  ~360K, Fit Medium). Prior sweep already marked Lubbock Tier 3 (Texas
  super-feed cluster) — re-verifying live.
- 2026-08-30 — Socrata: `domains=data.lubbocktx.gov` / `lubbocktx.gov` /
  `data.lubbocktx.us` / `opendata.lubbocktx.gov` / `data.lubbock.com` /
  `mylubbock.us` → **Domain not found (all)**. No Socrata.
- 2026-08-30 — Hub: `lubbock.opendata.arcgis.com` + `data-lubbockcma` →
  HTTP 401 private org. No public Hub.
- 2026-08-30 — ArcGIS Server hint hosts (`gis.lubbocktx.gov`,
  `gis.co.lubbock.tx.us`, `maps/*`, `services/*`) resolve but **ETIMEDOUT
  HTTP 000**. Found live city server **`pubgis.ci.lubbock.tx.us/server/rest/services`**
  (10.91): 20+ folders enumerated.
- 2026-08-30 — AGOL org `orgid:eYXun6c1pgy8Qpta AND type:"Feature Service"` =
  **164 Feature Services**; full title scan → **0 permit/311/license/deed
  transaction layers**. Owners `GISDS_CityofLubbock` / `THudson_CityofLubbock` /
  `CFields_CityofLubbock` / `LECDGIS` / `LCTechLogin` swept.
- 2026-08-30 — Permits: City permitting pages -> Tyler **EnerGov SelfService**
  Angular SPA (`egovaccess.ci.lubbock.tx.us/EnerGov_Prod/SelfService/`),
  `/selfservice/api/*` → 404, bearer `webApiBaseUrl=/user/token`. EnerGov
  MapServer layers are basemap/parcel/inspection-area reference only (no
  permit layer). Permitium `/rod` = vital-records order tracker.
- 2026-08-30 — 311: GovQA web form (`lubbocktx.govqa.us/.../SupportHome.aspx`);
  Code Cases are ArcGIS Insights workbooks (gated `insightsservices2.../
  WorkspaceServer` + Council_Districts basemap); geocoded layer is a geocoder
  output, not case records. Building Safety "Performance Metrics" Dashboard
  `data` references only the city website.
- 2026-08-30 — Deeds: LCAD `DashboardParcelData/2` Parcels = tax roll
  (LANDVALUE/IMPVALUE/TOTALVALUE/OWNER_NAME, **no sale price/date**); OpenData
  "Deeds" layers = City ROW/park **dedication polygons**, not ownership deeds.
- 2026-08-30 — Bonus Crime: `Police/Crime_Map` 53,355 pts, `REPORTDATE`
  non-null 53,355 but **max 2024-09-24** (~23 mo stale); `OFFENDATE`/`LASTUPDATE`
  0 non-null; SR 2276. Stale.
- 2026-08-30 — State super-feeds `s7ft-44qi` / `7358-krk7` / `7hf9-qc9f` →
  HTTP 200 live, county-filterable to Lubbock 48303 (SLA companion only).
- 2026-08-30 — **Verdict: Tier 3 REJECT — no registrable live row-level feed.**
  Permits vendor-locked (EnerGov), 311 GovQA/Insights-gated, SLA none municipal,
  deeds LCAD tax roll, crime stale. State super-feeds remain the SLA-only path.
- 2026-08-30 — Decision: **no leaf city module, no field_maps, no tests** —
  Tier 3 does not authorize leaf build; no spine hold (CityId/REGISTRY/
  dashboard). Write REJECT probe doc only. No commit, no Linear mutation.

## Current step

Probe doc written to `docs/research/probe-lubbock.md` (Tier 3 REJECT with
verdict, method, platform table, per-family row-level findings, hosts-rejected
table, recommendation, re-probe trigger). Stream log (this file) updated.
Verifying leaf-only constraint (no spine file touched).

## Next step

Verification: `git status` should show only `docs/research/probe-lubbock.md` +
`.streams/city-lubbock.md` as untracked; no `apps/api/src/*` edits. Report
verdict to caller; await orchestrator re-probe trigger (public
FeatureServer/datastore or Socrata `4x4` view with fresh watermark + native /
address geocode). State super-feeds (`s7ft-44qi`/`7358-krk7`/`7hf9-qc9f`,
48303) remain the SLA companion if Lubbock advances via derived-state
registration (no municipal leaf).

## Outcome

**Verdict:** Tier 3 REJECT (municipal). **Feeds verified registrable:** 0.
**Feeds as Tier 3:** permits (EnerGov vendor-lock), 311 (GovQA/Insights),
SLA (none municipal; state super-feeds companion), deeds (LCAD tax roll),
crime (stale 2024-09-24). **Files created:** `docs/research/probe-lubbock.md`,
`.streams/city-lubbock.md`. **No leaf files, no tests, no spine edits, no
commit, no Linear mutation.**

## Final verification

- `docs/research/probe-lubbock.md` written; `.streams/city-lubbock.md` written.
- No `apps/api/src/spatial/cities/lubbock.py`, no
  `apps/api/src/producers/field_maps_lubbock.py`, no
  `apps/api/tests/unit/test_producers_lubbock.py` — Tier 3 does not authorize.
- Interlock not implicated (no spine file touched). No commit / no Linear
  mutation per leaf-only constraint.
