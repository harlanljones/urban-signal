# Wave 3 Phase-0 probe — Birmingham, AL

**Date of probe: 2026-08-28 (UTC).** Row-level reads; catalog `modified` dates
were recorded but freshness was judged on the newest data row by watermark,
not on catalog timestamps.

Linear: **US-339**. Ticket hint: CKAN (`data.birminghamal.gov`) + Accela.

**Verdict: NO REGISTER (all four families Tier 3).** The CKAN is alive as a
portal — crime, courts, and finance datasets were modified in August 2026 —
but every family dataset on it is a frozen annual-file archive (2015–2019).
The live permit workflow is Accela Citizen Access (UI-only). No city-owned
live permits/311/license/deed feed found on Socrata, AGOL, or Hub.

---

## Method, and its limits

1. Hostname fingerprint: `data.birminghamal.gov` (HTTP 301 → HTTPS; CKAN
   `status_show` 200, **CKAN 2.9.11**), Socrata discovery (`domains=`
   → 0 results), Hub placeholders `birminghamal.opendata.arcgis.com` and
   `data-birminghamal.opendata.arcgis.com` (8 KB generic landing pages;
   Hub v1/v3 search APIs return **401 "private org … not accessible"**),
   `gis.birminghamal.gov` (DNS fail).
2. CKAN package_search per family: `permit` (34), `service request` (9),
   `business license` (8), `sales` (14), `property` (17); package_show on
   the survivors; newest resource `last_modified` per package; recent
   datasets sorted by `metadata_modified` to confirm the portal itself is
   maintained.
3. AGOL `sharing/rest/search` for Birmingham permit Feature Services
   (third-party/stale hits only); Accela ACA fingerprint
   (`aca-prod.accela.com/BIRMINGHAM/Welcome.aspx` → 200).

Limits: CKAN datastore API was not exercised row-by-row because every
family resource is a per-year downloadable file whose newest is 2019 or
older — there is no live table to watermark. A token-gated internal
ArcGIS Server cannot be ruled out from the outside.

---

## Headline table

| Family | Endpoint | Newest row (watermark) | Geocoding | Recent window | Tier |
|---|---|---|---|---|---|
| **PERMITS** | CKAN `building-permits-and-valuations-2017` (annual XLSX/CSV files) | 2017 file; newest resource `last_modified` 2017-06-09 | address columns in files; no live feed | none (no 2026 rows) | **3** |
| **311** | CKAN `311-cases-yearly` (annual files 2015–2019) | newest file is 2019 YTD (`2019cases.csv`, `last_modified` 2021-07-29) | address fields in files; feed dead | none | **3** |
| **SLA** | CKAN `new-business-licenses-issued` (Economic Development annual report XLSX, 2016–2017) | 2017 YTD file | n/a | none | **3** |
| **DEEDS** | none. Only "City Interest Real Property For Sale Or Development" (city surplus listings) | n/a | n/a | n/a | **3** |

**Keep or reject: needs-triage / defer.** No family is registrable today.
Re-probe trigger: Birmingham publishing live permit or 311 extracts to the
CKAN (the portal is maintained — crime files landed 2026-08-24 — so a
family revival is plausible but has not happened).

---

## Portal inventory

| Surface | What it is | Feed? |
|---|---|---|
| `data.birminghamal.gov` | CKAN 2.9.11 (Opengov stack). ~150+ datasets; live ones are crime/courts/finance | families frozen |
| `aca-prod.accela.com/birmingham` | Accela Citizen Access (permits/inspection portal) | UI only |
| `birminghamal.opendata.arcgis.com`, `data-birminghamal.opendata.arcgis.com` | ArcGIS Hub placeholders, org private, API 401 | no |
| Socrata | no domain | no |

Non-family live data on the CKAN (do not register as 311/SLA/deeds):
2026 YTD Part I Offenses, precinct crime files, Municipal Court dockets,
Capital Projects Status.

---

## Decision

**Do not register Birmingham as a Wave-3 metro.** All four families Tier 3:
CKAN family datasets are frozen annual files (permits ≤2017, 311 ≤2019,
licenses ≤2017, no deeds), and the operational systems (Accela) are UI-only.
Leave ticket in needs-triage with a re-probe trigger on CKAN family revival.
Stamp: 2026-08-28.
