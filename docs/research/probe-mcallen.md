# South Central Phase-0 probe — McAllen, TX (RGV / Hidalgo County)

**Date of probe: 2026-08-30 (UTC).** Socrata discovery (state + city), McAllen
Hub DCAT, AGOL org sweep (owner + service-directory enumeration), ArcGIS
Server host probes, and city-site portal probes (Accela ACA / CivicPlus
go2gov / OpenGov) plus row-level reads on every public family-adjacent layer.

Linear: **US-264**. Ticket hint: `data.texas.gov` County GIS / **Accela**,
pop ~870K (Hidalgo County), Fit Medium. Prior South-Central and
Southwest & Mountain West sweeps (2026-08-25 / 2026-08-30) graded the whole
Rio Grande Valley — Brownsville + McAllen / Cameron + Hidalgo — **Tier 3
DEFER** (permits behind Tyler/EnerGov + internal city systems, deeds as CAD
annual rolls, no public bulk stream). This probe **re-opens McAllen at the
datastore layer** and confirms the DEFER stands: no live family feed survives.

**Verdict: NO REGISTER (all four families Tier 3).** There is **no
municipal Socrata domain** (`api.us.socrata.com` → Domain not found for the
McAllen host), the McAllen ArcGIS **Hub is private** (401), the city's AGOL
org (`roymartinez_mcallen`, 184 items / `services3.arcgis.com/feieT9DHJD3rMLX7`,
~250 services) is **utility + Survey123 infrastructure**, the one
family-adjacent layer — `Residential_Building_Permits` — is a **geocoded
residential permit address log capped at 2020-12-31** (wrong grain, 6 years
stale), and both public transactional channels (permits **Accela ACA**,
311 **CivicPlus go2gov**) are **interactive forms with no bulk API**. County
deeds remain HCAD annual appraisal rolls. Only the state super-feeds (TX
TDLR/TREC/TABC) offer county-filterable SLA support, and that is a
companion, not a municipal leaf.

---

## Method, and its limits

1. **Socrata discovery** `api.us.socrata.com/api/catalog/v1?domains=...`:
   `data.texas.gov` (state) resolves with no McAllen/Hidalgo municipal
   permit/311/deed datasets; `domains=mcallen-tx.opendata.arcgis.com` →
   **Domain not found**. McAllen has no city Socrata domain.
2. **McAllen Hub** `mcallen-tx.opendata.arcgis.com` → 200 but is an SPA
   shell; v3 catalog `api/search/v1/collections/dataset/items` → **401
   (private)**, DCAT `api/feed/dcat-us/1.1.json` → 404. The `mcallen` /
   `mcallen_tx` / `cityofmcallen` Hub variants behave identically (401).
3. **AGOL org sweep**: `q=owner:roymartinez_mcallen` and the McAllen
   service directory
   `services3.arcgis.com/feieT9DHJD3rMLX7/arcgis/rest/services?f=json`
   (~250 services — utilities, TPWL, manholes, fiber, Survey123 forms,
   hydrants, parks, subdivisions, fire-call address points). No permits
   issuance stream, no 311 service-request stream, no license registry, no
   sales/deed layer.
4. **ArcGIS Server**: city hosts `gis.mcallen.net:6443`, `gis.mcallen.net`,
   `maps.mcallen.net`, `gismaps.mcallen.net` → all **000
   (DNS-dead)**. AGOL `mcallen.maps.arcgis.com` / `mcallen-tx.maps.arcgis.com`
   → 404. County `gis.hidalgocounty.us` / `mc-gis.hidalgocounty.us` →
   000; `adcog.maps.arcgis.com` / `hidalgocounty.maps.arcgis.com` → 404.
5. **Row-level reads** on every family-adjacent survivor:
   `Residential_Building_Permits` (all 7 layers, watermark via
   `Finaled_Da` DESC), `SubstandardVacantHousing` (empty), and
   `Fire_Department_Calls_WFL1` (all layers — no date-bearing column).
6. **City-site portal probes**: `www.mcallen.net` 200. Permits nav →
   `onlinepermits.mcallen.net/Portal/default.aspx` (Accela ACA; ACA
   cookies). Probe of every plausible Accela REST/record-search path →
   404/302. `aca.accela.com/mcallen` → 301 → `aca-prod.accela.com/mcallen`
   → **404**. 311 → `mcallen.net/departments/311/request` (city form) +
   `mcallen.go2gov.net` (CivicPlus, Cloudflare, SPA "Loading..."), no bulk
   API. OpenGov `mcallen-tx.portal.opengov.com` → generic dashboard shell,
   no city data.

Limits: `mcallen-tx.opendata.arcgis.com` Hub items are **private (401)** so
the Hub's own dataset catalog cannot be enumerated — the AGOL public search
+ service-directory walk is the authoritative standing-in, and it is
thorough. Accela ACA is an interactive ASP.NET portal; only its public
HTML/redirect surface was probed (REST paths 404'd), so the permits channel
is confirmed form-only without an auth-gated API sweep. CivicPlus go2gov is
a JS SPA; no JSON endpoint surface was confirmed.

---

## Headline table

| Family | Endpoint | Newest row (watermark) | Geocoding | Recent window | Tier |
|---|---|---|---|---|---|
| **PERMITS** | Accela ACA portal (`onlinepermits.mcallen.net/Portal/default.aspx`) — **interactive, no bulk API**; `aca-prod.accela.com/mcallen` → 404. AGOL `Residential_Building_Permits` (`services3.arcgis.com/feieT9DHJD3rMLX7/.../Residential_Building_Permits/FeatureServer`) — 7 yearly layers (`Log_In_2015`…`Log_In_2020`, layer 6 = 516 rows) | `Finaled_Da` max = **2020-12-31** (layer 6 `Log_In_2020`); layer 0 `Log_In_2015` has **no date field**; one anomalous row `2028-01-28` = data-entry error (permit `RES2019-5616`) | native Points (State Plane 2277 TX South Central; `X=1074219.13, Y=16642770.85`), plus geocoder output fields — but grain is a **geocoded address log** (`Field1`/`Field2`/`Contractor`/`Finaled_Da`/`Clerk`), no permit number / valuation / status / type | 60d **0** (capped 2020-12-31 → 2026-08-30 = **~5.7 years stale**) | **3** |
| **311** | City-site request form (`mcallen.net/departments/311/request`) + CivicPlus go2gov — both **interactive intake**; no service-request layer in AGOL org (~250 services) or any public Hub | n/a | n/a | n/a | **3** |
| **SLA** | No municipal license registry (AGOL sweep: `Code_ZonesCounts` is a zoning boundary layer, not a license stream) | n/a | n/a | n/a | **3** — use TX state super-feeds (TDLR `7358-krk7`, TREC `s7ft-44qi`, TABC `7hf9-qc9f`) filterable to **Hidalgo 48215** as SLA companion only |
| **DEEDS** | Hidalgo CAD (`hidalgoad.org`) — **annual appraisal rolls / parcel polygons**, not transactional recorded-sales; no sales/deed FeatureServer in AGOL or Hub | n/a | n/a | n/a | **3** |

**Keep or reject: REJECT for municipal leaf — all four families Tier 3.**

---

## Portal inventory

| Surface | What it is | Feed? |
|---|---|---|
| `data.texas.gov` (Socrata state) | State open-data super-feed | State TDLR/TREC/TABC SLA only (county-filterable to Hidalgo 48215); no McAllen/Hidalgo municipal permits/311/deeds |
| `api.us.socrata.com/...?domains=mcallen-tx.opendata.arcgis.com` | Socrata discovery for the McAllen Hub host | **Domain not found** — not Socrata |
| `mcallen-tx.opendata.arcgis.com` (+ `mcallen` / `mcallen_tx` / `cityofmcallen` variants) | ArcGIS Hub | **Private (401)** / DCAT 404 — no enumerable dataset catalog |
| `services3.arcgis.com/feieT9DHJD3rMLX7/arcgis/rest/services` | City AGOL org service directory (~250 services) | **Utility / Survey123 / infrastructure only**; one family-adjacent layer (Residential_Building_Permits) is a 2020-capped geocode log |
| `roymartinez_mcallen` AGOL org | City AGOL owner (184 items) | Same — no permits/311/license/sales stream |
| `gis.mcallen.net` / `maps.mcallen.net` | City ArcGIS Server | **DNS-dead (000)** |
| `onlinepermits.mcallen.net/Portal/default.aspx` | **Accela ACA** permit portal (`aca.accela.com/mcallen` → 301 → `aca-prod.accela.com/mcallen` → 404) | Interactive only — no bulk API (REST/Records/Search paths 404/302) |
| `www.mcallen.net/departments/311/request` + `mcallen.go2gov.net` | **CivicPlus go2gov** citizen request portal + city form | Interactive intake UI only — no bulk API |
| `mcallen-tx.portal.opengov.com` | OpenGov | Generic dashboard shell — no city data |
| `hidalgoad.org` | Hidalgo Central Appraisal District | Annual appraisal rolls / parcel polygons — no transactional deeds |
| `gis.hidalgocounty.us` / `adcog.maps.arcgis.com` | County GIS | **DNS-dead / 404** |

---

## Per-family findings

### Permits — Tier 3

- **Accela ACA** is the live permitting system at
  `onlinepermits.mcallen.net/Portal/default.aspx` (ACA cookies confirmed:
  `ACA_SS_STORE`, `ACA_USER_PREFERRED_CULTURE`). `aca.accela.com/mcallen`
  issues 301 → `aca-prod.accela.com/mcallen` → **404**. Every plausible
  bulk path (`Portal/RECORDSEARCH`, `Records/Search`,
  `Portal/api/v2/records`, `Portal/REST`, `REST/v4/records`,
  `aca-prod.accela.com/mcallen/Records`) → 404 or 302. The permits channel is
  a form, matching the Tyler/EnerGov + internal-systems DEFER in the
  Southwest sweep — **no public bulk stream**.
- **AGOL `Residential_Building_Permits`** (item `8bbcf290d77b4aec85c499c73c8d8d32`
  style; service host `services3.arcgis.com/feieT9DHJD3rMLX7`): 7 layers,
  `Log_In_2015` (layer 0) through `Log_In_2020` (layer 6). Layer 6 (516
  rows) fields: `Permit__` (e.g. `RES2019-`, `RES2020-`), `Field2` (permit
  sequence), `Contractor`, `Address`, `Finaled_Da` (ms epoch). Watermark
  `Finaled_Da` max = **2020-12-31**; the single `2028-01-28` row
  (`RES2019-5616`) is a keyed-in date error, not a live row. Grain is a
  **geocoded address-point log** — no permit number, no valuation, no
  status, no work type; and it is **~5.7 years stale** (0 rows in the last
  30/60 days). Do not register.
- **County feed**: `data.texas.gov` `q=mcallen` / `q=hidalgo` / `q=hidalgo
  building permits` → no relevant dataset. No bulk county permit endpoint
  reachable.

### 311 — Tier 3 (none)

- City nav → `mcallen.net/departments/311/request` is a **city-hosted form**
  (`window.dataLayer`/GTM/Clarity only — no API backend surfaced) plus
  `mcallen.go2gov.net` (CivicPlus, Cloudflare, SPA). Neither exposes a bulk
  service-request feed.
- AGOL org (~250 services) contains **no service-request layer**. The
  nearest thing, `Fire_Department_Calls_WFL1` (layers `745 - Alarm System
  Activation` … `111 - Structure Fire`, plus `Sheet1_Geocoded`), is a
  fire-call **address-point geocode log** with a World geocoder geometry and
  a free-text `USER_F111`/`IN_SingleLine` carrier — **no date field and no
  civic 311 taxonomy**; it is not a registrable 311 feed.
- `SubstandardVacantHousing` → **0 rows** (empty layer).

### SLA / business licenses — Tier 3 (none municipal)

- No municipal license dataset in the AGOL sweep. `Code_ZonesCounts`,
  `Districts`, `CUP_REZ_ZBOA_MapInfo` are zoning/boundary layers, not
  issuance streams.
- State companion (verified live 2026-08-30): **TDLR** `7358-krk7`
  (`business_county`), **TREC** `s7ft-44qi` (`county`), **TABC** `7hf9-qc9f`
  — all HTTP 200, county-filterable to **Hidalgo (48215)** via `SocrataClient`
  (already owns `data.texas.gov` SoQL). Recommended SLA ingestion path for
  the RGV — but it is a state super-feed, **not** a McAllen municipal leaf.

### Deeds / sales — Tier 3 (none)

- Hidalgo Central Appraisal District (`hidalgoad.org`, HTTP 200) publishes
  annual assessment rolls and parcel polygons — no transactional
  recorded-sales/deed feed.
- No sales/deed FeatureServer in the city AGOL org, in the Hub, or on a
  reachable county GIS host. `palmviewtx` `HCAD Palmview Parcels Official`
  (AGOL) is a parcel-polygon layer, not a sales stream. Matches the
  Hidalgo/Cameron CAD-roll **Tier 3 DEFER** stance in both prior sweeps.

---

## Hosts probed and rejected

| Host | Result |
|---|---|
| `data.texas.gov` (state Socrata) | Live — state super feeds only; no McAllen/Hidalgo municipal permits/311/deeds |
| `api.us.socrata.com/...?domains=mcallen-tx.opendata.arcgis.com` | **Domain not found** — not Socrata |
| `mcallen-tx.opendata.arcgis.com` (+ 3 variants) | Hub 200 shell, catalog **401 private**, DCAT 404 |
| `services3.arcgis.com/feieT9DHJD3rMLX7/arcgis/rest/services` | City AGOL org (~250 services) — utility/Survey123/infrastructure |
| `roymartinez_mcallen` AGOL owner | 184 items — no family stream |
| `Residential_Building_Permits` (FeatureServer, layers 0–6) | **Geocode log capped 2020-12-31**, wrong grain, stale |
| `SubstandardVacantHousing` | 0 rows |
| `Fire_Department_Calls_WFL1` (FeatureServer, layers 0–9) | Fire-call address-points, no date field — not a 311 civic feed |
| `gis.mcallen.net` / `maps.mcallen.net` / `gismaps.mcallen.net` | DNS-dead (000) |
| `mcallen.maps.arcgis.com` / `mcallen-tx.maps.arcgis.com` | 404 |
| `onlinepermits.mcallen.net/Portal/default.aspx` | Accela ACA — interactive; REST/Records/Search = 404/302 |
| `aca.accela.com/mcallen` / `aca-prod.accela.com/mcallen` | 301 → **404** (wrong environment path) |
| `mcallen.go2gov.net` | CivicPlus SPA — form-only |
| `mcallen-tx.portal.opengov.com` | OpenGov dashboard shell — no city data |
| `hidalgoad.org` | CAD annual rolls only |
| `gis.hidalgocounty.us` / `mc-gis.hidalgocounty.us` / `adcog.maps.arcgis.com` / `hidalgocounty.maps.arcgis.com` | DNS-dead / 404 |

---

## Recommendation

**REJECT McAllen, TX (`mcallen`, Hidalgo County 48215) for municipal leaf
registration — Tier 3 across all four families.** No public bulk REST
endpoint satisfies ADR 0004's row-level watermark + geocode requirements.
The McAllen Hub is private, there is no city Socrata/CKAN, the city AGOL
org is utility infrastructure, the only permit-adjacent layer is a
2020-capped geocode log, and both public transaction channels (Accela ACA
permits, CivicPlus go2gov 311) are interactive forms. County deeds remain
HCAD annual appraisal rolls.

The higher-leverage move — matching the RGV/Hidalgo **Tier 3 DEFER** and the
Corpus Christi municipal-Tier-3 stance — is to treat the metro as a
**state-feed-only county** via the existing `SocrataClient` on
`data.texas.gov` (`7358-krk7` TDLR, `s7ft-44qi` TREC, `7hf9-qc9f` TABC)
filtered to **Hidalgo 48215**, with no new city leaf. Re-probe trigger: an
Accela ACA public data-extract export, a public Hub dataset catalog, or the
AGOL org adding a current-year permit/311 service-request layer with a live
watermark.

No leaf files created (Tier 3 only): no `spatial/cities/mcallen.py`, no
`field_maps_mcallen.py`, no `test_producers_mcallen.py`. No spine edits, no
git commit, no Linear state change. Stamp: 2026-08-30.
