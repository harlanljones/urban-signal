# Wave 3 Phase-0 probe — Providence, RI

**Date of probe: 2026-08-27.** Row-level Socrata reads plus portal
replacements (ArcGIS Hub, PVD311 / Power Apps, SeeClickFix Open311,
ViewPoint / RI e-permitting, Kofile land evidence). "Newest row" is
`$order=<watermark> DESC` on the resource, not catalog `modified` /
`data_updated_at`.

**Verdict: REJECT.** All four feed families are Tier 3. Nothing live
and (natively geocoded or address-geocodable) on a supported client.
Operational systems exist behind citizen portals; none publish a
watermarked event extract.

Domain: **`data.providenceri.gov`** (Socrata; discovery
`resultSetSize=297`). Sister GIS hub
`providence-gis-hub-pvdgis.hub.arcgis.com` is reference layers only.

---

## Method, and its limits

1. Membership: `api.us.socrata.com/api/catalog/v1?domains=` against
   twelve hostname guesses. Only `data.providenceri.gov` answers (297).
2. Full catalog page (`offset` 0/100/200) and name-triage of every
   title, plus family queries (`building permits`, `311`, `service
   requests`, `business licenses`, `property sales`, plus synonyms).
3. Direct `/resource/<id>.json` on every family-shaped hit: column
   list, `count(*)`, newest/oldest watermark, 7d/60d/calendar-year
   windows.
4. Replacement hunt: city GIS Hub DCAT (63 items), PVD311
   (`311.providenceri.gov`), SeeClickFix Open311 at City Hall lat/lng,
   `providenceri.viewpointcloud.com` / `permits.ri.gov`, Board of
   Licenses, Recorder of Deeds / Kofile, RI LandRecords.com.

Limits: `/api/views/*` is 403 without an app token, so columns come
from sample rows. Hub `modified` is item metadata (ignored as
freshness). Citizen-portal UIs were fingerprinted, not scraped. A
dataset that is unpublished *and* unnamed cannot be ruled out, but
the 297-item catalog was read in full.

---

## Headline table

| Family | Best Socrata hit | Newest row (watermark) | Geocoding | 60d / 7d | Tier |
|---|---|---|---|---|---|
| **PERMITS** | `ufmm-rbej` Department of Inspections and Standards Permits 2009–2018 | `issueddate` = **2020-01-23**; `applieddate` = 2019-10-24 | native `geocoded_column` (77,025 / 80,874) + address | **0 / 0** | **3** |
| **311** | none. Closest: `tisk-wsvu` Pothole Tracking | `date_filled` = **2016-12-08** | street name only | 0 / 0 | **3** |
| **SLA** | `ui7z-kv69` Active Business Licenses (collapsed); `2f79-9nkc` Monthly Entertainment Licenses; `u7ik-g787` Mobile Food Establishments | ABL: 1 row, `permit_date` **2011-09-27**; entertainment `date_submitted` **2020-01-02**; food `date_issued` **2020-01-07** | ABL has `geolocation` (1 row); food has no address | 0 / 0 | **3** |
| **DEEDS** | none. Closest: `6ub4-iebe` 2025 Property Tax Roll (annual CAMA snapshot, **no sale/transfer date**) | no transaction watermark | point `property_location` + `formated_address` | n/a | **3** |

Prior 2026-08 surveys (`socrata-sweep.md`, `wave-2-city-candidates.md`)
called this "catalog answers, feeds 2020–2025 stale / 311 only". The
row-level re-probe **confirms the stale archives and does not find a
live 311 extract**. The live thing on the portal is police, not 311.

**Keep or reject: REJECT.** Do not register Providence. Do not park a
partial city on police-crime or the tax roll.

---

## Permits — Tier 3 (closed archive)

`https://data.providenceri.gov/resource/ufmm-rbej.json`

80,874 rows, 24 columns. Watermark `issueddate` newest **2020-01-23**
(PLUM-19-259, 116 Upton Ave). Calendar-year issued counts: 2017
8,206 · 2018 7,539 · 2019 6,545 · **2020 18 · 2021–2026 0**. 58,451
rows have null `issueddate`; `applieddate` last appears in 2019 (7,405
that year, 0 in 2020+). Native point geocode on 95% of rows plus
`originaladdress1` — spatial contract would have been fine if the
feed were live.

Special-event calendars (`sh7x-zyv3`, `rv3y-tq8q`) are not building
permits; newest `event_start` on `rv3y-tq8q` is 2022-05-07.

**Live replacement, not a feed:** permitting moved to OpenGov ViewPoint
Cloud (`providenceri.viewpointcloud.com`, DIS Building Permit record
type) and the RI Statewide E-Permitting portal (`permits.ri.gov`,
Providence listed since 2016-12-22). Both are account-gated application
UIs, not paginated JSON with a watermark. No Accela ACA host answered.
Not registrable on the existing Socrata/ArcGIS/CKAN/CSV clients.

---

## 311 — Tier 3 (no municipal extract)

Full-catalog name search: **zero** datasets titled 311, SeeClickFix,
QAlert, Cityworks, or constituent/service request. The
`service requests` catalog query's top hit is
`rz3y-pz8v` Providence Police Case Log — crime, not 311 (see
Non-family live data below).

`tisk-wsvu` Pothole Tracking: 3,804 rows, newest `date_filled`
**2016-12-08**. Dead.

**PVD311 is live as a CRM, not as open data.**
`https://311.providenceri.gov/` is a Microsoft Power Apps / Dynamics
portal (`gov.content.powerapps.us`, title "Constituent Services").
`/public-requests` and `/my-requests/new-request/` exist; `/_odata`
404s, Dataverse `api/data/v9.2` returns 406, `?format=json` still
serves HTML. No bulk extract, no watermark column, no existing-client
endpoint.

**SeeClickFix is a stale third-party leftover.** Place
`seeclickfix.com/providence` still renders. Unscoped Open311
`/open311/v2/requests.json?lat=41.824&long=-71.413` returns 20 rows
whose newest `requested_datetime` is **2021-09-09**;
`/services.json` at the same point is `[]`. SCF APIv2 `/issues` is
403. SCF's own license is CC-BY-NC-SA and forbids bulk reuse without
contact. Even if it were live, it would be a new client *and* a
license reject.

The prior sweep's "311 only" reading does not survive row-level
evidence: there is no 311 table on Socrata, and the public SCF
archive stopped in 2021. PVD311 replaced it behind a portal.

---

## SLA — Tier 3 (collapsed + 2020-stale)

| Dataset | Rows | Newest watermark | Note |
|---|---|---|---|
| `ui7z-kv69` Active Business Licenses | **1** | `permit_date` 2011-09-27; `expiration_date` 2101-10-31 sentinel | Catalog `data_updated_at` 2021-12-18 is a lie. Table is a single AS220 entertainment row at 115 Empire St with `geolocation`. |
| `vmru-8i5x` ABL_GIS | 1 | same row | Catalog type `filter` on the above. |
| `2f79-9nkc` Monthly Entertainment Licenses | 654 | `date_submitted` **2020-01-02** | Address-only `business_address`. 0 rows in 2021+. |
| `u7ik-g787` Mobile Food Establishments | 621 | `date_issued` **2020-01-07** | No address/coords. 0 rows in 2021+. |

**Live replacement, not a feed:** Board of Licenses
(`providenceri.gov/board-of-licenses/`) points at the same ViewPoint
Cloud portal and an IQM2 agenda board. No Socrata/ArcGIS license
registry.

---

## Deeds — Tier 3 (no transaction stream)

No catalog hit on property sales, transfers, recorded deeds, or
conveyances is a transaction table. "Sales" matches the collapsed ABL
table and a FY2010–2014 spending file.

`6ub4-iebe` **2025 Property Tax Roll**: 44,372 rows, point
`property_location`, `formated_address`, assessed value / tax. **No
sale date, sale price, grantor, grantee, or document number.** It is
an annual CAMA snapshot (catalog touched 2026-08-13). Sibling rolls
2005–2024 were bulk-reuploaded 2026-06-17 — that is catalog
maintenance, not a live transfer feed. Same shape as a parcel file,
not ACRIS.

`4hhd-fzq6` Unclaimed Property: uncashed city checks, newest
`check_date` 2025-08-26. Not deeds.

`nyp3-msmz` / `78bu-i8at` parcels: 2017 vintage polygons, no sale
fields.

GIS Hub parcel items (`06c4cfd2…` File GDB, `ad3d88d3…` shapefile) are
downloadable reference layers, not FeatureServer query endpoints.

**Live replacement, not a feed:** Recorder of Deeds is a Kofile
CountyFusion login (`countyfusion10.kofiletech.us`), records from
2004-08-01. RI LandRecords.com (`i2b.uslandrecords.com/RI/`) lists
other municipalities; **Providence is not in the dropdown**. No open
JSON/CSV of recorded documents.

---

## Non-family live data (do not register as 311 / deeds)

These are live today and will re-tempt a coarse catalog scan:

| Dataset | Newest row | Why it is not a family |
|---|---|---|
| `rz3y-pz8v` Police Case Log — Past 180 days | `reported_date` **2026-08-27T04:24:00**; 213 / 7d, 1,809 / 60d; 5,401 rows | Crime. Address is a hundred-block string (`100 Block 10TH ST`); no lat/lng. |
| `vank-fyx9` Arrests and Citations — Past 180 days | catalog `data_updated_at` 2026-08-27 | Same: public-safety, not 311. |
| `6ub4-iebe` 2025 Property Tax Roll | annual vintage | Assessment snapshot, no transfer watermark. |
| `9zbu-vjd2` 2025 City Holiday Schedule | n/a | Calendar. |

---

## Replacement platforms (none registrable)

| Surface | What it is | Feed? |
|---|---|---|
| `data.providenceri.gov` | Socrata, 297 assets | Four families stale / absent |
| `providence-gis-hub-pvdgis.hub.arcgis.com` | ArcGIS Hub, 63 DCAT items | Boundaries, zoning, parcels, trash-day apps. Zero permits/311/SLA/sales FeatureServers. |
| `311.providenceri.gov` | Power Apps PVD311 | Live CRM UI; no OData/Dataverse extract |
| SeeClickFix `providence` | Third-party 311 archive | Newest Open311 row 2021-09-09; NC license |
| ViewPoint Cloud / `permits.ri.gov` | E-permitting + licenses | Account UI, not an event API |
| Kofile CountyFusion | Land evidence | Login-walled images, not a stream |

No fifth-client build is justified: there is nothing public to point
one at.

---

## Decision

**Reject Providence for Wave 3 registration.** Re-probe only if the
city publishes a Socrata/ArcGIS/CKAN/CSV extract of ViewPoint permits,
PVD311, Board of Licenses, or recorded deeds with a row-level
watermark inside ~7–60 days. Until then the 2020–2025 stale reading
stands, and the "311 only" caveat is withdrawn: 311 is a portal, not
a feed.
