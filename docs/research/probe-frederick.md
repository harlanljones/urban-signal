# Wave 3 Phase-0 probe — Frederick, MD

**Date of probe: 2026-08-27.** Ticket US-315. Row-level standard applied where
any anonymous feed existed; none of the four families yielded one.

## Headline verdict

**T3 — no registerable feed in any family. REJECT / defer.** The ticket hint
(`frederickmd.opendata.arcgis.com`) is a **private ArcGIS Hub placeholder**
(401). The city runs permits on **OpenGov ViewPoint** (token/Auth0-gated
APIs, Ember SPA — UI only). The county AGOL org (`*_fcgmd`, ~300 items) is
reference GIS only. The county parcel layer is a live-maintained ownership
snapshot but carries **no sale date/price** — not a deeds stream.

| Family | Tier | Newest row (watermark) | Geocoding | Recent window | Tier |
|---|---|---|---|---|---|
| PERMITS | ViewPoint UI only | n/a | n/a | n/a | **3** |
| 311 | none queryable | n/a | n/a | n/a | **3** |
| SLA/licenses | none queryable | n/a | n/a | n/a | **3** |
| DEEDS/sales | parcel snapshot, no sale fields | n/a (usable) | n/a | n/a | **3** |

## Platform

Resolved: **OpenGov ViewPoint (citizen portal) + Frederick County AGOL /
ArcGIS Server (`fcgis.frederickcountymd.gov/server_pub`). No open-data
catalog.**

| Surface probed | Result |
|---|---|
| `frederickmd.opendata.arcgis.com` Hub search/DCAT | **401** `private org id … not accessible`; DCAT **404** |
| Socrata discovery (`frederickmd.opendata.arcgis.com`, `cityoffrederickmd.gov`, `frederickcountymd.gov`) | `Domain not found` ×3 |
| `data./gis./maps. cityoffrederickmd.gov`, `data.frederickmd.gov`, `opendata.frederickcountymd.gov` | **DNS fail** |
| `frederickcountymd.opendata.arcgis.com` | 200 generic Hub chrome; `/api/search/v1` **401** (private org) |
| AGOL `owner:gis_enterprise_fcgmd` | 207 items — parcels, streets, zoning, schools, service areas; **no permits/311/licenses/sales** |
| `frederickmd.portal.opengov.com` | ViewPoint SPA. APIs: `api-east.viewpointcloud.com/v2` (Auth0), `records.viewpointcloud.com/graphql` (token). `/api/*` returns the SPA shell. **UI only.** |
| `fcgis.frederickcountymd.gov/server_pub/rest/services/Basemap/Parcels/MapServer/0` | anonymous, live (`LAST_UPDATE` max **2026-08-18**), 48 fields incl. `Book`/`Page`/`BOOKPAGE` — **no sale date, no sale price** |
| `www.frederickcountymd.gov/311` | CivicPlus CMS page; no data links |
| `www.cityoffrederickmd.gov` permits pages | Application PDFs + ViewPoint portal links |
| AGOL `"Frederick County" AND "service request"` | **0 results** |

## Method, and its limits

1. Hub DCAT + Hub-search + Socrata discovery fingerprint on hint and
   conventional hosts (city and county).
2. AGOL item enumeration for the county org (`gis_enterprise_fcgmd`,
   `AWilliams@…_fcgmd`) and keyword searches for permits / service
   requests / licenses / sales.
3. Row-level `outStatistics` max on the parcel layer (the only anonymous
   survivor).
4. OpenGov portal JS config read to enumerate its backend APIs.

Limits: ViewPoint record search is public in the browser but rendered
client-side against token-gated GraphQL; scraping an account-free SPA was
not attempted (UI-only rule, Memphis Accela precedent). City of Frederick
business licenses run through ViewPoint too (same UI-only verdict). MD
SDAT / MDLANDREC deed search is a state UI, not a stream.

## Decision

**Do not register.** All four families Tier 3. Re-probe if Frederick
publishes the ViewPoint public-records API anonymously or the county Hub
org goes public.
Stamp: 2026-08-27.
