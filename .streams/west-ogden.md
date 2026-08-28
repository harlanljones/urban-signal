# Stream log — west-ogden — 2026-08-28

## Claim

- **Stream id:** `west-ogden`
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/ogden.py` — NOT BUILT (REJECT: no verified feeds)
  - `apps/api/src/producers/field_maps_ogden.py` — NOT BUILT (REJECT)
  - `apps/api/tests/unit/test_producers_ogden.py` — NOT BUILT (REJECT)
- **Spine files I expect to need:** NONE (leaf-only stream; no spine delta)

## Intent

Probe Ogden, UT municipal open-data feeds (ArcGIS Hub / ogdencity.com) live.
If 1-4 verifiable official feeds exist (permits / 311 / SLA licenses / deeds),
build the Ogden leaf. If no official feed verifies, report REJECT with
evidence. No git commits, no Linear updates.

## Outcome

**REJECT — Ogden, UT has NO verifiable official open-data feed** for any of the
preferred signals (permits / 311 / SLA / deeds). No leaf files built. Full
evidence below.

Verified-signal sweep (all live-probed 2026-08-28):

1. **Permits — REJECT.** Ogden City's permits run on Tyler **EnerGov**
   SelfService (`https://egselfservice.ogdencity.com/energovprod/SelfService`,
   `onestop.ogdencity.com` redirects here). It is a **transactional
   apply/renew/lookup-my-own portal**: no bulk query API — every candidate
   endpoint 404/500 (`api/query`, `api/cap`, `api/license`, `PublicQuery`,
   `PublicSearch`, `odata`, `swagger.json`); the AngularJS bundle exposes only
   account/application/report routes. The EnerGov→ArcGIS integration on
   `arcgis.ogdencity.com` serves only reference basemaps (EnerGov/Parcels,
   EnerGov/AddressPoints, EnerGovBaseMapCSS) — no permit layer.
2. **311 / service requests — REJECT.** "Ogden Serve" citizen-reporting is a
   **CivicPlus FormCenter** form (ogdencity.gov FormCenter, `connect.civicplus
   .com/referral` 403) with no public data API. Ogden's own ArcGIS
   `Graffiti_ViewLayer` is a graffiti-waiver survey (PII form), not a request
   feed.
3. **Business licenses (SLA) — REJECT.** Same EnerGov SelfService portal
   (transactional only). No bulk feed. (Weber County's own
   Business/Beer/STR licensing is county-level, not Ogden City, and has no
   public bulk feed either.)
4. **Recorded deeds/sales (Weber County) — REJECT.** No recorder's-office
   bulk feed reachable (recorder pages 404 on webercountyutah.gov; no OpenData
   portal). Weber County ArcGIS Server 11.4 (`maps.webercountyutah.gov/arcgis/
   rest/services`) assessor layers (`Assessed_Values_Map_2026`, `LEA`) are
   annual CAMA/snapshot parcel layers — no sale price/date, no watermark.
   Utah AGRC `Parcels_Weber_LIR` is the same class (CAMA, no sales).
   `Excavation_permits` is a misnamed city-boundary layer; `weeds_tracking` /
   `engineering_tracking` are internal ops layers (PII, no public contract).
5. **Open Data portal — REJECT.** `ogdenut-ogdencity.opendata.arcgis.com`
   ArcGIS Hub is a dead 404 shell (`window.__SITE...status:404`); no Hub
   datasets. No Socrata/CKAN anywhere. Ogden City ArcGIS Online org
   (`5bEsxSBu0dtu5rkP`, 596 public Feature Services) contains NO operational
   permits/311/licenses/deeds feeds — only reference/static/one-off study
   layers (e.g. Southeast_Ogden_Crime_WFL1 = 5-year community-study snapshot,
   not a live crime feed).

Small-city reality check: Ogden (pop ~87K city / ~240K metro) relies on
proprietary transactional portals (EnerGov, CivicPlus) without open-data
exports, exactly the class of host this repo's ADR-0004 / city-registration
rule rejects. Registering Ogden would mean ingesting a stale mirror or an
aggregate/dashboard view — forbidden. REJECT stands.

## Decisions

- 2026-08-28 — Claim made; US-246 fetched (thin: "verify the public feed, then
  open a spine hold"). Ogden's ArcGIS Hub is a dead 404 shell; the ArcGIS
  Online org (596 services) has no operational feeds.
- 2026-08-28 — EnerGov SelfService = transactional only (no bulk API); Ogden
  Serve 311 = CivicPlus forms; no SLA/deeds feeds anywhere. Weber County has
  CAMA parcel layers only, no deeds/sales. Verdict: REJECT, no leaf build.

## Current step

DONE. Probe complete, verdict recorded. No leaf files to build, no tests to
run, no git commits.

## Next step

Report REJECT via the stream log (this file) + recommended Linear comment on
US-246. Nothing further for this stream.
