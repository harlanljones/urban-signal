# Wave 3 Phase-0 probe — Anchorage, AK (Municipality of Anchorage)

**Probe stamp: 2026-08-27.** Every host, dataset, watermark, and row below was
read live that day. AGOL `item.modified` is a label only; freshness evidence
is newest-row-by-watermark.

Linear: **US-330**. Ticket hint was Open Data Portal (`opendata.muni.org`).

Success criterion (Wave 3 / ADR 0004): live **and** (native geometry **or**
address-geocodable). Tiers: **1** live + native geocode; **2** live +
address-only; **3** stale / absent / wrong family.

## Platform

| Host | What it is | Probe |
|---|---|---|
| `opendata.muni.org` | **Apache directory listing** — not a Hub, not CKAN, no API | title `opendata.muni.org - /` |
| `www.arcgis.com` AGOL orgs `MOA_HostedServices` (212 items) + `MOAGIS` (505) | **the real open-data surface** (hosted FeatureServers on `services2.arcgis.com/Ce3DhLRthdwbHlfF`) | live |
| `gis.muni.org` | Cloudflare-fronted web (IPv6 only resolved); `/arcgis/rest` + `/server/rest` **404** | no REST directory |
| `geo.akrr.com` | Alaska Railroad Corporation GIS (`SDELayers/Railroad_Boundary_Public/FeatureServer/1` = `DeedForPublish` — **ARR land deeds, not MOA**) | wrong owner/family |

## Summary

| Family | Dataset | Newest watermark | Geocode | 7d / 60d | Tier |
|---|---|---|---|---|---|
| **PERMITS** | none (only `MJ_Permits_Hosted`, frozen 2023) | `Approved_to_Operate` max **2023-04-24** | — | — | **3** |
| **311** | none on AGOL orgs | — | — | — | **3** |
| **SLA** | none (MJ permits are the only license-adjacent feed and are frozen) | — | — | — | **3** |
| **DEEDS** | `PropertyInformation_Hosted/FeatureServer/0` (assessor property file with `Deed_Date`/`Deed_Book`/`Deed_Page`) | `Deed_Date` max non-future **2026-08-25**; `PUBDATE` **2026-08-26 23:23** (daily publish) | polygon geometry (native) | **106 / 1,371** non-future | **1** |

**Wave-3-ready: yes** (DEEDS Tier 1 only).

## Deeds — Tier 1 (register)

### `PropertyInformation_Hosted` layer 0

- **URL:** `https://services2.arcgis.com/Ce3DhLRthdwbHlfF/arcgis/rest/services/PropertyInformation_Hosted/FeatureServer/0`
- **Rows:** 99,770 parcels; `Deed_Date` populated on **94,052** (1936 →
  2026 + sentinels). Polygon geometry (`esriGeometryPolygon`).
- **Watermark:** `Deed_Date`. Max **non-future** value **2026-08-25**
  (probe-day minus 2). **7d=106**, **60d=1,371** (non-future). Only **5**
  future sentinels (max 2035-03-03) — **exclude `Deed_Date > probe day`**
  from the high watermark.
- **Publish vintage:** `PUBDATE` max **2026-08-26 23:23 UTC** — the file is
  republished daily; deed-date rows track current recorded deeds.
- **Columns (selected):** `Parcel_ID`, `Owner_Name`, `Owner_Line_1..4`,
  `Parcel_Address`, `Legal_Description`, `Appraisal_Year`,
  `Appraised_Land/Building/Total_Value`, `Taxable_Value`, `Deed_Book`,
  `Deed_Page`, `Deed_Date`, `Zoning_District`, `Tax_District`, `YearBuilt`,
  `Total_Living_Units`, `Lot_Size`, `GIS_Site_Street_*`, `Shape__Area`,
  `Shape__Length`.
- **Grain caveat:** this is the assessor's **last-deed-per-parcel** property
  file (one row per parcel), not an append-only transaction log. Same grain
  as the live parcel-deed sources used elsewhere; the daily `PUBDATE` +
  non-future `Deed_Date` freshness makes it registrable. `Deed_Book` year
  matches the recording year (2025/2026 books on newest real rows).
- **Id keys:** `Parcel_ID` (+ `GIS_ParcelNum11`).
- **Geocoding:** native polygon; site-address parts present
  (`GIS_Site_Street_Number/Name/Pre/Suf/Type`, `GIS_Site_City/State/Zipcode`).

## Permits — Tier 3

- `MJ_Permits_Hosted/FeatureServer/0` (`services2.arcgis.com/Ce3DhLRthdwbHlfF`):
  211 rows; `Assembly_Approval_Date` / `Approved_to_Operate` max **2023-04-24**.
  Marijuana local-permit snapshot, frozen 3+ years. Do not register.
- No building-permit feed exists on either AGOL org (title search `permit`
  across `MOA_HostedServices` → 1 hit = MJ above). MOA Development Services
  has no anonymous bulk REST found.

## 311 — Tier 3

No 311/service-request dataset on either org. Anchorage 311 is an app with no
public bulk/Open311 endpoint discovered (`311.muni.org` DNS-fail).

## SLA — Tier 3

No business-license feed. MJ local permits (frozen) are the only
license-adjacent surface.

## Registration contract (`anchorage`)

| Feed | Dataset (watermark) | Platform | field_map budget | Quirks tests must pin |
|---|---|---|---|---|
| DEEDS | `PropertyInformation_Hosted/FeatureServer/0` (`Deed_Date`) | arcgis | ~10 | last-deed-per-parcel snapshot grain; exclude future `Deed_Date` sentinels (5 rows); polygon geometry `outSR=4326`; daily `PUBDATE`; `get_dataset` raises for PERMITS / 311 / SLA |

Suggested spec payload (leaf `cities/anchorage.py`, not applied this ticket):

```
DEEDS
  endpoint: https://services2.arcgis.com/Ce3DhLRthdwbHlfF/arcgis/rest/services/PropertyInformation_Hosted/FeatureServer/0
  platform: arcgis
  watermark_col: Deed_Date
  watermark_exclude_future: true
  id_keys: [Parcel_ID]
  extra:
    expected_cadence_days: 1
    max_record_count: 2000
    field_map:
      parcel_id: [Parcel_ID]
      deed_date: [Deed_Date]
      owner: [Owner_Name]
      address_street: [GIS_Site_Street_Number, GIS_Site_Street_Pre, GIS_Site_Street_Name, GIS_Site_Street_Suf, GIS_Site_Street_Type]
      zipcode: [GIS_Site_Zipcode]
      land_value: [Appraised_Land_Value]
      building_value: [Appraised_Building_Value]
      # geometry polygon -> centroid
```
