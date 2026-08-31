# Stream log — city-corpus_christi — 2026-08-31

## Claim

- **Stream id:** city-corpus_christi
- **Leaf files I will create/edit:** `docs/research/probe-corpus_christi.md` (probe), no leaf city module/field_maps/tests (Tier 3 REJECT — leaf build not authorized)
- **Spine files I expect to need:** none (leaf-only, no spine; Tier 3 so no CityId/REGISTRY/dashboard/product facts)

## Intent

LIVE probe Corpus Christi, TX (US-265, South Central, pop ~430K, Fit Medium) at 2026-08-31 UTC against Socrata (`cctexas.com`), Hub DCAT (`corpus-christi.opendata.arcgis.com`), ArcGIS Server, AGOL org sweep with row-level watermark/DESC/count/geocode tier checks for permits/311/SLA/deeds. Write `docs/research/probe-corpus_christi.md` with verdict. If Tier 1/2 authorize leaf build (`cities/corpus_christi.py`, `field_maps`, 30+ tests); if Tier 3 write REJECT doc. No spine edits, no commit, no Linear mutation — leaf-only interlock.

## Decisions

- 2026-08-31 — Claim filed; spine manifest read — 11 entries, all gated.
- 2026-08-31 — Prior sweep `southwest-mountain-expansion-probe-2026-08-30.md` Corpus Christi §2 read: prior Tier 3 DEFER (Dynamic Portal/EnerGov) with cctexas.gov infrastructure-only assessment — starting point.
- 2026-08-31 — Laredo leaf precedent `cities/laredo.py` + `field_maps_laredo.py` + `probe-laredo.md` inspected for leaf structure, tier-tripwire, and probe doc shape (Socrata vs CKAN vs Hub, watermark windows, geocode tier).
- 2026-08-31 — LIVE probe phase:
  - Socrata `api.us.socrata.com/api/catalog/v1?domains=cctexas.com` (and `data.cctexas.com`, `corpuschristitx.gov`, `nuecescountytx.gov`) → 404 Domain not found; `q=corpus christi` → 0 municipal datasets. **No Socrata.**
  - Hub `corpus-christi.opendata.arcgis.com/api/search/v1/collections/dataset/items` → 401 private org not accessible; DCAT `api/feed/dcat-ap/2.0.1.json` → 404 domain not found. Canonical is `gis-Corpus.opendata.arcgis.com` (65 features, `dcat:dataset: []` empty) — infra only.
  - ArcGIS Server 6 host probes (`gis.cctexas.com`, `maps.cctexas.com`, `gis.corpuschristitx.gov`, `gis.nuecescountytx.gov`, `gis.nueces-county.com`, `gis.nuecesco.com`) → NXDOMAIN/ETIMEDOUT; hosted path `services.arcgis.com/0J4ZNc4NaTguvRy0/arcgis/rest/services/OpenData/FeatureServer` → 76 layers + 4 OpenDataAdd, 293 orgid items — zero permit/311/license/deed transaction layers.
  - AGOL org `owner:ccgisadmin` 186, `bsnEnFfEn54YLVeq` 637 (regional coastal), `search q=Corpus Christi permits/311` 0 municipal hits.
  - Permits: sitemap → `dynamic-portal-guides` → Infor Rhythm `https://corpuschristi-prd.rhythmlabs.infor.com/` (CIVICS, Liferay `currentGroupId 5147586`) + PDF `/media/bopd00u3/dynamic-portal-training-guide.pdf` strings/pdftotext confirms Rhythm, `/api` 404, monthly PDF district maps (2021) — no FeatureServer. `aca-prod.accela.com/CORPUSCHRISTI` 404 — hint Accela is stale.
  - 311: `311.cctexas.com → /help/s/` Salesforce Experience Cloud (`corpuschristi311.my.site.com`, CSP `*.forceusercontent.com`, `cctexas-api.herokuapp.com` 404); `311.cctexas.gov` NXDOMAIN; AGOL `q=311 Corpus` 6 → no incident FeatureServer.
  - SLA/licenses: Hub 65-title scan + ccgisadmin 186 → 0; state `data.texas.gov/api/views/s7ft-44qi|7358-krk7|7hf9-qc9f` → 200 live — county-filterable to Nueces 48355.
  - Deeds: `NCad_Parcels` layer 43 polygon wkid 2279 fields AREA/PERIMETER only — no sale price/date; `owner:nuecescad` Web Map+WMTS only; alt GIS hosts DNS/404.
- 2026-08-31 — **Verdict: Tier 3 REJECT — no registrable live row-level feed.** Socrata absent, Hub DCAT empty/private, ArcGIS Server DNS-dead, hosted FeatureServer infra-only, Dynamic Portal is credentialed Infor Rhythm Liferay HTML wall, 311 is Salesforce SaaS wall, CAD is polygon roll. State super-feeds `s7ft-44qi/7358-krk7/7hf9-qc9f` remain viable for Nueces 48355 SLA-only pattern.
- 2026-08-31 — Decision: **no leaf city module, no field_maps, no tests** — Tier 3 does not authorize leaf build; no spine hold (CityId/REGISTRY/dashboard). Write REJECT probe doc only. No commit, no Linear mutation per leaf-only constraint.

## Current step

Probe doc written to `docs/research/probe-corpus_christi.md` (Tier 3 REJECT with method, platform table, summary matrix, per-family row-level findings, hosts-rejected table, recommendation, re-probe trigger). Stream log (this file) updated. Verifying leaf-only constraint (no spine file touched).

## Next step

Verification: `git status` should show only `docs/research/probe-corpus_christi.md` + `.streams/city-corpus_christi.md` as untracked/modified; no `apps/api/src/*` edits. Report verdict to caller; await orchestrator re-probe trigger (public FeatureServer/datastore or Socrata `4x4` view with fresh watermark + native/address geocode).
