# Wave 3 Phase-0 probe — Lynchburg, VA (US-318)

**Date of probe: 2026-08-27/28.** Row-level reads (ArcGIS `query` ordered by
watermark DESC / windowed `returnCountOnly`). Catalog dates ignored as
issuance evidence.

**Verdict: REGISTER (strong).** Three of four families registerable off one
open-data mirror: permits Tier 1 (same-day live, native points), business
licenses Tier 1 (live register, native points), property transfers Tier 2
(live, parcel-key/address geocode). 311 Tier 3. All data sits on a single
MapServer — no new client beyond `ArcGISClient`.

Platform: **ArcGIS Server** `https://mapviewer.lynchburgva.gov/arcgis/rest/services/OpenData/ODPDynamic/MapServer`
— one SDE open-data service ("intended for use by the Open Data Portal —
data.cityoflynchburg.opendata.arcgis.com"). The advertised Hub host
`lynchburgva.opendata.arcgis.com` is a **private-org placeholder** (Hub v3
401 Unauthorized); `data.lynchburgva.gov` DNS-fails. The real AGOL org is
`7UD44zrYCKZqL1ix` (owner `LynchburgGIS`, 398 feature services; tabular
items are AGOL views onto the ODPDynamic layers). Not Socrata, not CKAN.

---

## Method, and its limits

1. Hostname fingerprint + Hub v3 on two `.opendata.arcgis.com` hosts;
   AGOL global search found org `7UD44zrYCKZqL1ix` via owner
   `LynchburgGIS`.
2. Family keyword search inside the org (permit / service request /
   license / sales / deed / 311 / citizen request): "Building Permits —
   Locations/Tabular", "Business Licenses — Locations/Tabular",
   "Transfers — Tabular", "Development Projects", "Violation Cases",
   "Inspections". No 311/citizen-request layer.
3. Row-level on every survivor: fields, counts, newest watermark row,
   7d/60d/2026 window counts, geometry check on the Locations layers.

Limits: the ODPDynamic service (v10.91) advertises 51 layers + 6 tables;
tabular layers are non-spatial tables served at indices 33–40. Watermark
columns are date-typed; `orderByFields` + `date '…'` comparisons verified
working. No row-level check on the QAlert/SeeClickFix intake (Lynchburg
has no municipal 311 app found).

---

## Headline table

| Family | Endpoint | Newest row (watermark) | Geocoding | Recent window | Tier |
|---|---|---|---|---|---|
| **PERMITS** | `ODPDynamic/MapServer/18` (Locations) + `/37` (Tabular) | `StartDate` = **2026-08-26** | native points (49,076) + `Address` | 7d **36**; Aug **134**; 2026 **1,382**; total **49,757** | **1** |
| **311** | none found | n/a | n/a | n/a | **3** |
| **SLA** | `ODPDynamic/MapServer/2` (Locations) + `/33` (Tabular) | `LicenseIssued` = **2026-08-21** | native points (4,609 OBJECTIDs) + address | 7d **1**; 60d **25**; 2026 **77** | **1** (register, low volume) |
| **DEEDS** | `ODPDynamic/MapServer/34` (Transfers — Tabular) | `SaleDate` = **2026-08-26** | no address col — geocode via `LRSN`→Parcel join or ADR 0004 | 7d **38**; 60d **430**; Aug **197**; total **195,460** | **2** |

---

## Permits — Tier 1 (register)

Layer 37 `Building Permits - Tabluar` (49,757 rows) + layer 18
`Building Permits - Locations` (49,076 points).

- Columns: `RecordNo` (`COM26-00381`, `RES26-00798`), `Address`,
  `Name` (work description), `Type` (`BUILDING`), `SubType`
  (`ADDITION`/`REPAIR`/`NEW CONSTRUCTION`), `StartDate`, `EndDate`,
  `Status` (`APPROVED`/`EXPIRED`/…), `Neighborhood`, `JobValue`,
  `ParcelID`, `Contact`, `Owner_TRAKiT` (source system is TRAKiT).
- Watermark **`StartDate`** (date-typed). Newest row 2026-08-26
  (COM26-00293, 2000 Enterprise Dr, Azzel steel storage building,
  $75,000). Records are current-year series — daily cadence confirmed.
- Geocoding: layer 18 carries point geometry keyed by the same
  `RecordNo`; layer 37 is address-only. Register the pair (or 37 with
  ADR 0004 as fallback).
- id_keys: `["RecordNo"]`. Filter `Status` to approved/issued at
  registration (EXPIRED majority is historical).
- Client fit: existing `ArcGISClient` (MapServer layer, not
  FeatureServer — confirm client supports MapServer/`query` endpoints;
  Lynchburg ODPDynamic layers answer the same `/query` grammar).

## SLA — Tier 1 (register; low-volume)

Layer 33 `Business Licenses - Tabular` (2,182 rows) + layer 2
`Business License - Locations` (points with the same
`LicenseNumber`).

- Columns: `LicenseNumber` (031386…), `Company`, `TradeName`, `Status`
  (`ACTIVE`), `LicenseIssued`, `LicenseExpires` (2027-06…),
  `BusinessType` (`01 Retail Merchant`), `FeeType`, mail address parts,
  `ParcelID`.
- Watermark **`LicenseIssued`**. Newest 2026-08-21 (Needle Ninja LLC,
  924 Main St). 2026 YTD 77; 60d 25; 7d 1. Annual licenses renew
  mid-year — trickle cadence is the register's nature, not staleness.
- Geocode: layer 2 points (`ConcatenatedAddress` = `924 MAIN ST`);
  tabular side has mail-address parts → ADR 0004 fallback.
- id_keys: `["LicenseNumber"]`.

## Deeds — Tier 2 (register)

Layer 34 `Transfers - Tabular` — **195,460** rows.

- Columns: `LRSN`, `SaleDate`, `SaleAmount`, `DocumentNo`
  (`260005545`), `DocumentRef`, `Seller`, `Buyer`, `SaleType`,
  `TransferType`, `ConveyanceForm`.
- Watermark **`SaleDate`** (date-typed). Newest **2026-08-26**
  (DocNum 260000257) — same-day. 7d **38**, 60d **430**, Aug 2026
  **197**. Weekly-to-daily deed pull from the circuit court; live.
- Geocode: no street address on transfers. Path A: join `LRSN` →
  Parcel layer (41) for situs address; Path B: ADR 0004 with a
  parcel-key context. DocNum carries the leading "2600…" year series
  (2026 documents present). SaleAmount 0 on some non-arm's-length
  deeds — keep, don't drop.

## 311 — Tier 3

- No citizen-request layer in ODPDynamic (51 layers walked).
  `Violation Cases` (30/38) is TRAKiT **code enforcement**
  (`ZON26-…` records, newest 2026-08-21) — wrong family, do not
  register as 311.
- `CrisisTrack - Residential/Commercial` (43/44) are damage-assessment
  layers. SeeClickFix place for Lynchburg not confirmed; municipal
  bulk feed absent either way.

---

## Hostnames tried (negatives)

| Surface | Result |
|---|---|
| `lynchburgva.opendata.arcgis.com` | Hub placeholder, **private org** (401) |
| `data.lynchburgva.gov`, `gis./maps./opendata.lynchburgva.gov` | DNS fail |
| `data.cityoflynchburg.opendata.arcgis.com` | named in the service description; Hub search returned no items (placeholder) |
| Socrata discovery / CKAN | absent |

## Registration sketch (summary)

One base URL, three layers:
`https://mapviewer.lynchburgva.gov/arcgis/rest/services/OpenData/ODPDynamic/MapServer`
- PERMITS → `/37` (tabular; `/18` points), watermark `StartDate`,
  id_keys `RecordNo`, cadence 1d.
- SLA → `/33` (tabular; `/2` points), watermark `LicenseIssued`,
  id_keys `LicenseNumber`.
- DEEDS → `/34`, watermark `SaleDate`, id_keys
  `["LRSN","DocumentNo"]`, `needs_geocode=True` via parcel key.
- 311 → `get_dataset()` raises.

Re-probe all three watermarks ≤72 h before the implementation wave.
Stamp: 2026-08-28.
