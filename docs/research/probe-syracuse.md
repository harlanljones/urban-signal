# Wave 3 Phase-0 probe — Syracuse, NY

**Date of probe: 2026-08-27.** Ticket US-352. The ticket's portal hint
(`data.cityofsyracuse.gov`) **does not resolve**; the live portal is the
City's ArcGIS Hub at **`data.syrgov.net`** (113 city items, AGOL org
`services6.arcgis.com/bdPqSfflsdgFRVVM`). Every row below read live that day.

## Headline verdict

**Register partial — SLA/licenses Tier 1 via the Syracuse Rental Registry;
permits frozen, 311 and deeds absent.** The Rental Registry is same-day
live (newest application **2026-08-26**, 13 in the last 7 days) with native
lat/lng 500/500. "Permit Requests" (47,902 rows) stops at **2025-08-16**
with weak geocode coverage — frozen, do not register.

| Family | Endpoint | Newest row (watermark) | Geocoding | Recent window | Tier |
|---|---|---|---|---|---|
| **SLA/licenses** (rental registration) | `services6.arcgis.com/bdPqSfflsdgFRVVM/.../Syracuse_Rental_Registry/FeatureServer/0` | `RR_app_received` = **2026-08-26** (1217 Park St, SBL 007.-30-21.0) | native `Latitude`/`Longitude` **500/500** newest + `PropertyAddress`/`zip` 500/500; point geom | 7d **13**; 60d **196**; 2026 YTD **1,254**; total 10,926 | **1** |
| PERMITS | `.../Permit_Requests/FeatureServer/0` (47,902 rows) | `Issue_Date` max **2025-08-16**; **0 rows in 2026**; 2 since Jun 2025 | LAT/LONG only 350/500 newest; addr 367/500 | 0 since 2025-08-16 | **3** (frozen ~1 yr) |
| 311 | none (`q=311` → **0**) | n/a | n/a | n/a | **3** |
| DEEDS | parcel maps (`QPD_2026_01_26_L1_ODP_view`, "2025 Q4", 68 fields) have **no sale/deed fields** | n/a | n/a | n/a | **3** |

## SLA/licenses — Syracuse Rental Registry, Tier 1 (register)

- **Rows:** 10,926 rental properties, point geometry, `maxRecordCount`
  default 1000/2000.
- **Columns:** `SBL` (parcel id, e.g. `007.-30-21.0`),
  `PropertyAddress`, `zip`, `NeedsRR`, `inspect_period`,
  `completion_type_name`, `completion_date`, `valid_until`, `RRisValid`,
  **`RR_app_received`** (watermark), `RR_ext_insp_pass/fail`,
  `RR_int_insp_pass/fail`, `RR_contact_name`, `pc_owner`, native
  `Latitude`/`Longitude`, `SHAPE`.
- **Watermark:** `RR_app_received` — newest **2026-08-26**, one day before
  the probe. 13 applications in 7 days; 196 in 60 days; 1,254 in 2026.
  Event-driven and current.
- **Geocoding:** native WGS84 `Latitude`/`Longitude` on 500/500 newest
  (43.02–43.07, −76.13…, inside Syracuse); addresses + zip 500/500. No ADR
  0004 dependency.
- **id_keys:** `SBL`. Renewals reappear as new applications — same
  multi-row-per-entity caveat as Buffalo licenses; key on `SBL` +
  `RR_app_received` if row-level idempotency is needed.
- **PII — drop at ingest:** `RR_contact_name`, `pc_owner`
  (owner name/address block `Add*`-style fields are not in this layer, but
  the two named columns must not ship).
- **Family note:** this is *rental-property registration*, a property-use
  license — the licenses family's strongest available grain in Syracuse;
  there is no general business-license feed (nothing under `q=license`
  except Permit Requests).
- Client: existing ArcGIS client.

## Permits — Tier 3 (frozen)

`Permit_Requests` (47,902 rows; `Permit_Number`, `Full_Address`, `Owner`,
`Issue_Date`, `Permit_Type`, `Description_of_Work`, `LONG`, `LAT`) has a
**2025-08-16 max** and 0 rows in 2026. The tail of the extract is block
party permits with null coordinates — a stale partial sync, not a live
stream. "Building Permits (2013–2019)" is an explicit archive. Re-probe if
the city resumes the sync (and expect the LAT/LONG gap to need ADR 0004).

## 311 — Tier 3 (absent)

`q=311` and `q=service request` return nothing; Syracuse 311 is a
CitizenServe/UI operation with no open extract.

## Deeds — Tier 3 (assessment only)

Quarterly parcel maps (2017–2025 Q4) carry 68 assessment/owner/utilities
fields — **no `SALE_DATE`, no `SALE_PRICE`, no deed book/page**. The
newest published quarterly is "2025 Q4" (service built 2026-01-26); there
is no transaction stream.

## Platform / method / limits

Hub OGC collections search on `data.syrgov.net`; AGOL item→URL resolution;
layer metadata; `outStatistics` max/count; `returnCountOnly` windows;
newest-row reads; 500-row geocode completeness. Socrata discovery:
`domains=data.syrgov.net` / `syrgov.net` → `Domain not found` (the Hub
"socrata-style" URL paths 404 — it is the new Hub UI, not Socrata). Limits:
the ticket hint hostname is dead (DNS), so the negative evidence for
"data.cityofsyracuse.gov" is DNS-level; the Hub catalog itself was read in
full for the families above.

## Decision

**Register Syracuse partial on SLA/licenses** (Rental Registry). Re-probe
`Permit_Requests` ≤72 h before any implementation wave; if the 2025-08-16
max has moved, re-grade. Stamp: 2026-08-27.
