# Wave 3 Phase-0 probe — Dover, DE

**Date of probe: 2026-08-27.** Ticket US-317. Hosts read live that day.

## Headline verdict

**T3 — no transactional feed in any family. REJECT / defer.** The ticket
hint (`doverde.opendata.arcgis.com`) resolves to a **public Hub with ~11
items, all reference layers** (boundary, parking, truck routes, road
closures, restrooms). The real city GIS server (`gis.dover.de.us`, ~75
services) is **asset/reference GIS only** — hydrants, trees, light poles,
zoning, election districts. No permits, 311, licenses, or deeds/sales
anywhere; permitting is paper/PDF.

| Family | Tier | Newest row (watermark) | Geocoding | Recent window | Tier |
|---|---|---|---|---|---|
| PERMITS | paper/PDF only | n/a | n/a | n/a | **3** |
| 311 | none (`Crowdsource_Road_Problems` FeatureServer: **0 layers**) | n/a | n/a | n/a | **3** |
| SLA/licenses | none | n/a | n/a | n/a | **3** |
| DEEDS/sales | none | n/a | n/a | n/a | **3** |

## Platform

Resolved: **ArcGIS Hub (tiny) + on-prem ArcGIS Server** at
`gis.dover.de.us/arcgis/rest/services`. Not Socrata, not CKAN.

| Surface probed | Result |
|---|---|
| `doverde.opendata.arcgis.com` Hub OGC search | Public; **11 items**, `source: City of Dover Delaware` — boundary, parking, truck routes, road closure, restrooms, holiday activities, two survey forms; zero family datasets (`q=permit` → 1 MS4 training quiz form; `q=license`/`q=sales`/`q=deed` → **0**) |
| `gis.dover.de.us/arcgis/rest/services` | ~75 services (ADA_Compliance, Asset_Collection2, Electric_GPS, FM_Assets, Hydrants_Editing, Light_Pole_Collection, Storm/Water/Sanitary_Editing, Tree_Inventory, Vacant_Buildings, Zoning, …) — **no permits/311/licenses/sales** |
| `Crowdsource_Road_Problems/FeatureServer` | **0 layers** (dead crowdsource shell) |
| Socrata discovery `domains=doverde.opendata.arcgis.com` | `Domain not found` |
| Statewide Socrata `data.delaware.gov` `q="dover permit"` | 0 rows |
| FirstMap `opendata.firstmap.delaware.gov` Hub API | **401 Unauthorized** |
| `data.dover.de.gov`, `gis.dover.de.gov`, `data/gis.cityofdover.com` | DNS fail |
| `www.cityofdover.com` | Permit **PDF applications** (Public Works ROW, WCF), parking/boat permit pages — no online permit portal, no open-data link |

## Method, and its limits

1. Hub OGC collections search scoped to the Dover org + family keywords.
2. Full services-folder listing on the discovered `gis.dover.de.us` host
   (the ticket hint never names it; found via the Crowdsource Road Problems
   AGOL item URL).
3. Statewide Socrata catalog query; FirstMap Hub fingerprint.
4. City-site crawl for permit/license portals.

Limits: FirstMap (the DE statewide Hub) denies anonymous API reads (401), so
a Dover-tagged statewide dataset behind FirstMap could not be row-checked —
but FirstMap carries *state* reference layers, not city permit/311 streams.
No iWorQ/CitizenServe-style hosted portal surfaced on the city site.

## Decision

**Do not register.** All four families Tier 3 — no portal, wrong grain
everywhere. Re-probe only if Dover stands up an open-data portal or migrates
permitting online.
Stamp: 2026-08-27.
