# Stream log — city-lafayette — 2026-08-30

## Claim

- **Stream id:** city-lafayette
- **Leaf files I will create/edit:** `docs/research/probe-lafayette.md` (probe), no leaf city module / field_maps / tests (Tier 3 REJECT — leaf build not authorized)
- **Spine files I expect to need:** none (leaf-only, no spine; Tier 3 so no CityId/REGISTRY/dashboard/product-facts)

## Intent

LIVE probe Lafayette, LA (US-266, South Central, est pop ~478K Lafayette Parish,
Fit Medium) at 2026-08-30 UTC against the LCG self-hosted ArcGIS Server
(`maps.lafayettela.gov`), the LCG AGOL org (`fOr4AY8t0ujnJsua`, owner `lcgdata`,
278 items), the suspected Hub (`lafayette-la.opendata.arcgis.com`), and the LCG
website portals with row-level watermark/DESC/count/geocode tier checks for
permits/311/SLA/deeds. Write `docs/research/probe-lafayette.md` with verdict.
If Tier 1/2 authorize leaf build (`cities/lafayette.py`, `field_maps`, 30+ tests);
if Tier 3 write REJECT doc. No spine edits, no commit, no Linear mutation —
leaf-only interlock.

## Decisions

- 2026-08-30 — Claim filed; ticket hint hostname `gis.lafayettela.gov` → NXDOMAIN;
  real server is `maps.lafayettela.gov` (240 services, 15 folders). Hub
  `lafayette-la.opendata.arcgis.com` → stale DCAT `Domain record not found`.
- 2026-08-30 — AGOL org sweep: canonical public org `lcgdata`
  (`fOr4AY8t0ujnJsua`, 278 items enumerated; keyword sweep over all service
  names). Second org `xQcS4egPbZO43gZi` (CajunCodeFest) hosts the only public
  permit-named service — token-gated (499) / item subscription-canceled (403).
- 2026-08-30 — PERMITS row-level: `LCG_Permit_Status/FeatureServer/1` is a
  `Permit_Status` **Table** (layer 1; layer 0 is Address_Points), 31,158 rows,
  watermark `DATETIME` newest **2026-08-04**; `RES_TYPE` = Other 27,432 /
  Warning 3,277 / Hold 444 / Active 1; negligible `DEPT_DIV`; newest rows =
  condemnation holds; **no issuance columns / no geometry / `SITE_ADDRESS`
  mostly null → wrong grain Tier 3**. Portal `lafayettecsdgovla.tylerportico.com`
  (Tyler Portico) credentialed SPA → Tier 3. `CollectorGDB_Permit_gdb/0`
  `survey_collector` = narrow street/culvert/driveway survey form, not building
  permits. `xQcS4egPbZO43gZi …Lafayette_Planning_And_Zoning_Permits` → 499
  Token Required (private).
- 2026-08-30 — 311 row-level: live channel `311lafayette.services/en-US` is a
  Microsoft Dynamics 365 / Power Portal (interaction-type-deflection guid
  pattern; Login/Sign in; oData/`_api`/`api/data` all 404) → auth-walled Tier 3.
  Public AGOL `CitizenProblems_…/FeatureServer/0` (JerryBrushWithLocation):
  5,546 rows, native point `esrignss_latitude`, newest `CreationDate` =
  **2020-10-29** (Hurricane Delta), category domain {Brush Pile, Powerlines} →
  stale/narrow 2020 viewer, **0 in any 30/60 d window** → Tier 3. Self-hosted
  `CityWorks` folder = drainage coulees + infrastructure assets, no request rows.
- 2026-08-30 — SLA: no municipal business-license registry in 278-item catalog.
  `LASR_Registry_Form` = Louisiana Special At-Risk vulnerable-person registry
  (DOB/medical/race/PII blocks) — wrong domain + severe PII → do not register.
  LCG business-permits/licenses pages = Tyler Portico intake, no license feed.
- 2026-08-30 — DEEDS: `dbo_Parcels_with_CAMA_Data_View/FeatureServer/0` =
  119,666-polygon assessment-roll snapshot (uploaded 2026-04-29, newest
  `last_edi_1` **2026-04-06**), `Property_Transactions` = text-embedded
  instrument refs, no sale-price/date transaction stream → Tier 3.
- 2026-08-30 — **Verdict: Tier 3 REJECT — no registrable live row-level feed
  across permits/311/SLA/deeds.** No Socrata open-data domain
  (`lafayettela-of.finance.socrata.com` = Open Finance dashboard, catalog 0
  datasets); no CKAN; no Hub DCAT.
- 2026-08-30 — Decision: **no leaf city module, no field_maps, no tests** — Tier
  3 does not authorize leaf build; no spine hold (CityId/REGISTRY/dashboard
  wiring/product facts). Write REJECT probe doc only. No commit, no Linear
  mutation per leaf-only constraint.

## Current step

Probe doc written to `docs/research/probe-lafayette.md` (Tier 3 REJECT with
method, host/platform table, headline matrix, per-family row-level findings,
hosts-rejected table, decision, re-probe trigger). Stream log (this file)
updated. Verifying leaf-only constraint (no spine file touched).

## Next step

Verification: `git status` should show only `docs/research/probe-lafayette.md`
+ `.streams/city-lafayette.md` as modified/untracked; no `apps/api/src/*` edits.
Report verdict to caller; await orchestrator re-probe trigger (a public
`FeatureServer`/Hub/CKAN row-level permit or 311 feed with a fresh per-row
watermark <60 d and native-or-address geocode, or a public Socrata `4x4` view),
none observed 2026-08-30.
