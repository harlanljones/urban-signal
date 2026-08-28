# SE live probe — Birmingham, AL (US-339)

**Probe date: 2026-08-28 (UTC).** Re-probe of data.birminghamal.gov (CKAN),
Birmingham ArcGIS/Hub, Accela ACA, and Jefferson County GIS, done by the
`city-birmingham` leaf stream. Verdict is judged on **live row freshness**
(watermark), not catalog `modified` timestamps.

Linear: **US-339**. Brief hint: CKAN (`data.birminghamal.gov`) + Accela.

**Verdict: NOT-VIABLE — no family registrable.** The CKAN portal is alive
(last `metadata_modified` sweep 2026-08-24, all crime/courts/finance) but
every family dataset on it is a **frozen annual-file archive**. The live
permit workflow is Accela Citizen Access (UI-only, no public JSON). No city
or Jefferson County row-level permits/311/license/deed feed is queryable.

---

## Method (and its limits)

1. CKAN `package_search` per family (`permit`, `service request`,
   `business license`, `sales/transfer/deed`) against `data.birminghamal.gov`
   (CKAN 2.9.11, `status_show` 200); `package_show` on survivors.
2. Full portal enumeration (117 datasets) grouped by org, to catch any live
   family feed mis-tagged to a non-obvious org.
3. Resource-level `datastore_active`/`last_modified` inspection on the family
   candidates (datastore-active, so the CKAN client query path *would* work —
   the problem is the data, not the transport).
4. ArcGIS doors: `birminghamal.opendata.arcgis.com`,
   `data-birminghamal.opendata.arcgis.com` Hub landings (HTTP 200 body, org
   private — no data), `gs*.birminghamal.gov` (DNS fail),
   `birmingham.maps.arcgis.com` (city AGOL, referenced by CKAN GIS resources,
   but only reference web maps + 2018/19 static SHP/GeoJSON exports).
5. AGOL `sharing/rest/search` for `Birmingham` / `Jefferson County AL` family
   Feature Services — only third-party/HOLC/academic/UK-Birmingham hits, no
   authoritative city or county permit/license/311/deed Feature Service.
6. Jefferson County GIS: `jeffcoalabama.gov`, `jeffersoncountyal.gov`,
   `jefferson.countyal.gov`, `gis.jeffco.org` all **DNS fail**;
   `jeffersoncountyal.com` resolves but is an empty stub (`<title>` only, no
   family data, `/arcgis/rest/services` 404). AGOL owner search for county
   accounts: 0 results.
7. Accela ACA (`aca-prod.accela.com/BIRMINGHAM/Welcome.aspx`) — 200 on the
   portal home; every REST probe returns 404/"No HTTP resource" (no `v4`
   controller, no openapi). UI-only, login-walled.

Limits: no live family table exists to watermark. A token-gated internal
ArcGIS Server cannot be ruled out from outside; but it is not a City- or
county-published public feed.

---

## Probe table

| Family | Platform | Endpoint | Watermark col + newest value | 7d / 60d / total | Geo | Verdict |
|---|---|---|---|---|---|---|
| PERMITS | ckan | `ckan://data.birminghamal.gov/building-permits-and-valuations-2017` | Year-file boundary; newest resource `last_modified` 2017-06-09 (datastore-active, 6 resources) | no live cadence; 2017 YTD archive only | address columns in files; no live coords | **Tier 3 / stale** |
| COMPLAINTS_311 | ckan | `ckan://data.birminghamal.gov/311-cases-yearly` | Year-file; newest resource "311 Cases - 2019" `last_modified` 2021-07-29 (datastore-active) | no live cadence; 2019 YTD archive only | address fields in files; feed dead | **Tier 3 / stale** |
| SLA | ckan | `ckan://data.birminghamal.gov/new-business-licenses-issued` | Year-file; newest resource `last_modified` 2017-06-05 (datastore-active) | no live cadence; 2016/17 annual-report archive | n/a | **Tier 3 / stale** |
| DEEDS | none | — | none. `city-interest-real-property-for-sale-or-development` is city **surplus** listings, not property transfers | n/a | n/a | **no feed** |

Birmingham family candidates that look fresher but are NOT registrable:

| Dataset | Why not |
|---|---|
| `condemnation-notifications` (2024-10-11) | PDFs only, single building (Bankhead Towers). Not a 311/permit row feed. |
| `east-pinson-valley-data-may-2023-to-may-2025` (2025-05-12) | One PDF report; **not datastore**; Pinson Valley study, not city-wide 311. |
| `data-set-east-pinson-valley-community-2023-2024` (2025-08-20) | One XLSX community study (2023–2024 range); not a live watermark feed; Pinson Valley, not Birmingham 311. |
| `east-pinson-valley-data` (2025-08-20) | PDF/xlsx report; static. |

Portal is genuinely live, but only for: 2026 YTD Part I Offenses, precinct
crime files, Municipal Court dockets, Capital Projects Status, finance
reports. None are PERMITS/311/SLA/DEEDS (do not register).

---

## Decision

**NOT-VIABLE.** Register **zero** feeds. No `apps/api/src/spatial/cities/birmingham.py`,
no `field_maps_birmingham.py`, no `test_producers_birmingham.py` — building a
leaf against a frozen archive would fabricate spatial data against a stale
source, which the leaf contract forbids. No spine delta for the orchestrator.

**Re-probe trigger:** Birmingham publishing live permit or 311 row-level
extracts on the CKAN (the portal is actively maintained — crime files landed
2026-08-24 — so a family revival is plausible but has not happened), OR the
city making an Accela/ArcGIS feature layer publicly queryable, OR Jefferson
County bringing its GIS online as a queryable service. Re-open with a fresh
probe rather than patching the archive.

Stamp: 2026-08-28.
