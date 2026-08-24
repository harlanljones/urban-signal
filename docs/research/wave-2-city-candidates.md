# Wave-2 city candidates — survey beyond the 17 registered metros

**Date of survey: 2026-08-24.** Every endpoint below was probed live that day:
Socrata discovery + `/resource/<id>.json` reads, ArcGIS Hub v3 dataset search,
and direct FeatureServer `query` calls. "Newest row" means a row actually read
back ordered by its watermark descending — not a catalog `modified` timestamp.
Re-probe before acting on this (`city-expansion-candidates.md` states why).

Baseline at survey time, measured from the executable registry:
**17 cities, 55 feeds** — socrata 34, arcgis 14, carto 4, ckan 3.

## Method, and its limits

1. **Socrata membership** — 48 candidate domains queried against
   `api.us.socrata.com/api/catalog/v1?domains=<d>`; a nonzero `resultSetSize`
   proves the domain is in the discovery mesh.
2. **Feed families** — one query per family (`building permits`,
   `311 service requests`, `business licenses`, `property sales`) per surviving
   domain, top 3 hits each.
3. **ArcGIS Hub** — `<site>/api/search/v1/collections/dataset/items?q=…`, then
   item → FeatureServer URL, then layer metadata (`?f=json`) and a
   newest-row `query` with `orderByFields=<watermark> DESC`.
4. **Row-level verification** — column list, geocoding fields, newest watermark
   value, and a recent-window `count` for every candidate that survived step 3.

Limits, stated plainly:

- One query per family per domain, so "none found" is a weak negative — the
  Kansas City lesson below is this survey's own proof of that.
- Hub `modified` is item metadata and repeatedly disagreed with row reality in
  both directions. Only the newest-row reads in the tables below are evidence.
- Nine large metros were **not resolved to a platform** this pass (see
  [Unresolved](#unresolved-platform-not-identified)). Their absence here is a
  gap in the survey, not a finding about the cities.

## Headline findings

1. **The binding constraint is no longer platform clients — it is geocoding.**
   Four clients (socrata, arcgis, carto, ckan) covered every candidate found.
   No new client is required by anything in this document. What repeatedly
   failed was the *spatial* contract: address-only or non-spatial feeds.
2. **Kansas City is not dead.** The 2026-08-23 survey concluded "effectively
   dead" from stale top hits. Its 311 feed under a different name is live and
   geocoded (816,428 rows, newest 2026-08-17).
3. **Prince George's County MD is the strongest new registration candidate**,
   and it completes a National Capital Region cluster with two already-
   registered neighbours (Washington DC, Montgomery County).
4. **Columbus and Nashville are ready-now permits cities** through the existing
   `ArcGISClient` — zero platform code, point geometry, valuation fields.

## Tier 1 — verified, ready to register

| City | Feed | Endpoint | Platform | Newest row | Geocoding | Volume |
|---|---|---|---|---|---|---|
| **Columbus, OH** | PERMITS | `services1.arcgis.com/9yy6msODkIBzkUXU/.../Building_Permits/FeatureServer/0` | arcgis | `ISSUED_DT` = 2026-08-20 | point geometry | 6,782 issued since 2026-07-01 |
| **Nashville, TN** | PERMITS | `services2.arcgis.com/HdTo6HJqh92wn4D8/.../Building_Permits_Issued_2/FeatureServer/0` | arcgis | `Date_Issued` = 2026-08-20 | `Lat`/`Lon` attrs + point | 1,270 issued since 2026-07-01 |
| **Prince George's Co., MD** | 311 | `data.princegeorgescountymd.gov/resource/2ywx-ipcd` | socrata | `date_request_opened` = 2026-07-17 | `latitude`/`longitude` | 444,109 rows |
| **Kansas City, MO** | 311 | `data.kcmo.org/resource/d4px-6rwg` | socrata | `open_date_time` = 2026-08-17 | `latitude`/`longitude`, `lat_long` | 816,428 rows |

Field detail worth pinning in tests:

- **Columbus** — Accela-derived schema: `ISSUED_DT`, `LAST_STATUS_DT`,
  `G3_VALUE_TTL` (valuation, `0` is common and legitimate), `SQFT`, `UNITS`,
  `SITE_ADDRESS`, `B1_PARCEL_NBR`. All-uppercase spellings, `maxRecordCount`
  2000. `B1_ALT_ID` is the permit identifier — `OBJECTID` must not reach the
  job-id chain.
- **Nashville** — `Date_Issued` + `Date_Entered` (two-date model), `Const_Cost`,
  `Lat`/`Lon` as plain attributes, `Council_Dist` and `Census_Tract` already
  present. `maxRecordCount` 1000. Mixed-case spellings (`Lat`, not `latitude`).
- **PG County 311** — 12 columns, `date_request_opened` is date-typed.
  **Cadence caveat:** newest row is 38 days old at survey. The catalog claims a
  2026-08-13 refresh, so this looks like monthly batch publishing, not a dead
  feed — but it **fails the 7-day staleness gate as published** and must be
  registered with a documented cadence exception or held.
- **KC 311** — `open_date_time` watermark, `resolved_date`, `last_updated`.
  Newest row 7 days old at survey; re-probe for cadence before committing.

## Tier 2 — real data, blocked on a capability

| City | Feed | Endpoint | Blocker |
|---|---|---|---|
| Prince George's Co., MD | DEEDS-class | `data.princegeorgescountymd.gov/resource/qzrv-2tnv` ("Property") | Parcel **snapshot**, not a transaction stream: 353,062 rows, one per parcel. Carries `the_geom`, `sales_price`, `transfer_date`, `updated_date`. 4,647 rows with `transfer_date` after 2026-06-01. **`transfer_date` is a text column containing the sentinel `ZZZZZZZZ`**, which sorts above every real date — a naive `ORDER BY … DESC` watermark returns garbage. Needs snapshot ingestion (D4) **plus** text-watermark normalization. |
| Honolulu, HI | 311 | `data.honolulu.gov/resource/jdy7-ftwe` | Live (2026-08-23) but **9 columns and no coordinate field of any kind**. Fails the spatial contract outright. |
| Honolulu, HI | PERMITS | `data.honolulu.gov/resource/4vab-c87q` | 60 columns, rich date model (`issuedate`, `createddate`, `coissued`, `finalcoissued`) but address-only (`joblocation`). Title covers through 2025-06-30 — verify it is not a closed archive. Geocoding required. |
| Orlando, FL | SLA | `7388-4re5` Business Tax Receipts; `ssrj-rbua` STR Licenses | Both refreshed 2026-08-23 — genuinely live. Address-only, no coordinates. Geocoding required. STR feed is also a **new signal type** (investor-buyout pressure), not just an SLA. |
| Oakland, CA | 311 | `data.oaklandca.gov/resource/quth-gb8e` | Live 2026-08-23, but no coordinate fields. Also a **geography conflict**: Oakland is already the EAST_BAY division of the registered `san_francisco` metro, so this is division-level data, not a new registration (shape 1 vs shape 2, `metro-expansion-and-new-signals.md` §1). |
| Kansas City, MO | SLA | `data.kcmo.org/resource/pnm4-68wg` | `location` field only, and **no date column at all** — no watermark, no snapshot diff key worth trusting. Reject unless re-probed. |

**Seven of these blockers are the same blocker.** See the geocoding argument
below; it is the highest-leverage finding in this survey.

## Tier 3 — weak, stale, or rejected

| City | Verdict | Evidence |
|---|---|---|
| Kansas City, MO — permits | Dead, confirming prior survey | Newest permit listings 2019–2023; the live hits are annual archive tables |
| Sacramento, CA | Hold | Hub carries "Issued Building Permits Current Year" but item metadata is 2024-03-25 and 311 slices stop at 2016. Needs a row-level probe before any verdict |
| Portland, OR | Weak | Only "Residential Demolition Permits" is current (2026-08-22); the main residential permits item last moved 2023-08-31 |
| Charlotte, NC | Unresolved | 347-dataset Hub, but the family queries returned only zoning/floodplain layers. Search quality problem, not a proven absence — needs targeted probing |
| Tampa, FL | Weak | Best hit is "Construction Inspections" (2024-12-18) |
| Providence, RI · Richmond, VA · Fort Worth, TX · Miami, FL | Reject on this evidence | All four Socrata catalogs answer, but every feed-family hit is 2020–2025 stale. Miami's permits item last moved 2022-06-01 |
| Buffalo, NY · Mesa, AZ | Reject | Socrata catalogs answer (106 / 41 datasets); zero hits on all four families |
| Cambridge, MA · Bloomington, IN | Not applicable | Cambridge is already an alias of the registered `boston` metro |

## Unresolved — platform not identified

These metros were probed for Socrata membership (negative) and had at least one
Hub hostname guess fail. **No conclusion should be drawn about them from this
document**; they are the largest remaining blind spot and several are top-10 US
cities by population.

| Metro | What happened |
|---|---|
| **Houston, TX** | `cohgis-mycity.opendata.arcgis.com` answered the Hub API with **0 datasets** — wrong site, correct host pattern unknown |
| **Phoenix, AZ** | `phoenixopendata.com` — 404 on Hub API (likely CKAN or a custom portal) |
| **San Antonio, TX** | `data.sanantonio.gov` — 404 on Hub API |
| **San Jose, CA** | `data.sanjoseca.gov` — 404 on Hub API |
| **Atlanta, GA** | `opendata.atlantaga.gov` — TLS certificate verification failure |
| **Indianapolis, IN** | `data.indy.gov` — 404 on Hub API |
| **Jacksonville, FL** | `opendata.coj.net` — DNS does not resolve |
| **Milwaukee, WI** | `data.milwaukee.gov` — 404 on Hub API |
| **Las Vegas, NV** | `opendata.lasvegasnevada.gov` — DNS does not resolve |

## The geocoding argument

Counting only feeds already identified and verified as carrying real, current
data, blocked solely on the absence of an address → coordinate capability:

| City | Feeds blocked | Source |
|---|---|---|
| Norfolk (registered) | 311 `nbyu-xjez`, SLA `dpi6-sct5` | deferred at registration |
| Washington DC (registered) | SLA basic business licenses, DEEDS CAMA sales | non-spatial tables |
| Denver (registered) | SLA active licenses, DEEDS sales/transfers | `PARID`/address keys only |
| Montgomery Co. (registered) | MC311 `xtyh-brr2` | zip-only, excluded by construction |
| Honolulu (candidate) | 311, PERMITS | address-only |
| Orlando (candidate) | SLA ×2 | address-only |
| Oakland (division of SF) | 311 | no coordinates |

**Eleven feeds, seven of them inside cities that are already registered.** A
geocoding capability would add more live feeds to the product than the four
Tier-1 city registrations in this document combined — and it would do so
without adding a single new metro to hand-author, a new bbox to maintain, or a
new city to calibrate models for.

That is the recommendation this survey ends on: **build geocoding before
building Wave 2**, then register Columbus, Nashville, PG County and Kansas City
into a pipeline that can actually consume their weaker feeds too.
