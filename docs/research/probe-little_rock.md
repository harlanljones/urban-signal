# Wave 3 Phase-0 probe — Little Rock, AR

**Date of probe: 2026-08-28 (UTC).** Hub catalog enumeration, AGOL org
sweep, internal ArcGIS Server folder walks, and row-level reads on every
public survivor.

Linear: **US-346**. Ticket hint: Socrata + ArcGIS (`data.littlerock.gov`).

**Verdict: NO REGISTER (all four families Tier 3).** There is **no
Socrata** — `data.littlerock.gov` is a redirect to a WordPress page on
`littlerock.gov`. The city's real surfaces are an ArcGIS Hub (138 items,
reference layers and case files) and an internal ArcGIS Server 10.71.
The one interesting family-adjacent dataset — a city **Short-Term Rental
license registry** with native points — has a stale approval watermark
(newest 2026-06-08, 0 in the last 60 days).

---

## Method, and its limits

1. Socrata discovery `domains=data.littlerock.gov` → **Domain not
   found**; `data.littlerock.gov` redirects to
   `littlerock.gov/government/mayors-office/initiatives/city-of-lr-data/`
   (no feeds behind it).
2. Hub fingerprint: `littlerock.opendata.arcgis.com` public (the
   `data-littlerock` and `little-rock` placeholders 401). v3 catalog
   pagination → 138 items read; keyword sweeps for permit / 311 /
   service request / license / sale / deed / business.
3. AGOL org sweep: city owners `kpruett_littlerock` (386) and
   `mmahar_littlerock` (172); `BPADDLR` item resolved and read
   row-level (it is an address-point layer, not permits).
4. Internal server: `maps.littlerock.gov/server/rest/services`
   (ArcGIS Server 10.71 — GeoData, Hosted: Sanborn scans, surveys,
   wards). City 311 page 403s generic scrapers; the 311 platform
   surfaced from the city site nav: **Motorola CWI**
   (`littlerock-cwiprod.motorolasolutions.com/cwi/select`).
5. County: Pulaski `gis.pagis.org` REST walk (basemaps, locators,
   GeoDataServer; no sales); `pulaskico.opendata.arcgis.com` Hub
   private (401).

Limits: city web pages block non-browser UAs (403), so the 311
platform was identified from nav links, not a full page read; a
deeper Motorola CWI API audit was out of scope (it is an intake UI,
matching prior T3 stances).

---

## Headline table

| Family | Endpoint | Newest row (watermark) | Geocoding | Recent window | Tier |
|---|---|---|---|---|---|
| **PERMITS** | none. `BPADDLR` / `BPADD` (AGOL `services.arcgis.com/ae4pGnJE2BadeaiV`) are building-permit-derived **address points** (fields `BPADD_UNIQ`, `BP_CODE`, `VER_DATE`) — wrong grain, no permit number/valuation/status | n/a | n/a | n/a | **3** |
| **311** | Motorola CWI citizen portal (`littlerock-cwiprod.motorolasolutions.com/cwi/select`) — intake UI only; no public service-request layer in Hub (138 items) or AGOL org | n/a | n/a | n/a | **3** |
| **SLA** | `Short_Term_Rentals_(Public_View)/FeatureServer/2` (`STR_List_2026_02_02_26`) — 169 rows, point geometry | `APPROVAL_DATE` newest **2026-06-08** (STR-2 docketed); 2026 approvals **18**; 2025: 13; 2024: 86; **0 in last 60 days**; layer data last edited 2026-08-03 | native points (`outSR=4326` confirmed −92.31, 34.76) + `ADDRESS` | 60d **0** | **3** (stale watermark; see note) |
| **DEEDS** | none. PAgis has no sales layer; Pulaski Hub private | n/a | n/a | n/a | **3** |

**SLA note:** the STR registry is *maintained* (status churn through
2026-08-03) and natively geocoded, but the approval watermark is 11
weeks old at probe time and approval cadence is ~1.5/month — too weak
for the move-in/move-out flow signal. Re-probe trigger: approvals
resuming (≥1 in 60 days) would make this a Tier-1 SLA companion
(Orlando STR precedent).

**Keep or reject: needs-triage / defer.**

---

## Portal inventory

| Surface | What it is | Feed? |
|---|---|---|
| `data.littlerock.gov` | Redirect to WordPress "City of LR Data" page | no feeds |
| `littlerock.opendata.arcgis.com` | ArcGIS Hub, 138 items (HDC cases, code violations, STR registry, parks, surveys) | STR registry only (stale) |
| AGOL org `*_littlerock` | ~558 items incl. `BPADDLR` address points | wrong grain |
| `maps.littlerock.gov/server/rest` | ArcGIS Server 10.71 (basemaps, Sanborn, surveys) | no family feeds |
| `littlerock-cwiprod.motorolasolutions.com/cwi/select` | Motorola CWI citizen request portal | UI only |
| `gis.pagis.org` | Pulaski County ArcGIS Server (basemaps/locators) | no sales/deeds |
| `pulaskico.opendata.arcgis.com` | County Hub | private (401) |
| Socrata / CKAN | none | no |

---

## Decision

**Do not register Little Rock as a Wave-3 metro.** All four families
Tier 3. The STR license registry is the one live-maintained surface and
should be re-checked at the next wave; it needs approval flow to be
registrable. Stamp: 2026-08-28.
