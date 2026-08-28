# Wave 3 Phase-0 probe — Virginia Beach, VA (US-354)

**Date of probe: 2026-08-27/28.** Row-level ArcGIS reads (`query` ordered
by watermark DESC / windowed `returnCountOnly`). Catalog `modified`
ignored as issuance evidence.

**Verdict: REGISTER (three families).** Permits Tier 2 (live, daily,
address-only), business licenses Tier 2 (live register, address-only),
property sales Tier 2 (large live stream, batch cadence, address-only).
311 Tier 3. All three registerable layers are hosted FeatureServer
tables/views on the city's AGOL org — existing `ArcGISClient`, no fifth
client.

Platform: **ArcGIS Hub** at `data.virginiabeach.gov` ("The City of
Virginia Beach Open Data") over AGOL org `CyVvlIiUfRBmMQuu` (481 feature
services; the other org in the Hub, `36soGIYKLrgDhHrr`, is VBCPS school
zones). Hosted services at `services2.arcgis.com/CyVvlIiUfRBmMQuu/...`.
Not Socrata, not CKAN.

---

## Method, and its limits

1. Hostname fingerprint: `data.virginiabeach.gov` (Hub site, Hub Search
   API v3 live), `data.vbgov.com` (DNS fail), `vbgov.com` (city web).
2. Org enumeration via Hub v3 (two orgIds) then AGOL
   `sharing/rest/search` paged 1–300 over
   `orgid:CyVvlIiUfRBmMQuu AND type:"Feature Service"`; title regex
   `311|Citizen|Service Request|Permit|License|Deed|Transfer|Sale|Assess`.
3. Family survivors row-probed: `Building_Permits_Applications_view`,
   `Business_Licenses_view`, `Property_Sales_`, plus the joined point
   mirror `Building_Permits` and "Permits" (Wetlands Board) checked and
   set aside.
4. Watermark typing: Applications/Licenses watermarks are **text**
   (`YYYY/MM/DD`, `MM/DD/YYYY`) — window counts use string
   comparisons; Property Sales `Sales_Date` is date-typed (epoch ms).

Limits: VB 311 is a phone/app service (`vbgov.com/311` unreachable to
anonymous crawl); SeeClickFix returned no usable place payload. Police/
EMS/Fire "Calls for Service" layers are public-safety, not 311 family.
The joined point layer `Building_Permits` lags its source view
(max IssueDate 2026-07-31 vs view's 2026-08-21) — register the view.

---

## Headline table

| Family | Endpoint | Newest row (watermark) | Geocoding | Recent window | Tier |
|---|---|---|---|---|---|
| **PERMITS** | `services2.arcgis.com/CyVvlIiUfRBmMQuu/.../Building_Permits_Applications_view/FeatureServer/0` (table) | `IssueDate` = **2026-08-21** (text `YYYY/MM/DD`) | `StreetAddress`+`City`+`Zip` (+`GPIN`) → ADR 0004 | 7d **247**; 60d **4,790**; total **105,454** | **2** |
| **311** | none (VB 311 = phone/app; no CRM extract) | n/a | n/a | n/a | **3** |
| **SLA** | `.../Business_Licenses_view/FeatureServer/0` (table) | `Begin_Date` = **07/31/2026** (text `MM/DD/YYYY`) | `Business_Address` → ADR 0004 | 2026 YTD **77**; total **41,646** | **2** (annual-license cadence) |
| **DEEDS** | `.../Property_Sales_/FeatureServer/0` (points) | `Sales_Date` = **2026-08-10** | `Street_Address` (+`GPIN`) → ADR 0004 | 7d **0**; 60d **1,474**; 2026 **8,513**; total **594,771** | **2** (batch cadence caveat) |

---

## Permits — Tier 2 (register)

`Building_Permits_Applications_view` — 105,454 rows, table (no
geometry on the view).

- Columns: `PermitNumber` (`2026-BDCN-20445`, `2026-MECC-10572` —
  type prefix encodes permit family), `PermitType` (Building/
  Mechanical/…), `ConstructionType` (Commercial/Residential),
  `WorkType` (New/Addition/…), `ApplicationDate`, `IssueDate`,
  `FinalDate`, `Status` (`Active`), `WorkDesc`, `GPIN`,
  `StreetAddress`, `AddressUnit`, `City`, `State`, `Zip`,
  `CreatedBy`.
- Watermark **`IssueDate`**, text `YYYY/MM/DD` (ADR 0005:
  `watermark_type="text"`, `watermark_format="%Y/%m/%d"`). Newest
  **2026-08-21** (2026-MECC-10572, 1085 Virginia Beach Blvd). Daily
  cadence; the register is current to within 6 days of probe with a
  7-day count of 247 — live.
- **Set aside:** `Building_Permits` (202,601-row joined point mirror —
  parcels feature-to-point join; max `Building_Permits_IssueDate`
  **2026-07-31**, monthly refresh; and "Permits" =
  Wetlands Board Actions, wrong family). Register the **view**, not
  the mirror.
- Geocoding: address parts + `GPIN` (city parcel key). Set
  `needs_geocode=True`, `geocode_context="Virginia Beach, VA"`; GPIN
  join to parcels is the T1 upgrade path.
- id_keys: `["PermitNumber"]`. cadence 1d.

## SLA — Tier 2 (register)

`Business_Licenses_view` — 41,646 rows, table.

- Columns: `Begin_Date`, `Owner_Name`, `Trade_Name`,
  `Business_Address`, `Business_City/State/ZipCode(+_Ext)`,
  `Telephone` (**drop at ingest**), `Mailing_*` (drop), `NAICS`
  (`711320-01` — code + sub-code), `Business_Classification`.
- Watermark **`Begin_Date`**, text `MM/DD/YYYY` (ADR 0005
  `watermark_format="%m/%d/%Y"`). Newest **07/31/2026**; 2026 YTD 77;
  volume is annual-license trickle (renewal month + monthly new
  entrants) — register with documented annual-licensing cadence.
- Geocode: `Business_Address` + city/state/zip → ADR 0004.
- id_keys: `["Trade_Name","Owner_Name","Business_Address"]` (no
  license-number column exists — note in registration).
- PII: drop `Telephone` and mailing-address block at ingest.

## Deeds — Tier 2 (register)

`Property_Sales_` — **594,771** rows, point geometry.

- Columns: `GPIN`, `Street_Address`, `City`, `State`, `Zip_Code`,
  `Neighborhood`, `Land_Value`, `Improvement_Value`, `Total_Value`,
  `Sale_Price`, `Document_Number`, `Deed_Book`, `Deed_Page`,
  `Sales_Date`.
- Watermark **`Sales_Date`** (date-typed). Newest **2026-08-10**
  (2,335/2,333 Virginia Beach Blvd, $0 transfers — keep non-arms-
  length rows). 2026 YTD **8,513**; 60d **1,474** (~25/day); 7d **0**
  with the batch refresh landing every ~2–3 weeks. Same shape as the
  Memphis permits monthly-cadence precedent: register with a
  documented batch-cadence exception and re-probe ≤72 h before build;
  if no rows land by mid-September, treat as stalled.
- Geocode: native points exist on the layer (verified
  `esriGeometryPoint` service) + `Street_Address` fallback. Prefer
  `outSR=4326` geometry; ADR 0004 as supplement.
- id_keys: `["Document_Number","GPIN","Sales_Date"]` (doc numbers
  repeat across parcel splits).

## 311 — Tier 3

VB 311 is phone/app ("VB 311 Customer Service", `vbgov.com`); no CRM
extract published. Hub search `q=311` → 0; `q=request` → FOIA Requests
+ Police Calls for Service (public-safety, not 311). SeeClickFix not a
candidate (precedent). Do not register.

---

## Hostnames tried (negatives)

| Surface | Result |
|---|---|
| `data.vbgov.com` | DNS fail |
| `data.virginiabeach.gov` | Hub site live (the real portal) |
| `vbgov.com/311` pages | unreachable to anonymous crawl |
| Socrata discovery / CKAN | absent |

## Registration sketch (summary)

All three on `platform="arcgis"`, base
`https://services2.arcgis.com/CyVvlIiUfRBmMQuu/arcgis/rest/services/`:
- `city_registry.py` `VIRGINIA_BEACH.datasets[FeedType.PERMITS]` →
  `Building_Permits_Applications_view/FeatureServer/0`, watermark
  `IssueDate` text `%Y/%m/%d`, id_keys `["PermitNumber"]`,
  `needs_geocode=True`.
- `FeedType.SLA` → `Business_Licenses_view/FeatureServer/0`, watermark
  `Begin_Date` text `%m/%d/%Y`, drop `Telephone`/mailing block.
- `FeedType.DEEDS` → `Property_Sales_/FeatureServer/0`, watermark
  `Sales_Date` (date), `expected_cadence_days` 14 with batch note.
- 311 → `get_dataset()` raises.

Re-probe all three watermarks ≤72 h before the implementation wave.
Stamp: 2026-08-28.
