# City expansion candidates

**Date of survey: 2026-08-23.** Every endpoint below was probed live on that date;
"updated" is the dataset's own `rowsUpdatedAt`. Re-probe before acting on this —
LA's 311 feed is proof that a city can quietly retire an endpoint.

## Method, and its limits

Candidate domains were queried through the Socrata discovery API
(`api.us.socrata.com/api/catalog/v1`), scoped per-domain, one query per feed type
(`building permits`, `311 service requests`, `business licenses`, `property sales`).
Each top hit was then fetched directly for its update timestamp and column list.

**The catalog's top hit is often the wrong dataset.** Kansas City's top
`property sales` hit was a *monthly car auction*; Austin's was a 2016
single-family audit. Treat the per-city notes below as verified and the survey
method as a coarse filter — a city marked "no feed" may have one under a name the
query missed.

Only Socrata domains were surveyed. Cities on CKAN (Boston, Philadelphia,
San Diego) or ArcGIS Hub (Denver, DC, Minneapolis, Detroit) were out of scope for
this pass, but the ArcGIS client added for Seattle makes that second group
substantially cheaper to reach than it was.

## Recommendation

**New Orleans first, Austin second.** New Orleans is the only surveyed city with
three feeds confirmed live and geocoded, and it is the only one offering a
property-transfer feed at all. Austin has the strongest permits feed of the set
and a live general 311, but no usable sales feed.

## Per-city findings

### New Orleans, LA — `data.nola.gov` — strongest candidate

| Feed | Dataset | Updated | Coordinates |
|---|---|---|---|
| 311 | `2jgv-pqrq` 311 OPCD Calls (2012-Present) | 2026-08-23 | `latitude`, `longitude` |
| Licenses | `hjcd-grvu` Occupational Business Licenses | 2026-08-22 | `latitude`, `longitude` |
| Deeds | `hpm5-48nj` NORA Sold Properties | 2026-08-11 | `geopin`, `geocoded_column` |
| Permits | `nbcf-m6c2` Building Permits (2018-present) | 2025-08-17 | `the_geom`, `locationx/y` |

Three feeds live and directly geocoded — the least parser work of any candidate,
since `latitude`/`longitude` already match the existing fallback chains.

Two caveats. The permits feed last refreshed a year before this survey; confirm
whether that is a publishing lapse or a dead feed before committing. And "NORA
Sold Properties" is the New Orleans Redevelopment Authority's own disposals, not
a general recorded-deeds feed — narrower than NYC ACRIS or King County parcel
sales, and it will under-count ordinary market transactions.

### Austin, TX — `data.austintexas.gov` — strong permits, no sales

| Feed | Dataset | Updated | Coordinates |
|---|---|---|---|
| Permits | `quv8-5ckq` Issued Building Permits | 2026-08-08 | `latitude`, `longitude`, `location` |
| 311 | `xwdj-i9he` Austin 311 Public Data | 2026-08-23 | — (verify) |
| Licenses | none found | — | — |
| Deeds | none found | — | — |

The permits feed is the best in the survey: live, geocoded, and carrying
`issue_date`, `application_date`, `final_date` and `expiry_date`, which is a
richer date model than any currently registered city.

Note the discovery API's top 311 hit was a narrow "Signs and Markings" feed;
the real general feed is `xwdj-i9he`, found only by a second targeted query.
No business-licence or property-sales feed surfaced. Austin would register as a
partial city, like Los Angeles.

### Cambridge, MA — `data.cambridgema.gov` — live but small

All four queries returned hits and three refreshed on the survey date. But the
"licenses" hit was a *sheet metal permits* feed, the "deeds" hit was an aggregate
median-price series rather than transactions, and Cambridge is ~120k people.
High data quality, low signal value for a metro-scale product. Skip unless a
Greater Boston context is built where Cambridge is one submarket among many.

### Dallas, TX — `www.dallasopendata.com` — partial

311 (`d7e7-envw`) is live at 2026-08-12 with `lat_location`. The permits feed
(`e7gq-4sah`) last updated 2020-08-30 and should be treated as dead. No licences
or sales feeds surfaced.

### Kansas City, MO — `data.kcmo.org` — effectively dead

Every top hit was stale: permits last refreshed 2013, 311 in 2022. The one "live"
result was a car-auction listing matched by the `property sales` query. Not a
candidate on this evidence.

### No Socrata catalog

Baltimore, Nashville, Louisville, Hartford and Tempe returned nothing for any
query. Their open-data portals have moved off Socrata or restrict the discovery
API; each would need its own platform investigation.

Fort Worth and Bloomington returned a permits hit only and were not pursued.

## What a new city costs, now

Seattle and Los Angeles established the pattern, and the per-city work is now
mostly data, not code:

1. A `src/spatial/cities/<city>.py` module — metro bbox, division bboxes,
   submarkets, divisions. This is the bulk of the effort and is hand-authored.
2. Endpoint fields in `src/config.py`.
3. A `CityRegistration` in `REGISTRY`, plus aliases. Register only the feeds that
   exist; `get_dataset` raises a readable error for the rest.
4. Field-name fallbacks in whichever producers the city's schema does not already
   match. Every city so far has needed at least one.

Step 4 is the recurring tax. Each city arrives with its own spelling — Seattle's
ArcGIS layer uses `PIN`/`SaleDate`, LA spells longitude `lon` and cost
`valuation` — and the shared parsers grow another `or row.get(...)` each time.
Two or three more cities and that chain-of-fallbacks approach is worth replacing
with a per-city field-mapping table declared alongside the `DatasetSpec`.
