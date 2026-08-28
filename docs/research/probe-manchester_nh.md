# Wave 3 Phase-0 probe — Manchester, NH

**Date of probe: 2026-08-27.** Ticket US-313. All findings below were read
live that day; "newest row" reads (not catalog dates) would be the evidence
standard, but no queryable municipal feed surfaced at all.

## Headline verdict

**T3 — no public open-data portal. REJECT / defer for all four families.**
The ticket hint (`manchesternh.opendata.arcgis.com`) is a **private, empty
ArcGIS Hub placeholder** — the same trap class as the Memphis sibling hosts.
No Socrata, no CKAN, no anonymous ArcGIS Server, no DNS for the usual
`data./gis./maps.` hosts.

| Family | Tier | Newest row (watermark) | Geocoding | Recent window | Tier |
|---|---|---|---|---|---|
| PERMITS | none queryable | n/a | n/a | n/a | **3** |
| 311 | none queryable | n/a | n/a | n/a | **3** |
| SLA/licenses | none queryable | n/a | n/a | n/a | **3** |
| DEEDS/sales | none queryable | n/a | n/a | n/a | **3** |

## Platform

Resolved: **none.** Negative fingerprint:

| Surface probed | Result |
|---|---|
| `manchesternh.opendata.arcgis.com/api/search/v1` | **401** `private org id for manchesternh.opendata.arcgis.com is not accessible` |
| `manchesternh.hub.arcgis.com/api/search/v1` | **401** same private-org error |
| `manchesternh.opendata.arcgis.com/api/feed/dcat-us/1.1.json` | **404** |
| Socrata discovery `domains=manchesternh.opendata.arcgis.com` | `Domain not found` |
| Socrata discovery `domains=manchesternh.gov` | `Domain not found` |
| `data.manchesternh.gov` / `gis.manchesternh.gov` / `maps.manchesternh.gov` | **DNS fail** (host does not exist) |
| `highwaymapsplans.manchesternh.gov` | IIS **login-gated** ASP.NET app (`Login.aspx` / `NewUser.aspx` WebForms); not an anonymous feed |
| AGOL `sharing/rest/search?q=manchesternh` | 1 result, an unrelated Image item |
| `www.civicdata.com` CKAN `package_search?q=manchester` | 200, **count 0** |
| `www.manchesternh.gov` | No open-data/GIS links; Fire "data" page = historical PDFs by decade |

## Method, and its limits

1. Socrata discovery + Hub DCAT/Hub-search fingerprint on the ticket hint.
2. DNS + REST probes on conventional city hostnames.
3. AGOL org/item search (`manchesternh`, `"Manchester NH" AND permits`).
4. CKAN `package_search` on Accela CivicData.
5. City-site crawl for open-data links (found none).

Limits: the login-gated plans/permits web app was not crawled behind
authentication (account-gated UI is not a registrable feed regardless). A
dataset published as an anonymous share *inside* the private Hub org cannot
be ruled out, but the Hub API rejects even catalog reads, so there is
nothing to register against. No statewide NH bulk feed was treated as a
Manchester substitute.

## Decision

**Do not register.** All four families Tier 3 — no portal, wrong grain
everywhere. Re-probe if the city ever publishes the Hub org publicly
(`manchesternh.opendata.arcgis.com` is reserved but private) or stands up a
`data.manchesternh.gov`.
Stamp: 2026-08-27.
