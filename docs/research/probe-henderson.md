# Wave 3 Phase-0 probe — Henderson, NV

**Probe stamp: 2026-08-27.** Every host, dataset, watermark, and row below was
read live that day. Hub `item.modified` is a label only; freshness evidence is
newest-row-by-watermark.

Linear: **US-325**. Ticket hint was ArcGIS Hub (`opendata.cityofhenderson.com`
→ 302 → `gis-hendersonnv.opendata.arcgis.com`).

Success criterion (Wave 3 / ADR 0004): live **and** (native geometry **or**
address-geocodable). Tiers: **1** live + native geocode; **2** live +
address-only; **3** stale / absent / wrong family.

## Platform

| Host | What it is | Probe |
|---|---|---|
| `gis-hendersonnv.opendata.arcgis.com` | ArcGIS Hub (owner `HendersonNV_GIS`, AGOL org `naGsY5NZWVbd6bwD` on `services2.arcgis.com`) | STAC search `/api/search/v1/collections/dataset/items?q=…` |
| `maps.cityofhenderson.com/arcgis/rest/services` | City ArcGIS Server (`public/OpenDevPermits`, `public/OpenDataGovernment`) | live |
| `www.cityofhenderson.com` | city web | **403, AkamaiGHost WAF** (same wall-family as the OKC Incapsula precedent; do not scrape HTML — use REST) |

Hub search quirk: the v1 **collection** endpoint returns an empty shell;
query **`/items`** (`…/collections/dataset/items?q=…`) for results. The
ticket's `opendata.cityofhenderson.com` redirects to
`gis-hendersonnv.opendata.arcgis.com`.

## Summary

| Family | Dataset | Newest watermark | Geocode | 7d / 60d | Tier |
|---|---|---|---|---|---|
| **PERMITS** | `DSC_Permits` FeatureServer + full-history CSV | `IssueDate` **2026-08-25** (FS) / **2026-08-28** (CSV, local-time artifact) | native `GISX`/`GISY` (nulls 3,320 / 28,137 = 11.8%) + address parts | **106 / 4,179** (FS) | **1** |
| **311** | none on Hub | — | — | — | **3** |
| **SLA** | `Active Business Licenses` CSV + `All Business Licenses (MJBL)` CSV | Active: `Original Issue Date` **2026-08-21**; MJBL: `IssueDate` **2026-08-26 19:08** | address-only → ADR 0004 | Active **19 / 391**; MJBL **63 / 416** | **2** |
| **DEEDS** | none (Clark County recording) | — | — | — | **3** |

**Wave-3-ready: yes** (PERMITS Tier 1 + SLA Tier 2). Same shape as
Boise/Austin partials: 311 and deeds raise.

## Permits — Tier 1 (register)

### FeatureServer (registrable endpoint)

- **URL:** `https://services2.arcgis.com/naGsY5NZWVbd6bwD/arcgis/rest/services/DSC_Permits/FeatureServer/0`
- **Rows:** 28,137. `maxRecordCount=1000`, AGOL-hosted (v12).
- **Watermark:** `IssueDate` (esriFieldTypeDate). Newest **2026-08-25**;
  windows: **7d=106** (≥2026-08-20), **60d=4,179** (≥2026-06-28).
- **Columns (selected):** `ApplyDate`, `ExpireDate`, `IssueDate`,
  `FinalizedDate`, `PermitType`, `WorkClass`, `PermitNumber`,
  `PermitDescription`, `PermitStatus`, `Category`, `CommercialValue`,
  `ResidentialValue`, `ValuationTotal`, `ParcelNumber`,
  `ParcelAddressNumber/PreDirection/Street/StreetType/City/State/Zip`,
  `OwnerName`, `GISX`, `GISY`, `ObjectId`.
- **Geocoding:** `GISX`/`GISY` null on 3,320 / 28,137 (**11.8%**) — native
  coords for ~88%, address-part fallback (ADR 0004) for the rest.
- **Id keys:** `PermitNumber` + `ObjectId`.
- **Status mix:** Done / Expired / Active-Issued / Pending (see CSV below);
  filter to issued classes at registration.
- **Cadence:** daily (newest = probe-day minus 2). `expected_cadence_days: 1`.

### Full-history CSV (companion)

- **Item:** `53e66cc908fa4bcfbb81aa84cd5e2982` ("DSC Permits", 137.9 MB),
  download `https://www.arcgis.com/sharing/rest/content/items/53e66cc908fa4bcfbb81aa84cd5e2982/data`
- **272,250 rows** (IssueDate on 261,295; blank 10,955), 2017-02-21 →
  **2026-08-28**. `IssueDate` text format **`MM-DD-YYYY HH:MM`** (ADR 0005
  `watermark_type="text"`). The single newest value is probe-day+1 — treat
  **future-dated rows (≥ probe day) as sentinels to exclude** from the high
  watermark, same discipline as Albuquerque.
- **Status mix:** Done 164,445 / Expired 85,588 / Active-Issued 12,579 /
  Pending 8,128 / Template 1,183 / Hold 193.
- FeatureServer appears to be a filtered/recent view of this CSV; register the
  FS as primary (geometry) and the CSV as bulk backfill companion.

## 311 — Tier 3

Hub `q=311` → **0 datasets**. No Open311 endpoint found.

## SLA — Tier 2 (register; address-only)

### Active Business Licenses (CSV)

- **Item:** `2b3fac57210542229afc4bfddd6cd6e8` (3.9 MB; mod 2026-08-21)
- **12,851 rows**, all `Primary Jurisdiction = City of Henderson`.
- **Columns:** `License Number`, `Entity Name`, `DBA`, `Business Location`,
  City/State/Zip, `Business Phone`, `Original Issue Date`, `Expiration Date`,
  `License Type`, `License Sub-Type`, `Business Description`,
  jurisdiction flags, billing address.
- **Watermark:** `Original Issue Date` (`M/D/YYYY`). Newest **2026-08-21**;
  **7d=19**, **60d=391**. 12,848/12,851 have a date.
- **Geocoding:** address-only (`Business Location`, City, State, Zip) →
  `needs_geocode=True`, `geocode_context="Henderson, NV"`.
- **Id keys:** `License Number`.

### All Business Licenses — MJBL (CSV, companion)

- **Item:** `6c470a95e83e4051a4d1222afa056ed6` (12.8 MB; mod 2026-08-24)
- **50,554 rows county-wide** (ACTIVE 23,257 / INACTIVE 20,042 / EXPIRED
  6,929 / PENDING 326); Henderson rows 11,219; Las Vegas 15,191; Clark County
  13,919; North Las Vegas 10,225 — **filter `Jurisdiction='HENDERSON'`**.
- **Watermark:** `IssueDate` (`MM-DD-YYYY HH:MM`). Newest **2026-08-26
  19:08** (intraday — near-hourly republication); `UpdatedDate` max
  2026-08-26 20:08. **7d=63**, **60d=416**. `BusinessAddress` on 100%.
- **Id keys:** `MJBLNumber` + `IsPrimary`.
- Frozen lookalike: `Business Licenses` FeatureServer
  (`public/OpenDataGovernment/MapServer/0`, mod 2022) — **do not register**;
  row-frozen twin of the live CSVs.

## Deeds — Tier 3

Clark County Recorder has no anonymous bulk deed/sales API; Henderson Hub has
no sale dataset (`q=sale` → 0).

## Registration contract (`henderson`)

| Feed | Dataset (watermark) | Platform | field_map budget | Quirks tests must pin |
|---|---|---|---|---|
| PERMITS | `DSC_Permits/FeatureServer/0` (`IssueDate`) · companion CSV item `53e66cc9…` (`MM-DD-YYYY HH:MM`) | arcgis + csv | ~10 | GISX/GISY 11.8% nulls → address fallback; CSV future-dated sentinel exclude; status filter; `expected_cadence_days: 1` |
| SLA | Active Licenses CSV item `2b3fac57…` (`Original Issue Date`) · MJBL CSV item `6c470a95…` (`IssueDate`, filter HENDERSON) | csv ×2 | ~8 | address-only (needs_geocode, context "Henderson, NV"); MJBL county-wide filter; text watermarks; Active 7d≈19 is normal (small city) |

Suggested spec payloads (leaf `cities/henderson.py`, not applied this ticket):

```
PERMITS
  endpoint: https://services2.arcgis.com/naGsY5NZWVbd6bwD/arcgis/rest/services/DSC_Permits/FeatureServer/0
  platform: arcgis
  watermark_col: IssueDate
  id_keys: [PermitNumber, ObjectId]
  extra:
    expected_cadence_days: 1
    max_record_count: 1000
    companion: csv item 53e66cc908fa4bcfbb81aa84cd5e2982 (IssueDate %m-%d-%Y %H:%M, exclude >= probe-day sentinels)
    field_map:
      permit_id: [PermitNumber]
      issuance_date: [IssueDate]
      filing_date: [ApplyDate]
      status: [PermitStatus]
      job_type: [PermitType, WorkClass, Category]
      valuation: [ValuationTotal]
      address_street: [ParcelAddressNumber, ParcelAddressPreDirection, ParcelAddressStreet, ParcelAddressStreetType]
      city: [ParcelAddressCity]
      zipcode: [ParcelAddressZip]
      # lat/lng from GISX/GISY (null on ~11.8% -> geocode fallback)

SLA
  endpoint: https://www.arcgis.com/sharing/rest/content/items/2b3fac57210542229afc4bfddd6cd6e8/data
  platform: csv
  watermark_col: "Original Issue Date"
  watermark_type: text
  watermark_format: "%m/%d/%Y"
  id_keys: ["License Number"]
  extra:
    needs_geocode: True
    geocode_context: "Henderson, NV"
    companion: csv item 6c470a95e83e4051a4d1222afa056ed6 (MJBL, Jurisdiction=HENDERSON, IssueDate %m-%d-%Y %H:%M)
    field_map:
      license_id: ["License Number"]
      dba: [DBA, "Entity Name"]
      license_type: ["License Type", "License Sub-Type"]
      effective_date: ["Original Issue Date"]
      expiration_date: ["Expiration Date"]
      address_street: ["Business Location"]
```

G5 ≥ 99% reachable: permits via native GISX/Y + address fallback; SLA via
ADR 0004 geocoder on `Business Location`.
