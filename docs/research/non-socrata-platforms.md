# Non-Socrata platforms: CKAN, ArcGIS Hub, Carto, and the stragglers

**Date of survey: 2026-08-23.** Every platform and dataset below was probed live on
that date (HTTP GETs against each portal's own API); "updated" is evidence observed
that day — a dataset's max date field, its catalog `metadata_modified`, or a fresh
row read back from the endpoint. Re-probe before acting on this.

## Method, and its limits

The prior survey (`city-expansion-candidates.md`) covered Socrata discovery only
and named two out-of-scope groups: a "CKAN trio" (Boston, Philadelphia, San Diego)
and an ArcGIS Hub group (Denver, DC, Minneapolis, Detroit), plus five Socrata
stragglers (Baltimore, Nashville, Louisville, Hartford, Tempe). This pass probed
all eleven domains plus Philadelphia's actual data host:

- CKAN sites were queried through `/api/3/action/package_search` and
  `datastore_search(_sql)` with sample rows read back for column lists.
- ArcGIS Hub sites were searched through their v3 dataset search API
  (`<site>/api/search/v1/collections/dataset/items?q=…`), then item IDs were
  resolved to FeatureServer URLs via the ArcGIS Online sharing REST API and layer
  metadata + newest rows fetched directly.
- Recency was established by reading the newest row (ordered by OID or date
  descending) or counting rows past a recent date cutoff — not by trusting
  catalog timestamps alone.

Limits: one query per feed family per site, so a city marked "none found" may
have a feed under a name the query missed (the prior survey's Kansas City lesson
applies doubly across platforms). Baltimore's liquor-licenses layer and
Louisville's permit layers were identified but not field-probed. Tempe's newest
permit row was confirmed by count only.

## The headline: the groupings in the old survey were wrong

Every assumption about which platform backs which city was checked and most were
false. **Only Boston is CKAN.** Philadelphia's data lives on **CARTO**
(`phl.carto.com/api/v2/sql` — OpenDataPhilly is just a catalog site). San Diego is
a custom static portal serving **daily CSV dumps** from S3, no API. And all five
Socrata stragglers have moved to **ArcGIS Hub**, as has Baltimore — so nine of
the eleven domains are now reachable with the existing `ArcGISClient`.

| City | Portal domain | Actual platform (verified) |
|---|---|---|
| Boston | data.boston.gov | CKAN (datastore-active) |
| Philadelphia | opendataphilly.org | Catalog only; data on CARTO SQL API |
| San Diego | data.sandiego.gov | Custom DCAT portal → static CSVs (seshat.datasd.org) |
| Denver | data.denvergov.org | ArcGIS Hub (redirects to opendata-geospatialdenver.hub.arcgis.com) |
| Washington DC | opendata.dc.gov | ArcGIS Hub over maps2.dcgis.dc.gov REST services |
| Minneapolis | opendata.minneapolismn.gov | ArcGIS Hub ("OpenDataMPLS") |
| Detroit | data.detroitmi.gov | ArcGIS Hub |
| Baltimore | data.baltimorecity.gov | ArcGIS Hub ("Open Baltimore") |
| Nashville | data.nashville.gov | ArcGIS Hub |
| Louisville | data.louisvilleky.gov | ArcGIS Hub |
| Hartford | data.hartford.gov | ArcGIS Hub |
| Tempe | data.tempe.gov | ArcGIS Hub |

No endpoint probed required a token or API key, including Hartford's
`utility.arcgis.com` premium-proxy service URLs, which answered anonymously.

## Per-city findings

### Philadelphia — CARTO — best non-Socrata candidate

OpenDataPhilly catalogs datasets hosted on the city's CARTO account. The SQL API
is Postgres-flavored: `GET /api/v2/sql?q=SELECT …`, server-side paging via
keyset predicates (`WHERE key > last ORDER BY key LIMIT n`). All four feed
families exist, are geocoded, and refreshed within days of the survey:

| Feed family | Dataset/table | Platform detail | Updated | Geocoding | Client fit |
|---|---|---|---|---|---|
| Permits | `permits` (931,947 rows) | CARTO table | max `permitissuedate` = 2026-08-22 | `geocode_x`/`geocode_y`, address | Needs new small Carto client |
| 311 | `public_cases_fc` (5.9M rows) | CARTO table | max `requested_datetime` = 2026-08-23 | `lat`/`lon`/`the_geom` | Same |
| Licenses | `business_licenses` (433,977 rows) | CARTO table | sane max `mostrecentissuedate` = 2026-08-22 (see caveat) | `geocode_x`/`geocode_y` | Same |
| Deeds | `rtt_summary` (5.1M rows incl. mortgages; ~1.16M dated pre-now) | CARTO table | max real `document_date` = 2026-08-10 | `the_geom` point, address range | Same |

Caveats: `mostrecentissuedate` and `document_date` carry sentinel values (year
3200, year 9798) that any watermark query must exclude (`WHERE col < now()`).
`rtt_summary` is the Office of Realty Transfer Tax record — it mixes deeds with
mortgages and other recorded documents (`document_type` filter needed), like NYC
ACRIS but broader than NORA disposals in New Orleans. Paging must be keyset-based;
deep OFFSET on a 5M-row table degrades badly.

### Boston — CKAN — permits and 311 strong, no sales

The lone true CKAN site. Resources are datastore-active and, unusually,
`datastore_search_sql` is enabled (max-date watermarks work directly).

| Feed family | Dataset (resource) | Platform detail | Updated | Geocoding | Client fit |
|---|---|---|---|---|---|
| Permits | Approved Building Permits (`6ddcd912…`), 660,839 rows | CKAN datastore | max `issued_date` = 2026-08-22 | `y_latitude`/`x_longitude`, `gpsx`/`gpsy`; 15,697 rows (2.37%) carry no `y_latitude` — published gap, G5 passes under gap+2pp tolerance (newest-500 drop 1.8%, live-probed 2026-08-24) | Needs new CKAN client (~Socrata-sized) |
| 311 | 311 Service Requests (`254adca6…` current-year slice) | CKAN datastore, one resource per year | July 2026 rows in current slice | `longitude`/`latitude` | Same; year-resource rollover at New Year |
| Licenses | Licensing Board Licenses (`04dc653b…`), 3,659 rows; also Active Food Establishment Licenses | CKAN datastore | modified 2026-08-19 / 2026-08-23 | `gpsx`/`gpsy` — **State Plane meters (EPSG:26986), not degrees** (live-probed 2026-08-24: 498/500 newest rows rejected) | **Excluded from registration**: fails G5 by construction; CRS transform deferred to the geocoding wave |
| Deeds/sales | none found | — | — | — | — |

### Detroit — ArcGIS Hub — ready now, all four families

| Feed family | Dataset/layer | Platform detail | Updated | Geocoding | Client fit |
|---|---|---|---|---|---|
| Permits | BSEED Building Permits (`bseed_building_permits/FeatureServer/0`), 46,694 pts | FeatureServer, point, maxRecordCount 1000 | 3,779 issued since 2026-01-01 | `longitude`/`latitude` attrs + point geometry | Existing `ArcGISClient` |
| 311 | Improve Detroit Issues | FeatureServer | item modified 2026-05 (epoch 1778182499000) | point geometry | Existing client |
| Licenses | Business Licenses (Current) | FeatureServer table | item modified 2026-05 | unverified | Existing client |
| Sales/deeds | Assessor Property Sales (`assessor_property_sales_view/FeatureServer/0`), 534,779 pts | FeatureServer, point | newest `sale_date` = 2026-03-26 | `longitude`/`latitude` | Existing client |

Dates are typed `esriFieldTypeDateOnly`, so they arrive as `"YYYY-MM-DD"`
strings rather than epoch-ms — the client's epoch conversion skips them, and the
values are already parser-friendly. A genuine market-sales feed with grantor,
grantee, parcel ID, price, and coordinates: rare outside county assessors.

### Washington DC — ArcGIS Hub — ready now, watch the year-slicing

| Feed family | Dataset/layer | Platform detail | Updated | Geocoding | Client fit |
|---|---|---|---|---|---|
| Permits | Building Permits in 2026 (`FEEDS/DCRA/FeatureServer/18`) | Point layer, one layer per year | newest `ISSUE_DATE` = 2026-08-17 | `LATITUDE`/`LONGITUDE` attrs | Existing client; watermark must switch layers at New Year |
| 311 | 311 City Service Requests in 2026 (`ServiceRequests/FeatureServer/21`) | Point layer per year | newest `ADDDATE` = 2026-08-23 (survey day) | `LATITUDE`/`LONGITUDE` | Same caveats |
| Licenses | Basic Business Licenses (`FEEDS/DCRA/FeatureServer/0`) | Non-spatial table | newest `INITIALISSUEDATE` = 2026-08-06 | none (address only) | Existing client; no H3 without geocoding |
| Sales | Tax System Property Sales CAMA (`Property_and_Land_WebMercator/FeatureServer/57`) | Non-spatial table | newest `SALE_DATE` = 2026-08-12 | none (`SSL` parcel key only) | Existing client; join to parcel layer needed for H3 |

This server rejects `returnCountOnly` queries with where-clauses; recency checks
must page newest-first instead. Coordinate spellings are uppercase
(`LATITUDE`), which today's producer fallback chains will not match.

### Denver — ArcGIS Hub — three usable feeds, licenses weak, sales not geocoded

| Feed family | Dataset/layer | Platform detail | Updated | Geocoding | Client fit |
|---|---|---|---|---|---|
| Permits | Residential + Commercial Construction Permits (layer ids e.g. `…RESIDENTIALCONSTPERIT_P/FeatureServer/316`) | Points, maxRecordCount 2000 | 688 residential issued since 2026-07-01 | point geometry, ADDRESS fields | Existing client |
| 311 | ODC_service_requests_311 (table id 66), 400,164 rows | Non-spatial table | 5,512 created since 2026-08-16 | `Longitude`/`Latitude` attrs (uppercase) | Existing client |
| Licenses | Active Business Licenses (table id 31) | Non-spatial table | item modified 2026-08-22 | none; no issue-date field either | Existing client; weak sla fit |
| Sales | Real Property Sales and Transfers (table id 60), 309,548 rows | Non-spatial table | 2,295 receptions since 2026-06-01 | none — `PARID`/address keys only | Existing client; deeds unusable for H3 without geocoding |

`RECEPTION_DATE` is a numeric yyyymmdd integer, and the feed includes $0
city-to-city transfers that need filtering.

### Minneapolis — ArcGIS Hub — permits and 311 now, sales lagging

| Feed family | Dataset/layer | Platform detail | Updated | Geocoding | Client fit |
|---|---|---|---|---|---|
| Permits | CCS_Permits, points, **maxRecordCount 16000** | FeatureServer | item modified 2026-08-20 | `Longitude`/`Latitude` attrs + point geometry | Existing client |
| 311 | Public_311_2026 (one layer per year) | Points | item modified 2026-08-23 | point geometry (XCOORD/YCOORD are state-plane attrs; ignore) | Existing client; year rollover |
| Licenses | On_Sale_Liquor / Off_Sale_Liquor only | Points | modified 2026-08 | point geometry | Narrow liquor feeds; weak sla fit |
| Sales | Property_Sales_2021_to_2025 (table id 0), 38k+ rows | Non-spatial table | max `SALE_DATE` = 2025-09-30; zero rows in 2026 despite 2026-08-17 republish | county-coordinate X/Y, not lat/lng | Existing client; stale + ungeocoded |

### Baltimore — ArcGIS Hub — permits and 311 live; no market sales

| Feed family | Dataset/layer | Platform detail | Updated | Geocoding | Client fit |
|---|---|---|---|---|---|
| Permits | Housing and Building Permits 2019–Present (`DHCD_Open_Baltimore_Datasets/FeatureServer/3`) | Points, maxRecordCount 1000 | item modified 2026-08-21 | point geometry (+Address) | Existing client |
| 311 | 311 Customer Service Requests 2026 (`311_Customer_Service_Requests_current/FeatureServer/0`) | Points | row created 2026-08-22 seen | `Latitude`/`Longitude` attrs; **published geocode gap 25.07%** (585,130/780,954 rows carry real coords, probed 2026-08-24); newest-500 drop 35%, mature-window (≥9d old) drop 22.6% — G5 passes under gap+2pp tolerance against the published gap; newest window skews to freshly-created, still-ungeocoded requests. Address-only rows stay dropped until the geocoding wave | Existing client; year rollover |
| Licenses | Liquor Licenses | FeatureServer | item modified 2026-08-19 | verified: 500/500 newest rows parse (live-probed 2026-08-24) | Narrow; pinned notifications-grade |
| Sales/deeds | tax-lien sale lists only | — | stale (2021 lists) | — | Not a deeds feed |

### Nashville, Louisville, Tempe — partial; Hartford — dead

| City | Permits | 311 | Licenses | Deeds/sales | Verdict |
|---|---|---|---|---|---|
| Nashville | **Live**: Building Permits Issued, points, `Lon`/`Lat` attrs, `Date_Issued`; item modified 2026-08-23 | Latest slice is **2025** — no 2026 layer yet | Contractor/beer permits only | None (eBid surplus auctions matched the query) | Partial: permits-only city |
| Louisville | Active Construction Permits (snapshot, not history; modified 2026-08-18) — *identified, fields not probed* | Latest slice 2025 (modified 2026-07) | ABC alcohol/tobacco only | Landbank dispositions only | Weak partial |
| Tempe | **Live**: building_permits, points, Accela-style schema; 939 issued since 2026-05-01 | No raw requests — KPI summary layers only | None found | None found | Partial: permits-only city |
| Hartford | Building Permits table non-spatial, item modified **2024-09** | "Current Year" layer last touched 2025-01 | None found | None found | Effectively dead |

## Client-cost matrix

| Platform | Client status | Pagination model | Effort to add | Cities unlocked |
|---|---|---|---|---|
| Socrata | `SocrataClient` exists (~107 lines) | `$offset`/`$order`, short-page termination | — | NOLA, Austin (already recommended elsewhere) |
| ArcGIS FeatureServer / Hub | `ArcGISClient` exists (~258 lines), proven on Seattle KC sales | `resultOffset`/OID sort, `exceededTransferLimit`, per-layer `maxRecordCount` | **Zero platform code.** Per-city work is parser fallbacks only | **Detroit, DC, Denver, Minneapolis, Baltimore** (+ Nashville/Louisville/Tempe permits-only) |
| CARTO SQL (Philadelphia) | Missing | Keyset: `WHERE key > last ORDER BY key LIMIT n`; count/max aggregates free | New client ~120–180 lines incl. tests — comparable to `socrata_client.py`; simpler auth (none) | **Philadelphia (all four feeds)** |
| CKAN datastore (Boston) | Missing | `datastore_search` `limit`/`offset`; bonus `datastore_search_sql` for watermarks | New client ~150–200 lines; resource-ID indirection adds plumbing | Boston (2.5 feeds) |
| Static CSV dumps (San Diego seshat.datasd.org) | No client possible in streaming model | None — whole-file download | Reject: full re-download per cycle, no watermark, no incremental fetch | San Diego (would otherwise offer permits/311/licenses, no deeds) |

Two shared wrinkles for the ArcGIS cities, both cheap: several layers spell
coordinates uppercase (`LATITUDE`/`Longitude`), which today's case-sensitive
producer fallback chains miss — either add spellings per city (step 4 tax as
usual) or lowercase keys once in `_flatten_feature`. And DC/Nashville/Baltimore/
Minneapolis slice layers by calendar year, so a registration there needs a
current-layer pointer maintained across New Year, unlike any registered city so far.

## Recommendation

Positioning against the existing recommendation (**New Orleans first, Austin
second** — both pure Socrata, zero client work):

1. **Keep New Orleans first.** It remains the cheapest full four-feed add:
   Socrata end to end, three feeds geocoded, no new client.
2. **Detroit second** — ahead of Austin if a property-sales feed matters.
   It is the only ready-now city offering all four families through the
   existing `ArcGISClient`, including a genuine assessor sales feed with
   grantor/grantee/price/parcel and coordinates, current to 2026-03. Cost is
   the usual step-4 parser fallbacks plus one `cities/detroit.py` module.
   Austin keeps the richer permits date model; pick by whether sales or
   permit-detail depth is worth more.
3. **Philadelphia third, and first among the non-Socrata platforms proper** —
   the only non-Socrata city with all four families live, fresh, and geocoded,
   including the survey's only true recorded-documents feed outside NYC/King
   County. Prerequisite: a small CARTO keyset-paging client (~150 lines) plus
   sentinel-date filtering and an `rtt_summary` document-type filter. Its 5.9M-row
   311 table also makes the initial backfill materially heavier than NOLA's.
4. **DC fourth among ArcGIS cities** if the year-sliced layer rollover is
   acceptable; its 311 feed is the freshest observed anywhere in either survey.
5. **Boston only if a CKAN client is wanted strategically** — its two strong
   feeds don't justify the client alone. **San Diego: reject** (dump-only).
6. Skip Hartford (dead), and treat Nashville/Louisville/Tempe/Baltimore/
   Minneapolis as opportunistic permits-or-311 partials, same shape as LA.
