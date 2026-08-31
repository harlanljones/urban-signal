# Stream log — city-mcallen — 2026-08-30

## Claim

- **Stream id:** city-mcallen
- **Linear:** US-264 (McAllen, TX — South Central, pop ~870K Hidalgo Co, `data.texas.gov` County GIS / Accela, Fit Medium)
- **Leaf files I created/edited (leaf-only, no spine):**
  - `docs/research/probe-mcallen.md` (rejection probe doc)
  - (no leaf code — verdict is Tier 3)
- **Spine files I expect to need:** NONE — REJECT, no registration.

## Intent

Onboard McAllen, TX as a South Central metro if a live family feed satisfied
ADR 0004. Live phase-0 probe (2026-08-30) finds **all four families Tier 3**:
permits, 311, SLA, deeds. Verdict is **REJECT for municipal leaf** — a
state-feed-only (TDLR/TREC/TABC, Hidalgo 48215) companion is the only viable
SLA path, matching the prior RGV/Hidalgo Tier-3 DEFER and the Corpus Christi
municipal-Tier-3 stance. No leaf code, no spine delta.

## Live probe summary (2026-08-30 UTC)

- **Socrata discovery:** `domains=data.texas.gov` (state) resolves — no
  McAllen/Hidalgo municipal permits/311/deeds datasets; `q=mcallen`,
  `q=hidalgo`, `q=hidalgo building permits` → no relevant results.
  `domains=mcallen-tx.opendata.arcgis.com` → **Domain not found** (not Socrata).
- **McAllen Hub:** `mcallen-tx.opendata.arcgis.com` 200 but SPA shell; v3
  catalog `api/search/v1/collections/dataset/items` → **401 private**, DCAT
  `api/feed/dcat-us/1.1.json` → 404. `mcallen` / `mcallen_tx` /
  `cityofmcallen` variants identical (401).
- **AGOL org sweep:** `q=owner:roymartinez_mcallen` 184 items + service
  directory `services3.arcgis.com/feieT9DHJD3rMLX7/arcgis/rest/services?f=json`
  (~250 services — utilities, TPWL, manholes, fiber, Survey123 forms,
  hydrants, parks, subdivisions, fire-call address points). No permits
  issuance stream, no 311 service-request layer, no license registry, no
  sales/deed layer.
- **ArcGIS Server:** city `gis.mcallen.net` / `maps.mcallen.net` /
  `gismaps.mcallen.net` (and `:6443`) → all 000 DNS-dead; AGOL
  `mcallen.maps.arcgis.com` / `mcallen-tx.maps.arcgis.com` → 404; county
  `gis.hidalgocounty.us` / `mc-gis.hidalgocounty.us` / `adcog…` →
  000/404.
- **City-site portals:** `www.mcallen.net` 200. Permits →
  `onlinepermits.mcallen.net/Portal/default.aspx` = **Accela ACA** (ACA
  cookies); `aca.accela.com/mcallen` → 301 → `aca-prod.accela.com/mcallen`
  → **404**; all plausible REST/Records/Search paths → 404/302 (interactive
  form only). 311 → `mcallen.net/departments/311/request` city form +
  `mcallen.go2gov.net` **CivicPlus** SPA (no bulk API).
  `mcallen-tx.portal.opengov.com` → OpenGov dashboard shell, no city data.
- **Row-level family verification (AGOL FeatureServer):**
  - PERMITS `Residential_Building_Permits` layers 0–6 (`Log_In_2015`…
    `Log_In_2020`): layer 6 (516 rows) `Finaled_Da` max = **2020-12-31**;
    layer 0 has **no date field**; one anomalous row `RES2019-5616`
    `2028-01-28` = data-entry error. Grain is a **geocoded address-point
    log** (`Permit__`/`Field2`/`Contractor`/`Finaled_Da`/`Clerk`) — no
    permit number/valuation/status/work type. ~5.7 years stale → **Tier 3**.
  - 311 `Fire_Department_Calls_WFL1` layers 0–9 (`745 - Alarm System
    Activation`…`111 - Structure Fire`, `Sheet1_Geocoded`): World-geocoder
    address-points with free-text `USER_F111`/`IN_SingleLine` carrier — **no
    date-bearing column and no civic 311 taxonomy** → not a registrable 311
    feed.
  - `SubstandardVacantHousing` → **0 rows**.
  - SLA / deeds: no license registry, no sales/deed FeatureServer (HCAD
    `hidalgoad.org` = annual rolls/parcel polygons only; `palmviewtx` HCAD
    Palmview Parcels is a parcel polygon, not a sales stream).

## Verdict

**REJECT — all four families Tier 3.** No live family feed satisfies ADR
0004 (row-level watermark + native-or-address geocode). Permits are behind
an interactive Accela ACA portal with no bulk API; the only AGOL permit
layer is a 2020-capped geocode log; 311 is a city form / CivicPlus intake
with no public layer; deeds are HCAD annual rolls. No leaf code, no spine
delta. State super-feeds (TDLR `7358-krk7`, TREC `s7ft-44qi`, TABC
`7hf9-qc9f`, all live 200, `business_county`/`county` filterable to Hidalgo
48215) are a **companion only**, not a municipal leaf.

## Leaf artifacts (this hold)

- `docs/research/probe-mcallen.md` — South Central phase-0 rejection probe
  (portals, headline tier table, per-family findings, hosts probed/rejected,
  recommendation), structure mirrors `probe-little_rock.md` / `probe-laredo.md`.
- No leaf code (`spatial/cities/mcallen.py`, `field_maps_mcallen.py`,
  `test_producers_mcallen.py`) — NOT created (Tier-3 rejection per
  onboarding protocol step 5).

## Spine delta

**NONE.** No CityId.mcallen, no ALIASES, no REGISTRY, no config, no
METRO_META, no facts. If the metro is later pursued, it must be via a
state-feed-only (SNAP/TDLR/TREC/TABC Hidalgo 48215) path like the RGV Tier-3
cluster — not a municipal leaf.

## Verification

- No leaf tests to run (no leaf code created).
- No spine edits in this hold (`git status` clean on spine manifest paths).
- No Linear state change, no git commit per leaf-only instruction.

## Risk / re-probe trigger

Re-probe if: (1) Accela ACA exposes a public data-extract/bulk export; (2)
the McAllen Hub catalog becomes public (401 → 200) with permit/311 layers;
or (3) the AGOL org ships a current-year permit or 311 service-request layer
with a live watermark. Until then RGV/Hidalgo stays state-feed-only.

## Current step

Probe + rejection doc complete. Leaf closed without code (Tier 3).

## Next step

None — ticket stays in Backlog. Orchestrator may note the RGV/Hidalgo
state-only SLA path; do NOT open a spine hold for city-mcallen.
