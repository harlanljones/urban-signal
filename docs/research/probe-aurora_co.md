# Wave 3 Phase-0 probe — Aurora, CO

**Probe stamp: 2026-08-27.** Every host, dataset, watermark, and row below was
read live that day. Hub `item.modified` is a label only; freshness evidence is
newest-row-by-watermark.

Linear: **US-326**. Ticket hint was ArcGIS Hub
(`data-auroraco.opendata.arcgis.com`).

Success criterion (Wave 3 / ADR 0004): live **and** (native geometry **or**
address-geocodable). Tiers: **1** live + native geocode; **2** live +
address-only; **3** stale / absent / wrong family.

## Platform

| Host | What it is | Probe |
|---|---|---|
| `data-auroraco.opendata.arcgis.com` | ArcGIS Hub ("City of Aurora, Colorado") | STAC `/api/search/v1/collections/dataset/items` — **13 permit hits**, 4 license |
| `ags.auroragov.org/aurora/rest/services/OpenData/MapServer` | City ArcGIS Server — **the live layers** (250+ layers incl. 44/156/157 permits, 4/34/36/77 licenses) | live |

Hub search quirk: same as Henderson — query `/items`, not the collection root.

## Summary

| Family | Dataset | Newest watermark | Geocode | 7d / 60d | Tier |
|---|---|---|---|---|---|
| **PERMITS** | `OpenData/MapServer/44` "Building Permits" (full) + rolling views L156 (6mo) / L157 (1mo) | `IssueDate` **2026-08-26 18:30** | native point + `PropX`/`PropY` (nulls 8,231 / 162,767 = 5.1%); `Address` null 8,082 | **317 / 2,582**; 2026 YTD 9,734 | **1** |
| **311** | none on Hub (`q=311` → 0) | — | — | — | **3** |
| **SLA** | L34 Liquor (545), L77 Businesses-All-Non-Home (8,528), L36 Businesses (12,721), L4 Marijuana (26) | L34 `Issue_Date` **2026-08-17**; L77 **2026-08-21** | native `X`/`Y` + point | L77 60d=166; L34 60d=1 (start-date based) | **1** |
| **DEEDS** | none (Arapahoe/Adams/Douglas county recording) | — | — | — | **3** |

**Wave-3-ready: yes** (PERMITS Tier 1 + SLA Tier 1).

## Permits — Tier 1 (register)

### Primary — `OpenData/MapServer/44` "Building Permits" (full history)

- **URL:** `https://ags.auroragov.org/aurora/rest/services/OpenData/MapServer/44`
- **Rows:** 162,767. Point geometry; native SR **WKID 2232** (NAD83 Colorado
  South ftUS) → `outSR=4326` per `ArcGISClient`.
- **Watermark:** `IssueDate` (esriFieldTypeDate). Newest **2026-08-26
  18:30:01 UTC** (probe-day). Windows: **7d=317** (≥2026-08-20),
  **60d=2,582** (≥2026-06-28), 2026 YTD **9,734**.
- **Columns:** `OBJECTID`, `FolderRSN`, `Permit_`, `InDate`, `FolderType`,
  `FolderDesc`, `FolderGroupDesc`, `SubDesc`, `FolderDescription`,
  `FolderCondition`, `IssueDate`, `valuation`, `PropertyRSN`, `PropX`,
  `PropY`, `Address`, `PropertyRoll`, `GlobalID`, `Shape`.
- **Geocoding:** `PropX` null 8,231 / 162,767 (**5.1%**); `Address` null
  8,082. Point geometry is the primary path; address fallback for the rest.
- **Id keys:** `Permit_` + `FolderRSN` + `OBJECTID`.
- **Cadence:** daily (newest = probe-day). `expected_cadence_days: 1`.
- Sample newest row: `26-2649763-000-00` Counter Permit, valuation 8,000,
  2349 N ELMIRA ST, issued 2026-08-26 18:30.

### Rolling-window views (companion / context, do not substitute)

- L157 "Building Permits 1 Month": 1,385 rows, IssueDate 2026-07-26 →
  2026-08-23, 7d=317, geocoded columns (`Match_addr`, `ARC_Street`,
  `PropX` null 84/1,385 = 6.1%).
- L156 "Building Permits 6 Months": 7,738 rows, 2026-02-24 → 2026-08-23.
- **Quirk:** both are **rolling windows** — rows age out. Register L44 as
  primary; the views only demonstrate the pipeline is current.

## 311 — Tier 3

Hub `q=311` → 0. "Access Aurora" 311 has no bulk/Open311 surface found
(`auroragov.org` 311 page 404'd at probe).

## SLA — Tier 1 (register)

- **Liquor:** `OpenData/MapServer/34` — 545 rows; `License_Number`,
  `Business_Name`, `Business_Address`, `Start_Date`, `End_Date`, `Issue_Date`,
  NAICS, native `X`/`Y` + point. Max `Issue_Date` **2026-08-17** (live).
- **Businesses (All Non-Home):** `MapServer/77` — 8,528 rows; same schema.
  Max `Issue_Date` **2026-08-21**; **60d=166** (≥2026-06-28). LIVE.
- **Businesses (L36):** 12,721 rows (incl. home-based) — companion.
- **Marijuana Retail (L4):** 26 rows, max `Issue_Date` 2026-08-07 — tiny
  cap-limited universe; companion only.
- License rows are **current-license snapshots** with issue/start dates and
  live maintenance — same grain as Milwaukee/Denver liquor precedents. The
  `Start_Date` window is small because most licenses predate the 60d window;
  the watermark for freshness is `Issue_Date` max.

## Deeds — Tier 3

Aurora spans Arapahoe/Adams/Douglas counties; none publish an anonymous bulk
deed/sales stream. Hub `q=sale` → Urban Renewal Areas (planning) only.

## Registration contract (`aurora_co`)

| Feed | Dataset (watermark) | Platform | field_map budget | Quirks tests must pin |
|---|---|---|---|---|
| PERMITS | `OpenData/MapServer/44` (`IssueDate`) | arcgis | ~8 | WKID 2232 → `outSR=4326`; rolling L156/L157 are windows (don't register); PropX 5.1% null → address fallback; daily |
| SLA | L34 liquor + L77 non-home businesses (+L36/L4 companions) (`Issue_Date`) | arcgis ×2–4 | ~8 | native X/Y; snapshot grain (watermark = max Issue_Date, not window counts); 60d window small by design |

Suggested spec payloads (leaf `cities/aurora_co.py`, not applied this ticket):

```
PERMITS
  endpoint: https://ags.auroragov.org/aurora/rest/services/OpenData/MapServer/44
  platform: arcgis
  watermark_col: IssueDate
  id_keys: [Permit_, FolderRSN, OBJECTID]
  extra:
    expected_cadence_days: 1
    max_record_count: 2000
    field_map:
      permit_id: [Permit_]
      issuance_date: [IssueDate]
      filing_date: [InDate]
      job_type: [FolderDesc, FolderGroupDesc, SubDesc]
      status: [FolderCondition]
      valuation: [valuation]
      address_street: [Address]
      # lat/lng from geometry (outSR=4326); PropX/PropY fallback

SLA
  endpoint: https://ags.auroragov.org/aurora/rest/services/OpenData/MapServer/77
  platform: arcgis
  watermark_col: Issue_Date
  id_keys: [License_Number, entity_key, OBJECTID]
  extra:
    companion_endpoints:
      liquor: https://ags.auroragov.org/aurora/rest/services/OpenData/MapServer/34
      all_businesses: https://ags.auroragov.org/aurora/rest/services/OpenData/MapServer/36
      marijuana: https://ags.auroragov.org/aurora/rest/services/OpenData/MapServer/4
    field_map:
      license_id: [License_Number, TL_License_Number]
      dba: [Business_Name]
      license_type: [NAICS_Title, NAICS_Sector]
      effective_date: [Start_Date]
      expiration_date: [End_Date]
      address_street: [Business_Address, BusinessAddress_DirSuf]
      latitude: [Y]
      longitude: [X]
```

`needs_geocode` is **false** on both registered families (native points / X-Y).
