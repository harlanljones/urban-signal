# Wave 3 Phase-0 probe — Buffalo, NY

**Date of probe: 2026-08-27.** Ticket US-349. Socrata portal
`data.buffalony.gov` (106 catalog datasets); every row below read live that
day, newest-row by watermark, catalog `updatedAt` never trusted.

## Headline verdict

**Register partial — SLA/licenses is Tier 1; permits and 311 are not
registrable.** The ticket's "Data fit: High" rests on permits + 311, and
both are broken in the portal today: every permit dataset in the catalog
fails with `Cannot read rows for view` (metadata refreshes daily; the
backends are gone), and the 311 extracts are frozen at **2024-05-10**.
The licenses family is the surprise: **Restaurant Licenses** is live
(7-day window 23), natively geocoded 500/500.

| Family | Endpoint | Newest row (watermark) | Geocoding | Recent window | Tier |
|---|---|---|---|---|---|
| **SLA/licenses** | `data.buffalony.gov/resource/4pp3-qkuj.json` (Restaurant Licenses) | `issdttm` = **2026-08-20** (RTO26-10058465, 235 Delaware) | native `latitude`/`longitude` **500/500** + `location` point geom + `address`/`zip` 500/500 | last-7d **23**; last-60d **253**; 2026 YTD **383**; total 1,429 | **1** |
| PERMITS | `e48j-dfaz` ("All permits since 1/1/2018") + every sibling | **unreadable** — Socrata `Cannot read rows for view` (tested e48j-dfaz, 3tnd-ht8n, bdaa-83my, fwsu-wwzs, i3tg-pndu; JSON + CSV endpoints) | n/a | n/a | **3** (broken backends) |
| 311 | `swrm-8aj4` (311_InitialFil), `wfjn-ivqa` (311 Filtered View) | `open_date` max **2024-05-10** (case 1002056634) | native lat/lng on newest rows | 0 since 2024-05-10 | **3** (frozen >2 yr) |
| DEEDS | none in the 106-item catalog | n/a | n/a | n/a | **3** |

## Platform

Resolved: **Socrata** (`data.buffalony.gov`, CiviSQL/BLDS-style extracts,
anonymous `resource/*.json`, `api/views/*.json` metadata). CKAN: not
applicable. No ArcGIS Hub found in the catalog domain list.

## Restaurant Licenses — Tier 1 (register)

- **Columns:** `aplickey`, `uniqkey`, `licenseno` (`RST26-10059075`,
  `RTO26-10058465`), `businessname`, `code`/`descript` (RST Restaurant, RTO
  Restaurant Take Out, …), `licstatus` (Active), `licensedttm` (original
  license date), **`issdttm`** (renewal/issuance — the watermark),
  `statusdttm`, `expdttm`, `prclid`, `gpsx`/`gpsy` (State Plane),
  `latitude`/`longitude` (WGS84 text), `address`, `city`, `state`, `zip`,
  `location` (GeoJSON point).
- **Watermark `issdttm`:** newest non-null **2026-08-20** (7 days before
  probe). Only **2/1,429** rows have null `issdttm` — but Socrata orders
  NULLs first on `…&$order=issdttm DESC`; always query
  `$where=issdttm IS NOT NULL`.
- **Cadence:** 23 issuances in the 7 days before probe; 253 in 60 days;
  383 in 2026 YTD. Event-driven, production-grade.
- **Geocoding:** native WGS84 `latitude`/`longitude` on 500/500 newest
  (42.83–42.92, −78.82…, inside Buffalo) + GeoJSON `location` point;
  `address` + `zip` 500/500. No ADR 0004 dependency.
- **id_keys caveat:** `licenseno` repeats across rows (e.g. `RST25-10057856`
  twice) — renewals produce multiple rows per license; key on
  `licenseno`+`issdttm` (or `uniqkey`) and dedupe.
- **Watermark caution:** `expdttm` max is 2027-09-30 — an *expiration*
  date; do not watermark on it. `licensedttm` is the original-license date,
  not the renewal stream.
- Client: existing Socrata client; no fifth platform.

## Permits — Tier 3 (broken backends)

All permit datasets carry a catalog `updatedAt` of **2026-08-27** (a
morning metadata refresh) yet fail row reads on both `/resource/<id>.json`
and `/resource/<id>.csv`:

| Dataset | id | Row read |
|---|---|---|
| All permits since 1/1/2018 | `e48j-dfaz` | `Cannot read rows for view` |
| Building Permits Issued in 2017 | `3tnd-ht8n` | same |
| Permits March 2018 | `bdaa-83my` | same |
| Window-Related Permits Since Jan 2018 | `fwsu-wwzs` | same |
| Permits related to windows and paint | `i3tg-pndu` | same |

This is exactly the catalog-lies case the wave-3 method exists for: the
`updatedAt` stamp is not issuance evidence. Non-permit datasets (311, code
violations, licenses) read fine from the same domain at the same time, so
the failure is per-dataset, not a portal outage. Re-probe `e48j-dfaz` — if
Buffalo ever fixes the backend, permits likely resumes as the Tier-1
anchor.

## 311 — Tier 3 (frozen)

- `311_InitialFil` (`swrm-8aj4`) and `311 Filtered View` (`wfjn-ivqa`):
  schema rich (`case_reference`, `open_date`, `closed_date`, `subject`,
  `reason`, `type`, address parts, `latitude`/`longitude`, council/police
  district, census geoms) — but newest `open_date` **2024-05-10**.
- The rest of the 311 family is filtered/specialized views with the same
  freeze (catalog `updatedAt` 2024-05/2025-01). Do not register a 2-year
  dead CRM extract.

## Deeds — Tier 3

Zero sales/deed/transfer datasets in the full 106-item catalog
(`q=sales`, `q=deed`, `q=property sales` → no municipal transaction
stream). Deeds live at Erie County; that is outside the city portal and was
not treated as registrable.

## Method, and its limits

Socrata discovery (`domains=data.buffalony.gov`, 106 rows, 2 pages);
family keyword search; `api/views/<id>.json` schema reads; row reads via
`$order=<watermark> DESC` with null-guards; `count(*)` window queries;
500-row geocode completeness. Limits: permit backends are unreadable, so no
row-level evidence exists for that family beyond the error itself; the
contractor-license dataset (`xu7s-vsr5`, General/Home/Handyman/Light
Commercial + trade subsets) has **no issuance date** (`status`, `expdate`
only) and was not treated as a second registrable feed. Citywide business
licensing beyond restaurants/contractors (e.g. taxi, salvage) did not
appear in the catalog.

## Decision

**Register Buffalo partial on SLA/licenses only** (Restaurant Licenses,
`4pp3-qkuj`). Re-probe `e48j-dfaz` permits ≤72 h before any implementation
wave; re-probe 311 only if Buffalo's CRM extract resumes. Stamp:
2026-08-27.
