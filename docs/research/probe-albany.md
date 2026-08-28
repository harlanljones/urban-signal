# Wave 3 Phase-0 probe — Albany, NY

**Date of probe: 2026-08-27.** Ticket US-353. The ticket hints only at
"municipal GIS"; surfaces below were discovered and read live that day.

## Headline verdict

**T3 — no transactional feed in any family. REJECT / defer.** Albany's GIS
footprint is a **private ArcGIS Hub org** (`albanyny.opendata.arcgis.com` →
401) whose public data actually lives as **53 reference feature services**
under the city's GIS account (`mmillus` / org
`services6.arcgis.com/JJzptGyn7EDStgyp`) and the Hub site
`city-albanyny-gis.hub.arcgis.com` — zoning, parcels, parks, trails,
parking, wards. No permits, no 311 CRM, no licenses, no sale-attribute
stream. The RPS parcel layer carries deed book/page **pointers** but no
sale date or price.

| Family | Tier | Newest row (watermark) | Geocoding | Recent window | Tier |
|---|---|---|---|---|---|
| PERMITS | none | n/a | n/a | n/a | **3** |
| 311 | SeeClickFix-style export, **no date field** | n/a (no watermark column) | native Lat/Lng | unverifiable | **3** |
| SLA/licenses | none | n/a | n/a | n/a | **3** |
| DEEDS/sales | RPS parcel snapshot, no sale fields | `Roll_Year` = **2023** (29,465 rows) | points + addresses | frozen 2023 roll | **3** |

## Platform

Resolved: **ArcGIS Online public items + private Hub shell.** Not Socrata
(`Domain not found` for `data.albany.ny.us`, `data.albany.ny.gov`,
`albanyny.gov`). Not CKAN. No ArcGIS Server host found
(`gis./maps.albany.ny.us` DNS fail; `data.albany.gov`,
`opendata.albanyny.gov` DNS fail).

| Surface probed | Result |
|---|---|
| `albanyny.opendata.arcgis.com` | HTML chrome 200; Hub search **401** `private org id … not accessible`; OGC search empty |
| `city-albanyny-gis.hub.arcgis.com` OGC search | **0 items** (site index private/empty) |
| AGOL `owner:mmillus` Feature Services | 53 items — all reference (Zoning, Tax Parcels, Parks, Trails, Parking Signs, Metered Zones, Code Inspection **Zones**, Wards, Street Lights, Bike/Ped plans) |
| `TaxParcelsWithRPS/FeatureServer/0` | 29,465 points, `Roll_Year` **2023** only; `Deed_Reference(_Book/_Page)` present; **no `SALE_DATE`, no `SALE_PRICE`** |
| `Quality_of_Life_Hot_Spots/FeatureServer/0` | SCF-style crowdsource export (`Id`, `Status`, `Summary`, `Address`, `Lat`, `Lng`, `Export_tagged_places`); newest Id ~17.8M (~2022 SCF range); **no date column — no watermark to verify** |
| Socrata discovery (3 candidate domains) | `Domain not found` ×3 |
| City site `www.albanyny.gov` | no open-data / GIS data links |
| AGOL `"Albany" AND NY AND permit` | only zoning/parking/wetland reference layers from other orgs |

## Method, and its limits

1. Socrata/Hub/CKAN fingerprints on conventional hosts.
2. AGOL item enumeration via the GIS owner account and Hub-site item
   (`mmillus`, 53 Feature Services), title sweep for the four families.
3. Row-level reads on the two transactional-adjacent survivors (RPS
   parcels, QoL Hot Spots).
4. City-site crawl for permit portals.

Limits: the private Hub org may hold unshared items invisible to the API;
the QoL Hot Spots layer has no timestamp field, so its freshness could not
be row-verified (its SCF-provenance Id range and the `Export_tagged_places`
column mark it as a SeeClickFix export — third-party intake, not a
municipal CRM extract, per the Albuquerque/Phoenix stance). No NYS
statewide feed was treated as an Albany substitute.

## Decision

**Do not register.** All four families Tier 3. Re-probe if the city
publishes the Hub org, stands up a permit/311 extract, or the county
(Hudson Valley/A Albany clerk) deed stream ever lands as a city-grain
open feed.
Stamp: 2026-08-27.
