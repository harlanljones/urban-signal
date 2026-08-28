# Stream log — city-birmingham — 2026-08-28

Phase-2 leaf stream for Linear US-339: Birmingham, AL metro registration
(CKAN + Accela per brief, portal data.birminghamal.gov). Spine is serial after
this stream; do not edit spine files here.

## Claim

- **Stream id:** `city-birmingham`
- **Leaf files I will create/edit:**
  - `.streams/city-birmingham.md` (this file)
  - `docs/research/se-probe-birmingham.md` (NEW)
  - `apps/api/src/spatial/cities/birmingham.py` (NEW)
  - `apps/api/src/producers/field_maps_birmingham.py` (NEW)
  - `apps/api/tests/unit/test_producers_birmingham.py` (NEW)
- **Spine files I expect to need (do NOT edit in this stream):**
  - `apps/api/src/spatial/city_registry.py` (CityId.BIRMINGHAM, ALIASES, REGISTRY)
  - `apps/api/src/spatial/cities/__init__.py`
  - `apps/api/src/config.py`
  - `apps/api/src/serving/dashboard.py` METRO_META
  - `apps/dashboard/public/index.html` (city registration rule)

## Intent

LIVE-probe Birmingham's open data (CKAN data.birminghamal.gov + ArcGIS/Hub
fallbacks) across PERMITS / COMPLAINTS_311 / SLA / DEEDS. Register ONLY feeds
that are live and queryable; partial registration is correct and expected.
If every family is stale or none is live: STOP, write NOT-VIABLE findings to
docs/research/se-probe-birmingham.md, and report back — do not fabricate data.

## Decisions

- 2026-08-28 — Stream claimed from _TEMPLATE. Nothing else written yet; prior
  run was cancelled before creating files. Start clean.
- 2026-08-28 — Live probe complete → **NOT-VIABLE**. No leaf files built (no
  birmingham.py / field_maps / tests). See docs/research/se-probe-birmingham.md.

## Live probe (2026-08-28 UTC) — VERDICT NOT-VIABLE

Trusted live rows over the brief. Portal `data.birminghamal.gov` is CKAN 2.9.11
and is alive (`status_show` 200; newest datasets 2026-08-24 = crime/courts/
finance), but every family dataset is a frozen annual-file archive:

| Family | Platform | Endpoint | Watermark col + newest | 7d/60d/total | Geo | Verdict |
|---|---|---|---|---|---|---|
| PERMITS | ckan | `ckan://data.birminghamal.gov/building-permits-and-valuations-2017` | year-file; newest resource `last_modified` **2017-06-09** | no live cadence (2017 YTD archive) | address cols in files | Tier 3 / stale |
| COMPLAINTS_311 | ckan | `ckan://data.birminghamal.gov/311-cases-yearly` | year-file; "311 Cases - 2019" `last_modified` **2021-07-29** | no live cadence (2019 YTD archive) | address fields | Tier 3 / stale |
| SLA | ckan | `ckan://data.birminghamal.gov/new-business-licenses-issued` | year-file; newest resource `last_modified` **2017-06-05** | no live cadence (2016/17 report) | n/a | Tier 3 / stale |
| DEEDS | none | — | `city-interest-real-property-...` is city **surplus** listings | n/a | n/a | no feed |

Fresher-looking but NOT registrable: `condemnation-notifications` (PDFs, one
building), `east-pinson-valley-data-may-2023-to-may-2025` + `-community-2023-
2024` (PDF/XLSX Pinson Valley study, not datastore, not city 311).

ArcGIS doors: Hub landings `birminghamal.opendata.arcgis.com` /
`data-birminghamal.opendata.arcgis.com` body 200 but org private; `gis*.birminghamal.gov`
DNS fail; `birmingham.maps.arcgis.com` only reference web maps + 2018/19 static
SHP/GeoJSON; AGOL search → third-party/HOLC/academic/UK-Birmingham hits only.
Jefferson County: `jeffcoalabama.gov`/`jeffersoncountyal.gov`/`gis.jeffco.org`
DNS fail; `jeffersoncountyal.com` is an empty stub; AGOL owner search 0.
Accela ACA `aca-prod.accela.com/BIRMINGHAM` 200 on home but UI-only: every REST
probe 404/"No HTTP resource" (no v4 controller, no openapi) — login-walled.

## Plan deviation: STOP, no leaf

Per the leaf contract ("NEVER point a feed at a stale/frozen source ... if
every family is stale or none is live: STOP"), so no new city module, no field
map, no producer tests. Registration of zero feeds is the correct outcome.

## Current step

DONE — probe + verdict recorded. No spine edits (nothing to register). No
code to test.

## Next step

Report VERDICT: NOT-VIABLE to the orchestrator. Re-probe trigger: Birmingham
publishing live permit/311 row feeds on the CKAN, or a public Accela/ArcGIS
layer, or Jefferson County GIS online. Do not build the leaf against the frozen
archive.
