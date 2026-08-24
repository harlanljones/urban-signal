# Socrata domain sweep — systematic city expansion candidates

**Date of survey: 2026-08-23.** Follow-up to `city-expansion-candidates.md`
(same day), redoing its coarse pass systematically: cross-domain catalog scans
with multiple phrasings per feed family, name-level triage, and direct
resource verification of every dataset reported below. "Updated" is verified
against the resource itself (newest row / bounded-window counts), not just the
catalog timestamp. Re-probe before acting on this.

Scope exclusions carried over: the five registered metros (NYC, Chicago,
SF Bay Area, Seattle, LA) and New Orleans + Austin (owned by another stream;
briefly reconfirmed live during scanning but excluded from ranking).

## Method, and its limits

Two discovery passes against `api.us.socrata.com/api/catalog/v1`:

1. **Global scan** — 16 phrasings across the four feed families
   (permits ×3, 311 ×4, licenses ×4, deeds/sales ×6) with NO domain filter,
   `limit=500` each ≈ 3,300 raw hits, aggregated per domain × family.
2. **Targeted scan** — the global top-500 hides entire cities, so a curated
   list of ~55 additional domains (phase-A survivors plus known big-city
   portals) was scanned through the central catalog with the `domains=`
   filter. That filter doubles as a membership test: an unknown domain 404s.

**How the top-hit trap was avoided.** Every candidate was triaged by dataset
NAME before verification, and every dataset reported here was then probed
directly (`$limit=1` for columns, `$select=count(*)`, newest row via
`$order=<col> DESC&$where=<col> IS NOT NULL`, and 60/7-day bounded-window
counts). Name triage caught the documented failure modes and their cousins:
Kansas City's `property sales` top hit is *again* the Monthly Car Auction
(`7wyi-8tqr`), Fulton County's is Vendor Payments, Mesa's "Tax Licenses" is a
monthly count-by-category aggregate (not a registry), and Mesa's and Ramsey
County's "service requests" hits are internal IT/purchasing metrics.

Other limits:

- The catalog exposes freshness as `resource.data_updated_at` (ISO string),
  not `rowsUpdatedAt`; the `/api/catalog/v1/domains` endpoint does not exist
  on this deployment; some Socrata domains' local `/api/catalog/v1` 404s —
  always use the central API with `domains=`.
- `/api/views/*` metadata endpoints are blocked without an app token, so
  column inventories came from sample rows; a dataset can have more columns
  than shown here.
- Text-typed date fields bite: Prince George's `transfer_date` is
  `YYYYMMDD` text with `'ZZZZZZZZ'` sentinels — a naive `DESC` sort returns
  sentinels first and lexicographic `>= '2026-06-24'` inflates counts
  (4,647 apparent vs 0 real in the window). Sentinel/future dates also occur
  in Cincinnati's combo permits (`entry_date` year 3201) and Norfolk
  applications (future-dated filings).
- Snapshot-style registries (Baton Rouge businesses, Montgomery ABS
  licensees) carry no usable watermark column — they would be full-refresh
  feeds.
- Socrata-only by scope; cities that left the platform are invisible to the
  discovery API and were spot-checked by homepage fingerprint only.

## Recommendation

**Norfolk first, Cincinnati second, Baton Rouge third.**

- **Norfolk is the only surveyed city with all four families live and
  refreshed within ~60 days**, including a real property-transfer feed
  (consideration, grantee, parcel GPIN, freshest transfer 2026-08-19) —
  materially better than New Orleans' NORA-disposals stand-in and wider than
  anything Austin offers. Its permits and sales feeds need address-based
  geocoding (no native coordinates), which is exactly the existing fallback
  path.
- **Cincinnati** pairs a 33k/60-day geocoded 311 with a fresh geocoded
  licenses feed and a healthy permits register; it has no sales/deed feed at
  all, so it registers partial (LA precedent).
- **Baton Rouge / East Baton Rouge Parish** mirrors New Orleans' shape:
  geocoded 311, geocoded business registry, daily permits — but no market
  sales (adjudicated/foreclosure parcels only).

Montgomery County MD (county-scale, strong permits + licenses, 311 without
coordinates) and Orlando (clean permits + licenses, nothing else) are the
next tier if those metros matter.

## Ranked candidate table

Verified newest-row dates and 60-day volumes from direct probes on
2026-08-23. Geocoding legend: **pts** = lat/lng or point geometry;
**addr** = street address (+parcel id), needs geocoding; **—** = none.

| City | Domain | Permits | 311 | Licenses | Deeds/Sales | Best updated | Geocoding |
|---|---|---|---|---|---|---|---|
| Norfolk, VA | `data.norfolk.gov` | ✔ | ✔ | ✔ | ✔ | 2026-08-19…22 | pts (311); addr (rest) |
| Cincinnati, OH | `data.cincinnati-oh.gov` | ✔ | ✔ | ✔ | ✘ | 2026-08-19…21 | pts (311, licenses); addr (permits) |
| Baton Rouge, LA | `data.brla.gov` | ✔ | ✔ | ✔ | ✘ | 2026-08-21…23 | pts (311, licenses); addr (permits) |
| Montgomery Co., MD | `data.montgomerycountymd.gov` | ✔ | ◐ | ✔ | ✘ | 2026-08-20…23 | pts (permits, licenses); zip/city only (MC311) |
| Orlando, FL | `data.cityoforlando.net` | ✔ | ✘ | ✔ | ✘ | 2026-08-23 | pts |
| Prince George's Co., MD | `data.princegeorgescountymd.gov` | ◐ | ◐ | ✘ | ◐ | 2026-07-17…08-14 | pts (311, permits); polys (property) |

✔ = live + <~60 days + verified · ◐ = live but caveated (see section)

## Per-city findings

### Norfolk, VA — `data.norfolk.gov` — 4/4 families, top candidate

| Feed | Dataset | Updated | Rows/60d | Coordinates |
|---|---|---|---|---|
| Deeds/Sales | `qva7-tzrf` Property Assessment and Sales – FY27 | transfer 2026-08-19 | 1,068 | addr + `gpin` |
| Permits | `fahm-yuh4` Permits | application 2026-08 (live) | 2,464 | addr + `gpin` |
| Inspections (permits-adjacent) | `ihzr-5x5n` Inspections | completed 2026-08-21 | 11,120 | addr + `gpin` |
| 311 | `nbyu-xjez` MyNorfolk Service Requests | modified 2026-08-21 | n/a (1.16M total) | `location` point |
| Licenses | `dpi6-sct5` Business Licenses | opened 2026-08-21 | 178 | `location_address` |

The sales series is published as annual fiscal-year datasets (FY23…FY27);
register the current-year file and expect to rotate IDs each July. Records
carry `transfer_date`, `consideration`, `grantee`, owner, values, and full
situs address — ordinary market transactions, unlike NOLA's NORA disposals.
No lat/lng anywhere except 311; the parsers' address fallback chain will do
the work. Caveats: `fahm-yuh4` has future-dated applications (max seen
2027-01-27 — scheduled filings, fine once known); `bnrb-u445` "Permits and
Inspections" looks attractive and is point-geocoded but carries **no date
column at all** — do not use it as the permits watermark feed.

### Cincinnati, OH — `data.cincinnati-oh.gov` — 3/4, strongest urban 311

| Feed | Dataset | Updated | Rows/60d | Coordinates |
|---|---|---|---|---|
| 311 | `gcej-gmiw` Cincinnati 311 (Non-Emergency) Service Requests | 2026-08-21 | 33,107 | `latitude`, `longitude`, `location`, `address` |
| Licenses | `ehdi-ajku` Licenses (and Use Permits) | entered 2026-08-19 | 2,579 | `latitude`, `longitude`, `full_address` |
| Permits | `uhjb-xac9` Cincinnati Building Permits | issued 2026-08-21 | 1,900 | addr + `pin`, `neighborhood` |
| Deeds/Sales | none found | — | — | — |

The plain permits register (`applieddate`/`issueddate`/`completeddate`,
cost, units) is address-only; a companion line-item table `thvx-5mem`
("Combo") carries point `location` entries but junk sentinel `entry_date`
values (year 3201) — usable for geometry joins, not as a watermark. A second
license registry `7dk3-gngs` (Business Licenses, effectivefrom/to) has no
geometry; prefer `ehdi-ajku`. No property-sales or recorded-documents feed
surfaced under any phrasing. Registers partial, like Los Angeles.

### Baton Rouge / East Baton Rouge Parish, LA — `data.brla.gov` — 3/4

| Feed | Dataset | Updated | Rows/60d | Coordinates |
|---|---|---|---|---|
| 311 | `7ixm-mnvx` 311 Citizen Requests for Service | created 2026-08-21 | 13,867 | `latitude`, `longitude` |
| Licenses | `xw6s-bcqm` Businesses Registered with EBR Parish | snapshot (upd 2026-08-23) | n/a | `geolocation` point |
| Permits | `7fq7-8j7r` EBR Building Permits | issued 2026-08-21 | 1,562 | addr + zip |
| Deeds/Sales | ✘ (adjudicated/foreclosure parcels only: `shrr-fsqq`, `a4h4-zi7e`) | — | — | `the_geom` |

City-Parish consolidated portal covering the whole parish (~440k). The
business registry is parish-wide with NAICS codes and point geometry but no
open-date column — full-refresh feed. An ABC liquor-license table
(`xhjf-mdnv`, upd 2026-08-11) also exists. No market sales feed; the
adjudicated-parcel tables are tax-foreclosure disposals, narrower even than
NOLA's NORA feed.

### Montgomery County, MD — `data.montgomerycountymd.gov` — 2 solid + 1 weak

| Feed | Dataset | Updated | Rows/60d | Coordinates |
|---|---|---|---|---|
| Permits | `m88u-pqki` Residential Permit (also `i26v-w6bd` Commercial, `b6ht-fw3x` Demolition, `qxie-8qnp` Electrical) | added 2026-08-20 | 1,201 (res.) | `location` point; **published geocode gap 4.97%** (9,244/186,140 rows without coordinates, probed 2026-08-24); newest-500 drop 4.8% — G5 passes under gap+2pp tolerance |
| 311 | `xtyh-brr2` MC311 Service Requests | created 2026-08-22 | n/a (7.9M total) | **none** — `x_city`/`x_zipcode`/districts only |
| Licenses | `c6rw-fazn` ABS Licensee Data (liquor); many vendor-license sets | quarterly (2026-04-01) | n/a (1,132 rows) | `location` point |
| Deeds/Sales | none found | — | — | — |

Deep, well-maintained county portal (DPS permit families are numerous and
daily). The catch: flagship MC311 has no coordinates and no street field —
zip/city/district resolution only, below the bar unless supplemented by
`k9nj-z35d` Housing Code Violations (a fully geocoded service-request feed,
but code-enforcement-scoped). Liquor licensee list is small and quarterly;
vendor/business license sets are niche. County-scale geography (~1M, DC
suburbs) rather than a single city.

### Orlando, FL — `data.cityoforlando.net` — clean but thin

| Feed | Dataset | Updated | Rows/60d | Coordinates |
|---|---|---|---|---|
| Permits | `ryhf-m453` Permit Applications | issue_permit_date 2026-08-23 | 5,065 | `geocoded_column`, `location` |
| Licenses | `7388-4re5` Business Tax Receipts | received 2026-08-23 | 267 | `geocoded_column` |
| 311 | none found | — | — | — |
| Deeds/Sales | none found | — | — | — |

Both live feeds are point-geocoded and refresh daily — the least parser work
per feed of any candidate — but there is nothing beyond the two families.

### Prince George's County, MD — `data.princegeorgescountymd.gov` — near-miss

| Feed | Dataset | Updated | Rows/60d | Coordinates |
|---|---|---|---|---|
| Permits | `weik-ttee` Residential and Commercial Permits (Jul 2013–Present) | issuance 2026-08-14 | 55 (!) | `location` point |
| 311 | `2ywx-ipcd` PG County 311 | opened 2026-07-17 | 7,082 | `latitude`, `longitude` |
| Property | `qzrv-2tnv` Property | load 2026-06-10; newest transfer **2026-05-29** | 0 in 60d | polygon `the_geom` |

Everything is half-alive. The permits file touched 2026-08-17 but recorded
only 55 issuances in 60 days (either issuance lag or migration toward
`245r-4wz8`). The 311 replacement feed is geocoded but trails ~5 weeks. The
property file is tantalizing — `sales_price`, `transfer_date`,
liber/folio land-record refs, parcel polygons — but transfers run ~3 months
behind and `transfer_date` is `YYYYMMDD` text polluted with `'ZZZZZZZZ'`
sentinels. Worth revisiting if the county catches up; not competitive today.

## Skipped and dead ends

**Left Socrata / not in the discovery universe** (404 under `domains=`;
homepage fingerprints where checked): Detroit (ArcGIS), Raleigh (ArcGIS),
Milwaukee (CKAN+Esri), Pittsburgh/WPRDC (CKAN), Charlotte, Albuquerque,
Sacramento (city+county), Tulsa, Memphis, Indianapolis, Wake County NC,
St. Louis, Clark County NV, Harris County TX, Broward FL, Hillsborough FL,
Orange County FL, Fairfax County VA, Lexington KY, Spokane, Jersey City,
Plano, Rochester NY, Cleveland, Omaha, Chattanooga, Knoxville, Shreveport.
Consistent with the prior survey's CKAN/ArcGIS out-of-scope note.

**Confirmed stale or trap-ridden (rechecked with broader queries):**
- Kansas City `data.kcmo.org`: only 311 is alive (`d4px-6rwg`, 26,372/60d,
  lat/lng — fine in isolation). Permits remain decade-dead listings plus one
  15-month-old CPD extract; licenses 7 months stale; and the `property
  sales` top hit is *still* the Kansas City Monthly Car Auction. Not a
  candidate.
- Fulton County GA (`sharefulton.fultoncountyga.gov`): "fresh" deeds hit was
  Vendor Payments; permits are annual aggregates; Atlanta proper is off-platform.
- Ramsey County MN (`data.ramseycountymn.gov`, St. Paul): assessor parcel
  data (March 2026) and a 2019 sales-ratio series; "service requests" hit is
  homeless-prevention caseload; no permits/licenses of the right kind.
- Providence RI: 311 only; permits/licenses/sales years stale.
- Miami, Honolulu, Oakland, Dallas, Fort Collins, Roseville CA: one live
  family at best (Dallas 311, Oakland OAK311, Honolulu 311, Mesa permits —
  see below), rest stale or absent.

**Under 200k population, noted not pursued:** Corona CA (`corstat.coronaca.gov`
— surprisingly good CorStat building-permit family, daily, but SeeClickFix
311 and licenses are 1–2 years stale), Everett WA (permits + licenses both
fresh — best small-city find), Roseville CA, Fort Collins, Gainesville,
Cambridge MA (covered in prior survey), Somerville, Providence (~190k,
listed above), Auburn WA, College Station TX, Bloomington IN, West
Hollywood, Janesville WI, Dumfries VA.

**Excluded by brief:** New Orleans and Austin (both rescanned incidentally
and still live; owned by another stream), the five registered metros, Bay
Area regionals (Oakland, Santa Clara, San Mateo, MTC — Oakland's feeds are
mostly stale regardless), Cook County IL (alias of registered Chicago).

## What a new city costs (unchanged, evidence updated)

Same recipe as the prior survey (city module, config endpoints,
registration, parser fallbacks). New datapoints from this sweep:

- Norfolk would arrive needing address-geocoding for three of four feeds —
  the fallback chain pays rent immediately; consider promoting the
  per-city field-mapping-table refactor before onboarding it.
- Fiscal-year-partitioned sales datasets (Norfolk) need an ID-rotation
  convention the registry does not have yet; King County's ArcGIS precedent
  covers platform quirks, not partitioning.
- Snapshot registries without watermarks (Baton Rouge businesses) want a
  `full_refresh: true`-style hint in `DatasetSpec.extra`.
